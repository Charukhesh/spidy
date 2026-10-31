"""Athena Floating Answer & History HUD Overlay.

Sleek translucent floating HUD displayed near the bottom-right of the screen.
Features:
- Glassmorphic dark styling with subtle border and shadow
- Shows user's latest query and Athena's spoken response
- 1-click "Copy Answer" button (copies response to clipboard)
- Smooth auto-fade after 8 seconds
- Auto-pause on mouse hover so user can read or copy at leisure
- Close button to dismiss immediately
"""

import logging
from typing import Optional

from PyQt5.QtCore import (
    Qt,
    QTimer,
    QPoint,
    QPropertyAnimation,
    QEasingCurve,
    pyqtSignal,
)
from PyQt5.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QFrame,
    QApplication,
    QGraphicsOpacityEffect,
)
from PyQt5.QtGui import QFont, QColor, QCursor

logger = logging.getLogger("athena.floating_hud")


class FloatingHistoryCard(QWidget):
    """Translucent floating HUD card displaying Athena's latest answer."""

    dismissed = pyqtSignal()

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

        self._fade_timer = QTimer(self)
        self._fade_timer.setSingleShot(True)
        self._fade_timer.timeout.connect(self._start_fade_out)
        self._auto_fade_delay_ms = 8000

        self._opacity_effect = QGraphicsOpacityEffect(self)
        self.setGraphicsEffect(self._opacity_effect)
        self._opacity_anim: Optional[QPropertyAnimation] = None

        self._current_response_text = ""
        self._build_ui()

    def _build_ui(self):
        self.setFixedWidth(380)

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(10, 10, 10, 10)

        # Outer Glass Card
        self.card_frame = QFrame(self)
        self.card_frame.setObjectName("cardFrame")
        self.card_frame.setStyleSheet("""
            QFrame#cardFrame {
                background-color: rgba(18, 22, 32, 0.94);
                border: 1px solid rgba(80, 140, 255, 0.40);
                border-radius: 12px;
            }
        """)

        card_layout = QVBoxLayout(self.card_frame)
        card_layout.setContentsMargins(14, 12, 14, 12)
        card_layout.setSpacing(8)

        # Header: Athena Logo/Badge + Close Button
        header_layout = QHBoxLayout()
        header_layout.setContentsMargins(0, 0, 0, 0)

        self.title_label = QLabel("✦ Athena", self.card_frame)
        self.title_label.setStyleSheet("color: #4DA6FF; font-weight: bold; font-size: 13px;")

        self.status_badge = QLabel("Active", self.card_frame)
        self.status_badge.setStyleSheet("""
            color: #A0C8FF;
            background-color: rgba(77, 166, 255, 0.15);
            border-radius: 8px;
            padding: 2px 6px;
            font-size: 10px;
        """)

        self.btn_close = QPushButton("✕", self.card_frame)
        self.btn_close.setFixedSize(20, 20)
        self.btn_close.setCursor(QCursor(Qt.PointingHandCursor))
        self.btn_close.setStyleSheet("""
            QPushButton {
                color: #8892B0;
                background: transparent;
                border: none;
                font-size: 12px;
                font-weight: bold;
            }
            QPushButton:hover {
                color: #FF5555;
            }
        """)
        self.btn_close.clicked.connect(self.hide_card)

        header_layout.addWidget(self.title_label)
        header_layout.addWidget(self.status_badge)
        header_layout.addStretch()
        header_layout.addWidget(self.btn_close)
        card_layout.addLayout(header_layout)

        # User Query Pill (optional if query exists)
        self.query_label = QLabel(self.card_frame)
        self.query_label.setWordWrap(True)
        self.query_label.setStyleSheet("""
            color: #8892B0;
            font-size: 11px;
            font-style: italic;
            border-left: 2px solid #4DA6FF;
            padding-left: 6px;
        """)
        self.query_label.hide()
        card_layout.addWidget(self.query_label)

        # Spoken Response Body in scrollable or auto-sizing container
        self.response_label = QLabel(self.card_frame)
        self.response_label.setWordWrap(True)
        self.response_label.setTextInteractionFlags(Qt.TextSelectableByMouse)
        self.response_label.setStyleSheet("""
            color: #F0F4FC;
            font-size: 13px;
            line-height: 1.4;
        """)
        card_layout.addWidget(self.response_label)

        # Action Bar: Copy Button + Timestamp/Hint
        action_layout = QHBoxLayout()
        action_layout.setContentsMargins(0, 4, 0, 0)

        self.btn_copy = QPushButton("📋 Copy Answer", self.card_frame)
        self.btn_copy.setCursor(QCursor(Qt.PointingHandCursor))
        self.btn_copy.setStyleSheet("""
            QPushButton {
                background-color: rgba(77, 166, 255, 0.20);
                color: #BEE3FF;
                border: 1px solid rgba(77, 166, 255, 0.35);
                border-radius: 6px;
                padding: 4px 10px;
                font-size: 11px;
                font-weight: 600;
            }
            QPushButton:hover {
                background-color: rgba(77, 166, 255, 0.35);
                color: #FFFFFF;
            }
            QPushButton:pressed {
                background-color: rgba(77, 166, 255, 0.50);
            }
        """)
        self.btn_copy.clicked.connect(self._copy_to_clipboard)

        self.hint_label = QLabel("auto-fades in 8s", self.card_frame)
        self.hint_label.setStyleSheet("color: #64748B; font-size: 10px;")

        action_layout.addWidget(self.btn_copy)
        action_layout.addStretch()
        action_layout.addWidget(self.hint_label)
        card_layout.addLayout(action_layout)

        main_layout.addWidget(self.card_frame)

    def show_response(self, text: str, query: Optional[str] = None):
        """Display an answer on the floating HUD and start the auto-fade countdown."""
        if not text or not text.strip():
            return

        self._current_response_text = text.strip()
        self.response_label.setText(self._current_response_text)

        if query and query.strip():
            self.query_label.setText(f"You: \"{query.strip()}\"")
            self.query_label.show()
        else:
            self.query_label.hide()

        self.btn_copy.setText("📋 Copy Answer")
        self.hint_label.setText("auto-fades in 8s")

        # Reposition to bottom-right of primary screen
        self._reposition_bottom_right()

        # Stop existing animations
        if self._opacity_anim and self._opacity_anim.state() == QPropertyAnimation.Running:
            self._opacity_anim.stop()

        self._opacity_effect.setOpacity(1.0)
        self.show()
        self.raise_()

        # Reset auto-fade timer
        self._fade_timer.stop()
        self._fade_timer.start(self._auto_fade_delay_ms)

    def _reposition_bottom_right(self):
        """Place HUD neatly in bottom-right corner above taskbar."""
        app = QApplication.instance()
        if not app:
            return
        screen = app.primaryScreen()
        avail = screen.availableGeometry()

        self.adjustSize()
        w = self.width()
        h = self.height()

        margin_right = 24
        margin_bottom = 24
        x = avail.right() - w - margin_right
        y = avail.bottom() - h - margin_bottom

        self.move(x, y)

    def _copy_to_clipboard(self):
        """Copy answer text to system clipboard."""
        if not self._current_response_text:
            return
        clipboard = QApplication.clipboard()
        if clipboard:
            clipboard.setText(self._current_response_text)
            self.btn_copy.setText("✓ Copied!")
            QTimer.singleShot(2000, lambda: self.btn_copy.setText("📋 Copy Answer"))

    def _start_fade_out(self):
        """Smoothly fade card out."""
        self._opacity_anim = QPropertyAnimation(self._opacity_effect, b"opacity")
        self._opacity_anim.setDuration(600)
        self._opacity_anim.setStartValue(1.0)
        self._opacity_anim.setEndValue(0.0)
        self._opacity_anim.setEasingCurve(QEasingCurve.OutCubic)
        self._opacity_anim.finished.connect(self.hide_card)
        self._opacity_anim.start()

    def hide_card(self):
        """Instantly dismiss card."""
        self._fade_timer.stop()
        if self._opacity_anim and self._opacity_anim.state() == QPropertyAnimation.Running:
            self._opacity_anim.stop()
        self.hide()
        self.dismissed.emit()

    def enterEvent(self, event):
        """Pause auto-fade when mouse hovers over card so user can comfortably read."""
        self._fade_timer.stop()
        if self._opacity_anim and self._opacity_anim.state() == QPropertyAnimation.Running:
            self._opacity_anim.stop()
        self._opacity_effect.setOpacity(1.0)
        self.hint_label.setText("paused while hovered")
        super().enterEvent(event)

    def leaveEvent(self, event):
        """Resume fade out after 3 seconds when mouse leaves."""
        self.hint_label.setText("auto-fades in 3s")
        self._fade_timer.start(3000)
        super().leaveEvent(event)

