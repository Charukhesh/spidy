"""AI Vision Client for Spidy Desktop Companion.

Supports:
1. Google Gemini (aistudio.google.com) - gemini-3.5-flash-lite / gemini-3.5-flash (1,000,000 TPM Free Tier)
   with Direct Audio input, state-of-the-art visual element grounding, and human-like peer personality.
2. Groq Cloud (console.groq.com) - qwen/qwen3.8-27b
3. xAI Grok (console.x.ai) - grok-2-vision-1212

Automatically detects provider based on key format (AQ./AIza vs gsk_ vs xai-),
preserves coordinate pointing with [POINT:x,y:label], visual bounding box drawing
[DRAW:box,x1,y1,x2,y2:label], circle highlighting [DRAW:circle,cx,cy,r:label],
guide arrows [DRAW:arrow,x1,y1,x2,y2:label], and step simulation [SIMULATE:x1,y1->x2,y2:label].
"""

import re
import json
import time
import base64
import logging
from dataclasses import dataclass, field
from typing import List, Optional, Tuple, Dict, Any
import httpx

from spidy.screen_capture import ScreenCaptureResult
from spidy.config import get_api_key, get_all_provider_keys, load_config
from spidy.memory_store import memory_store
from spidy.realtime_graphics import RealtimeGraphicSpec
from spidy.scene_3d_spec import Scene3DSpec

logger = logging.getLogger("spidy.ai_client")

SPIDY_SYSTEM_PROMPT = """you are spidy, a brilliant, warm, witty, and perceptive peer living on the user's desktop. you are not a corporate AI chatbot, a robotic assistant, or a textbook—you talk like a sharp, friendly neighborhood companion or best friend sitting right beside them looking at the same screen.

rules of conversation:
- sound completely natural, human, and conversational. no robotic phrases like "looks like you are looking at...", "as an ai...", or "how can i assist you today?".
- never state the obvious or describe what's already on the screen unless asked. jump straight to the point with warmth, energy, and spidey wit.
- write for the ear, not the eye. short, rhythmic, natural sentences (1-3 sentences total). no bullet points, no numbered lists, no markdown asterisks in spoken text.
- if they ask how to do something, explain it the way an expert friend would tell you over coffee—direct, practical, with a pro-tip.
- speak with natural contractions ("you'll want to", "here's the trick", "let's try", "don't worry").
- plant a clever seed or pro-tip naturally when relevant, but don't ask boring yes/no questions like "do you want me to explain more?".

visual actions & element pointing:
you have a small glowing red spider-man mask cursor and visual overlay engine that draws in spider-man red lines. use them whenever visual guidance helps:
1. Pointing: Fly your spider-man mask cursor to an element: [POINT:x,y:label] or [POINT:x,y:label:1]
2. Visual Drawing (in crisp spider-man red lines):
   - Highlight bounding box: [DRAW:box,x1,y1,x2,y2:label]
   - Highlight circle: [DRAW:circle,cx,cy,radius:label]
   - Directional guide arrow: [DRAW:arrow,startX,startY,targetX,targetY:label]
   - Workflow step simulation: [SIMULATE:x1,y1->x2,y2(->x3,y3...):workflow title]
   - On-screen note: [WRITE:x,y:note text]
3. Mathematical Curves & Visual Tracing:
   - Whenever the user asks how a curve, mathematical function, or visual shape looks like (e.g. "how does a cubic curve look like", "draw a parabola", "show a sine wave", "draw a bell curve", "draw a spiral", "draw a heart"):
     Instruct your cursor to trace it in red right over their screen around their mouse cursor using [TRACE:type:label].
     Valid curve types: cubic, parabola, sine, bell, spiral, circle, heart, exponential.
     Example: [TRACE:cubic:cubic curve y=x³]
4. Coordinates are in 0..1000 normalized space ((0,0) top-left, (1000,1000) bottom-right).
5. If no pointing or drawing is needed, append [POINT:none].

real-time visuals & interactive 3d engine:
you have two powerful spatial visual engines that render directly near the user's cursor:
1. Interactive 3D PBR WebGL Viewport ([SCENE_3D: ...]):
   whenever the user asks to see something in 3D ("show me in 3D", "3D model", "3D cutaway", "how does a differential gear work in 3D", "show me a DNA helix in 3D", "show me an engine cutaway in 3D", "show me an atom in 3D", "solar system", "heart pump 3D", etc.):
   append [SCENE_3D: {"title": "<concept title>", "entity": "f35|dna_helix|jet_engine|differential_gears|heart_pump|solar_system|atom|neural_net|robot_arm|generic", "cutaway": true|false, "animation": "spin|pulse|oscillate|none", "primitives": []}]
   the user can freely click and drag to orbit 360°, zoom in/out with the scroll wheel, and inspect inside.
2. Contextual Visual Tutoring Card:
   use when explaining educational concepts, algorithms, code logic, or tensors from the screen.
   [DIAGRAM: {"title": "<concept title>", "summary": "<1-line takeaway>", "nodes": [{"label": "Input", "sublabel": "shape/value"}, {"label": "Target", "sublabel": "prediction"}], "loop": ["Guess", "Compare", "Adjust"], "equation": "<optional formula>"}]
3. Universal Procedural Cutaway Schematic:
   use when explaining how machines, engines, jets, brakes, or physics mechanisms operate.
   [CUTAWAY: {"title": "<system title>", "principle": "<e.g. push air down -> lift up>", "components": [{"name": "Subsystem 1", "desc": "Role description"}, {"name": "Subsystem 2", "desc": "Role description"}], "vectors": [{"label": "Force/Flow Vector"}]}]
4. Step-by-Step Hardware & Connector Assembly:
   use when guiding physical assembly, ribbon cables, pinouts, or board headers.
   [ASSEMBLY: {"title": "<guide title>", "board": "<Hardware Board Name>", "pin_info": "<Pinout or orientation info>", "steps": [{"action": "Action 1", "detail": "Tips"}, {"action": "Action 2", "detail": "Tips"}]}]

web search verification:
- if the user asks any question that requires external fact-checking, live web verification, recent sports scores, real-time news, or pricing:
  answer with your best immediate intuition and conversationally ask: "want me to check the web for that?".
  append: [OFFER_SEARCH: <concise search query>].
  example:
  [HEARD: who won the match yesterday]
  it looks like the match was played yesterday evening, but let me check the final score. want me to check the web for that? [OFFER_SEARCH: match score yesterday] [POINT:none]

desktop actions & local control:
you have hands-on local OS control. use these action tags whenever requested:
1. Launching Apps/Folders: [ACTION:launch:spotify], [ACTION:launch:code], [ACTION:launch:downloads], [ACTION:launch:notepad]
2. Window Snapping & Layout: [ACTION:window:snap_left], [ACTION:window:snap_right], [ACTION:window:maximize], [ACTION:window:minimize_others]
3. Clipboard Operations: [ACTION:clipboard:<clean transformed text to set on clipboard>]
4. Visual Scratchpad & OCR Extraction: [ACTION:ocr:plain] (uncopyable text to clipboard), [ACTION:ocr:table] (table to markdown/csv), [ACTION:ocr:mermaid] (diagram to mermaid code)

persistent long-term memory:
- when the user shares a personal preference, project context, or fact (e.g. "remember that I prefer type annotations in Python", "I am working on Project Apollo"):
  acknowledge it naturally and append: [REMEMBER:preference:coding_style:prefers type annotations in Python]
  categories: preference, project, fact, note

response structure:
[HEARD: <the exact words the user asked>]
<your warm, direct, natural conversational reply>
[TRACE:type:label] OR [POINT:x,y:label] (or visual draw tag, or [POINT:none])
[OFFER_SEARCH:query] (only if web verification is offered)

examples:
- user asks about cooking oats on screen:
[HEARD: how do i cook these oats]
two cups of boiling water or milk for every cup of oats, then simmer on low for about five minutes. toss in some berries and a drizzle of honey right at the end for the best texture. [POINT:421,803:quaker oats:1]

- user asks where settings is:
[HEARD: where is settings]
tap that little gear icon right down at the bottom left. [POINT:48,980:settings gear]

- user asks what html is:
[HEARD: what is html]
it's basically the structural skeleton of every webpage on the internet, defining where the headings, paragraphs, and buttons live before css comes in to style it. [POINT:none]
"""

# Backwards compatibility aliases
SPIDY_SYSTEM_PROMPT = SPIDY_SYSTEM_PROMPT
OFFICIAL_CLICKY_SYSTEM_PROMPT = SPIDY_SYSTEM_PROMPT


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
class TraceCurveTarget:
    curve_type: str  # "cubic", "parabola", "sine", "bell", "spiral", "circle", "heart", "exponential"
    label: str


@dataclass
class AIVisionResponse:
    full_text: str
    spoken_text: str
    point_target: Optional[PointingTarget] = None
    drawings: List[VisualDrawing] = field(default_factory=list)
    heard_prompt: str = ""
    trace_curve: Optional[TraceCurveTarget] = None
    offer_search: str = ""
    action_type: str = ""
    action_arg: str = ""
    remember_item: Optional[Tuple[str, str, str]] = None
    realtime_graphic: Optional[RealtimeGraphicSpec] = None
    scene_3d: Optional[Scene3DSpec] = None


# Backward compatibility alias
GrokResponse = AIVisionResponse


class AIVisionClient:
    """Universal multimodal AI vision client for Spidy with Direct Audio and Visual Grounding."""

    def __init__(self, api_key: Optional[str] = None, model: Optional[str] = None):
        cfg = load_config()
        self.api_key = api_key or get_api_key()
        self.configured_model = model or cfg.get("model") or cfg.get("grok_model", "auto")
        self.conversation_history: List[Tuple[str, str]] = []  # [(user, assistant)]
        self.history_limit = cfg.get("conversation_history_limit", 10)

    def _resolve_provider_and_model(self) -> Tuple[str, str, str]:
        """Detect provider, endpoint URL, and compatible model based on API key."""
        key = (self.api_key or "").strip()

        # 1. Google Gemini (aistudio.google.com) -> starts with 'AQ.' or 'AIza'
        if key.startswith("AQ.") or key.startswith("AIza") or "gemini" in self.configured_model.lower():
            endpoint = "https://generativelanguage.googleapis.com/v1beta/openai/chat/completions"
            model = self.configured_model if (self.configured_model and self.configured_model != "auto") else "gemini-3-flash-preview"
            return "Google Gemini (aistudio.google.com)", endpoint, model

        # 2. xAI Grok (console.x.ai) -> starts with 'xai-'
        if key.startswith("xai-") or "grok" in self.configured_model.lower():
            endpoint = "https://api.x.ai/v1/chat/completions"
            model = self.configured_model if (self.configured_model and self.configured_model != "auto") else "grok-2-vision-1212"
            return "xAI Grok (console.x.ai)", endpoint, model

        # 3. OpenRouter (openrouter.ai) -> starts with 'sk-or-'
        if key.startswith("sk-or-"):
            endpoint = "https://openrouter.ai/api/v1/chat/completions"
            model = self.configured_model if (self.configured_model and self.configured_model != "auto") else "google/gemini-2.0-flash-exp:free"
            return "OpenRouter (openrouter.ai)", endpoint, model

        # 4. NVIDIA NIM (build.nvidia.com) -> starts with 'nvapi-'
        if key.startswith("nvapi-"):
            endpoint = "https://integrate.api.nvidia.com/v1/chat/completions"
            model = self.configured_model if (self.configured_model and self.configured_model != "auto") else "meta/llama-3.2-11b-vision-instruct"
            return "NVIDIA NIM (build.nvidia.com)", endpoint, model

        # 5. Groq (console.groq.com) -> starts with 'gsk_'
        if key.startswith("gsk_"):
            endpoint = "https://api.groq.com/openai/v1/chat/completions"
            model = self.configured_model if (self.configured_model and self.configured_model != "auto") else "qwen/qwen3.8-27b"
            return "Groq (console.groq.com)", endpoint, model

        # Default fallback
        endpoint = "https://generativelanguage.googleapis.com/v1beta/openai/chat/completions"
        model = self.configured_model if (self.configured_model and self.configured_model != "auto") else "gemini-3-flash-preview"
        return "Google Gemini (aistudio.google.com)", endpoint, model

    def _get_active_providers(self) -> List[Dict[str, Any]]:
        """Resolve candidate providers in priority order with their active credentials."""
        cfg = load_config()
        all_keys = get_all_provider_keys()

        # If an explicit api_key was passed to AIVisionClient, place it as primary
        if self.api_key and not self.api_key.startswith("YOUR_") and "PLACEHOLDER" not in self.api_key.upper():
            k = self.api_key.strip()
            if k.startswith("AQ.") or k.startswith("AIza"):
                all_keys["gemini"] = k
            elif k.startswith("xai-"):
                all_keys["grok"] = k
            elif k.startswith("sk-or-"):
                all_keys["openrouter"] = k
            elif k.startswith("nvapi-"):
                all_keys["nvidia_nim"] = k
            elif k.startswith("gsk_"):
                all_keys["groq"] = k
            elif not any(all_keys.values()):
                all_keys["gemini"] = k

        priority_order = cfg.get(
            "provider_priority",
            ["gemini", "grok", "openrouter", "nvidia_nim", "groq"]
        )

        providers: List[Dict[str, Any]] = []
        for prov_id in priority_order:
            key = (all_keys.get(prov_id) or "").strip()
            if not key or key.startswith("YOUR_") or "PLACEHOLDER" in key.upper():
                continue

            if prov_id == "gemini":
                model = self.configured_model if (self.configured_model and self.configured_model != "auto" and "gemini" in self.configured_model.lower()) else "gemini-3-flash-preview"
                providers.append({
                    "id": "gemini",
                    "name": "Google Gemini",
                    "endpoint": "https://generativelanguage.googleapis.com/v1beta/openai/chat/completions",
                    "model": model,
                    "key": key,
                    "headers": {
                        "Authorization": f"Bearer {key}",
                        "Content-Type": "application/json",
                    }
                })
            elif prov_id == "grok":
                model = self.configured_model if (self.configured_model and self.configured_model != "auto" and "grok" in self.configured_model.lower()) else "grok-2-vision-1212"
                providers.append({
                    "id": "grok",
                    "name": "xAI Grok",
                    "endpoint": "https://api.x.ai/v1/chat/completions",
                    "model": model,
                    "key": key,
                    "headers": {
                        "Authorization": f"Bearer {key}",
                        "Content-Type": "application/json",
                    }
                })
            elif prov_id == "openrouter":
                model = self.configured_model if (self.configured_model and self.configured_model != "auto" and "/" in self.configured_model) else "google/gemini-2.5-flash"
                providers.append({
                    "id": "openrouter",
                    "name": "OpenRouter",
                    "endpoint": "https://openrouter.ai/api/v1/chat/completions",
                    "model": model,
                    "key": key,
                    "headers": {
                        "Authorization": f"Bearer {key}",
                        "Content-Type": "application/json",
                        "HTTP-Referer": "https://github.com/Charukhesh/spidy",
                        "X-Title": "Spidy Desktop Companion",
                    }
                })
            elif prov_id == "nvidia_nim":
                model = self.configured_model if (self.configured_model and self.configured_model != "auto" and "meta/" in self.configured_model) else "meta/llama-3.2-11b-vision-instruct"
                providers.append({
                    "id": "nvidia_nim",
                    "name": "NVIDIA NIM",
                    "endpoint": "https://integrate.api.nvidia.com/v1/chat/completions",
                    "model": model,
                    "key": key,
                    "headers": {
                        "Authorization": f"Bearer {key}",
                        "Content-Type": "application/json",
                    }
                })
            elif prov_id == "groq":
                model = self.configured_model if (self.configured_model and self.configured_model != "auto" and "qwen" in self.configured_model.lower()) else "qwen/qwen3.8-27b"
                providers.append({
                    "id": "groq",
                    "name": "Groq Cloud",
                    "endpoint": "https://api.groq.com/openai/v1/chat/completions",
                    "model": model,
                    "key": key,
                    "headers": {
                        "Authorization": f"Bearer {key}",
                        "Content-Type": "application/json",
                    }
                })

        return providers

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
            with httpx.Client(timeout=25.0) as client:
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
        audio_bytes: Optional[bytes] = None,
    ) -> AIVisionResponse:
        """Send user voice audio/transcript, active window context, and screen capture(s) to multimodal vision LLM with auto-failover."""
        active_providers = self._get_active_providers()
        if not active_providers:
            return AIVisionResponse(
                full_text="please enter your api key in the spidy settings or .env file first [POINT:none]",
                spoken_text="please enter your api key in the spidy settings or .env file first",
            )

        # Build message contents
        user_content: List[Dict[str, Any]] = []

        # 1. Attach direct audio if available, otherwise textual transcript
        if audio_bytes and len(audio_bytes) > 1000:
            b64_audio = base64.b64encode(audio_bytes).decode("utf-8")
            user_content.append({
                "type": "input_audio",
                "input_audio": {
                    "data": b64_audio,
                    "format": "wav"
                }
            })
            prompt_instruction = (
                "Listen directly to the user's voice audio recording and look at the screen image(s). "
                "Structure your reply as:\n"
                "[HEARD: <exact words the user said>]\n"
                "<Your warm, natural, human conversational reply>\n"
                "[POINT:x,y:label] (or visual drawing tag, or [POINT:none])"
            )
            user_content.append({"type": "text", "text": prompt_instruction})
        elif transcript and transcript.strip():
            user_content.append({"type": "text", "text": transcript.strip()})

        # 2. Inject Active Application & Selected Text Context if available
        if active_context and active_context.strip():
            user_content.append({"type": "text", "text": active_context.strip()})

        # 2.5 Inject Relevant Long-Term Memories if available
        mem_context = memory_store.format_memories_for_prompt(transcript or "")
        if mem_context:
            user_content.append({"type": "text", "text": mem_context})

        # 3. Attach screenshots with image dimension labels
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
            {"role": "system", "content": SPIDY_SYSTEM_PROMPT}
        ]

        for prev_user, prev_assistant in self.conversation_history[-self.history_limit:]:
            messages.append({"role": "user", "content": prev_user})
            messages.append({"role": "assistant", "content": prev_assistant})

        messages.append({"role": "user", "content": user_content})

        last_error_details = []

        for p_idx, prov in enumerate(active_providers):
            provider_name = prov["name"]
            endpoint_url = prov["endpoint"]
            active_model = prov["model"]
            headers = prov["headers"]
            prov_id = prov.get("id", "")

            logger.info(
                f"[AI Vision Failover] Trying provider {p_idx+1}/{len(active_providers)}: "
                f"{provider_name} ({active_model})"
            )

            # Non-Gemini providers (OpenRouter, Groq, Grok) do not accept audio bytes; use textual transcript
            prov_messages = messages
            if prov_id != "gemini" and audio_bytes:
                filtered_user_content = []
                for item in user_content:
                    if item.get("type") == "input_audio":
                        continue
                    if item.get("type") == "text" and "Listen directly to the user" in item.get("text", ""):
                        if transcript and transcript.strip():
                            filtered_user_content.append({"type": "text", "text": transcript.strip()})
                        continue
                    filtered_user_content.append(item)
                prov_messages = messages[:-1] + [{"role": "user", "content": filtered_user_content}]

            payload = {
                "model": active_model,
                "messages": prov_messages,
                "temperature": 0.5,
                "max_tokens": 2048,
            }

            try:
                if not hasattr(self, "_http_client") or self._http_client.is_closed:
                    self._http_client = httpx.Client(timeout=22.0)

                response = self._http_client.post(endpoint_url, headers=headers, json=payload)
                response.raise_for_status()
                data = response.json()
                msg_obj = data["choices"][0].get("message", {})
                raw_reply = msg_obj.get("content") or ""

                logger.info(f"[AI Vision Failover] Provider '{provider_name}' responded successfully.")

                # Parse pointing coordinates, visual drawings, heard prompt, curve tracing, web search, action, remember, realtime graphics, and 3D scenes
                spoken_text, point_target, drawings, heard_prompt, trace_curve, offer_search, action_type, action_arg, remember_item, realtime_graphic, scene_3d = self.parse_visual_tags(raw_reply)

                # Map normalized [0..1000] coordinates to screenshot pixel resolution
                point_target, drawings = self._scale_to_capture_pixels(point_target, drawings, screen_captures)

                # Save exchange in history
                saved_prompt = heard_prompt or transcript or "Voice Request"
                self.conversation_history.append((saved_prompt, spoken_text))
                if len(self.conversation_history) > self.history_limit:
                    self.conversation_history.pop(0)

                return AIVisionResponse(
                    full_text=raw_reply,
                    spoken_text=spoken_text,
                    point_target=point_target,
                    drawings=drawings,
                    heard_prompt=heard_prompt,
                    trace_curve=trace_curve,
                    offer_search=offer_search,
                    action_type=action_type,
                    action_arg=action_arg,
                    remember_item=remember_item,
                    realtime_graphic=realtime_graphic,
                    scene_3d=scene_3d,
                )

            except httpx.HTTPStatusError as e:
                status = e.response.status_code
                snippet = e.response.text[:200]
                logger.warning(
                    f"[AI Vision Failover] Provider '{provider_name}' failed with HTTP {status}: {snippet}. "
                    f"Failing over to next available provider..."
                )
                last_error_details.append(f"{provider_name} (HTTP {status})")
                continue
            except Exception as e:
                logger.warning(
                    f"[AI Vision Failover] Provider '{provider_name}' failed with error: {e}. "
                    f"Failing over to next available provider..."
                )
                last_error_details.append(f"{provider_name} ({e})")
                continue

        # If all active providers were tried and none succeeded
        all_errs = ", ".join(last_error_details) if last_error_details else "all models busy"
        err_msg = (
            "all configured vision models experienced rate limits or errors. "
            "please check your api keys or try again in a moment"
        )
        logger.error(f"[AI Vision] All providers exhausted: {all_errs}")
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
        res = cls.parse_visual_tags(response_text)
        return res[0], res[1]

    @staticmethod
    def parse_visual_tags(
        response_text: str,
    ) -> Tuple[str, Optional[PointingTarget], List[VisualDrawing], str, Optional[TraceCurveTarget], str, str, str, Optional[Tuple[str, str, str]], Optional[RealtimeGraphicSpec], Optional[Scene3DSpec]]:
        """Parse visual tags, actions, memories, heard prompts, drawings, RTG, and 3D scenes."""
        spoken = response_text
        point_target: Optional[PointingTarget] = None
        drawings: List[VisualDrawing] = []
        heard_prompt = ""
        trace_curve: Optional[TraceCurveTarget] = None
        offer_search = ""
        action_type = ""
        action_arg = ""
        remember_item = None

        # 0. Parse [HEARD: <exact words>]
        heard_pattern = re.compile(r"\[HEARD:\s*([^\]\r\n]+)(?:\]|\r?\n|$)", re.IGNORECASE)
        match_heard = heard_pattern.search(spoken)
        if match_heard:
            heard_prompt = match_heard.group(1).strip()
            spoken = heard_pattern.sub("", spoken)

        # 1. Parse [POINT:x,y:label(:screenN or :N)]
        # Accepts :1, :screen1, :screen 1, etc.
        point_pattern = re.compile(
            r"\[POINT:\s*(\d+)\s*,\s*(\d+)\s*[,:]\s*([^:,\]]+)(?:[,:]\s*(?:screen\s*)?(\d+))?\s*\]",
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

        # 2. Parse [DRAW:box,x1,y1,x2,y2:label(:screenN or :N)]
        box_pattern = re.compile(
            r"\[DRAW:\s*box\s*,\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)\s*[,:]\s*([^:,\]]+)(?:[,:]\s*(?:screen\s*)?(\d+))?\s*\]",
            re.IGNORECASE,
        )
        for m in box_pattern.finditer(spoken):
            x1, y1, x2, y2 = int(m.group(1)), int(m.group(2)), int(m.group(3)), int(m.group(4))
            lbl = m.group(5).strip()
            s_num = int(m.group(6)) if m.group(6) else 1
            drawings.append(VisualDrawing(kind="box", coords=[x1, y1, x2, y2], label=lbl, screen_number=s_num))
        spoken = box_pattern.sub("", spoken)

        # 3. Parse [DRAW:circle,cx,cy,radius:label(:screenN or :N)]
        circle_pattern = re.compile(
            r"\[DRAW:\s*circle\s*,\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)\s*[,:]\s*([^:,\]]+)(?:[,:]\s*(?:screen\s*)?(\d+))?\s*\]",
            re.IGNORECASE,
        )
        for m in circle_pattern.finditer(spoken):
            cx, cy, r = int(m.group(1)), int(m.group(2)), int(m.group(3))
            lbl = m.group(4).strip()
            s_num = int(m.group(5)) if m.group(5) else 1
            drawings.append(VisualDrawing(kind="circle", coords=[cx, cy, r], label=lbl, screen_number=s_num))
        spoken = circle_pattern.sub("", spoken)

        # 4. Parse [DRAW:arrow,x1,y1,x2,y2:label(:screenN or :N)]
        arrow_pattern = re.compile(
            r"\[DRAW:\s*arrow\s*,\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)\s*[,:]\s*([^:,\]]+)(?:[,:]\s*(?:screen\s*)?(\d+))?\s*\]",
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
            r"\[SIMULATE:\s*([0-9,\->\s]+)\s*[,:]\s*([^:,\]]+)(?:[,:]\s*(?:screen\s*)?(\d+))?\s*\]",
            re.IGNORECASE,
        )
        for m in simulate_pattern.finditer(spoken):
            path_str = m.group(1).strip()
            lbl = m.group(2).strip()
            s_num = int(m.group(3)) if m.group(3) else 1
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
            r"\[WRITE:\s*(\d+)\s*,\s*(\d+)\s*[,:]\s*([^:,\]]+)(?:[,:]\s*(?:screen\s*)?(\d+))?\s*\]",
            re.IGNORECASE,
        )
        for m in write_pattern.finditer(spoken):
            x, y = int(m.group(1)), int(m.group(2))
            txt = m.group(3).strip()
            s_num = int(m.group(4)) if m.group(4) else 1
            drawings.append(VisualDrawing(kind="text", coords=[x, y], label=txt, screen_number=s_num))
        spoken = write_pattern.sub("", spoken)

        # 7. Parse [TRACE:type:label]
        trace_pattern = re.compile(
            r"\[TRACE:\s*([a-zA-Z0-9_\^\-]+)\s*[,:]\s*([^\]]+)\]",
            re.IGNORECASE,
        )
        match_trace = trace_pattern.search(spoken)
        if match_trace:
            c_type = match_trace.group(1).strip()
            c_label = match_trace.group(2).strip()
            trace_curve = TraceCurveTarget(curve_type=c_type, label=c_label)
            spoken = trace_pattern.sub("", spoken)

        # 8. Parse [OFFER_SEARCH:query]
        search_pattern = re.compile(r"\[OFFER_SEARCH:\s*([^\]]+)\]", re.IGNORECASE)
        match_search = search_pattern.search(spoken)
        if match_search:
            offer_search = match_search.group(1).strip()
            spoken = search_pattern.sub("", spoken)

        # 9. Parse [ACTION:type:arg]
        action_pattern = re.compile(r"\[ACTION:\s*([a-zA-Z0-9_\-]+)\s*[,:]\s*([^\]]+)\]", re.IGNORECASE)
        match_action = action_pattern.search(spoken)
        if match_action:
            action_type = match_action.group(1).strip()
            action_arg = match_action.group(2).strip()
            spoken = action_pattern.sub("", spoken)

        # 10. Parse [REMEMBER:category:key:content]
        rem_pattern = re.compile(r"\[REMEMBER:\s*([^:,\]]+)\s*[,:]\s*([^:,\]]+)\s*[,:]\s*([^\]]+)\]", re.IGNORECASE)
        match_rem = rem_pattern.search(spoken)
        if match_rem:
            remember_item = (match_rem.group(1).strip(), match_rem.group(2).strip(), match_rem.group(3).strip())
            spoken = rem_pattern.sub("", spoken)

        # 11. Parse [DIAGRAM:...], [CUTAWAY:...], [ASSEMBLY:...]
        realtime_graphic: Optional[RealtimeGraphicSpec] = None
        match_start = re.search(r"\[(DIAGRAM|CUTAWAY|ASSEMBLY):\s*", spoken, re.IGNORECASE)
        if match_start:
            kind_tag = match_start.group(1).lower()
            tag_start_idx = match_start.start()
            content_start_idx = match_start.end()

            # If payload starts with JSON '{', find balanced '}'
            if content_start_idx < len(spoken) and spoken[content_start_idx] == "{":
                brace_count = 0
                in_string = False
                escape_char = False
                end_brace_idx = -1

                for idx in range(content_start_idx, len(spoken)):
                    ch = spoken[idx]
                    if escape_char:
                        escape_char = False
                        continue
                    if ch == "\\":
                        escape_char = True
                        continue
                    if ch == '"':
                        in_string = not in_string
                        continue
                    if not in_string:
                        if ch == "{":
                            brace_count += 1
                        elif ch == "}":
                            brace_count -= 1
                            if brace_count == 0:
                                end_brace_idx = idx
                                break

                if end_brace_idx != -1:
                    raw_body = spoken[content_start_idx : end_brace_idx + 1]
                    closing_bracket_idx = spoken.find("]", end_brace_idx)
                    tag_end_idx = (closing_bracket_idx + 1) if closing_bracket_idx != -1 else (end_brace_idx + 1)
                else:
                    closing_bracket_idx = spoken.find("]", content_start_idx)
                    tag_end_idx = (closing_bracket_idx + 1) if closing_bracket_idx != -1 else len(spoken)
                    raw_body = spoken[content_start_idx : tag_end_idx - (1 if closing_bracket_idx != -1 else 0)].strip()
            else:
                closing_bracket_idx = spoken.find("]", content_start_idx)
                tag_end_idx = (closing_bracket_idx + 1) if closing_bracket_idx != -1 else len(spoken)
                raw_body = spoken[content_start_idx : tag_end_idx - (1 if closing_bracket_idx != -1 else 0)].strip()

            try:
                parsed_data = json.loads(raw_body)
                title = parsed_data.get("title", f"Spidy {kind_tag.capitalize()}")
                sub = parsed_data.get("summary") or parsed_data.get("principle") or parsed_data.get("pin_info") or parsed_data.get("hardware", "")
                realtime_graphic = RealtimeGraphicSpec(
                    kind=kind_tag,
                    title=title,
                    subtitle=sub,
                    data=parsed_data,
                    raw_payload=raw_body,
                )
            except Exception as e:
                logger.debug(f"RTG JSON parse fallback: {e}")
                realtime_graphic = RealtimeGraphicSpec(
                    kind=kind_tag,
                    title=f"Spidy {kind_tag.capitalize()}",
                    subtitle=raw_body[:60],
                    data={"summary": raw_body},
                    raw_payload=raw_body,
                )
            spoken = spoken[:tag_start_idx] + spoken[tag_end_idx:]

        # 12. Parse [SCENE_3D:...]
        scene_3d: Optional[Scene3DSpec] = None
        match_3d = re.search(r"\[SCENE_3D:\s*", spoken, re.IGNORECASE)
        if match_3d:
            tag_start_idx = match_3d.start()
            content_start_idx = match_3d.end()

            if content_start_idx < len(spoken) and spoken[content_start_idx] == "{":
                brace_count = 0
                in_string = False
                escape_char = False
                end_brace_idx = -1

                for idx in range(content_start_idx, len(spoken)):
                    ch = spoken[idx]
                    if escape_char:
                        escape_char = False
                        continue
                    if ch == "\\":
                        escape_char = True
                        continue
                    if ch == '"':
                        in_string = not in_string
                        continue
                    if not in_string:
                        if ch == "{":
                            brace_count += 1
                        elif ch == "}":
                            brace_count -= 1
                            if brace_count == 0:
                                end_brace_idx = idx
                                break

                if end_brace_idx != -1:
                    raw_body = spoken[content_start_idx : end_brace_idx + 1]
                    closing_bracket_idx = spoken.find("]", end_brace_idx)
                    tag_end_idx = (closing_bracket_idx + 1) if closing_bracket_idx != -1 else (end_brace_idx + 1)
                else:
                    closing_bracket_idx = spoken.find("]", content_start_idx)
                    tag_end_idx = (closing_bracket_idx + 1) if closing_bracket_idx != -1 else len(spoken)
                    raw_body = spoken[content_start_idx : tag_end_idx - (1 if closing_bracket_idx != -1 else 0)].strip()
            else:
                closing_bracket_idx = spoken.find("]", content_start_idx)
                tag_end_idx = (closing_bracket_idx + 1) if closing_bracket_idx != -1 else len(spoken)
                raw_body = spoken[content_start_idx : tag_end_idx - (1 if closing_bracket_idx != -1 else 0)].strip()

            try:
                parsed_3d = json.loads(raw_body)
                scene_3d = Scene3DSpec(
                    title=parsed_3d.get("title", "3D Interactive View"),
                    entity=parsed_3d.get("entity", "generic"),
                    subtitle=parsed_3d.get("subtitle", ""),
                    cutaway=bool(parsed_3d.get("cutaway", False)),
                    primitives=parsed_3d.get("primitives", []),
                    callouts=parsed_3d.get("callouts", []),
                    animation=parsed_3d.get("animation", "spin"),
                    raw_payload=raw_body,
                    options=parsed_3d.get("options", {}),
                )
            except Exception as e:
                logger.debug(f"3D Scene JSON parse fallback: {e}")
                scene_3d = Scene3DSpec(
                    title="3D Interactive View",
                    entity=raw_body[:30].strip(),
                    raw_payload=raw_body,
                )

            spoken = spoken[:tag_start_idx] + spoken[tag_end_idx:]

        # Failsafe cleanup: strip any remaining bracketed tags or negative control [POINT:none]
        spoken = re.sub(
            r"\[(?:POINT|DRAW|SIMULATE|WRITE|HEARD|TRACE|OFFER_SEARCH|ACTION|REMEMBER|DIAGRAM|CUTAWAY|ASSEMBLY|SCENE_3D)[^\]]*\]",
            "",
            spoken,
            flags=re.IGNORECASE,
        )
        spoken = re.sub(r"\[POINT:\s*none\s*\]", "", spoken, flags=re.IGNORECASE).strip()
        spoken = re.sub(r"\s+", " ", spoken).strip()

        return spoken.strip(), point_target, drawings, heard_prompt, trace_curve, offer_search, action_type, action_arg, remember_item, realtime_graphic, scene_3d


# Backward compatibility alias
GrokClient = AIVisionClient
