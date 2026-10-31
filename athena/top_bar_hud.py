"""Athena Top-Center Black Glass Dynamic Bar HUD.

A sleek, aesthetic top-center glass dynamic island inspired by Clicky:
- Idle State: 2-3 mm thickness (~10px height, 110px width) obsidian black glass bar pinned to top-center.
- Listening State: Dynamic pill showing blue audio pulse and 'Listening...'.
- Thinking State: Pulsing glow and 'Thinking...'.
- Expanded State: Smooth fluid downward expansion displaying user prompt, formatted response text,
  one-click 'Copy Answer' button, and dismiss action.
- Auto-collapse: Smoothly returns to the 2-3 mm bar after 8 seconds (pauses on hover).
- Click-to-reopen: Clicking or hovering the collapsed top bar re-opens the latest answer.
"""

import logging
from enum import Enum
from typing import Optional

from PyQt5.QtCore import (
    Qt,
    QTimer,
    QPoint,
    QRect,
    QPropertyAnimation,
    QEasingCurve,
    pyqtSignal,
    pyqtProperty,
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
from PyQt5.QtGui import QFont, QColor, QCursor, QPainter, QBrush, QPen

logger = logging.getLogger("athena.top_bar_hud")


class TopBarState(Enum):
    COLLAPSED = "collapsed"
    LISTENING = "listening"
    THINKING = "thinking"
    EXPANDED = "expanded"


class TopBarGlassHUD(QWidget):
    """Dynamic top-center black glass bar HUD."""

    copied_signal = pyqtSignal()
    dismissed_signal = pyqtSignal()

    # Clicky Design System Colors (decoded from Swift DesignSystem)
    COLOR_BG = "rgba(16, 18, 17, 0.94)"       # DS.Colors.background #101211
    COLOR_SURFACE = "rgba(23, 25, 24, 0.96)"  # DS.Colors.surface1 #171918
    COLOR_SURFACE2 = "rgba(32, 34, 33, 0.90)" # DS.Colors.surface2 #202221
    COLOR_BORDER = "rgba(55, 59, 57, 0.70)"   # DS.Colors.borderSubtle #373B39
    COLOR_TEXT_PRIMARY = "#ECEEED"             # DS.Colors.textPrimary
    COLOR_TEXT_SECONDARY = "#ADB5B2"           # DS.Colors.textSecondary
    COLOR_ACCENT = "#2563eb"                  # DS.Colors.blue600
    COLOR_ACCENT_GLOW = "#60a5fa"             # DS.Colors.blue400

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

        self.current_state = TopBarState.COLLAPSED
        self.last_query = ""
        self.last_response = ""

        # Auto-collapse timer
        self._collapse_timer = QTimer(self)
        self._collapse_timer.setSingleShot(True)
        self._collapse_timer.timeout.connect(self.collapse_to_bar)
        self._auto_collapse_delay_ms = 8000

        # Animation
        self._anim = QPropertyAnimation(self, b"geometry")
        self._anim.setEasingCurve(QEasingCurve.OutCubic)
        self._anim.setDuration(240)

        self._build_ui()
        self.collapse_to_bar(animated=False)

    def _build_ui(self):
        """Construct the glass container and widgets."""
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        self.main_layout.setSpacing(0)

        # Main Glass Card Frame
        self.glass_frame = QFrame(self)
        self.glass_frame.setObjectName("glassFrame")
        self._apply_frame_style(TopBarState.COLLAPSED)

        self.frame_layout = QVBoxLayout(self.glass_frame)
        self.frame_layout.setContentsMargins(4, 1, 4, 1)
        self.frame_layout.setSpacing(0)

        # 1. Collapsed Hairline Indicator Widget (2-3 mm high)
        self.collapsed_pill = QFrame(self.glass_frame)
        self.collapsed_pill.setFixedHeight(2)
        self.collapsed_pill.setFixedWidth(36)
        self.collapsed_pill.setStyleSheet(f"""
            QFrame {{
                background-color: {self.COLOR_BORDER};
                border-radius: 1px;
            }}
            QFrame:hover {{
                background-color: {self.COLOR_ACCENT_GLOW};
            }}
        """)
        self.frame_layout.addWidget(self.collapsed_pill, alignment=Qt.AlignCenter)

        # 2. Status Row (Listening / Thinking pill)
        self.status_row = QWidget(self.glass_frame)
        status_layout = QHBoxLayout(self.status_row)
        status_layout.setContentsMargins(4, 2, 4, 2)
        status_layout.setSpacing(6)

        self.status_icon = QLabel("●", self.status_row)
        self.status_icon.setStyleSheet(f"color: {self.COLOR_ACCENT_GLOW}; font-size: 11px;")
        self.status_text = QLabel("Listening...", self.status_row)
        self.status_text.setStyleSheet(f"color: {self.COLOR_TEXT_PRIMARY}; font-size: 12px; font-weight: 600;")

        status_layout.addStretch()
        status_layout.addWidget(self.status_icon)
        status_layout.addWidget(self.status_text)
        status_layout.addStretch()
        self.status_row.setVisible(False)
        self.frame_layout.addWidget(self.status_row)

        # 3. Expanded Content Container
        self.content_widget = QWidget(self.glass_frame)
        content_layout = QVBoxLayout(self.content_widget)
        content_layout.setContentsMargins(4, 0, 4, 2)
        content_layout.setSpacing(6)

        # Top Header Row: Brand badge + Close Button
        header_row = QHBoxLayout()
        header_row.setContentsMargins(0, 0, 0, 0)

        self.brand_label = QLabel("✦ Athena", self.content_widget)
        self.brand_label.setStyleSheet(f"""
            color: {self.COLOR_ACCENT_GLOW};
            font-size: 12px;
            font-weight: bold;
            font-family: 'Segoe UI', system-ui, sans-serif;
        """)

        self.state_chip = QLabel("Ready", self.content_widget)
        self.state_chip.setStyleSheet(f"""
            color: {self.COLOR_TEXT_SECONDARY};
            background-color: {self.COLOR_SURFACE2};
            border-radius: 6px;
            padding: 1px 6px;
            font-size: 10px;
        """)

        self.btn_close = QPushButton("✕", self.content_widget)
        self.btn_close.setFixedSize(18, 18)
        self.btn_close.setCursor(QCursor(Qt.PointingHandCursor))
        self.btn_close.setStyleSheet(f"""
            QPushButton {{
                color: {self.COLOR_TEXT_SECONDARY};
                background: transparent;
                border: none;
                font-size: 11px;
                font-weight: bold;
            }}
            QPushButton:hover {{
                color: #ff6b6b;
            }}
        """)
        self.btn_close.clicked.connect(self.collapse_to_bar)

        header_row.addWidget(self.brand_label)
        header_row.addWidget(self.state_chip)
        header_row.addStretch()
        header_row.addWidget(self.btn_close)
        content_layout.addLayout(header_row)

        # User Query Prompt Pill
        self.query_label = QLabel("", self.content_widget)
        self.query_label.setWordWrap(True)
        self.query_label.setStyleSheet(f"""
            color: {self.COLOR_TEXT_SECONDARY};
            font-size: 11px;
            font-style: italic;
            padding: 2px 4px;
        """)
        content_layout.addWidget(self.query_label)

        # Response Scroll Area
        self.scroll_area = QScrollArea(self.content_widget)
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setFrameShape(QFrame.NoFrame)
        self.scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.scroll_area.setStyleSheet("""
            QScrollArea {
                background: transparent;
                border: none;
            }
            QScrollBar:vertical {
                background: transparent;
                width: 4px;
                margin: 0;
            }
            QScrollBar::handle:vertical {
                background: rgba(255, 255, 255, 0.2);
                border-radius: 2px;
            }
        """)

        self.response_label = QLabel("", self.scroll_area)
        self.response_label.setWordWrap(True)
        self.response_label.setTextInteractionFlags(Qt.TextSelectableByMouse)
        self.response_label.setStyleSheet(f"""
            color: {self.COLOR_TEXT_PRIMARY};
            font-size: 13px;
            line-height: 1.45;
            font-family: 'Segoe UI', system-ui, sans-serif;
            background: transparent;
            padding: 2px 0px;
        """)
        self.scroll_area.setWidget(self.response_label)
        content_layout.addWidget(self.scroll_area)

        # Action Button Row (Copy Answer)
        action_row = QHBoxLayout()
        action_row.setContentsMargins(0, 4, 0, 0)

        self.btn_copy = QPushButton("Copy Answer", self.content_widget)
        self.btn_copy.setCursor(QCursor(Qt.PointingHandCursor))
        self.btn_copy.setStyleSheet(f"""
            QPushButton {{
                background-color: {self.COLOR_SURFACE2};
                color: {self.COLOR_TEXT_PRIMARY};
                border: 1px solid {self.COLOR_BORDER};
                border-radius: 6px;
                padding: 4px 10px;
                font-size: 11px;
                font-weight: 500;
            }}
            QPushButton:hover {{
                background-color: {self.COLOR_ACCENT};
                border-color: {self.COLOR_ACCENT};
                color: #FFFFFF;
            }}
        """)
        self.btn_copy.clicked.connect(self._copy_answer_to_clipboard)

        action_row.addStretch()
        action_row.addWidget(self.btn_copy)
        content_layout.addLayout(action_row)

        self.content_widget.setVisible(False)
        self.frame_layout.addWidget(self.content_widget)

        self.main_layout.addWidget(self.glass_frame)

    def _apply_frame_style(self, state: TopBarState):
        """Update glass stylesheet based on state."""
        if state == TopBarState.COLLAPSED:
            self.glass_frame.setStyleSheet(f"""
                QFrame#glassFrame {{
                    background-color: {self.COLOR_BG};
                    border-bottom: 1px solid {self.COLOR_BORDER};
                    border-left: 1px solid {self.COLOR_BORDER};
                    border-right: 1px solid {self.COLOR_BORDER};
                    border-top: none;
                    border-bottom-left-radius: 6px;
                    border-bottom-right-radius: 6px;
                }}
            """)
        elif state in (TopBarState.LISTENING, TopBarState.THINKING):
            self.glass_frame.setStyleSheet(f"""
                QFrame#glassFrame {{
                    background-color: {self.COLOR_BG};
                    border: 1px solid {self.COLOR_ACCENT_GLOW};
                    border-top: none;
                    border-bottom-left-radius: 10px;
                    border-bottom-right-radius: 10px;
                }}
            """)
        else:  # EXPANDED
            self.glass_frame.setStyleSheet(f"""
                QFrame#glassFrame {{
                    background-color: {self.COLOR_SURFACE};
                    border: 1px solid {self.COLOR_BORDER};
                    border-top: none;
                    border-bottom-left-radius: 14px;
                    border-bottom-right-radius: 14px;
                }}
            """)

    def _get_top_center_rect(self, width: int, height: int) -> QRect:
        """Calculate screen-centered geometry anchored to top edge."""
        screen = QApplication.primaryScreen()
        geom = screen.geometry() if screen else QRect(0, 0, 1920, 1080)
        x = geom.x() + (geom.width() - width) // 2
        y = geom.y()
        return QRect(x, y, width, height)

    def set_listening(self):
        """Transition HUD into Listening pill mode."""
        self.current_state = TopBarState.LISTENING
        self._collapse_timer.stop()
        self._apply_frame_style(TopBarState.LISTENING)

        self.frame_layout.setContentsMargins(6, 2, 6, 2)
        self.frame_layout.setSpacing(4)
        self.collapsed_pill.setVisible(False)
        self.content_widget.setVisible(False)
        self.status_row.setVisible(True)

        self.status_icon.setText("●")
        self.status_icon.setStyleSheet(f"color: {self.COLOR_ACCENT_GLOW}; font-size: 11px;")
        self.status_text.setText("Listening...")

        target_rect = self._get_top_center_rect(180, 28)
        self._animate_to_rect(target_rect)
        self.show()

    def set_thinking(self):
        """Transition HUD into Thinking pill mode."""
        self.current_state = TopBarState.THINKING
        self._collapse_timer.stop()
        self._apply_frame_style(TopBarState.THINKING)

        self.frame_layout.setContentsMargins(6, 2, 6, 2)
        self.frame_layout.setSpacing(4)
        self.collapsed_pill.setVisible(False)
        self.content_widget.setVisible(False)
        self.status_row.setVisible(True)

        self.status_icon.setText("✦")
        self.status_icon.setStyleSheet(f"color: #93c5fd; font-size: 11px;")
        self.status_text.setText("Thinking...")

        target_rect = self._get_top_center_rect(180, 28)
        self._animate_to_rect(target_rect)
        self.show()

    def show_response(self, response_text: str, query_text: str = ""):
        """Expand downward to display textual prompt and answer."""
        self.current_state = TopBarState.EXPANDED
        self.last_query = query_text.strip()
        self.last_response = response_text.strip()

        self.frame_layout.setContentsMargins(12, 8, 12, 10)
        self.frame_layout.setSpacing(6)
        self.collapsed_pill.setVisible(False)
        self.status_row.setVisible(False)
        self.content_widget.setVisible(True)

        if self.last_query:
            self.query_label.setText(f'"{self.last_query}"')
            self.query_label.setVisible(True)
        else:
            self.query_label.setVisible(False)

        self.response_label.setText(self.last_response)
        self.state_chip.setText("Answered")
        self.btn_copy.setText("Copy Answer")
        self._apply_frame_style(TopBarState.EXPANDED)

        # Compute dynamic card height
        font = self.response_label.font()
        # Rough line height estimate
        char_count = len(self.last_response)
        estimated_height = min(260, max(120, 80 + (char_count // 40) * 18))
        self.scroll_area.setFixedHeight(min(160, estimated_height - 60))

        target_rect = self._get_top_center_rect(420, estimated_height)
        self._animate_to_rect(target_rect)
        self.show()

        # Start auto-collapse countdown
        self._collapse_timer.start(self._auto_collapse_delay_ms)

    def collapse_to_bar(self, animated: bool = True):
        """Collapse into the 2-3 mm black glass bar."""
        self._collapse_timer.stop()
        self.current_state = TopBarState.COLLAPSED
        self._apply_frame_style(TopBarState.COLLAPSED)

        self.frame_layout.setContentsMargins(4, 1, 4, 1)
        self.frame_layout.setSpacing(0)
        self.content_widget.setVisible(False)
        self.status_row.setVisible(False)
        self.collapsed_pill.setVisible(True)

        # 2-3 mm on standard displays is 8-10 pixels
        target_rect = self._get_top_center_rect(110, 10)

        if animated:
            self._animate_to_rect(target_rect)
        else:
            self.setGeometry(target_rect)
            self.resize(110, 10)

        self.show()
        self.dismissed_signal.emit()

    def _animate_to_rect(self, target_rect: QRect):
        """Smoothly interpolate geometry to target."""
        self._anim.stop()
        self._anim.setStartValue(self.geometry())
        self._anim.setEndValue(target_rect)
        self._anim.start()

    def _copy_answer_to_clipboard(self):
        """Copy response text to system clipboard."""
        if self.last_response:
            clipboard = QApplication.clipboard()
            clipboard.setText(self.last_response)
            self.btn_copy.setText("✓ Copied!")
            self.copied_signal.emit()
            QTimer.singleShot(1800, lambda: self.btn_copy.setText("Copy Answer"))

    def enterEvent(self, event):
        """Mouse hover: pause auto-collapse or show slight expansion on bar."""
        if self.current_state == TopBarState.EXPANDED:
            self._collapse_timer.stop()
        elif self.current_state == TopBarState.COLLAPSED:
            # Subtle hover expansion for tactile feedback
            hover_rect = self._get_top_center_rect(120, 14)
            self._animate_to_rect(hover_rect)
        super().enterEvent(event)

    def leaveEvent(self, event):
        """Mouse leaves: resume countdown or return bar to 10px."""
        if self.current_state == TopBarState.EXPANDED:
            self._collapse_timer.start(4000)
        elif self.current_state == TopBarState.COLLAPSED:
            bar_rect = self._get_top_center_rect(110, 10)
            self._animate_to_rect(bar_rect)
        super().leaveEvent(event)

    def mousePressEvent(self, event):
        """Clicking collapsed bar re-expands the last response if available."""
        if self.current_state == TopBarState.COLLAPSED:
            if self.last_response:
                self.show_response(self.last_response, self.last_query)
            else:
                self.set_thinking()
                QTimer.singleShot(1200, self.collapse_to_bar)
        super().mousePressEvent(event)
