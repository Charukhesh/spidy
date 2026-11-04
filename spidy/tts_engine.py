"""Text-To-Speech (TTS) Engine using Microsoft Edge Neural TTS with SAPI fallback.
Completely free, natural neural voices, zero API cost.
"""

import os
import sys
import asyncio
import tempfile
import threading
import logging
from typing import Optional, List, Callable

logger = logging.getLogger("clicky.tts")


class TextToSpeech:
    """High-quality zero-cost TTS using edge-tts + pygame playback."""

    def __init__(self, voice: str = "en-US-JennyNeural", rate: str = "+0%"):
        self.voice = voice
        self.rate = rate
        self._is_playing = False
        self._stop_event = threading.Event()
        self._lock = threading.Lock()
        self._init_pygame()

    def _init_pygame(self):
        try:
            import pygame
            if not pygame.mixer.get_init():
                pygame.mixer.init(frequency=24000, size=-16, channels=1, buffer=1024)
        except Exception as e:
            logger.warning(f"Pygame mixer init warning: {e}")

    @property
    def is_playing(self) -> bool:
        try:
            import pygame
            if pygame.mixer.get_init():
                return pygame.mixer.music.get_busy() or self._is_playing
        except Exception:
            pass
        return self._is_playing

    def stop(self):
        """Immediately interrupt and stop any ongoing speech playback."""
        self._stop_event.set()
        try:
            import pygame
            if pygame.mixer.get_init():
                pygame.mixer.music.stop()
        except Exception:
            pass
        self._is_playing = False

    def speak(self, text: str, on_complete: Optional[Callable[[], None]] = None):
        """Asynchronously speak text aloud."""
        clean_text = text.strip()
        if not clean_text:
            if on_complete:
                on_complete()
            return

        threading.Thread(
            target=self._speak_worker,
            args=(clean_text, on_complete),
            daemon=True,
        ).start()

    def _speak_worker(self, text: str, on_complete: Optional[Callable[[], None]] = None):
        self.stop()
        self._stop_event.clear()
        self._is_playing = True

        try:
            # 1. Try Microsoft Edge Neural TTS
            success = self._speak_edge_tts(text)
            if not success and not self._stop_event.is_set():
                # 2. Fallback to Windows SAPI
                self._speak_sapi(text)
        except Exception as e:
            logger.error(f"TTS error: {e}")
        finally:
            self._is_playing = False
            if on_complete and not self._stop_event.is_set():
                try:
                    on_complete()
                except Exception:
                    pass

    def _speak_edge_tts(self, text: str) -> bool:
        """Synthesize via edge-tts and play with pygame."""
        try:
            import edge_tts
            import pygame

            with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as tf:
                mp3_path = tf.name

            async def _run():
                communicate = edge_tts.Communicate(text, self.voice, rate=self.rate)
                await communicate.save(mp3_path)

            asyncio.run(_run())

            if self._stop_event.is_set():
                try:
                    os.remove(mp3_path)
                except Exception:
                    pass
                return True

            if os.path.exists(mp3_path) and os.path.getsize(mp3_path) > 100:
                pygame.mixer.music.load(mp3_path)
                pygame.mixer.music.play()

                while pygame.mixer.music.get_busy() and not self._stop_event.is_set():
                    pygame.time.Clock().tick(30)

                if self._stop_event.is_set():
                    pygame.mixer.music.stop()

                try:
                    os.remove(mp3_path)
                except Exception:
                    pass
                return True
        except Exception as e:
            logger.warning(f"Edge TTS synthesis notice: {e}")
        return False

    def _speak_sapi(self, text: str):
        """Windows native SAPI voice fallback."""
        try:
            import win32com.client
            speaker = win32com.client.Dispatch("SAPI.SpVoice")
            speaker.Speak(text)
        except Exception:
            import subprocess
            import sys
            escaped = text.replace("'", "''").replace('"', '`"')
            ps = f'Add-Type -AssemblyName System.Speech; (New-Object System.Speech.Synthesis.SpeechSynthesizer).Speak("{escaped}")'
            creationflags = 0x08000000 if sys.platform == "win32" else 0
            subprocess.run(["powershell", "-NoProfile", "-Command", ps], capture_output=True, creationflags=creationflags)

