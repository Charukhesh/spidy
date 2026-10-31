"""Clicky Blue Cursor Overlay Window for Windows.

Implements the complete visual companion from the original macOS HeyClicky:
- Glowing blue equilateral triangle (#3380FF) tracking the cursor at (+35, +25)
- Multi-monitor coordinate mapping using mapFromGlobal (handles negative screen coords & DPI)
- Smooth spring physics / fluid easing
- Real-time animated audio waveform during push-to-talk listening
- Glowing rotating spinner during AI processing
- Bezier arc swooping flight animation with scale-up and rotation to point at UI elements
- Navigation speech bubble pop-in with bounce
- Transparent click-through overlay (WS_EX_TRANSPARENT, WS_EX_LAYERED, WS_EX_NOACTIVATE)
"""

import math
import ctypes
from ctypes import wintypes
from enum import Enum
from typing import Optional, Tuple, Callable

from PyQt5.QtCore import (
    Qt,
    QTimer,
    QPoint,
    QPointF,
    QRect,
    QRectF,
    pyqtSignal,
    QObject,
)
from PyQt5.QtGui import (
    QPainter,
    QColor,
    QPolygonF,
    QPen,
    QBrush,
    QFont,
    QPainterPath,
    QFontMetrics,
    QCursor,
)
from athena.sound_effects import sounds
from PyQt5.QtWidgets import QWidget, QApplication

# Windows API Constants for click-through transparent overlay
GWL_EXSTYLE = -20
WS_EX_LAYERED = 0x00080000
WS_EX_TRANSPARENT = 0x00000020
WS_EX_TOOLWINDOW = 0x00000080
WS_EX_NOACTIVATE = 0x08000000

CLICKY_BLUE = QColor("#3380FF")
CLICKY_BLUE_GLOW = QColor(51, 128, 255, 120)


class VoiceState(Enum):
    IDLE = "idle"
    LISTENING = "listening"
    PROCESSING = "processing"
    RESPONDING = "responding"


class NavigationMode(Enum):
    FOLLOWING_CURSOR = "following"
    NAVIGATING_TO_TARGET = "navigating"
    POINTING_AT_TARGET = "pointing"
    RETURNING_TO_CURSOR = "returning"


class OverlaySignals(QObject):
    state_changed = pyqtSignal(VoiceState)
    audio_level_changed = pyqtSignal(float)
    point_at_target = pyqtSignal(int, int, str)
    speech_bubble_text = pyqtSignal(str)


class ClickyCursorOverlay(QWidget):
    """Full-screen click-through transparent overlay window for Clicky."""

    def __init__(self, parent=None):
        super().__init__(parent)

        self.signals = OverlaySignals()
        self.signals.state_changed.connect(self._on_state_changed)
        self.signals.audio_level_changed.connect(self._on_audio_level)
        self.signals.point_at_target.connect(self._start_navigation)
        self.signals.speech_bubble_text.connect(self._set_speech_bubble)

        # State tracking
        self.voice_state = VoiceState.IDLE
        self.nav_mode = NavigationMode.FOLLOWING_CURSOR
        self.audio_level = 0.0
        self.spinner_angle = 0.0

        # Physical positions in Global Desktop Coordinates
        initial_cursor = QCursor.pos()
        self.current_global_pos = QPointF(initial_cursor.x() + 35.0, initial_cursor.y() + 25.0)
        self.velocity = QPointF(0.0, 0.0)
        self.triangle_rotation = -35.0  # Default cursor angle

        # Flight animation (stored in Global Desktop Coordinates)
        self.flight_start_pos = QPointF(0.0, 0.0)
        self.flight_target_pos = QPointF(0.0, 0.0)
        self.flight_control_point = QPointF(0.0, 0.0)
        self.flight_scale = 1.0
        self.flight_duration_ms = 850
        self.flight_elapsed_ms = 0

        # Speech bubble
        self.bubble_text = ""
        self.bubble_scale = 1.0
        self.bubble_opacity = 0.0
        self.target_element_label = ""

        # Window configuration
        self.setWindowFlags(
            Qt.WindowStaysOnTopHint
            | Qt.FramelessWindowHint
            | Qt.SubWindow
            | Qt.WindowDoesNotAcceptFocus
        )
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        self.setAttribute(Qt.WA_ShowWithoutActivating, True)

        # Span all monitors in virtual desktop
        self._update_geometry()

        # 60 FPS animation loop
        self.anim_timer = QTimer(self)
        self.anim_timer.timeout.connect(self._on_tick)
        self.anim_timer.start(16)

    def _update_geometry(self):
        """Cover entire virtual desktop across all monitors."""
        app = QApplication.instance()
        virtual_rect = QRect()
        for screen in app.screens():
            virtual_rect = virtual_rect.united(screen.geometry())

        self.setGeometry(virtual_rect)

    def showEvent(self, event):
        super().showEvent(event)
        self._update_geometry()
        self._enable_click_through()

    def _enable_click_through(self):
        """Configure Windows OS to make this window 100% click-through."""
        hwnd = int(self.winId())
        user32 = ctypes.windll.user32
        style = user32.GetWindowLongW(hwnd, GWL_EXSTYLE)
        user32.SetWindowLongW(
            hwnd,
            GWL_EXSTYLE,
            style | WS_EX_LAYERED | WS_EX_TRANSPARENT | WS_EX_TOOLWINDOW | WS_EX_NOACTIVATE,
        )

    # MARK: - Public State Controllers

    def set_voice_state(self, state: VoiceState):
        self.signals.state_changed.emit(state)

    def update_audio_power(self, level: float):
        self.signals.audio_level_changed.emit(level)

    def point_to(self, x: int, y: int, label: str):
        self.signals.point_at_target.emit(x, y, label)

    def show_speech_bubble(self, text: str):
        self.signals.speech_bubble_text.emit(text)

    # MARK: - Signal Handlers

    def _on_state_changed(self, state: VoiceState):
        self.voice_state = state
        self.update()

    def _on_audio_level(self, level: float):
        self.audio_level = level
        self.update()

    def _set_speech_bubble(self, text: str):
        self.bubble_text = text
        self.bubble_opacity = 1.0 if text else 0.0
        self.bubble_scale = 1.0
        self.update()

    def _start_navigation(self, target_global_x: int, target_global_y: int, label: str):
        """Initiate bezier arc flight toward target element in global coordinates."""
        self.target_element_label = label
        self.flight_start_pos = QPointF(self.current_global_pos.x(), self.current_global_pos.y())
        self.flight_target_pos = QPointF(float(target_global_x), float(target_global_y))

        # Calculate a curved control point for natural swooping bezier arc
        mid_x = (self.flight_start_pos.x() + self.flight_target_pos.x()) / 2.0
        mid_y = (self.flight_start_pos.y() + self.flight_target_pos.y()) / 2.0
        dist = math.hypot(
            self.flight_target_pos.x() - self.flight_start_pos.x(),
            self.flight_target_pos.y() - self.flight_start_pos.y(),
        )
        arc_lift = min(220.0, max(70.0, dist * 0.35))
        self.flight_control_point = QPointF(mid_x, mid_y - arc_lift)

        self.flight_elapsed_ms = 0
        self.nav_mode = NavigationMode.NAVIGATING_TO_TARGET
        self.bubble_text = ""
        self.bubble_opacity = 0.0

    def start_flying_back(self):
        """Fly back to mouse cursor."""
        cursor_pt = QCursor.pos()
        self.flight_start_pos = QPointF(self.current_global_pos.x(), self.current_global_pos.y())
        self.flight_target_pos = QPointF(cursor_pt.x() + 35.0, cursor_pt.y() + 25.0)

        mid_x = (self.flight_start_pos.x() + self.flight_target_pos.x()) / 2.0
        mid_y = (self.flight_start_pos.y() + self.flight_target_pos.y()) / 2.0
        self.flight_control_point = QPointF(mid_x, mid_y - 80.0)

        self.flight_elapsed_ms = 0
        self.nav_mode = NavigationMode.RETURNING_TO_CURSOR
        self.bubble_opacity = 0.0

    # MARK: - Frame-by-Frame Physics & Animation

    def _on_tick(self):
        if self.nav_mode == NavigationMode.FOLLOWING_CURSOR:
            # Get cursor position directly from Qt in global screen space
            mouse_pos = QCursor.pos()
            target_x = mouse_pos.x() + 35.0
            target_y = mouse_pos.y() + 25.0

            # Spring dampening (response: 0.2, dampingFraction: 0.6)
            k_spring = 0.22
            damping = 0.70

            force_x = (target_x - self.current_global_pos.x()) * k_spring
            force_y = (target_y - self.current_global_pos.y()) * k_spring

            vel_x = (self.velocity.x() + force_x) * damping
            vel_y = (self.velocity.y() + force_y) * damping
            self.velocity = QPointF(vel_x, vel_y)

            self.current_global_pos = QPointF(
                self.current_global_pos.x() + vel_x,
                self.current_global_pos.y() + vel_y,
            )
            self.triangle_rotation = -35.0
            self.flight_scale = 1.0

        elif self.nav_mode in (
            NavigationMode.NAVIGATING_TO_TARGET,
            NavigationMode.RETURNING_TO_CURSOR,
        ):
            # Advance quadratic Bezier arc flight
            self.flight_elapsed_ms += 16
            t = min(1.0, self.flight_elapsed_ms / self.flight_duration_ms)
            # Smooth ease-in-out easing
            ease_t = 0.5 - 0.5 * math.cos(t * math.pi)

            p0 = self.flight_start_pos
            p1 = self.flight_control_point
            p2 = self.flight_target_pos

            bx = (1 - ease_t) ** 2 * p0.x() + 2 * (1 - ease_t) * ease_t * p1.x() + ease_t**2 * p2.x()
            by = (1 - ease_t) ** 2 * p0.y() + 2 * (1 - ease_t) * ease_t * p1.y() + ease_t**2 * p2.y()

            # Tangent vector for dynamic flight angle
            dx = 2 * (1 - ease_t) * (p1.x() - p0.x()) + 2 * ease_t * (p2.x() - p1.x())
            dy = 2 * (1 - ease_t) * (p1.y() - p0.y()) + 2 * ease_t * (p2.y() - p1.y())
            angle_deg = math.degrees(math.atan2(dy, dx)) + 90.0

            # Scale up to 1.3x mid-flight
            scale = 1.0 + 0.35 * math.sin(t * math.pi)

            self.current_global_pos = QPointF(bx, by)
            self.triangle_rotation = angle_deg
            self.flight_scale = scale

            if t >= 1.0:
                if self.nav_mode == NavigationMode.NAVIGATING_TO_TARGET:
                    self.nav_mode = NavigationMode.POINTING_AT_TARGET
                    self.triangle_rotation = 0.0
                    self.flight_scale = 1.0
                    # Pop speech bubble with bounce
                    self.bubble_text = (
                        self.target_element_label
                        if self.target_element_label
                        else "right here!"
                    )
                    self.bubble_scale = 0.5
                    self.bubble_opacity = 1.0
                    sounds.play_arrival()
                else:
                    self.nav_mode = NavigationMode.FOLLOWING_CURSOR
                    self.triangle_rotation = -35.0
                    self.flight_scale = 1.0

        elif self.nav_mode == NavigationMode.POINTING_AT_TARGET:
            # Spring bounce for navigation bubble
            if self.bubble_scale < 1.0:
                self.bubble_scale = min(1.0, self.bubble_scale + 0.08)

        # Spinner rotation increment
        if self.voice_state == VoiceState.PROCESSING:
            self.spinner_angle = (self.spinner_angle + 12.0) % 360.0

        self.update()

    # MARK: - Rendering / Painting

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing, True)
        painter.setRenderHint(QPainter.SmoothPixmapTransform, True)

        # Convert global screen coordinates to local widget coordinates!
        # This completely resolves multi-monitor offsets and DPI shifts!
        local_pos = self.mapFromGlobal(
            QPoint(int(self.current_global_pos.x()), int(self.current_global_pos.y()))
        )
        lx = float(local_pos.x())
        ly = float(local_pos.y())

        # 1. State: LISTENING -> Audio Waveform
        if self.voice_state == VoiceState.LISTENING and self.nav_mode == NavigationMode.FOLLOWING_CURSOR:
            self._draw_waveform(painter, lx, ly)

        # 2. State: PROCESSING -> Rotating Spinner
        elif self.voice_state == VoiceState.PROCESSING and self.nav_mode == NavigationMode.FOLLOWING_CURSOR:
            self._draw_spinner(painter, lx, ly)

        # 3. State: IDLE / RESPONDING / NAVIGATING / POINTING -> Blue Triangle
        else:
            self._draw_triangle(painter, lx, ly)

        # 4. Speech Bubble (when pointing or answering)
        if self.bubble_opacity > 0.0 and self.bubble_text:
            self._draw_speech_bubble(painter, lx, ly)

    def _draw_triangle(self, painter: QPainter, x: float, y: float):
        painter.save()
        painter.translate(x, y)
        painter.rotate(self.triangle_rotation)
        painter.scale(self.flight_scale, self.flight_scale)

        # Outer blue glow shadow
        for r in (12, 8, 4):
            glow_poly = QPolygonF([
                QPointF(0.0, -9.0 - r * 0.4),
                QPointF(-8.0 - r * 0.4, 7.0 + r * 0.4),
                QPointF(8.0 + r * 0.4, 7.0 + r * 0.4),
            ])
            painter.setBrush(QBrush(QColor(51, 128, 255, 30)))
            painter.setPen(Qt.NoPen)
            painter.drawPolygon(glow_poly)

        # Solid Clicky Blue Triangle
        poly = QPolygonF([
            QPointF(0.0, -9.0),
            QPointF(-8.0, 7.0),
            QPointF(8.0, 7.0),
        ])
        painter.setBrush(QBrush(CLICKY_BLUE))
        painter.setPen(QPen(QColor(255, 255, 255, 180), 1.0))
        painter.drawPolygon(poly)

        painter.restore()

    def _draw_waveform(self, painter: QPainter, x: float, y: float):
        """Draw 5 vertical pulsing blue bars reacting to voice loudness."""
        painter.save()
        painter.translate(x, y)

        bars = 5
        bar_width = 3.0
        gap = 3.0
        total_width = bars * bar_width + (bars - 1) * gap
        start_x = -total_width / 2.0

        painter.setPen(Qt.NoPen)

        # Glow behind waveform
        painter.setBrush(QBrush(QColor(51, 128, 255, 60)))
        painter.drawEllipse(QPointF(0, 0), 16, 16)

        painter.setBrush(QBrush(CLICKY_BLUE))
        # Center bar peaks highest, sides taper
        factors = [0.45, 0.75, 1.0, 0.75, 0.45]
        min_height = 4.0
        max_height = 24.0

        for i in range(bars):
            h = min_height + (max_height - min_height) * self.audio_level * factors[i]
            bx = start_x + i * (bar_width + gap)
            by = -h / 2.0
            painter.drawRoundedRect(QRectF(bx, by, bar_width, h), 1.5, 1.5)

        painter.restore()

    def _draw_spinner(self, painter: QPainter, x: float, y: float):
        """Draw blue glowing circular spinner."""
        painter.save()
        painter.translate(x, y)
        painter.rotate(self.spinner_angle)

        radius = 8.0
        pen = QPen(CLICKY_BLUE, 2.5)
        pen.setCapStyle(Qt.RoundCap)
        painter.setPen(pen)
        painter.setBrush(Qt.NoBrush)

        rect = QRectF(-radius, -radius, radius * 2, radius * 2)
        painter.drawArc(rect, 0, 260 * 16)

        painter.restore()

    def _draw_speech_bubble(self, painter: QPainter, x: float, y: float):
        """Draw rounded speech bubble next to pointer or cursor."""
        painter.save()

        font = QFont("Segoe UI", 9, QFont.Medium)
        painter.setFont(font)
        metrics = QFontMetrics(font)

        text_width = metrics.horizontalAdvance(self.bubble_text)
        text_height = metrics.height()

        padding_x = 10
        padding_y = 6
        bubble_w = text_width + padding_x * 2
        bubble_h = text_height + padding_y * 2

        bx = x + 14
        by = y + 14

        painter.translate(bx + bubble_w / 2.0, by + bubble_h / 2.0)
        painter.scale(self.bubble_scale, self.bubble_scale)
        painter.translate(-bubble_w / 2.0, -bubble_h / 2.0)

        # Glow shadow
        shadow_rect = QRectF(-2, -2, bubble_w + 4, bubble_h + 4)
        painter.setBrush(QBrush(QColor(51, 128, 255, 60)))
        painter.setPen(Qt.NoPen)
        painter.drawRoundedRect(shadow_rect, 8, 8)

        # Background bubble (Clicky Blue)
        bubble_rect = QRectF(0, 0, bubble_w, bubble_h)
        painter.setBrush(QBrush(CLICKY_BLUE))
        painter.setPen(QPen(QColor(255, 255, 255, 100), 1.0))
        painter.drawRoundedRect(bubble_rect, 6, 6)

        # Crisp White Text
        painter.setPen(QPen(Qt.white))
        painter.drawText(
            QRectF(padding_x, padding_y, text_width, text_height),
            Qt.AlignCenter,
            self.bubble_text,
        )

        painter.restore()
