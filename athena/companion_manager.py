"""Central Companion Manager for Clicky Windows.

Orchestrates:
- Hardware-level Push-to-Talk hotkey detection via GetAsyncKeyState
- Pure ctypes PCM audio capture with live waveform level feedback
- Multi-monitor screenshot capture
- Local Faster-Whisper transcription directly from memory (float32 numpy array)
- Multimodal AI reasoning via Grok 2 Vision
- Multi-monitor coordinate mapping and bezier flight pointing animations
- Natural voice speech playback via Microsoft Edge Neural TTS
"""

import os
import time
import ctypes
import threading
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

        # Pipeline state flags
        self.is_hotkey_down = False
        self._processing_lock = threading.Lock()
        self._stop_hotkey_thread = threading.Event()

        # Start hardware hotkey polling thread
        self._start_hotkey_listener()

    def _start_hotkey_listener(self):
        """Hardware-level hotkey polling thread using GetAsyncKeyState.
        
        Guarantees 100% reliable detection of key press and key release,
        immune to modifier release order and Windows OS keyrepeat deadlocks.
        """
        user32 = ctypes.windll.user32

        def _poll_keys():
            was_pressed = False
            while not self._stop_hotkey_thread.is_set():
                hotkey_choice = self.config.get("hotkey", "ctrl+shift").lower()

                if hotkey_choice == "ctrl+alt":
                    is_pressed = bool(user32.GetAsyncKeyState(VK_CONTROL) & 0x8000) and bool(
                        user32.GetAsyncKeyState(VK_MENU) & 0x8000
                    )
                elif hotkey_choice == "alt+space":
                    is_pressed = bool(user32.GetAsyncKeyState(VK_MENU) & 0x8000) and bool(
                        user32.GetAsyncKeyState(VK_SPACE) & 0x8000
                    )
                else:  # default "ctrl+shift"
                    is_pressed = bool(user32.GetAsyncKeyState(VK_CONTROL) & 0x8000) and bool(
                        user32.GetAsyncKeyState(VK_SHIFT) & 0x8000
                    )

                # State Transitions
                if is_pressed and not was_pressed:
                    was_pressed = True
                    self.is_hotkey_down = True
                    self._on_hotkey_pressed()
                elif not is_pressed and was_pressed:
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
        self.audio_recorder.start()

    def _on_hotkey_released(self):
        """Push-to-talk released: process audio, screenshot, and query Grok."""
        logger.info("Push-to-talk released -> Processing...")
        self.status_updated.emit("Thinking...")
        self.overlay.set_voice_state(VoiceState.PROCESSING)

        pcm_data = self.audio_recorder.stop()
        if not pcm_data or len(pcm_data) < 3200:
            logger.info("Voice input too brief. Returning to idle.")
            self.overlay.set_voice_state(VoiceState.IDLE)
            self.status_updated.emit("Ready")
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
                # 1. Capture screen context immediately upon release
                screen_captures = ScreenCaptureUtility.capture_all_screens()

                # 2. Transcribe audio in-memory using Faster-Whisper float32 array
                transcript = self.stt_engine.transcribe_pcm(pcm_data)
                logger.info(f"User voice transcript: '{transcript}'")

                if not transcript.strip():
                    logger.info("Empty transcript. Resetting.")
                    self.overlay.set_voice_state(VoiceState.IDLE)
                    self.status_updated.emit("Ready")
                    return

                # 3. Query Multimodal AI Vision (Gemini / Groq / Grok)
                ai_response = self.ai_client.query(transcript, screen_captures)
                logger.info(f"Clicky AI replied: '{ai_response.spoken_text}'")

                # 4. Map element pointing coordinates to global screen points
                if ai_response.point_target and screen_captures:
                    target = ai_response.point_target
                    global_x, global_y = self._map_target_to_global_coords(target, screen_captures)
                    logger.info(f"Pointing at ({global_x}, {global_y}) - label='{target.label}'")
                    self.overlay.point_to(global_x, global_y, target.label)

                # 5. Speak response via Edge Neural TTS
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

        self.overlay.point_to(target_x, target_y, "hey! i'm athena")
        self.overlay.set_voice_state(VoiceState.RESPONDING)

        welcome_text = "hey! i'm athena. hold control plus shift anytime and talk to me while looking at your screen."

        def on_done():
            self.overlay.start_flying_back()
            self.overlay.set_voice_state(VoiceState.IDLE)
            self.status_updated.emit("Ready")

        self.tts_engine.speak(welcome_text, on_complete=on_done)
