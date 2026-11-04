"""System Tray and Companion Panel Management for Clicky Windows.
Provides system tray icon, companion status, and opens the floating companion panel.
"""

from typing import Callable, Optional
from PyQt5.QtWidgets import QSystemTrayIcon, QMenu, QAction
from PyQt5.QtGui import QIcon, QPixmap, QPainter, QColor, QPolygonF
from PyQt5.QtCore import QPointF, Qt

from spidy.companion_panel import CompanionPanel

SPIDY_RED = QColor("#3380FF")


def create_spidy_icon() -> QIcon:
    """Dynamically generate a high-DPI 32x32 glowing blue triangle Spidy icon."""
    pixmap = QPixmap(32, 32)
    pixmap.fill(Qt.transparent)

    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.Antialiasing, True)

    poly = QPolygonF([
        QPointF(16.0, 4.0),
        QPointF(4.0, 26.0),
        QPointF(28.0, 26.0),
    ])
    painter.setBrush(SPIDY_RED)
    painter.setPen(Qt.NoPen)
    painter.drawPolygon(poly)
    painter.end()

    return QIcon(pixmap)


# Backwards compatibility alias
create_clicky_icon = create_spidy_icon


class TrayManager:
    """Manages the Windows system tray icon and companion dropdown panel."""

    def __init__(
        self,
        app,
        on_toggle_visibility: Optional[Callable[[bool], None]] = None,
        on_test_demo: Optional[Callable[[], None]] = None,
    ):
        self.app = app
        self.on_toggle_visibility = on_toggle_visibility
        self.on_test_demo = on_test_demo

        self.panel = CompanionPanel()
        if on_test_demo:
            self.panel.demo_requested.connect(on_test_demo)

        self.tray_icon = QSystemTrayIcon(create_spidy_icon(), self.app)
        self.tray_icon.setToolTip("Spidy — Everyday AI Desktop Companion")

        # Click on tray icon toggles Companion Panel
        self.tray_icon.activated.connect(self._on_tray_activated)

        self.menu = QMenu()
        self._build_menu()
        self.tray_icon.setContextMenu(self.menu)
        self.tray_icon.show()

    def _build_menu(self):
        self.menu.clear()

        panel_action = QAction("Open Companion Panel", self.menu)
        panel_action.triggered.connect(self.panel.show_near_tray)
        self.menu.addAction(panel_action)

        self.menu.addSeparator()

        demo_action = QAction("✨ Test Pointing Demo", self.menu)
        if self.on_test_demo:
            demo_action.triggered.connect(self.on_test_demo)
        self.menu.addAction(demo_action)

        self.menu.addSeparator()

        quit_action = QAction("Quit Spidy", self.menu)
        quit_action.triggered.connect(self.app.quit)
        self.menu.addAction(quit_action)

    def _on_tray_activated(self, reason):
        if reason == QSystemTrayIcon.Trigger:
            if self.panel.isVisible():
                self.panel.hide()
            else:
                self.panel.show_near_tray()

    def update_status(self, text: str):
        self.panel.set_status(text)
        self.tray_icon.setToolTip(f"Clicky — Status: {text}")
