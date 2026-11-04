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
import base64
import logging
from dataclasses import dataclass, field
from typing import List, Optional, Tuple, Dict, Any
import httpx

from spidy.screen_capture import ScreenCaptureResult
from spidy.config import get_api_key, load_config
from spidy.memory_store import memory_store
from spidy.realtime_graphics import RealtimeGraphicSpec

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

real-time graphics (RTG):
you have a zero-compute real-time vector graphics engine. whenever a visual explanation, cutaway diagram, or hardware walkthrough provides immense clarity, append one of these tags:
1. Contextual Visual Tutoring Card:
   use when explaining educational concepts, code logic, or tensors from the screen.
   [DIAGRAM: {"title": "<concept title>", "summary": "<1-line takeaway>", "nodes": [{"label": "Input", "sublabel": "shape/value"}, {"label": "Target", "sublabel": "prediction"}], "loop": ["Guess", "Compare", "Adjust"], "equation": "<optional formula>"}]
2. Mechanical & Physics Cutaway Schematic:
   use when explaining how machines, engines, jets, or physics mechanisms operate.
   [CUTAWAY: {"title": "<system title>", "principle": "<e.g. push air down -> lift up>", "components": [{"name": "Lift Fan", "desc": "Counter-rotating air column"}, {"name": "Swivel Nozzle", "desc": "3-bearing vector duct"}], "vectors": [{"label": "Downward Thrust"}]}]
3. Step-by-Step Hardware & Connector Assembly:
   use when guiding physical assembly, ribbon cables, pinouts, or board headers.
   [ASSEMBLY: {"title": "<guide title>", "board": "Raspberry Pi 5", "pin_info": "22-pin ribbon, contacts facing inward", "steps": [{"action": "Gently lift retaining collar", "detail": "Pull straight up 1mm"}, {"action": "Slide ribbon into slot", "detail": "Ensure contacts align"}, {"action": "Press collar down firmly", "detail": "Locks cable in place"}]}]

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
        key = self.api_key.strip()

        # 1. Google Gemini (aistudio.google.com) -> starts with 'AQ.' or 'AIza'
        if key.startswith("AQ.") or key.startswith("AIza") or "gemini" in self.configured_model.lower():
            endpoint = "https://generativelanguage.googleapis.com/v1beta/openai/chat/completions"
            if self.configured_model in ("gemini-3.5-flash", "gemini-3.5-flash-lite", "gemini-3.1-flash-lite", "gemini-3-flash-preview"):
                model = self.configured_model
            else:
                model = "gemini-3.1-flash-lite"
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
        """Send user voice audio/transcript, active window context, and screen capture(s) to multimodal vision LLM."""
        if not self.api_key or self.api_key.startswith("YOUR_") or "PLACEHOLDER" in self.api_key.upper():
            return AIVisionResponse(
                full_text="please enter your api key in the spidy settings first [POINT:none]",
                spoken_text="please enter your api key in the spidy settings first",
            )

        provider_name, endpoint_url, active_model = self._resolve_provider_and_model()
        logger.info(f"Using Provider: {provider_name} | Endpoint: {endpoint_url} | Model: {active_model}")

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

        headers = {
            "Authorization": f"Bearer {self.api_key.strip()}",
            "Content-Type": "application/json",
        }

        payload = {
            "model": active_model,
            "messages": messages,
            "temperature": 0.5,
            "max_tokens": 450,
        }

        try:
            if not hasattr(self, "_http_client") or self._http_client.is_closed:
                self._http_client = httpx.Client(timeout=25.0)

            response = self._http_client.post(endpoint_url, headers=headers, json=payload)
            response.raise_for_status()
            data = response.json()
            raw_reply = data["choices"][0]["message"].get("content", "")

            # Parse pointing coordinates, visual drawings, heard prompt, curve tracing, web search, action, remember, and realtime graphics
            spoken_text, point_target, drawings, heard_prompt, trace_curve, offer_search, action_type, action_arg, remember_item, realtime_graphic = self.parse_visual_tags(raw_reply)

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
        res = cls.parse_visual_tags(response_text)
        return res[0], res[1]

    @staticmethod
    def parse_visual_tags(
        response_text: str,
    ) -> Tuple[str, Optional[PointingTarget], List[VisualDrawing], str, Optional[TraceCurveTarget], str, str, str, Optional[Tuple[str, str, str]], Optional[RealtimeGraphicSpec]]:
        """Parse visual tags, actions, memories, heard prompts, and drawings."""
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
        heard_pattern = re.compile(r"\[HEARD:\s*([^\]]+)\]", re.IGNORECASE)
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

        # Failsafe cleanup: strip any remaining bracketed tags or negative control [POINT:none]
        spoken = re.sub(
            r"\[(?:POINT|DRAW|SIMULATE|WRITE|HEARD|TRACE|OFFER_SEARCH|ACTION|REMEMBER|DIAGRAM|CUTAWAY|ASSEMBLY)[^\]]*\]",
            "",
            spoken,
            flags=re.IGNORECASE,
        )
        spoken = re.sub(r"\[POINT:\s*none\s*\]", "", spoken, flags=re.IGNORECASE).strip()
        spoken = re.sub(r"\s+", " ", spoken).strip()

        return spoken.strip(), point_target, drawings, heard_prompt, trace_curve, offer_search, action_type, action_arg, remember_item, realtime_graphic


# Backward compatibility alias
GrokClient = AIVisionClient
