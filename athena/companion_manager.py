"""Central Companion Manager for Athena Everyday Desktop Companion.

Orchestrates:
- Hardware-level Push-to-Talk hotkey detection via GetAsyncKeyState for both:
  1. Main Visual Assistant (default 'Ctrl+Shift')
  2. Global Voice Dictation into active application (default 'Ctrl+Alt')
- High-tech interactive audio cues (activate, thinking, pointing arrival ding, dictation)
- Deep Context Awareness (active foreground window, app title, and selected text)
- Floating Response & History HUD card with 1-click Copy button
- Pure ctypes PCM audio capture with live waveform level feedback
- Multi-monitor screenshot capture
- Local Faster-Whisper transcription directly from memory
- Multimodal AI reasoning via Google Gemini / Grok 2 Vision
- Multi-monitor coordinate mapping and bezier flight pointing animations
- Natural voice speech playback via Microsoft Edge Neural TTS
"""

import os
import time
import ctypes
import threading
import concurrent.futures
import logging
from typing import Optional

from PyQt5.QtCore import QObject, pyqtSignal, QTimer
from PyQt5.QtWidgets import QApplication

from athena.config import load_config
from athena.audio_recorder import AudioRecorder
from athena.stt_engine import SpeechToText
from athena.tts_engine import TextToSpeech
from athena.screen_capture import ScreenCaptureUtility, ScreenCaptureResult
from athena.ai_vision_client import AIVisionClient, GrokClient, PointingTarget
from athena.cursor_overlay import ClickyCursorOverlay, VoiceState
from athena.sound_effects import sounds
from athena.context_inspector import inspector
from athena.top_bar_hud import TopBarGlassHUD

logger = logging.getLogger("athena.companion")

# Windows Virtual Key Codes
VK_SHIFT = 0x10
VK_CONTROL = 0x11
VK_MENU = 0x12  # Alt
VK_SPACE = 0x20


class CompanionManager(QObject):
    """Coordinates the entire push-to-talk voice and visual interaction pipeline."""

    status_updated = pyqtSignal(str)

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

        # Top-Center Black Glass Dynamic Bar HUD
        self.top_bar_hud = TopBarGlassHUD()
        self.history_hud = self.top_bar_hud  # Backward compatibility alias

        # Pipeline state flags
        self.is_hotkey_down = False
        self._processing_lock = threading.Lock()
        self._stop_hotkey_thread = threading.Event()

        # Start hardware hotkey polling thread (Ctrl + Alt)
        self._start_hotkey_listener()

    def _start_hotkey_listener(self):
        """Hardware-level hotkey polling thread using GetAsyncKeyState.
        
        Guarantees 100% reliable detection of key press and key release
        for the unified Ctrl + Alt hotkey.
        """
        user32 = ctypes.windll.user32

        def _poll_keys():
            was_pressed = False

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

                # State Transitions
                if is_hotkey_raw and not was_pressed:
                    was_pressed = True
                    self.is_hotkey_down = True
                    self._on_hotkey_pressed()
                elif not is_hotkey_raw and was_pressed:
                    was_pressed = False
                    self.is_hotkey_down = False
                    self._on_hotkey_released()

                time.sleep(0.015)  # ~66 Hz check rate

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
        QTimer.singleShot(0, self.top_bar_hud.set_listening)
        sounds.play_activate()
        self.audio_recorder.start()

    def _on_hotkey_released(self):
        """Push-to-talk released: process audio, screenshot, and query Gemini/Grok."""
        logger.info("Push-to-talk released -> Processing...")
        self.status_updated.emit("Thinking...")
        self.overlay.set_voice_state(VoiceState.PROCESSING)
        QTimer.singleShot(0, self.top_bar_hud.set_thinking)
        sounds.play_thinking()

        pcm_data = self.audio_recorder.stop()
        if not pcm_data or len(pcm_data) < 3200:
            logger.info("Voice input too brief. Returning to idle.")
            self.overlay.set_voice_state(VoiceState.IDLE)
            self.status_updated.emit("Ready")
            QTimer.singleShot(0, self.top_bar_hud.collapse_to_bar)
            return

        # Run pipeline asynchronously in background thread
        threading.Thread(
            target=self._run_inference_pipeline,
            args=(pcm_data,),
            daemon=True,
        ).start()

    def _run_inference_pipeline(self, pcm_data: bytes):
        with self._processing_lock:
            try:
                # 1. Concurrently run Screen Capture, Context Inspection, and Audio STT in parallel
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
                    fut_stt = executor.submit(self.stt_engine.transcribe_pcm, pcm_data)

                    transcript = fut_stt.result()
                    screen_captures = fut_screens.result()
                    active_context_str = fut_ctx.result()

                logger.info(f"User voice transcript: '{transcript}'")

                if not transcript.strip():
                    logger.info("Empty transcript. Resetting.")
                    self.overlay.set_voice_state(VoiceState.IDLE)
                    self.status_updated.emit("Ready")
                    QTimer.singleShot(0, self.top_bar_hud.collapse_to_bar)
                    return

                # 4. Query Multimodal AI Vision (Gemini / Groq / Grok) with Active Context
                ai_response = self.ai_client.query(
                    transcript,
                    screen_captures,
                    active_context=active_context_str,
                )
                logger.info(f"Athena AI replied: '{ai_response.spoken_text}'")

                # Show Top-Center Black Glass HUD response
                if self.config.get("top_bar_hud_enabled", True) or self.config.get("floating_card_enabled", True):
                    QTimer.singleShot(
                        0,
                        lambda: self.top_bar_hud.show_response(ai_response.spoken_text, transcript)
                    )

                # 5. Map element pointing coordinates to global screen points
                if ai_response.point_target and screen_captures:
                    target = ai_response.point_target
                    global_x, global_y = self._map_target_to_global_coords(target, screen_captures)
                    logger.info(f"Pointing at ({global_x}, {global_y}) - label='{target.label}'")
                    self.overlay.point_to(global_x, global_y, target.label)

                # 6. Speak response via Edge Neural TTS
                self.overlay.set_voice_state(VoiceState.RESPONDING)
                self.status_updated.emit("Speaking...")

                def on_speech_done():
                    logger.info("Speech finished.")
                    # Fly back if pointing
                    if self.overlay.nav_mode.value == "pointing":
                        self.overlay.start_flying_back()
                    self.overlay.set_voice_state(VoiceState.IDLE)
                    self.status_updated.emit("Ready")

                self.tts_engine.speak(ai_response.spoken_text, on_complete=on_speech_done)

            except Exception as e:
                logger.error(f"Error in pipeline: {e}")
                self.overlay.set_voice_state(VoiceState.IDLE)
                self.status_updated.emit("Ready")

    def _map_target_to_global_coords(
        self,
        target: PointingTarget,
        captures: list[ScreenCaptureResult],
    ) -> tuple[int, int]:
        """Convert screenshot pixel coordinates to Windows global screen points."""
        cap = captures[0]
        if target.screen_number and 1 <= target.screen_number <= len(captures):
            cap = captures[target.screen_number - 1]

        # Clamp
        clamped_x = max(0, min(target.x, cap.width))
        clamped_y = max(0, min(target.y, cap.height))

        # Look up matching screen geometry
        app = QApplication.instance()
        screens = app.screens()
        matching_screen = screens[0]
        for s in screens:
            geom = s.geometry()
            if geom.left() == cap.left and geom.top() == cap.top:
                matching_screen = s
                break

        geom = matching_screen.geometry()
        # Scale screenshot pixels to screen points
        scale_x = geom.width() / float(cap.width) if cap.width > 0 else 1.0
        scale_y = geom.height() / float(cap.height) if cap.height > 0 else 1.0

        global_x = int(geom.left() + clamped_x * scale_x)
        global_y = int(geom.top() + clamped_y * scale_y)
        return global_x, global_y

    def run_onboarding_demo(self):
        """Show off pointing capabilities during onboarding demo."""
        logger.info("Running onboarding demo...")
        self.status_updated.emit("Running Demo...")

        app = QApplication.instance()
        primary_geom = app.primaryScreen().geometry()
        target_x = primary_geom.left() + primary_geom.width() // 2
        target_y = primary_geom.top() + primary_geom.height() // 3

        sounds.play_activate()
        self.overlay.point_to(target_x, target_y, "hey! i'm athena")
        self.overlay.set_voice_state(VoiceState.RESPONDING)

        welcome_text = "hey! i'm athena. hold control plus shift anytime and talk to me, or hold control plus alt to dictate text directly into any app."

        if self.config.get("floating_card_enabled", True):
            self.history_hud.show_response(welcome_text, "Who are you?")

        def on_done():
            self.overlay.start_flying_back()
            self.overlay.set_voice_state(VoiceState.IDLE)
            self.status_updated.emit("Ready")

        self.tts_engine.speak(welcome_text, on_complete=on_done)
