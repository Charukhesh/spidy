"""Spidy Beige Rounded Tab HUD for Windows.

An elegant, warm-beige rounded card inspired by paper notebooks and tactile minimalism:
- Background: Soft warm beige / parchment (#F5F2EB) with subtle border (#E3DEC3) and 16px rounded corners.
- Typography: Exclusively Calibri / Calibri (Body) across all elements.
- Voice-First Companion: Pure conversational answers are spoken aloud; pressing '~' (tilde)
  toggles this tab to view and copy the text reply.
- Intelligent Auto-Display: Code blocks, tables, lists, and OCR results automatically display
  this tab with a 1-click Copy button.
"""

import logging
from typing import Optional

from PyQt5.QtCore import (
    Qt,
    QTimer,
    QPoint,
    QRect,
    QRectF,
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
    QGraphicsDropShadowEffect,
)
from PyQt5.QtGui import QFont, QColor, QCursor, QPainter, QBrush, QPen, QIcon
from spidy.sound_effects import sounds

logger = logging.getLogger("spidy.beige_hud")


class BeigeCardHUD(QWidget):
    """Warm beige rounded floating tab for Spidy's textual responses and code."""

    copied_signal = pyqtSignal()
    dismissed_signal = pyqtSignal()

    # Color Palette: Warm Beige & Espresso Ink
    COLOR_BG = QColor(245, 242, 235, 250)         # Soft parchment beige #F5F2EB
    COLOR_BORDER = QColor(227, 222, 204, 230)     # Muted border #E3DEC3
    COLOR_TEXT_PRIMARY = "#2C2523"                # Warm deep espresso charcoal
    COLOR_TEXT_SECONDARY = "#78716C"              # Muted warm stone gray
    COLOR_TEXT_PROMPT = "#57534E"                 # Prompt text color
    COLOR_BUTTON_BG = "#EAE5D9"                   # Slightly deeper beige button
    COLOR_BUTTON_HOVER = "#DDD7C8"                # Button hover
    COLOR_BUTTON_BORDER = "#D6CFBF"               # Button outline
    COLOR_ACCENT_RED = "#DC2626"                  # Spidy Red accent

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

        self.last_query = ""
        self.last_response = ""
        self._is_visible_on_screen = False

        # Drop shadow for soft floating depth
        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(28)
        shadow.setColor(QColor(0, 0, 0, 45))
        shadow.setOffset(0, 6)
        self.setGraphicsEffect(shadow)

        self._build_ui()
        self.hide()

    def _build_ui(self):
        """Construct the warm beige container with Calibri typography."""
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(14, 14, 14, 14)
        self.main_layout.setSpacing(0)

        # Card Container Frame
        self.card_frame = QFrame(self)
        self.card_frame.setObjectName("cardFrame")
        self.card_frame.setStyleSheet(f"""
            QFrame#cardFrame {{
                background-color: rgba(245, 242, 235, 0.98);
                border: 1.5px solid rgba(227, 222, 204, 0.95);
                border-radius: 16px;
            }}
        """)

        card_layout = QVBoxLayout(self.card_frame)
        card_layout.setContentsMargins(18, 14, 18, 14)
        card_layout.setSpacing(8)

        # 1. Header Bar: Spidy Badge + Prompt + Action Buttons
        header_layout = QHBoxLayout()
        header_layout.setContentsMargins(0, 0, 0, 0)
        header_layout.setSpacing(8)

        # Spidy Mini Emblem / Pill
        self.badge_label = QLabel("SPIDY")
        self.badge_label.setFont(QFont("Calibri", 10, QFont.Bold))
        self.badge_label.setStyleSheet(f"""
            color: {self.COLOR_ACCENT_RED};
            background-color: rgba(220, 38, 38, 0.08);
            border: 1px solid rgba(220, 38, 38, 0.20);
            border-radius: 10px;
            padding: 2px 8px;
        """)
        header_layout.addWidget(self.badge_label)

        # Prompt Query Label
        self.query_label = QLabel("")
        self.query_label.setFont(QFont("Calibri", 10, QFont.Medium))
        self.query_label.setStyleSheet(f"color: {self.COLOR_TEXT_PROMPT}; font-style: italic;")
        self.query_label.setWordWrap(False)
        header_layout.addWidget(self.query_label, stretch=1)

        # 1-Click Copy Button
        self.copy_btn = QPushButton("COPY")
        self.copy_btn.setFont(QFont("Calibri", 10, QFont.Bold))
        self.copy_btn.setCursor(Qt.PointingHandCursor)
        self.copy_btn.setStyleSheet(f"""
            QPushButton {{
                color: {self.COLOR_TEXT_PRIMARY};
                background-color: {self.COLOR_BUTTON_BG};
                border: 1px solid {self.COLOR_BUTTON_BORDER};
                border-radius: 8px;
                padding: 4px 12px;
            }}
            QPushButton:hover {{
                background-color: {self.COLOR_BUTTON_HOVER};
            }}
            QPushButton:pressed {{
                background-color: #D1C9B6;
            }}
        """)
        self.copy_btn.clicked.connect(self._on_copy_clicked)
        header_layout.addWidget(self.copy_btn)

        # Dismiss (Close) Button
        self.close_btn = QPushButton("✕")
        self.close_btn.setFont(QFont("Calibri", 10, QFont.Bold))
        self.close_btn.setFixedSize(24, 24)
        self.close_btn.setCursor(Qt.PointingHandCursor)
        self.close_btn.setStyleSheet(f"""
            QPushButton {{
                color: {self.COLOR_TEXT_SECONDARY};
                background: transparent;
                border: none;
                border-radius: 12px;
            }}
            QPushButton:hover {{
                background-color: rgba(0, 0, 0, 0.06);
                color: {self.COLOR_TEXT_PRIMARY};
            }}
        """)
        self.close_btn.clicked.connect(self.hide_card)
        header_layout.addWidget(self.close_btn)

        card_layout.addLayout(header_layout)

        # 2. Response Text Body (Scrollable if lengthy)
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setFrameShape(QFrame.NoFrame)
        self.scroll_area.setStyleSheet("background: transparent;")
        self.scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)

        self.response_label = QLabel("")
        self.response_label.setFont(QFont("Calibri", 11))
        self.response_label.setStyleSheet(f"""
            color: {self.COLOR_TEXT_PRIMARY};
            line-height: 1.45;
            background: transparent;
        """)
        self.response_label.setWordWrap(True)
        self.response_label.setTextInteractionFlags(Qt.TextSelectableByMouse)

        self.scroll_area.setWidget(self.response_label)
        card_layout.addWidget(self.scroll_area)

        # Keyboard hint pill at bottom
        hint_layout = QHBoxLayout()
        self.hint_label = QLabel("Press ~ (tilde) to toggle  •  Esc to close")
        self.hint_label.setFont(QFont("Calibri", 9))
        self.hint_label.setStyleSheet(f"color: {self.COLOR_TEXT_SECONDARY};")
        hint_layout.addWidget(self.hint_label, alignment=Qt.AlignRight)
        card_layout.addLayout(hint_layout)

        self.main_layout.addWidget(self.card_frame)

    def _position_near_cursor(self, width: int = 500, height: int = 220):
        """Position the floating card cleanly near the mouse cursor within visible screen bounds."""
        app = QApplication.instance()
        cursor_pos = QCursor.pos()
        screen = (app.screenAt(cursor_pos) if app else None) or (app.primaryScreen() if app else None)
        avail = screen.availableGeometry() if screen else QRect(0, 0, 1920, 1080)

        # Offset slightly down and right from cursor tip
        x = cursor_pos.x() + 18
        y = cursor_pos.y() + 18

        # Flip to left of cursor if it would clip the right edge
        if x + width > avail.right() - 12:
            x = cursor_pos.x() - width - 18

        # Flip to above cursor if it would clip the bottom edge
        if y + height > avail.bottom() - 12:
            y = cursor_pos.y() - height - 18

        # Hard clamp within available desktop rectangle
        x = max(avail.left() + 10, min(x, avail.right() - width - 10))
        y = max(avail.top() + 10, min(y, avail.bottom() - height - 10))

        self.setGeometry(x, y, width, height)

    def show_response(self, response_text: str, query: str = ""):
        """Display generated response text in the beige tab spawned near cursor."""
        self.last_query = query.strip()
        self.last_response = response_text.strip()

        # Update Query
        if self.last_query:
            display_q = f"“{self.last_query[:48]}...”" if len(self.last_query) > 48 else f"“{self.last_query}”"
            self.query_label.setText(display_q)
        else:
            self.query_label.setText("")

        # Update Response
        self.response_label.setText(self.last_response)

        # Compute dynamic card height based on text length
        lines = self.last_response.count("\n") + len(self.last_response) // 55
        target_h = min(400, max(130, 95 + lines * 20))
        self._position_near_cursor(width=500, height=target_h)

        # Reset copy button text
        self.copy_btn.setText("COPY")
        self.copy_btn.setStyleSheet(f"""
            QPushButton {{
                color: {self.COLOR_TEXT_PRIMARY};
                background-color: {self.COLOR_BUTTON_BG};
                border: 1px solid {self.COLOR_BUTTON_BORDER};
                border-radius: 8px;
                padding: 4px 12px;
            }}
            QPushButton:hover {{
                background-color: {self.COLOR_BUTTON_HOVER};
            }}
        """)

        self.show()
        self.raise_()
        self._is_visible_on_screen = True

    def toggle_visibility(self):
        """Toggle card on/off when user presses '~'."""
        if self.isVisible():
            self.hide_card()
        else:
            if self.last_response:
                self.show_response(self.last_response, self.last_query)
            else:
                self.show_response("Ready! Hold Ctrl+Alt to ask me anything.", "Spidy")

    def hide_card(self):
        """Close the floating card."""
        self.hide()
        self._is_visible_on_screen = False
        self.dismissed_signal.emit()

    def _on_copy_clicked(self):
        """Copy response to clipboard with confirmation feedback."""
        if not self.last_response:
            return
        clipboard = QApplication.clipboard()
        if clipboard:
            clipboard.setText(self.last_response)
            sounds.play_ding()
            self.copy_btn.setText("✓ Copied!")
            self.copy_btn.setStyleSheet(f"""
                QPushButton {{
                    color: #FFFFFF;
                    background-color: #16A34A;
                    border: 1px solid #15803D;
                    border-radius: 8px;
                    padding: 4px 12px;
                }}
            """)
            self.copied_signal.emit()
            QTimer.singleShot(2200, self._reset_copy_btn)

    def _reset_copy_btn(self):
        self.copy_btn.setText("COPY")
        self.copy_btn.setStyleSheet(f"""
            QPushButton {{
                color: {self.COLOR_TEXT_PRIMARY};
                background-color: {self.COLOR_BUTTON_BG};
                border: 1px solid {self.COLOR_BUTTON_BORDER};
                border-radius: 8px;
                padding: 4px 12px;
            }}
            QPushButton:hover {{
                background-color: {self.COLOR_BUTTON_HOVER};
            }}
        """)

    def keyPressEvent(self, event):
        """Dismiss on Esc or '~'."""
        if event.key() in (Qt.Key_Escape, Qt.Key_AsciiTilde):
            self.hide_card()
            event.accept()
        else:
            super().keyPressEvent(event)

