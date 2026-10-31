"""AI Vision Client for Athena Desktop Companion.

Supports:
1. Google Gemini (aistudio.google.com) - gemini-3.5-flash-lite / gemini-3.5-flash (1,000,000 TPM Free Tier)
2. Groq Cloud (console.groq.com) - qwen/qwen3.8-27b
3. xAI Grok (console.x.ai) - grok-2-vision-1212

Automatically detects provider based on key format (AQ./AIza vs gsk_ vs xai-),
preserves coordinate pointing with [POINT:x,y:label], visual bounding box drawing
[DRAW:box,x1,y1,x2,y2:label], circle highlighting [DRAW:circle,cx,cy,r:label],
guide arrows [DRAW:arrow,x1,y1,x2,y2:label], and step simulation [SIMULATE:x1,y1->x2,y2:label].
"""

import re
import json
import base64
import logging
from dataclasses import dataclass, field
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
- if [ACTIVE APPLICATION CONTEXT] is provided, use it to know what software, tab, or file the user has open. If they have code or text highlighted, prioritize explaining or fixing that selected text.
- if the screenshot doesn't seem relevant to their question, just answer the question directly.
- you can help with anything — coding, writing, general knowledge, brainstorming.
- never say "simply" or "just".
- don't read out code verbatim. describe what the code does or what needs to change conversationally.
- focus on giving a thorough, useful explanation. don't end with simple yes/no questions like "want me to explain more?" or "should i show you?" — those are dead ends that force the user to just say yes.
- instead, when it fits naturally, end by planting a seed — mention something bigger or more ambitious they could try, a related concept that goes deeper, or a next-level technique that builds on what you just explained. make it something worth coming back for, not a question they'd just nod to. it's okay to not end with anything extra if the answer is complete on its own.
- if you receive multiple screen images, the one labeled "primary focus" is where the cursor is — prioritize that one but reference others if relevant.

visual assistance (pointing, drawing, simulation):
you have a small glowing triangle cursor and visual overlay engine that can point at things, draw bounding boxes, highlight circles, arrows, and simulate workflow paths on screen. use them whenever visual assistance would genuinely help the user navigate, debug, or learn:
1. Pointing:
   Fly your glowing blue cursor to point at a specific UI element: [POINT:x,y:label] or [POINT:x,y:label:screenN]
2. Visual Drawing & Highlighting:
   To draw a glowing box around a button, error, code, or area: [DRAW:box,x1,y1,x2,y2:label]
   To draw a glowing circle around an icon or focal point: [DRAW:circle,x,y,radius:label]
   To draw a directional guide arrow pointing towards an element: [DRAW:arrow,startX,startY,targetX,targetY:label]
   To write a floating note next to an element: [WRITE:x,y:note text]
3. Workflow Simulation:
   If the user asks you to simulate, demonstrate, or show steps for how to perform an action:
   [SIMULATE:x1,y1->x2,y2(->x3,y3...):workflow label]
   This draws a connected numbered path (①, ②, ③) guiding them through the exact sequence of clicks or interactions.

coordinate space:
coordinates are normalized to a 0..1000 integer coordinate space where (0,0) is top-left and (1000,1000) is bottom-right of the screenshot image.
append your tag(s) at the very end of your response, AFTER your spoken text.
if pointing or drawing wouldn't help (e.g. general knowledge question), append [POINT:none].

examples:
- user asks how to save: "click that blue save button in the top toolbar to keep your changes. [POINT:495,37:save button]"
- user asks to highlight an error: "that syntax error is happening right here in your import statement. [DRAW:box,120,340,580,380:syntax error]"
- user asks how to add a file: "first click the new file button up top, then name it in the sidebar. [SIMULATE:48,110->160,240:add new file]"
- user asks what html is: "html stands for hypertext markup language, basically the skeleton of every website. curious how it hooks into the css you're editing? [POINT:none]"
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
class VisualDrawing:
    kind: str  # "box", "circle", "arrow", "simulate", "text"
    coords: List[int]  # [x1, y1, x2, y2] or [cx, cy, r] or [x1, y1, x2, y2, ...]
    label: str
    screen_number: int = 1


@dataclass
class AIVisionResponse:
    full_text: str
    spoken_text: str
    point_target: Optional[PointingTarget] = None
    drawings: List[VisualDrawing] = field(default_factory=list)


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
            # Support gemini-3.5-flash-lite as the robust 1,000,000 TPM default
            if self.configured_model in ("gemini-3.5-flash", "gemini-3.5-flash-lite", "gemini-3.1-flash-lite"):
                model = self.configured_model
            else:
                model = "gemini-3.5-flash-lite"
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
            "messages": [{"role": "user", "content": "respond with pong"}],
            "max_tokens": 10,
        }

        try:
            with httpx.Client(timeout=10.0) as client:
                res = client.post(endpoint_url, headers=headers, json=payload)
                res.raise_for_status()
                return True, f"Successfully connected to {provider_name} ({active_model})."
        except httpx.HTTPStatusError as e:
            return False, f"HTTP {e.response.status_code}: {e.response.text[:200]}"
        except Exception as e:
            return False, f"Connection error: {e}"

    def query(
        self,
        transcript: str,
        screen_captures: List[ScreenCaptureResult],
        active_context: Optional[str] = None,
    ) -> AIVisionResponse:
        """Send user transcript, active window context, and screen capture(s) to multimodal vision LLM."""
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

        # Inject Active Application & Selected Text Context if available
        if active_context and active_context.strip():
            user_content.append({"type": "text", "text": active_context.strip()})

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
            "temperature": 0.4,
            "max_tokens": 450,
        }

        try:
            if not hasattr(self, "_http_client") or self._http_client.is_closed:
                self._http_client = httpx.Client(timeout=25.0)

            response = self._http_client.post(endpoint_url, headers=headers, json=payload)
            response.raise_for_status()
            data = response.json()
            raw_reply = data["choices"][0]["message"].get("content", "")

            # Parse pointing coordinates and visual drawings
            spoken_text, point_target, drawings = self.parse_visual_tags(raw_reply)

            # Map normalized [0..1000] coordinates to screenshot pixel resolution
            point_target, drawings = self._scale_to_capture_pixels(point_target, drawings, screen_captures)

            # Save exchange in history
            self.conversation_history.append((transcript, spoken_text))
            if len(self.conversation_history) > self.history_limit:
                self.conversation_history.pop(0)

            return AIVisionResponse(
                full_text=raw_reply,
                spoken_text=spoken_text,
                point_target=point_target,
                drawings=drawings,
            )

        except httpx.HTTPStatusError as e:
            err_body = e.response.text
            logger.error(f"{provider_name} API HTTP error {e.response.status_code}: {err_body}")

            if e.response.status_code == 401:
                err_msg = f"invalid api key for {provider_name}. please check your key in settings"
            elif "model_not_found" in err_body or "deactivated" in err_body or "no longer available" in err_body:
                err_msg = f"model {active_model} is unavailable on {provider_name}. please select another model"
            elif e.response.status_code == 429:
                err_msg = "api rate limit exceeded. please wait a moment before trying again"
            else:
                err_msg = f"api error {e.response.status_code}. check your network or key"

            return AIVisionResponse(full_text=err_msg, spoken_text=err_msg)
        except Exception as e:
            logger.error(f"AI client request error: {e}")
            err_msg = "sorry, i ran into an issue connecting to the vision service"
            return AIVisionResponse(full_text=err_msg, spoken_text=err_msg)

    def _scale_to_capture_pixels(
        self,
        point_target: Optional[PointingTarget],
        drawings: List[VisualDrawing],
        screen_captures: List[ScreenCaptureResult],
    ) -> Tuple[Optional[PointingTarget], List[VisualDrawing]]:
        """Scale normalized [0..1000] coordinates to physical screenshot pixel dimensions."""
        if not screen_captures:
            return point_target, drawings

        # Scale point_target
        if point_target:
            cap = screen_captures[0]
            if 1 <= point_target.screen_number <= len(screen_captures):
                cap = screen_captures[point_target.screen_number - 1]
            if cap.width > 1050 or cap.height > 1050:
                if 0 <= point_target.x <= 1000 and 0 <= point_target.y <= 1000:
                    scaled_x = int(round((point_target.x / 1000.0) * cap.width))
                    scaled_y = int(round((point_target.y / 1000.0) * cap.height))
                    point_target = PointingTarget(
                        x=scaled_x,
                        y=scaled_y,
                        label=point_target.label,
                        screen_number=point_target.screen_number,
                    )

        # Scale drawings
        scaled_drawings = []
        for d in drawings:
            cap = screen_captures[0]
            if 1 <= d.screen_number <= len(screen_captures):
                cap = screen_captures[d.screen_number - 1]

            if (cap.width > 1050 or cap.height > 1050) and all(0 <= c <= 1000 for c in d.coords):
                scaled_coords = []
                for i in range(0, len(d.coords), 2):
                    cx = d.coords[i]
                    cy = d.coords[i + 1] if i + 1 < len(d.coords) else 0
                    sx = int(round((cx / 1000.0) * cap.width))
                    sy = int(round((cy / 1000.0) * cap.height))
                    scaled_coords.extend([sx, sy])
                scaled_drawings.append(VisualDrawing(
                    kind=d.kind,
                    coords=scaled_coords,
                    label=d.label,
                    screen_number=d.screen_number,
                ))
            else:
                scaled_drawings.append(d)

        return point_target, scaled_drawings

    @classmethod
    def parse_pointing_coordinates(cls, response_text: str) -> Tuple[str, Optional[PointingTarget]]:
        """Backward-compatible pointing coordinate parser."""
        spoken, target, _ = cls.parse_visual_tags(response_text)
        return spoken, target

    @staticmethod
    def parse_visual_tags(response_text: str) -> Tuple[str, Optional[PointingTarget], List[VisualDrawing]]:
        """Parse [POINT:...], [DRAW:...], [SIMULATE:...], and [WRITE:...] tags from reply text."""
        spoken = response_text
        point_target: Optional[PointingTarget] = None
        drawings: List[VisualDrawing] = []

        # 1. Parse [POINT:x,y:label] or [POINT:x,y:label:screenN]
        point_pattern = re.compile(
            r"\[POINT:\s*(\d+)\s*,\s*(\d+)\s*[,:]\s*([^:,\]]+)(?:[,:]\s*screen(\d+))?\s*\]",
            re.IGNORECASE,
        )
        match_point = point_pattern.search(spoken)
        if match_point:
            x = int(match_point.group(1))
            y = int(match_point.group(2))
            label = match_point.group(3).strip()
            screen_num = int(match_point.group(4)) if match_point.group(4) else 1
            point_target = PointingTarget(x=x, y=y, label=label, screen_number=screen_num)
            spoken = point_pattern.sub("", spoken)

        # 2. Parse [DRAW:box,x1,y1,x2,y2:label(:screenN)]
        box_pattern = re.compile(
            r"\[DRAW:\s*box\s*,\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)\s*[,:]\s*([^:,\]]+)(?:[,:]\s*screen(\d+))?\s*\]",
            re.IGNORECASE,
        )
        for m in box_pattern.finditer(spoken):
            x1, y1, x2, y2 = int(m.group(1)), int(m.group(2)), int(m.group(3)), int(m.group(4))
            lbl = m.group(5).strip()
            s_num = int(m.group(6)) if m.group(6) else 1
            drawings.append(VisualDrawing(kind="box", coords=[x1, y1, x2, y2], label=lbl, screen_number=s_num))
        spoken = box_pattern.sub("", spoken)

        # 3. Parse [DRAW:circle,cx,cy,radius:label(:screenN)]
        circle_pattern = re.compile(
            r"\[DRAW:\s*circle\s*,\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)\s*[,:]\s*([^:,\]]+)(?:[,:]\s*screen(\d+))?\s*\]",
            re.IGNORECASE,
        )
        for m in circle_pattern.finditer(spoken):
            cx, cy, r = int(m.group(1)), int(m.group(2)), int(m.group(3))
            lbl = m.group(4).strip()
            s_num = int(m.group(5)) if m.group(5) else 1
            drawings.append(VisualDrawing(kind="circle", coords=[cx, cy, r], label=lbl, screen_number=s_num))
        spoken = circle_pattern.sub("", spoken)

        # 4. Parse [DRAW:arrow,x1,y1,x2,y2:label(:screenN)]
        arrow_pattern = re.compile(
            r"\[DRAW:\s*arrow\s*,\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)\s*[,:]\s*([^:,\]]+)(?:[,:]\s*screen(\d+))?\s*\]",
            re.IGNORECASE,
        )
        for m in arrow_pattern.finditer(spoken):
            x1, y1, x2, y2 = int(m.group(1)), int(m.group(2)), int(m.group(3)), int(m.group(4))
            lbl = m.group(5).strip()
            s_num = int(m.group(6)) if m.group(6) else 1
            drawings.append(VisualDrawing(kind="arrow", coords=[x1, y1, x2, y2], label=lbl, screen_number=s_num))
        spoken = arrow_pattern.sub("", spoken)

        # 5. Parse [SIMULATE:x1,y1->x2,y2(->x3,y3...):label]
        simulate_pattern = re.compile(
            r"\[SIMULATE:\s*([0-9,\->\s]+)\s*[,:]\s*([^:,\]]+)(?:[,:]\s*screen(\d+))?\s*\]",
            re.IGNORECASE,
        )
        for m in simulate_pattern.finditer(spoken):
            path_str = m.group(1).strip()
            lbl = m.group(2).strip()
            s_num = int(m.group(3)) if m.group(3) else 1
            # Parse nodes: "x1,y1->x2,y2"
            raw_coords = []
            for seg in path_str.split("->"):
                parts = seg.replace(" ", "").split(",")
                if len(parts) >= 2 and parts[0].isdigit() and parts[1].isdigit():
                    raw_coords.extend([int(parts[0]), int(parts[1])])
            if len(raw_coords) >= 4:
                drawings.append(VisualDrawing(kind="simulate", coords=raw_coords, label=lbl, screen_number=s_num))
        spoken = simulate_pattern.sub("", spoken)

        # 6. Parse [WRITE:x,y:text]
        write_pattern = re.compile(
            r"\[WRITE:\s*(\d+)\s*,\s*(\d+)\s*[,:]\s*([^:,\]]+)(?:[,:]\s*screen(\d+))?\s*\]",
            re.IGNORECASE,
        )
        for m in write_pattern.finditer(spoken):
            x, y = int(m.group(1)), int(m.group(2))
            txt = m.group(3).strip()
            s_num = int(m.group(4)) if m.group(4) else 1
            drawings.append(VisualDrawing(kind="text", coords=[x, y], label=txt, screen_number=s_num))
        spoken = write_pattern.sub("", spoken)

        # Remove negative control tag [POINT:none]
        spoken = re.sub(r"\[POINT:\s*none\s*\]", "", spoken, flags=re.IGNORECASE).strip()

        return spoken.strip(), point_target, drawings


# Backward compatibility alias
GrokClient = AIVisionClient