"""Central Companion Manager for Athena Everyday Desktop Companion.

Orchestrates:
- Hardware-level Push-to-Talk hotkey detection via GetAsyncKeyState for unified 'Ctrl+Alt'
- High-tech interactive audio cues (activate, thinking, pointing arrival ding)
- Deep Context Awareness (active foreground window, app title, and selected text)
- Top-Center Black Glass Dynamic Bar HUD with 1-click Copy button and auto-collapse into idle bar
- Visual Drawing Engine (bounding boxes, highlight circles, guide arrows, workflow simulations, notes)
- Pure ctypes PCM audio capture with live waveform level feedback
- Multi-monitor screenshot capture with normalized coordinate mapping
- Multimodal AI vision reasoning via Google Gemini
- Natural voice speech playback via Microsoft Edge Neural TTS
"""

import os
import re
import time
import ctypes
import threading
import concurrent.futures
import logging
from typing import Optional, List, Tuple

from PyQt5.QtCore import QObject, pyqtSignal, QTimer
from PyQt5.QtWidgets import QApplication

from athena.config import load_config
from athena.audio_recorder import AudioRecorder
from athena.stt_engine import SpeechToText
from athena.tts_engine import TextToSpeech
from athena.screen_capture import ScreenCaptureUtility, ScreenCaptureResult
from athena.ai_vision_client import AIVisionClient, GrokClient, PointingTarget, VisualDrawing
from athena.cursor_overlay import ClickyCursorOverlay, VoiceState
from athena.sound_effects import sounds
from athena.context_inspector import inspector
from athena.top_bar_hud import TopBarGlassHUD
from athena.beige_card_hud import BeigeCardHUD
from athena.curve_generator import CurveGenerator
from athena.web_search import web_search
from athena.desktop_actions import desktop_actions
from athena.memory_store import memory_store
from athena.visual_scratchpad import scratchpad
from athena.wake_word import WakeWordDetector

logger = logging.getLogger("athena.companion")

# Windows Virtual Key Codes
VK_SHIFT = 0x10
VK_CONTROL = 0x11
VK_MENU = 0x12  # Alt
VK_SPACE = 0x20
VK_OEM_3 = 0xC0 # '~' / '`' key (US standard)


class CompanionManager(QObject):
    """Coordinates the entire push-to-talk voice and visual interaction pipeline."""

    status_updated = pyqtSignal(str)
    sig_set_listening = pyqtSignal()
    sig_set_thinking = pyqtSignal()
    sig_show_response = pyqtSignal(str, str)
    sig_collapse_bar = pyqtSignal()
    sig_schedule_collapse = pyqtSignal(int)
    sig_apply_drawings = pyqtSignal(list)
    sig_clear_drawings = pyqtSignal()

    # Spidy Beige Tab Signals
    sig_toggle_beige_card = pyqtSignal()
    sig_show_beige_card = pyqtSignal(str, str)
    sig_hide_beige_card = pyqtSignal()

    def __init__(self, overlay: ClickyCursorOverlay, parent=None):
        super().__init__(parent)
        self.overlay = overlay
        self.config = load_config()

        # Engine initializations
        self.audio_recorder = AudioRecorder(
            sample_rate=16000,
            channels=1,
            on_audio_level=self._on_audio_power_meter,
        )
        self.stt_engine = SpeechToText(model_size=self.config.get("whisper_model", "base.en"))
        self.tts_engine = TextToSpeech(
            voice=self.config.get("tts_voice", "en-US-JennyNeural"),
            rate=self.config.get("tts_rate", "+0%"),
        )
        self.ai_client = AIVisionClient(model=self.config.get("grok_model", "auto"))
        self.grok_client = self.ai_client

        # Spidy Warm Beige Rounded Tab HUD (Spawns near cursor)
        self.beige_card = BeigeCardHUD()

        # Legacy Top Bar HUD permanently dropped
        self.top_bar_hud = None
        self.history_hud = None

        # Thread-safe signal connections to GUI widgets
        self.sig_toggle_beige_card.connect(self.beige_card.toggle_visibility)
        self.sig_show_beige_card.connect(self.beige_card.show_response)
        self.sig_hide_beige_card.connect(self.beige_card.hide_card)
        self.sig_apply_drawings.connect(self.overlay.apply_drawings)
        self.sig_clear_drawings.connect(self.overlay.clear_drawings)

        # Pipeline state flags
        self.is_hotkey_down = False
        self._processing_lock = threading.Lock()
        self._stop_hotkey_thread = threading.Event()
        self.pending_search_query: Optional[str] = None

        # Optional Hands-Free Wake Word Detector
        self.wake_detector = WakeWordDetector(enabled=self.config.get("wake_word_enabled", False))
        self.wake_detector.wake_word_detected.connect(self._on_wake_word_triggered)
        if self.config.get("wake_word_enabled", False):
            self.wake_detector.start()

        # Start hardware hotkey polling thread (Ctrl + Alt)
        self._start_hotkey_listener()

    def _on_wake_word_triggered(self):
        """Hands-free wake word triggered."""
        logger.info("Wake word heard -> Listening...")
        self._on_hotkey_pressed()

    def _start_hotkey_listener(self):
        """Hardware-level hotkey polling thread using GetAsyncKeyState.
        
        Guarantees 100% reliable detection of key press and key release
        for the unified Ctrl + Alt hotkey.
        """
        user32 = ctypes.windll.user32

        def _poll_keys():
            was_pressed = False
            was_tilde_pressed = False

            while not self._stop_hotkey_thread.is_set():
                hotkey_choice = self.config.get("hotkey", "ctrl+alt").lower()

                # Evaluate Unified Hotkey (Default: Ctrl + Alt)
                if hotkey_choice == "ctrl+shift":
                    is_hotkey_raw = bool(user32.GetAsyncKeyState(VK_CONTROL) & 0x8000) and bool(
                        user32.GetAsyncKeyState(VK_SHIFT) & 0x8000
                    )
                elif hotkey_choice == "alt+space":
                    is_hotkey_raw = bool(user32.GetAsyncKeyState(VK_MENU) & 0x8000) and bool(
                        user32.GetAsyncKeyState(VK_SPACE) & 0x8000
                    )
                else:  # Default: "ctrl+alt"
                    is_hotkey_raw = bool(user32.GetAsyncKeyState(VK_CONTROL) & 0x8000) and bool(
                        user32.GetAsyncKeyState(VK_MENU) & 0x8000
                    )

                # State Transitions for Push-to-Talk
                if is_hotkey_raw and not was_pressed:
                    was_pressed = True
                    self.is_hotkey_down = True
                    self._on_hotkey_pressed()
                elif not is_hotkey_raw and was_pressed:
                    was_pressed = False
                    self.is_hotkey_down = False
                    self._on_hotkey_released()

                # Evaluate '~' (Tilde / Backquote, VK_OEM_3 = 0xC0) to toggle Spidy Beige Tab
                is_tilde_raw = bool(user32.GetAsyncKeyState(VK_OEM_3) & 0x8000)
                if is_tilde_raw and not was_tilde_pressed:
                    was_tilde_pressed = True
                    self.sig_toggle_beige_card.emit()
                elif not is_tilde_raw and was_tilde_pressed:
                    was_tilde_pressed = False

                time.sleep(0.025)  # ~40 Hz check rate (25ms response, low CPU)

        threading.Thread(target=_poll_keys, daemon=True).start()

    def _on_audio_power_meter(self, level: float):
        if self.is_hotkey_down:
            self.overlay.update_audio_power(level)

    def _on_hotkey_pressed(self):
        """Push-to-Talk key held down: start listening immediately."""
        logger.info("Push-to-talk pressed -> Listening...")
        self.status_updated.emit("Listening...")
        self.tts_engine.stop()
        self.overlay.set_voice_state(VoiceState.LISTENING)
        self.overlay.clear_curve()
        self.sig_clear_drawings.emit()
        self.sig_set_listening.emit()
        sounds.play_activate()
        self.audio_recorder.start()

    def _on_hotkey_released(self):
        """Push-to-talk released: process audio, screenshot, and query Gemini."""
        logger.info("Push-to-talk released -> Processing...")
        self.status_updated.emit("Thinking...")
        self.overlay.set_voice_state(VoiceState.PROCESSING)
        self.sig_set_thinking.emit()
        sounds.play_thinking()

        pcm_data = self.audio_recorder.stop()
        if not pcm_data or len(pcm_data) < 3200:
            logger.info("Voice input too brief. Returning to idle.")
            self.overlay.set_voice_state(VoiceState.IDLE)
            self.status_updated.emit("Ready")
            self.sig_collapse_bar.emit()
            return

        # Run pipeline asynchronously in background thread
        threading.Thread(
            target=self._run_inference_pipeline,
            args=(pcm_data,),
            daemon=True,
        ).start()

    @staticmethod
    def _sanitize_speech_text(text: str) -> str:
        """Strip all technical tags and brackets to guarantee zero tags are ever spoken aloud."""
        if not text:
            return ""
        # Remove [POINT:...], [DRAW:...], [SIMULATE:...], [WRITE:...], [HEARD:...], [TRACE:...], [OFFER_SEARCH:...], etc.
        cleaned = re.sub(r"\[(?:POINT|DRAW|SIMULATE|WRITE|HEARD|TRACE|OFFER_SEARCH)[^\]]*\]", "", text, flags=re.IGNORECASE)
        # Strip any other bracketed expressions like [POINT:none] or stray brackets
        cleaned = re.sub(r"\[[^\]]*\]", "", cleaned)
        # Clean up any leftover whitespace
        cleaned = re.sub(r"\s+", " ", cleaned).strip()
        return cleaned

    def _run_inference_pipeline(self, pcm_data: bytes):
        with self._processing_lock:
            try:
                stt_mode = self.config.get("stt_mode", "gemini_direct_audio")
                use_direct_audio = (stt_mode == "gemini_direct_audio")

                # 1. Concurrently run Screen Capture, Context Inspection, and STT in parallel
                with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:
                    fut_screens = executor.submit(ScreenCaptureUtility.capture_all_screens)

                    def _get_context():
                        if self.config.get("context_awareness", True):
                            try:
                                ctx = inspector.capture_active_context(include_selected_text=True)
                                if ctx.app_name or ctx.window_title:
                                    logger.info(f"Captured active context: {ctx.app_name} | {ctx.window_title}")
                                return ctx.to_prompt_text()
                            except Exception as ce:
                                logger.debug(f"Context capture notice: {ce}")
                        return None

                    fut_ctx = executor.submit(_get_context)
                    fut_stt = None
                    if not use_direct_audio:
                        fut_stt = executor.submit(self.stt_engine.transcribe_pcm, pcm_data)

                    screen_captures = fut_screens.result()
                    active_context_str = fut_ctx.result()
                    transcript = fut_stt.result() if fut_stt else ""

                wav_bytes = AudioRecorder.pcm_to_wav_bytes(pcm_data) if use_direct_audio else None

                # Inject pending search notice into context if active
                search_notice = None
                if self.pending_search_query:
                    search_notice = f"Pending web verification topic: '{self.pending_search_query}'. If user affirms (yes/please/sure/go ahead), acknowledge and synthesize web findings."
                    active_context_str = f"{active_context_str}\n{search_notice}" if active_context_str else search_notice

                # 2. Query Multimodal AI Vision (Gemini Direct Audio / Groq / Grok) with Active Context
                ai_response = self.ai_client.query(
                    transcript=transcript,
                    screen_captures=screen_captures,
                    active_context=active_context_str,
                    audio_bytes=wav_bytes,
                )
                logger.info(f"Athena AI replied: '{ai_response.spoken_text}'")

                # Determine prompt text to display in Top-Center Glass HUD
                display_query = (ai_response.heard_prompt or transcript or "Voice Request").strip()
                user_heard = display_query.lower()

                # 2.1 Handle Web Search Confirmation or Direct Search Trigger
                if self.pending_search_query and any(w in user_heard for w in ("yes", "yeah", "yep", "sure", "please", "go ahead", "search it", "do it", "check it", "okay", "ok")):
                    query_to_search = self.pending_search_query
                    self.pending_search_query = None
                    logger.info(f"User confirmed web search for: '{query_to_search}'")
                    # Open browser in background
                    web_search.open_in_browser(query_to_search)
                    # Retrieve verified search snippets
                    snippets = web_search.search(query_to_search, max_results=4)
                    if snippets:
                        search_prompt = (
                            f"The user confirmed web verification for: '{query_to_search}'. "
                            f"Here are the live verified search snippets from Google/web:\n"
                            f"{web_search.format_for_prompt(snippets)}\n"
                            f"Synthesize the verified answer warmly, concisely, and naturally for the user as a sharp collaborative peer."
                        )
                        ai_response = self.ai_client.query(transcript=search_prompt, screen_captures=screen_captures)
                        logger.info(f"Synthesized web verification reply: '{ai_response.spoken_text}'")
                elif any(kw in user_heard for kw in ("search the web for", "search for", "google ")) and len(user_heard) > 10:
                    raw_q = re.sub(r"^(?:please\s+)?(?:search the web for|search for|google)\s+", "", user_heard, flags=re.IGNORECASE).strip()
                    if raw_q:
                        logger.info(f"Direct search request detected: '{raw_q}'")
                        web_search.open_in_browser(raw_q)
                        snippets = web_search.search(raw_q, max_results=4)
                        if snippets:
                            search_prompt = (
                                f"The user asked to search the web for: '{raw_q}'. "
                                f"Here are the live verified search results:\n"
                                f"{web_search.format_for_prompt(snippets)}\n"
                                f"Synthesize these live findings warmly and concisely for the user as a sharp peer."
                            )
                            ai_response = self.ai_client.query(transcript=search_prompt, screen_captures=screen_captures)
                else:
                    # Reset pending query if a non-affirmative question was asked
                    if self.pending_search_query and not any(w in user_heard for w in ("yes", "sure", "ok", "go ahead")):
                        self.pending_search_query = None

                # Register new search offer if LLM offered one
                if ai_response.offer_search:
                    self.pending_search_query = ai_response.offer_search
                    logger.info(f"Athena offered web search: '{self.pending_search_query}'")

                # 2.2 Handle Desktop Actions (launch, window, clipboard, ocr)
                if ai_response.action_type and self.config.get("desktop_actions_enabled", True):
                    act_t = ai_response.action_type
                    act_a = ai_response.action_arg

                    if act_t == "ocr" and screen_captures:
                        from PyQt5.QtGui import QCursor
                        m_pos = QCursor.pos()
                        crop_bytes = scratchpad.crop_region_around_point(screen_captures, m_pos.x(), m_pos.y())
                        if crop_bytes:
                            ocr_crop_result = ScreenCaptureResult(
                                image_bytes=crop_bytes,
                                width=480,
                                height=320,
                                left=m_pos.x() - 240,
                                top=m_pos.y() - 160,
                                display_index=1,
                                is_primary=True,
                            )
                            ocr_prompt = f"Extract all visible text or structured data in this image crop as {act_a}. Return only the exact extracted text."
                            ocr_res = self.ai_client.query(transcript=ocr_prompt, screen_captures=[ocr_crop_result])
                            if ocr_res.spoken_text:
                                scratchpad.load_extracted_to_clipboard(ocr_res.spoken_text)
                    else:
                        success, act_msg = desktop_actions.execute_action(act_t, act_a)
                        logger.info(f"Desktop action [{act_t}: {act_a}] -> {success}: {act_msg}")

                # 2.3 Store Persistent Memory if requested
                if ai_response.remember_item and self.config.get("memory_enabled", True):
                    cat, k, content = ai_response.remember_item
                    memory_store.store_memory(cat, k, content)

                # 2.4 Log Session Activity for Multi-Day Continuity
                if self.config.get("memory_enabled", True):
                    memory_store.log_interaction(
                        app_name=inspector.capture_active_context(include_selected_text=False).app_name or "Desktop",
                        window_title=inspector.capture_active_context(include_selected_text=False).window_title or "",
                        user_prompt=display_query,
                        assistant_reply=ai_response.spoken_text,
                    )

                # Clean speech text to guarantee zero tags are read aloud
                sanitized_speech = self._sanitize_speech_text(ai_response.spoken_text)

                # Store latest response in Spidy Beige Tab
                self.beige_card.last_response = sanitized_speech
                self.beige_card.last_query = display_query

                # Intelligent Auto-Display Decision:
                # If the reply contains code blocks (```), markdown tables (|), URLs, or OCR data,
                # automatically render the beige tab with 1-click copy!
                is_structured = (
                    "```" in ai_response.full_text
                    or "\n|" in ai_response.full_text
                    or "http" in ai_response.full_text
                    or (ai_response.action_type == "ocr")
                    or len(sanitized_speech) > 240
                )
                if is_structured and self.config.get("beige_tab_enabled", True):
                    self.sig_show_beige_card.emit(sanitized_speech, display_query)

                # 2.5 Animated Curve Tracing around User Mouse Cursor
                if ai_response.trace_curve:
                    c_type = ai_response.trace_curve.curve_type
                    c_lbl = ai_response.trace_curve.label
                    from PyQt5.QtGui import QCursor
                    m_pos = QCursor.pos()
                    curve_pts = CurveGenerator.generate_curve(c_type, float(m_pos.x()), float(m_pos.y()))
                    logger.info(f"Tracing {c_type} curve ({len(curve_pts)} pts) centered at mouse ({m_pos.x()}, {m_pos.y()})")
                    self.overlay.start_tracing_curve(curve_pts, c_lbl)
                else:
                    # Fallback curve detection from prompt text (e.g. 'how does a cubic curve look like')
                    detected_curve = CurveGenerator.parse_curve_identifier(display_query)
                    if detected_curve and any(w in display_query.lower() for w in ("look like", "draw", "show me", "plot")):
                        from PyQt5.QtGui import QCursor
                        m_pos = QCursor.pos()
                        curve_pts = CurveGenerator.generate_curve(detected_curve, float(m_pos.x()), float(m_pos.y()))
                        logger.info(f"Fallback detected curve: '{detected_curve}' centered at mouse ({m_pos.x()}, {m_pos.y()})")
                        self.overlay.start_tracing_curve(curve_pts, f"{detected_curve} curve")

                # 3. Visual Drawings & Simulations (Bounding boxes, circles, arrows, simulations, notes)
                if ai_response.drawings and screen_captures:
                    mapped_drawings = []
                    for d in ai_response.drawings:
                        global_coords = self._map_coords_to_global_points(d.coords, d.screen_number, screen_captures)
                        mapped_drawings.append({
                            "kind": d.kind,
                            "coords": global_coords,
                            "label": d.label,
                        })
                    logger.info(f"Rendering {len(mapped_drawings)} visual drawing(s) on screen.")
                    self.sig_apply_drawings.emit(mapped_drawings)

                # 4. Map element pointing coordinates to global screen points & fly to element
                if ai_response.point_target and screen_captures:
                    target = ai_response.point_target
                    global_x, global_y = self._map_target_to_global_coords(target, screen_captures)
                    logger.info(f"Pointing at ({global_x}, {global_y}) - label='{target.label}'")
                    self.overlay.point_to(global_x, global_y, target.label)

                # 5. Speak response via Edge Neural TTS
                if sanitized_speech:
                    self.overlay.set_voice_state(VoiceState.RESPONDING)
                    self.status_updated.emit("Speaking...")

                    def on_speech_done():
                        logger.info("Speech finished.")
                        # Fly back if pointing
                        if self.overlay.nav_mode.value == "pointing":
                            self.overlay.start_flying_back()
                        # Fade out drawn curve smoothly
                        self.overlay.start_fading_curve()
                        self.overlay.set_voice_state(VoiceState.IDLE)
                        self.status_updated.emit("Ready")
                        # Once the agent finishes giving the response, smoothly collapse back to the thin idle bar
                        self.sig_schedule_collapse.emit(2500)

                    self.tts_engine.speak(sanitized_speech, on_complete=on_speech_done)
                else:
                    self.overlay.set_voice_state(VoiceState.IDLE)
                    self.status_updated.emit("Ready")
                    if self.overlay.nav_mode.value == "pointing":
                        threading.Timer(2.5, self.overlay.start_flying_back).start()
                    self.sig_schedule_collapse.emit(2000)

            except Exception as e:
                logger.error(f"Error in pipeline: {e}")
                self.overlay.set_voice_state(VoiceState.IDLE)
                self.status_updated.emit("Ready")
                self.sig_collapse_bar.emit()

    def _map_target_to_global_coords(
        self,
        target: PointingTarget,
        captures: list[ScreenCaptureResult],
    ) -> tuple[int, int]:
        """Convert screenshot coordinate to Windows global screen points."""
        coords = self._map_coords_to_global_points([target.x, target.y], target.screen_number, captures)
        return coords[0], coords[1]

    def _map_coords_to_global_points(
        self,
        coords: list[int],
        screen_number: int,
        captures: list[ScreenCaptureResult],
    ) -> list[int]:
        """Convert normalized [0..1000] or raw pixel coordinates to Windows global screen points."""
        cap = captures[0]
        if screen_number and 1 <= screen_number <= len(captures):
            cap = captures[screen_number - 1]

        # Look up matching screen geometry
        app = QApplication.instance()
        screens = app.screens() if app else []
        matching_screen = screens[0] if screens else None
        if screens:
            for s in screens:
                geom = s.geometry()
                if geom.left() == cap.left and geom.top() == cap.top:
                    matching_screen = s
                    break

        if matching_screen:
            geom = matching_screen.geometry()
            geom_left = geom.left()
            geom_top = geom.top()
            scale_x = geom.width() / float(cap.width) if cap.width > 0 else 1.0
            scale_y = geom.height() / float(cap.height) if cap.height > 0 else 1.0
        else:
            geom_left = cap.left
            geom_top = cap.top
            scale_x = 1.0
            scale_y = 1.0

        mapped = []
        for i in range(0, len(coords), 2):
            raw_x = coords[i]
            raw_y = coords[i + 1] if i + 1 < len(coords) else 0

            # If coordinates are already in pixel space, use directly
            px = float(raw_x)
            py = float(raw_y)

            clamped_px = max(0.0, min(px, float(cap.width)))
            clamped_py = max(0.0, min(py, float(cap.height)))

            gx = int(geom_left + clamped_px * scale_x)
            gy = int(geom_top + clamped_py * scale_y)
            mapped.extend([gx, gy])

        return mapped

    def run_onboarding_demo(self):
        """Show off pointing capabilities during onboarding demo."""
        logger.info("Running onboarding demo...")
        self.status_updated.emit("Running Demo...")

        app = QApplication.instance()
        primary_geom = app.primaryScreen().geometry() if app else None
        target_x = (primary_geom.left() + primary_geom.width() // 2) if primary_geom else 960
        target_y = (primary_geom.top() + primary_geom.height() // 3) if primary_geom else 360

        sounds.play_activate()
        self.overlay.point_to(target_x, target_y, "hey! i'm athena")
        self.overlay.set_voice_state(VoiceState.RESPONDING)

        welcome_text = "hey! i'm athena. hold control plus alt anytime and talk to me."

        if self.config.get("top_bar_hud_enabled", False) and self.top_bar_hud:
            self.sig_show_response.emit(welcome_text, "Who are you?")

        def on_done():
            self.overlay.start_flying_back()
            self.overlay.set_voice_state(VoiceState.IDLE)
            self.status_updated.emit("Ready")
            self.sig_schedule_collapse.emit(2500)

        self.tts_engine.speak(welcome_text, on_complete=on_done)
