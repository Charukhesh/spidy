"""AI Vision Client for Athena Desktop Companion.

Supports:
1. Google Gemini (aistudio.google.com) - gemini-3.5-flash (1,000,000 TPM Free Tier)
2. Groq Cloud (console.groq.com) - qwen/qwen3.8-27b
3. xAI Grok (console.x.ai) - grok-2-vision-1212

Automatically detects provider based on key format (AQ./AIza vs gsk_ vs xai-),
preserves coordinate pointing with [POINT:x,y:label] element grounding.
"""

import re
import json
import base64
import logging
from dataclasses import dataclass
from typing import List, Optional, Tuple, Dict, Any
import httpx

from athena.screen_capture import ScreenCaptureResult
from athena.config import get_api_key, load_config

logger = logging.getLogger("athena.ai_client")

ATHENA_SYSTEM_PROMPT = """you're athena, a perceptive and friendly always-on companion that lives on the user's desktop. the user just spoke to you via push-to-talk and you can see their screen(s). your reply will be spoken aloud via text-to-speech, so write the way you'd actually talk. this is an ongoing conversation — you remember everything they've said before.

rules:
- default to one or two sentences. be direct and dense. BUT if the user asks you to explain more, go deeper, or elaborate, then go all out — give a thorough, detailed explanation with no length limit.
- all lowercase, casual, warm. no emojis.
- write for the ear, not the eye. short sentences. no lists, bullet points, markdown, or formatting — just natural speech.
- don't use abbreviations or symbols that sound weird read aloud. write "for example" not "e.g.", spell out small numbers.
- if the user's question relates to what's on their screen, reference specific things you see.
- if the screenshot doesn't seem relevant to their question, just answer the question directly.
- you can help with anything — coding, writing, general knowledge, brainstorming.
- never say "simply" or "just".
- don't read out code verbatim. describe what the code does or what needs to change conversationally.
- focus on giving a thorough, useful explanation. don't end with simple yes/no questions like "want me to explain more?" or "should i show you?" — those are dead ends that force the user to just say yes.
- instead, when it fits naturally, end by planting a seed — mention something bigger or more ambitious they could try, a related concept that goes deeper, or a next-level technique that builds on what you just explained. make it something worth coming back for, not a question they'd just nod to. it's okay to not end with anything extra if the answer is complete on its own.
- if you receive multiple screen images, the one labeled "primary focus" is where the cursor is — prioritize that one but reference others if relevant.

element pointing:
you have a small glowing triangle cursor that can fly to and point at things on screen. use it whenever pointing would genuinely help the user — if they're asking how to do something, looking for a menu, trying to find a button, or need help navigating an app, point at the relevant element. err on the side of pointing rather than not pointing, because it makes your help way more useful and concrete.

don't point at things when it would be pointless — like if the user asks a general knowledge question, or the conversation has nothing to do with what's on screen, or you'd just be pointing at something obvious they're already looking at. but if there's a specific UI element, menu, button, or area on screen that's relevant to what you're helping with, point at it.

when you point, append a coordinate tag at the very end of your response, AFTER your spoken text. the screenshot images are labeled with their pixel dimensions. use those dimensions as the coordinate space. the origin (0,0) is the top-left corner of the image. x increases rightward, y increases downward.

format: [POINT:x,y:label] where x,y are integer pixel coordinates in the screenshot's coordinate space, and label is a short 1-3 word description of the element (like "search bar" or "save button"). if the element is on the cursor's screen you can omit the screen number. if the element is on a DIFFERENT screen, append :screenN where N is the screen number from the image label (e.g. :screen2). this is important — without the screen number, the cursor will point at the wrong place.

if pointing wouldn't help, append [POINT:none].

examples:
- user asks how to save: "click that blue save button in the top toolbar to keep your changes. [POINT:850,38:save button]"
- user asks what html is: "html stands for hypertext markup language, basically the skeleton of every website. curious how it hooks into the css you're editing? [POINT:none]"
- user asks where settings is: "open up settings using that gear icon right down in the bottom left. [POINT:48,980:settings gear]"
"""

# Backwards compatibility alias
OFFICIAL_CLICKY_SYSTEM_PROMPT = ATHENA_SYSTEM_PROMPT


@dataclass
class PointingTarget:
    x: int
    y: int
    label: str
    screen_number: int = 1


@dataclass
class AIVisionResponse:
    full_text: str
    spoken_text: str
    point_target: Optional[PointingTarget] = None


# Backward compatibility alias
GrokResponse = AIVisionResponse


class AIVisionClient:
    """Universal multimodal AI vision client for Athena."""

    def __init__(self, api_key: Optional[str] = None, model: Optional[str] = None):
        cfg = load_config()
        self.api_key = api_key or get_api_key()
        self.configured_model = model or cfg.get("model") or cfg.get("grok_model", "auto")
        self.conversation_history: List[Tuple[str, str]] = []  # [(user, assistant)]
        self.history_limit = cfg.get("conversation_history_limit", 10)

    def _resolve_provider_and_model(self) -> Tuple[str, str, str]:
        """Detect provider, endpoint URL, and compatible model based on API key."""
        key = self.api_key.strip()

        # 1. Google Gemini (aistudio.google.com) -> starts with 'AQ.' or 'AIza'
        if key.startswith("AQ.") or key.startswith("AIza") or "gemini" in self.configured_model.lower():
            endpoint = "https://generativelanguage.googleapis.com/v1beta/openai/chat/completions"
            model = (
                self.configured_model
                if self.configured_model not in (
                    "auto",
                    "grok-2-vision-1212",
                    "grok-vision-beta",
                    "llama-3.2-11b-vision-preview",
                    "llama-3.2-90b-vision-preview",
                    "qwen/qwen3.8-27b",
                    "gemini-2.0-flash",
                    "gemini-2.5-flash",
                )
                else "gemini-3.5-flash"
            )
            return "Google Gemini (aistudio.google.com)", endpoint, model

        # 2. Groq (console.groq.com) -> starts with 'gsk_'
        if key.startswith("gsk_"):
            endpoint = "https://api.groq.com/openai/v1/chat/completions"
            model = (
                self.configured_model
                if self.configured_model not in (
                    "auto",
                    "grok-2-vision-1212",
                    "grok-vision-beta",
                    "llama-3.2-11b-vision-preview",
                    "llama-3.2-90b-vision-preview",
                    "gemini-2.0-flash",
                    "gemini-1.5-flash",
                    "gemini-3.5-flash",
                )
                else "qwen/qwen3.8-27b"
            )
            return "Groq (console.groq.com)", endpoint, model

        # 3. xAI Grok (console.x.ai) -> starts with 'xai-'
        endpoint = "https://api.x.ai/v1/chat/completions"
        model = (
            self.configured_model
            if self.configured_model != "auto"
            else "grok-2-vision-1212"
        )
        return "xAI Grok (console.x.ai)", endpoint, model

    def set_api_key(self, key: str):
        self.api_key = key.strip()

    def clear_history(self):
        self.conversation_history.clear()

    def test_connection(self) -> Tuple[bool, str]:
        """Test current API key and provider/model connectivity."""
        if not self.api_key or self.api_key.startswith("YOUR_") or "PLACEHOLDER" in self.api_key.upper():
            return False, "Please enter your actual API key first (replace placeholder)."

        provider_name, endpoint_url, active_model = self._resolve_provider_and_model()
        headers = {
            "Authorization": f"Bearer {self.api_key.strip()}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": active_model,
            "messages": [{"role": "user", "content": "ping"}],
            "max_tokens": 10,
        }

        try:
            with httpx.Client(timeout=15.0) as client:
                res = client.post(endpoint_url, headers=headers, json=payload)
                if res.status_code == 200:
                    return True, f"Connected successfully to {provider_name} using model {active_model}!"
                elif res.status_code == 401:
                    return False, f"401 Unauthorized: Invalid API key for {provider_name}."
                else:
                    return False, f"HTTP {res.status_code}: {res.text[:200]}"
        except Exception as e:
            return False, f"Connection error: {str(e)}"

    def query(
        self,
        transcript: str,
        screen_captures: List[ScreenCaptureResult],
    ) -> AIVisionResponse:
        """Send user transcript and screen capture(s) to multimodal vision LLM."""
        if not self.api_key or self.api_key.startswith("YOUR_") or "PLACEHOLDER" in self.api_key.upper():
            return AIVisionResponse(
                full_text="please enter your api key in the athena settings first [POINT:none]",
                spoken_text="please enter your api key in the athena settings first",
            )

        provider_name, endpoint_url, active_model = self._resolve_provider_and_model()
        logger.info(f"Using Provider: {provider_name} | Endpoint: {endpoint_url} | Model: {active_model}")

        # Build message contents
        user_content: List[Dict[str, Any]] = [
            {"type": "text", "text": transcript}
        ]

        # Attach screenshots with image dimension labels
        for cap in screen_captures:
            b64_img = base64.b64encode(cap.image_bytes).decode("utf-8")
            focus_label = "primary focus" if cap.is_primary else f"screen {cap.display_index}"
            dimension_label = f"Screenshot {focus_label} (image dimensions: {cap.width}x{cap.height} pixels):"

            user_content.append({"type": "text", "text": dimension_label})
            user_content.append({
                "type": "image_url",
                "image_url": {
                    "url": f"data:image/jpeg;base64,{b64_img}",
                }
            })

        # Assemble full conversation history
        messages: List[Dict[str, Any]] = [
            {"role": "system", "content": ATHENA_SYSTEM_PROMPT}
        ]

        for prev_user, prev_assistant in self.conversation_history[-self.history_limit:]:
            messages.append({"role": "user", "content": prev_user})
            messages.append({"role": "assistant", "content": prev_assistant})

        messages.append({"role": "user", "content": user_content})

        headers = {
            "Authorization": f"Bearer {self.api_key.strip()}",
            "Content-Type": "application/json",
        }

        payload = {
            "model": active_model,
            "messages": messages,
            "temperature": 0.5,
            "max_tokens": 1000,
        }

        try:
            with httpx.Client(timeout=30.0) as client:
                response = client.post(endpoint_url, headers=headers, json=payload)
                response.raise_for_status()
                data = response.json()
                raw_reply = data["choices"][0]["message"]["content"]

                # Parse pointing coordinates
                spoken_text, point_target = self.parse_pointing_coordinates(raw_reply)

                # Save exchange in history
                self.conversation_history.append((transcript, spoken_text))
                if len(self.conversation_history) > self.history_limit:
                    self.conversation_history.pop(0)

                return AIVisionResponse(
                    full_text=raw_reply,
                    spoken_text=spoken_text,
                    point_target=point_target,
                )

        except httpx.HTTPStatusError as e:
            err_body = e.response.text
            logger.error(f"{provider_name} API HTTP error {e.response.status_code}: {err_body}")

            if e.response.status_code == 401:
                err_msg = f"invalid api key for {provider_name}. please check your key in settings"
            elif "model_not_found" in err_body or "deactivated" in err_body or "no longer available" in err_body:
                err_msg = f"model {active_model} is unavailable on {provider_name}. please select another model"
            else:
                err_msg = f"api error {e.response.status_code}. check your network or key"

            return AIVisionResponse(full_text=err_msg, spoken_text=err_msg)
        except Exception as e:
            logger.error(f"AI client request error: {e}")
            err_msg = "sorry, i ran into an issue connecting to the vision service"
            return AIVisionResponse(full_text=err_msg, spoken_text=err_msg)

    @staticmethod
    def parse_pointing_coordinates(response_text: str) -> Tuple[str, Optional[PointingTarget]]:
        """Parse [POINT:x,y:label] or [POINT:none] tag from reply text."""
        point_pattern = re.compile(
            r"\[POINT:\s*(\d+)\s*,\s*(\d+)\s*:\s*([^:\]]+)(?::screen(\d+))?\s*\]",
            re.IGNORECASE,
        )

        match = point_pattern.search(response_text)
        if match:
            x = int(match.group(1))
            y = int(match.group(2))
            label = match.group(3).strip()
            screen_num = int(match.group(4)) if match.group(4) else 1

            spoken = point_pattern.sub("", response_text).strip()
            spoken = re.sub(r"\[POINT:\s*none\s*\]", "", spoken, flags=re.IGNORECASE).strip()

            return spoken, PointingTarget(x=x, y=y, label=label, screen_number=screen_num)

        spoken = re.sub(r"\[POINT:\s*none\s*\]", "", response_text, flags=re.IGNORECASE).strip()
        return spoken, None


# Backward compatibility alias
GrokClient = AIVisionClient

