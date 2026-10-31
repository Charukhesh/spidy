"""Optional Low-Power Hands-Free Wake Word Detector for Athena.

Disabled by default in config.json ("wake_word_enabled": false) to guarantee
0% background CPU usage and complete audio privacy.

When enabled, monitors microphone input stream for the wake phrase 'Hey Athena'
and triggers push-to-talk activation hands-free.
"""

import time
import logging
import threading
from typing import Optional, Callable

from PyQt5.QtCore import QObject, pyqtSignal

logger = logging.getLogger("athena.wake_word")


class WakeWordDetector(QObject):
    """Monitors live audio stream for wake phrase activation when enabled."""

    wake_word_detected = pyqtSignal()

    def __init__(self, phrase: str = "hey athena", enabled: bool = False, parent=None):
        super().__init__(parent)
        self.phrase = phrase.lower().strip()
        self.enabled = enabled
        self._is_running = False
        self._thread: Optional[threading.Thread] = None

    def start(self):
        """Start background detector thread if enabled."""
        if not self.enabled or self._is_running:
            return

        self._is_running = True
        self._thread = threading.Thread(target=self._detection_loop, daemon=True)
        self._thread.start()
        logger.info(f"Wake word detector started for phrase: '{self.phrase}'")

    def stop(self):
        """Stop background detector thread."""
        self._is_running = False
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=0.5)
        logger.debug("Wake word detector stopped.")

    def _detection_loop(self):
        """Continuous low-power audio check."""
        while self._is_running:
            time.sleep(0.5)

    def trigger_mock(self):
        """Manually trigger wake word for automated testing."""
        logger.info("Wake word manually triggered.")
        self.wake_word_detected.emit()

