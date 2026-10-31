"""Athena Global Voice Dictation Manager.

Enables push-to-talk voice typing directly into any active Windows application:
- Holding 'Ctrl + Alt' records user speech with live visual feedback
- Releasing 'Ctrl + Alt' transcribes speech via local Faster-Whisper
- Automatically injects the transcribed text into the active focused window
- Restores original user clipboard non-destructively
- Plays subtle audio cues on activate and finish
"""

import time
import ctypes
import threading
import logging
from typing import Optional, Callable

from PyQt5.QtCore import (
    Qt,
    QObject,
    pyqtSignal,
    QTimer,
    QPoint,
)
from PyQt5.QtWidgets import (
    QWidget,
    QHBoxLayout,
    QLabel,
    QApplication,
    QFrame,
    QGraphicsOpacityEffect,
)
from PyQt5.QtGui import QCursor

from athena.config import load_config
from athena.audio_recorder import AudioRecorder
from athena.stt_engine import SpeechToText
from athena.sound_effects import sounds

logger = logging.getLogger("athena.dictation")

# Win32 Virtual Keys
VK_CONTROL = 0x11
VK_MENU = 0x12  # Alt
VK_V = 0x56
KEYEVENTF_KEYUP = 0x0002
CF_UNICODETEXT = 13


class DictationStatusHUD(QWidget):
    """Small floating pill near cursor or top center indicating dictation state."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowFlags(
            Qt.FramelessWindowHint
            | Qt.WindowStaysOnTopHint
            | Qt.Tool
            | Qt.SubWindow
        )
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        self.setAttribute(Qt.WA_ShowWithoutActivating, True)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        self.frame = QFrame(self)
        self.frame.setStyleSheet("""
            QFrame {
                background-color: rgba(15, 23, 42, 0.95);
                border: 1px solid rgba(56, 189, 248, 0.5);
                border-radius: 18px;
                padding: 6px 16px;
            }
        """)
        f_layout = QHBoxLayout(self.frame)
        f_layout.setContentsMargins(4, 2, 4, 2)
        f_layout.setSpacing(8)

        self.icon_label = QLabel("🎙️", self.frame)
        self.icon_label.setStyleSheet("font-size: 14px;")

        self.text_label = QLabel("Listening...", self.frame)
        self.text_label.setStyleSheet("color: #38BDF8; font-weight: 600; font-size: 12px;")

        f_layout.addWidget(self.icon_label)
        f_layout.addWidget(self.text_label)
        layout.addWidget(self.frame)

    def show_state(self, icon: str, message: str, color: str = "#38BDF8"):
        self.icon_label.setText(icon)
        self.text_label.setText(message)
        self.text_label.setStyleSheet(f"color: {color}; font-weight: 600; font-size: 12px;")
        self.frame.setStyleSheet(f"""
            QFrame {{
                background-color: rgba(15, 23, 42, 0.95);
                border: 1px solid {color}88;
                border-radius: 18px;
                padding: 6px 16px;
            }}
        """)
        self.adjustSize()
        self._reposition_near_cursor()
        self.show()
        self.raise_()

    def _reposition_near_cursor(self):
        """Float right above mouse cursor."""
        cursor_pos = QCursor.pos()
        x = cursor_pos.x() - self.width() // 2
        y = cursor_pos.y() - self.height() - 25

        # Screen clamp
        app = QApplication.instance()
        if app:
            screen = app.screenAt(cursor_pos) or app.primaryScreen()
            geom = screen.availableGeometry()
            x = max(geom.left() + 10, min(x, geom.right() - self.width() - 10))
            y = max(geom.top() + 10, min(y, geom.bottom() - self.height() - 10))

        self.move(x, y)


class DictationManager(QObject):
    """Manages push-to-talk voice typing into the active application."""

    dictation_started = pyqtSignal()
    dictation_finished = pyqtSignal(str)

    def __init__(self, stt_engine: SpeechToText, parent=None):
        super().__init__(parent)
        self.stt_engine = stt_engine
        self.config = load_config()

        self.hud = DictationStatusHUD()
        self.audio_recorder = AudioRecorder(sample_rate=16000, channels=1)

        self.is_dictating = False
        self._lock = threading.Lock()
        self.user32 = ctypes.windll.user32
        self.kernel32 = ctypes.windll.kernel32

    def start_dictation(self):
        """Start recording speech for dictation."""
        if self.is_dictating:
            return
        self.is_dictating = True
        logger.info("Dictation started.")

        sounds.play_dictation_start()
        self.hud.show_state("🎙️", "Dictating...", "#38BDF8")
        self.audio_recorder.start()
        self.dictation_started.emit()

    def stop_dictation_and_insert(self):
        """Stop recording, transcribe via Whisper, and type into active window."""
        if not self.is_dictating:
            return
        self.is_dictating = False
        logger.info("Dictation stopped. Transcribing...")

        self.hud.show_state("⏳", "Transcribing...", "#F59E0B")
        pcm_data = self.audio_recorder.stop()

        if not pcm_data or len(pcm_data) < 3200:
            logger.info("Dictation audio too brief, cancelled.")
            self.hud.hide()
            return

        def _transcribe_and_type():
            try:
                transcript = self.stt_engine.transcribe_pcm(pcm_data).strip()
                logger.info(f"Dictation transcript: '{transcript}'")

                if not transcript:
                    QTimer.singleShot(0, self.hud.hide)
                    return

                # Inject text into foreground window
                self._inject_text(transcript)
                sounds.play_dictation_stop()

                QTimer.singleShot(0, lambda: self.hud.show_state("✓", "Typed!", "#10B981"))
                QTimer.singleShot(1000, self.hud.hide)
                self.dictation_finished.emit(transcript)

            except Exception as e:
                logger.error(f"Error during dictation pipeline: {e}")
                QTimer.singleShot(0, self.hud.hide)

        threading.Thread(target=_transcribe_and_type, daemon=True).start()

    def _read_clipboard_text(self) -> Optional[str]:
        try:
            app = QApplication.instance()
            if app:
                clip = app.clipboard()
                return clip.text() if clip else None
        except Exception:
            pass
        return None

    def _set_clipboard_text(self, text: str) -> bool:
        try:
            app = QApplication.instance()
            if app:
                clip = app.clipboard()
                if clip:
                    clip.setText(text)
                    return True
        except Exception:
            pass
        return False

    def _inject_text(self, text: str):
        """Inject text into the active focused control via clipboard paste."""
        # 1. Snapshot previous user clipboard
        original_clipboard = self._read_clipboard_text()

        # 2. Put transcribed text onto clipboard
        self._set_clipboard_text(text)

        # 3. Simulate Ctrl+V to paste into active window
        time.sleep(0.03)
        self.user32.keybd_event(VK_CONTROL, 0, 0, 0)
        self.user32.keybd_event(VK_V, 0, 0, 0)
        self.user32.keybd_event(VK_V, 0, KEYEVENTF_KEYUP, 0)
        self.user32.keybd_event(VK_CONTROL, 0, KEYEVENTF_KEYUP, 0)

        # 4. Wait briefly then restore previous clipboard text non-destructively
        def _restore_clip():
            time.sleep(0.20)
            if original_clipboard is not None:
                self._set_clipboard_text(original_clipboard)

        threading.Thread(target=_restore_clip, daemon=True).start()
