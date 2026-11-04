"""Spidy Everyday Desktop Companion for Windows.

Entry point initializing:
- High-DPI PyQt5 application
- Transparent click-through cursor overlay window
- Companion system tray icon with settings
- Push-to-talk voice pipeline with Google Gemini / Groq Vision integration
"""

import sys
import os
import logging
from PyQt5.QtWidgets import QApplication
from PyQt5.QtCore import Qt

# Ensure package import works from root
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from spidy.config import load_config
from spidy.cursor_overlay import ClickyCursorOverlay
from spidy.companion_manager import CompanionManager
from spidy.tray_manager import TrayManager

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)


def main():
    # Enable High DPI scaling
    QApplication.setAttribute(Qt.AA_EnableHighDpiScaling, True)
    QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps, True)

    app = QApplication(sys.argv)
    app.setApplicationName("Spidy")
    app.setQuitOnLastWindowClosed(False)

    # 1. Initialize Fullscreen Transparent Overlay Window
    overlay = ClickyCursorOverlay()
    overlay.show()

    # 2. Initialize Companion Coordinator Pipeline
    manager = CompanionManager(overlay=overlay)

    # 3. Initialize System Tray Manager
    def on_toggle_visibility(visible: bool):
        if visible:
            overlay.show()
        else:
            overlay.hide()

    tray = TrayManager(
        app=app,
        on_toggle_visibility=on_toggle_visibility,
        on_test_demo=manager.run_onboarding_demo,
    )

    # Connect status signal
    manager.status_updated.connect(tray.update_status)

    logging.info("=" * 60)
    logging.info("🕷️ Spidy Everyday Desktop Companion is active!")
    logging.info("Hold 'Ctrl + Alt' to speak to Spidy and analyze your screen.")
    logging.info("Press '~' (tilde) to toggle the warm beige card and copy text responses.")
    logging.info("=" * 60)

    # Start Qt event loop
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()

