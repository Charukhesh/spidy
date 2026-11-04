"""Clicky Blue Cursor Overlay Window for Windows.

Implements the complete visual companion from the original macOS HeyClicky:
- Glowing blue equilateral triangle (#3380FF) tracking the cursor at (+35, +25)
- Multi-monitor coordinate mapping using mapFromGlobal (handles negative screen coords & DPI)
- Smooth spring physics / fluid easing
- Real-time animated audio waveform during push-to-talk listening
- Glowing rotating spinner during AI processing
- Bezier arc swooping flight animation with scale-up and rotation to point at UI elements
- Visual Drawing Engine: bounding boxes, glowing circles, arrows, workflow simulations, and notes
- Transparent click-through overlay (WS_EX_TRANSPARENT, WS_EX_LAYERED, WS_EX_NOACTIVATE)
"""

import math
import ctypes
from ctypes import wintypes
from enum import Enum
from typing import Optional, Tuple, Callable, List, Dict, Any

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
from athena.config import load_config
from PyQt5.QtWidgets import QWidget, QApplication

# Windows API Constants for click-through transparent overlay
GWL_EXSTYLE = -20
WS_EX_LAYERED = 0x00080000
WS_EX_TRANSPARENT = 0x00000020
WS_EX_TOOLWINDOW = 0x00000080
WS_EX_NOACTIVATE = 0x08000000

# Spidy Signature Spider-Man Color Palette
SPIDY_RED = QColor("#DC2626")           # Vibrant Spider-Man Red
SPIDY_CRIMSON = QColor("#991B1B")       # Dark Crimson Web Lattice
SPIDY_RED_GLOW = QColor(220, 38, 38, 120)
SPIDY_WEB_WHITE = QColor("#F8FAFC")     # Clean Web White Lens
SPIDY_LENS_BLACK = QColor("#111827")    # Deep Black Eye Contour
SPIDY_AMBER_SENSE = QColor(251, 191, 36) # Spider-Sense Amber

# Color aliases for drawings and retro-compatibility
CLICKY_BLUE = SPIDY_RED
CLICKY_BLUE_GLOW = SPIDY_RED_GLOW
NEON_CYAN = SPIDY_RED


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
    TRACING_CURVE = "tracing_curve"


class OverlaySignals(QObject):
    state_changed = pyqtSignal(VoiceState)
    audio_level_changed = pyqtSignal(float)
    point_at_target = pyqtSignal(int, int, str)
    speech_bubble_text = pyqtSignal(str)
    draw_visuals = pyqtSignal(list)
    clear_visuals = pyqtSignal()
    trace_curve = pyqtSignal(list, str)
    fade_curve = pyqtSignal()
    clear_curve = pyqtSignal()


class ClickyCursorOverlay(QWidget):
    """Full-screen click-through transparent overlay window for Clicky and Athena."""

    def __init__(self, parent=None):
        super().__init__(parent)

        self.signals = OverlaySignals()
        self.signals.state_changed.connect(self._on_state_changed)
        self.signals.audio_level_changed.connect(self._on_audio_level)
        self.signals.point_at_target.connect(self._start_navigation)
        self.signals.speech_bubble_text.connect(self._set_speech_bubble)
        self.signals.draw_visuals.connect(self._on_draw_visuals)
        self.signals.clear_visuals.connect(self._on_clear_visuals)
        self.signals.trace_curve.connect(self._on_trace_curve)
        self.signals.fade_curve.connect(self._on_fade_curve)
        self.signals.clear_curve.connect(self._on_clear_curve)

        # Dynamic Curve Tracing State
        self.curve_points: List[QPointF] = []
        self.curve_trail_points: List[QPointF] = []
        self.curve_center: QPointF = QPointF(0.0, 0.0)
        self.curve_label: str = ""
        self.curve_duration_ms: int = 1800
        self.curve_elapsed_ms: int = 0
        self.curve_opacity: float = 1.0
        self.curve_is_fading: bool = False

        # Configuration & Performance Tuning
        self.config = load_config()
        self.transient_mode = self.config.get("transient_mode", False)

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

        # Visual Drawings (boxes, circles, arrows, simulations, notes)
        # Each item: {"kind": str, "coords": [int, ...], "label": str} in global screen coordinates
        self.active_drawings: List[Dict[str, Any]] = []
        self.drawing_opacity: float = 1.0

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
        if not app:
            return
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

    def apply_drawings(self, drawings: list):
        """Display visual bounding boxes, circles, arrows, or workflow simulations."""
        self.signals.draw_visuals.emit(drawings)

    def clear_drawings(self):
        """Remove active visual drawings."""
        self.signals.clear_visuals.emit()

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

    def _on_draw_visuals(self, drawings: list):
        self.active_drawings = drawings
        self.drawing_opacity = 1.0
        self.update()

    def _on_clear_visuals(self):
        self.active_drawings = []
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

    def start_tracing_curve(self, points: list, label: str = ""):
        """Start drawing curve with cursor gliding in real-time along the path."""
        self.signals.trace_curve.emit(points, label)

    def start_fading_curve(self):
        """Begin graceful fade out of the drawn curve."""
        self.signals.fade_curve.emit()

    def clear_curve(self):
        """Immediately clear drawn curve."""
        self.signals.clear_curve.emit()

    def _on_trace_curve(self, points: list, label: str):
        if not points:
            return
        self.curve_points = [QPointF(float(p[0]), float(p[1])) for p in points]
        self.curve_trail_points = [self.curve_points[0]]
        self.curve_label = label
        self.curve_elapsed_ms = 0
        self.curve_opacity = 1.0
        self.curve_is_fading = False

        xs = [p.x() for p in self.curve_points]
        ys = [p.y() for p in self.curve_points]
        self.curve_center = QPointF(sum(xs) / len(xs), sum(ys) / len(ys))

        self.current_global_pos = self.curve_points[0]
        self.nav_mode = NavigationMode.TRACING_CURVE
        self.bubble_text = ""
        self.bubble_opacity = 0.0
        self.update()

    def _on_fade_curve(self):
        self.curve_is_fading = True
        self.update()

    def _on_clear_curve(self):
        self.curve_points = []
        self.curve_trail_points = []
        self.curve_opacity = 0.0
        self.curve_is_fading = False
        self.update()

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

            dx = target_x - self.current_global_pos.x()
            dy = target_y - self.current_global_pos.y()
            dist_sq = dx * dx + dy * dy
            vel_sq = self.velocity.x() ** 2 + self.velocity.y() ** 2

            is_idle = (
                self.voice_state == VoiceState.IDLE
                and self.bubble_opacity <= 0.0
                and not self.curve_trail_points
                and not self.active_drawings
                and not self.curve_is_fading
            )

            # Performance Optimization: Settle at rest and eliminate redundant 60 FPS repaints
            if is_idle and dist_sq < 0.25 and vel_sq < 0.04:
                if self.velocity.x() != 0.0 or self.velocity.y() != 0.0:
                    self.velocity = QPointF(0.0, 0.0)
                    self.current_global_pos = QPointF(target_x, target_y)
                    self.update()
                return

            # Spring dampening (response: 0.2, dampingFraction: 0.6)
            k_spring = 0.22
            damping = 0.70

            force_x = dx * k_spring
            force_y = dy * k_spring

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

        elif self.nav_mode == NavigationMode.TRACING_CURVE:
            self.curve_elapsed_ms += 16
            t = min(1.0, self.curve_elapsed_ms / max(1, self.curve_duration_ms))
            # Smooth ease-in-out cosine easing
            ease_t = 0.5 - 0.5 * math.cos(t * math.pi)

            if len(self.curve_points) >= 2:
                total_segs = len(self.curve_points) - 1
                float_idx = ease_t * total_segs
                base_idx = min(int(float_idx), total_segs - 1)
                frac = float_idx - base_idx

                p_a = self.curve_points[base_idx]
                p_b = self.curve_points[base_idx + 1]

                curr_x = p_a.x() + frac * (p_b.x() - p_a.x())
                curr_y = p_a.y() + frac * (p_b.y() - p_a.y())
                new_pt = QPointF(curr_x, curr_y)

                dx = p_b.x() - p_a.x()
                dy = p_b.y() - p_a.y()
                angle_deg = math.degrees(math.atan2(dy, dx)) + 90.0

                self.current_global_pos = new_pt
                self.triangle_rotation = angle_deg
                self.curve_trail_points.append(new_pt)

            if t >= 1.0:
                self.nav_mode = NavigationMode.POINTING_AT_TARGET
                self.triangle_rotation = 0.0
                self.bubble_text = self.curve_label or "curve"
                self.bubble_scale = 0.5
                self.bubble_opacity = 1.0
                sounds.play_arrival()

        if self.curve_is_fading:
            self.curve_opacity = max(0.0, self.curve_opacity - 0.015)
            if self.curve_opacity <= 0.0:
                self.curve_trail_points = []
                self.curve_points = []
                self.curve_is_fading = False

        # Spinner rotation increment
        if self.voice_state == VoiceState.PROCESSING:
            self.spinner_angle = (self.spinner_angle + 12.0) % 360.0

        self.update()

    # MARK: - Rendering / Painting

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing, True)
        painter.setRenderHint(QPainter.SmoothPixmapTransform, True)

        # 0. Render Active Curve Trail (Neon glow polyline)
        if self.curve_trail_points and self.curve_opacity > 0.0:
            self._render_curve_trail(painter)

        # 0.5. Render Active Visual Drawings (Bounding Boxes, Circles, Arrows, Simulations, Notes)
        if self.active_drawings:
            self._render_active_drawings(painter)

        # Convert global screen coordinates to local widget coordinates!
        local_pos = self.mapFromGlobal(
            QPoint(int(self.current_global_pos.x()), int(self.current_global_pos.y()))
        )
        lx = float(local_pos.x())
        ly = float(local_pos.y())

        # 1. State: LISTENING -> Audio Waveform
        if self.voice_state == VoiceState.LISTENING and self.nav_mode == NavigationMode.FOLLOWING_CURSOR:
            self._draw_waveform(painter, lx, ly)

        # 2. State: PROCESSING -> Spider-Sense Tingling Pulse
        elif self.voice_state == VoiceState.PROCESSING and self.nav_mode == NavigationMode.FOLLOWING_CURSOR:
            self._draw_spiderman_loading(painter, lx, ly)

        # 3. State: IDLE / RESPONDING / NAVIGATING / POINTING -> Spider-Man Mask
        else:
            if not (self.transient_mode and self.voice_state == VoiceState.IDLE and self.nav_mode == NavigationMode.FOLLOWING_CURSOR):
                self._draw_spiderman_icon(painter, lx, ly)

        # 4. Speech Bubble (when pointing or answering)
        if self.bubble_opacity > 0.0 and self.bubble_text:
            self._draw_speech_bubble(painter, lx, ly)

    # MARK: - Visual Drawing Renderers

    def _render_curve_trail(self, painter: QPainter):
        """Render high-voltage neon glow polyline for curve tracing."""
        if len(self.curve_trail_points) < 2:
            return

        painter.save()

        # Subtle coordinate axes centered at self.curve_center
        if self.curve_center and self.curve_opacity > 0.2:
            cc = self.mapFromGlobal(QPoint(int(self.curve_center.x()), int(self.curve_center.y())))
            axis_len = 150.0
            axis_pen = QPen(QColor(255, 255, 255, int(35 * self.curve_opacity)), 1, Qt.DashLine)
            painter.setPen(axis_pen)
            painter.drawLine(int(cc.x() - axis_len), cc.y(), int(cc.x() + axis_len), cc.y())
            painter.drawLine(cc.x(), int(cc.y() - 90), cc.x(), int(cc.y() + 90))

        # Build QPainterPath for smooth curve
        path = QPainterPath()
        p0 = self.mapFromGlobal(QPoint(int(self.curve_trail_points[0].x()), int(self.curve_trail_points[0].y())))
        path.moveTo(QPointF(p0.x(), p0.y()))
        for pt in self.curve_trail_points[1:]:
            l_pt = self.mapFromGlobal(QPoint(int(pt.x()), int(pt.y())))
            path.lineTo(QPointF(l_pt.x(), l_pt.y()))

        # Layer 1: Wide electric Spider-Man Red outer glow
        glow_alpha = int(85 * self.curve_opacity)
        painter.setPen(QPen(QColor(220, 38, 38, glow_alpha), 9, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
        painter.setBrush(Qt.NoBrush)
        painter.drawPath(path)

        # Layer 2: Radiant Crimson mid glow
        crimson_alpha = int(190 * self.curve_opacity)
        painter.setPen(QPen(QColor(239, 68, 68, crimson_alpha), 4.5, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
        painter.drawPath(path)

        # Layer 3: White-hot core beam
        beam_alpha = int(240 * self.curve_opacity)
        painter.setPen(QPen(QColor(255, 255, 255, beam_alpha), 2.0, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
        painter.drawPath(path)

        # Pulse ring at cursor position if tracing
        if self.nav_mode == NavigationMode.TRACING_CURVE:
            head = self.mapFromGlobal(QPoint(int(self.current_global_pos.x()), int(self.current_global_pos.y())))
            painter.setPen(QPen(QColor(239, 68, 68, 180), 2))
            painter.setBrush(QBrush(QColor(220, 38, 38, 70)))
            painter.drawEllipse(head, 8, 8)

        painter.restore()

    def _render_active_drawings(self, painter: QPainter):
        """Render all on-screen drawings (boxes, circles, arrows, simulations, notes)."""
        for item in self.active_drawings:
            kind = item.get("kind", "")
            coords = item.get("coords", [])
            label = item.get("label", "")

            if kind == "box" and len(coords) >= 4:
                self._draw_visual_box(painter, coords[0], coords[1], coords[2], coords[3], label)
            elif kind == "circle" and len(coords) >= 3:
                self._draw_visual_circle(painter, coords[0], coords[1], coords[2], label)
            elif kind == "arrow" and len(coords) >= 4:
                self._draw_visual_arrow(painter, coords[0], coords[1], coords[2], coords[3], label)
            elif kind == "simulate" and len(coords) >= 4:
                self._draw_visual_simulate(painter, coords, label)
            elif kind == "text" and len(coords) >= 2:
                self._draw_visual_text(painter, coords[0], coords[1], label)

    def _draw_visual_box(self, painter: QPainter, gx1: int, gy1: int, gx2: int, gy2: int, label: str):
        """Draw a sleek, glowing Spidy red rounded bounding box with label badge."""
        p1 = self.mapFromGlobal(QPoint(min(gx1, gx2), min(gy1, gy2)))
        p2 = self.mapFromGlobal(QPoint(max(gx1, gx2), max(gy1, gy2)))

        rect = QRectF(p1.x(), p1.y(), max(10, p2.x() - p1.x()), max(10, p2.y() - p1.y()))

        painter.save()
        # Outer glow
        glow_rect = rect.adjusted(-4, -4, 4, 4)
        painter.setPen(QPen(QColor(220, 38, 38, 70), 6))
        painter.setBrush(Qt.NoBrush)
        painter.drawRoundedRect(glow_rect, 10, 10)

        # Semi-translucent crimson glass fill
        painter.setPen(QPen(SPIDY_RED, 2.5))
        painter.setBrush(QBrush(QColor(220, 38, 38, 35)))
        painter.drawRoundedRect(rect, 8, 8)

        # Label Pill Badge at top-left
        if label:
            font = QFont("Calibri", 10, QFont.Bold)
            painter.setFont(font)
            metrics = QFontMetrics(font)
            badge_w = metrics.horizontalAdvance(label) + 14
            badge_h = 22
            badge_rect = QRectF(rect.x() + 4, max(0.0, rect.y() - 24), badge_w, badge_h)

            painter.setPen(QPen(SPIDY_RED, 1))
            painter.setBrush(QBrush(QColor(16, 18, 17, 230)))
            painter.drawRoundedRect(badge_rect, 6, 6)

            painter.setPen(QPen(Qt.white))
            painter.drawText(badge_rect, Qt.AlignCenter, label)

        painter.restore()

    def _draw_visual_circle(self, painter: QPainter, gcx: int, gcy: int, radius: int, label: str):
        """Draw a glowing highlight circle in Spidy red around a focal UI element."""
        center = self.mapFromGlobal(QPoint(gcx, gcy))
        r = float(max(12, radius))

        painter.save()
        # Glow ring
        painter.setPen(QPen(QColor(220, 38, 38, 70), 6))
        painter.setBrush(Qt.NoBrush)
        painter.drawEllipse(center, r + 4, r + 4)

        # Main Neon Red Ring
        painter.setPen(QPen(SPIDY_RED, 2.5))
        painter.setBrush(QBrush(QColor(220, 38, 38, 30)))
        painter.drawEllipse(center, r, r)

        if label:
            font = QFont("Calibri", 10, QFont.Bold)
            painter.setFont(font)
            metrics = QFontMetrics(font)
            badge_w = metrics.horizontalAdvance(label) + 14
            badge_h = 22
            badge_rect = QRectF(center.x() - badge_w / 2.0, center.y() + r + 6, badge_w, badge_h)

            painter.setPen(QPen(SPIDY_RED, 1))
            painter.setBrush(QBrush(QColor(16, 18, 17, 230)))
            painter.drawRoundedRect(badge_rect, 6, 6)

            painter.setPen(QPen(Qt.white))
            painter.drawText(badge_rect, Qt.AlignCenter, label)

        painter.restore()

    def _draw_visual_arrow(self, painter: QPainter, gx1: int, gy1: int, gx2: int, gy2: int, label: str):
        """Draw a crisp glowing directional vector guide arrow."""
        p1 = self.mapFromGlobal(QPoint(gx1, gy1))
        p2 = self.mapFromGlobal(QPoint(gx2, gy2))

        painter.save()
        pen = QPen(NEON_CYAN, 3)
        pen.setCapStyle(Qt.RoundCap)
        painter.setPen(pen)
        painter.drawLine(p1, p2)

        # Arrowhead at p2
        angle = math.atan2(p2.y() - p1.y(), p2.x() - p1.x())
        arrow_size = 14.0
        p_left = QPointF(
            p2.x() - arrow_size * math.cos(angle - math.pi / 6),
            p2.y() - arrow_size * math.sin(angle - math.pi / 6),
        )
        p_right = QPointF(
            p2.x() - arrow_size * math.cos(angle + math.pi / 6),
            p2.y() - arrow_size * math.sin(angle + math.pi / 6),
        )

        arrow_head = QPolygonF([QPointF(p2.x(), p2.y()), p_left, p_right])
        painter.setBrush(QBrush(NEON_CYAN))
        painter.setPen(Qt.NoPen)
        painter.drawPolygon(arrow_head)

        if label:
            font = QFont("Calibri", 10, QFont.Bold)
            painter.setFont(font)
            metrics = QFontMetrics(font)
            badge_w = metrics.horizontalAdvance(label) + 14
            badge_h = 22
            badge_rect = QRectF(p1.x() - badge_w / 2.0, p1.y() - 26, badge_w, badge_h)

            painter.setPen(QPen(SPIDY_RED, 1))
            painter.setBrush(QBrush(QColor(16, 18, 17, 230)))
            painter.drawRoundedRect(badge_rect, 6, 6)

            painter.setPen(QPen(Qt.white))
            painter.drawText(badge_rect, Qt.AlignCenter, label)

        painter.restore()

    def _draw_visual_simulate(self, painter: QPainter, coords: List[int], label: str):
        """Draw connected workflow simulation path with numbered step badges (①, ②, ③)."""
        nodes = []
        for i in range(0, len(coords), 2):
            if i + 1 < len(coords):
                nodes.append(self.mapFromGlobal(QPoint(coords[i], coords[i + 1])))

        if not nodes:
            return

        painter.save()

        # Connect nodes with glowing dashed curve / lines
        pen = QPen(SPIDY_RED, 2.5, Qt.DashLine)
        painter.setPen(pen)
        for i in range(len(nodes) - 1):
            painter.drawLine(nodes[i], nodes[i + 1])

        # Step badges at each node
        step_symbols = ["①", "②", "③", "④", "⑤", "⑥", "⑦", "⑧"]
        font = QFont("Calibri", 11, QFont.Bold)
        painter.setFont(font)

        for idx, node in enumerate(nodes):
            sym = step_symbols[idx] if idx < len(step_symbols) else str(idx + 1)
            # Glowing node circle
            painter.setPen(QPen(SPIDY_RED, 2))
            painter.setBrush(QBrush(QColor(16, 18, 17, 240)))
            painter.drawEllipse(node, 15, 15)

            painter.setPen(QPen(SPIDY_RED))
            node_rect = QRectF(node.x() - 15, node.y() - 15, 30, 30)
            painter.drawText(node_rect, Qt.AlignCenter, sym)

        # Title badge above the first node
        if label and nodes:
            first = nodes[0]
            font_title = QFont("Calibri", 10, QFont.Bold)
            painter.setFont(font_title)
            metrics = QFontMetrics(font_title)
            title_w = metrics.horizontalAdvance(label) + 16
            title_h = 24
            title_rect = QRectF(first.x() - title_w / 2.0, first.y() - 44, title_w, title_h)

            painter.setPen(QPen(SPIDY_RED, 1))
            painter.setBrush(QBrush(QColor(16, 18, 17, 240)))
            painter.drawRoundedRect(title_rect, 6, 6)

            painter.setPen(QPen(Qt.white))
            painter.drawText(title_rect, Qt.AlignCenter, label)

        painter.restore()

    def _draw_visual_text(self, painter: QPainter, gx: int, gy: int, text: str):
        """Draw an on-screen floating annotation card in Calibri."""
        pos = self.mapFromGlobal(QPoint(gx, gy))

        painter.save()
        font = QFont("Calibri", 10)
        painter.setFont(font)
        metrics = QFontMetrics(font)

        lines = text.split("\n")
        w = max(metrics.horizontalAdvance(line) for line in lines) + 20
        h = len(lines) * metrics.height() + 16

        card_rect = QRectF(pos.x() + 10, pos.y() + 10, w, h)

        painter.setPen(QPen(NEON_CYAN, 1.2))
        painter.setBrush(QBrush(QColor(16, 18, 17, 235)))
        painter.drawRoundedRect(card_rect, 8, 8)

        painter.setPen(QPen(Qt.white))
        painter.drawText(card_rect.adjusted(10, 8, -10, -8), Qt.AlignLeft | Qt.AlignTop, text)

        painter.restore()

    # MARK: - Spidy Spider-Man Mask Pointer, Waveform, Spider-Sense Loading & Bubble

    def _draw_spiderman_icon(self, painter: QPainter, x: float, y: float):
        """Render iconic Spider-Man mask in signature red with sharp white lenses."""
        painter.save()
        painter.translate(x, y)
        painter.rotate(self.triangle_rotation)
        painter.scale(self.flight_scale, self.flight_scale)

        # 1. Subtle Crimson Outer Drop Shadow / Glow
        for r in (8, 4):
            painter.setBrush(QBrush(QColor(220, 38, 38, 35)))
            painter.setPen(Qt.NoPen)
            painter.drawEllipse(QRectF(-12.0 - r * 0.4, -14.0 - r * 0.4, 24.0 + r * 0.8, 28.0 + r * 0.8))

        # 2. Signature Mask Contour (Egg-shaped tapered down at chin)
        mask_path = QPainterPath()
        mask_path.moveTo(0.0, -13.0)
        mask_path.cubicTo(11.0, -13.0, 10.0, 4.0, 3.5, 12.0)
        mask_path.quadTo(0.0, 14.5, -3.5, 12.0)
        mask_path.cubicTo(-10.0, 4.0, -11.0, -13.0, 0.0, -13.0)

        painter.setBrush(QBrush(SPIDY_RED))
        painter.setPen(QPen(SPIDY_CRIMSON, 1.2))
        painter.drawPath(mask_path)

        # 3. Web lattice accents on mask
        painter.setPen(QPen(SPIDY_CRIMSON, 0.9))
        # Center vertical web line from forehead to chin
        painter.drawLine(QPointF(0.0, -13.0), QPointF(0.0, 13.5))
        # Subtle horizontal web cross-curves
        painter.drawArc(QRectF(-8.0, -10.0, 16.0, 10.0), 20 * 16, 140 * 16)
        painter.drawArc(QRectF(-9.5, -4.0, 19.0, 11.0), 20 * 16, 140 * 16)
        painter.drawArc(QRectF(-7.0, 2.0, 14.0, 10.0), 20 * 16, 140 * 16)

        # 4. Iconic Angular White Eyes / Lenses with Black Outlines
        # Right Eye
        r_eye = QPainterPath()
        r_eye.moveTo(1.5, -4.0)
        r_eye.lineTo(8.5, -7.5)   # Top slant up to temple
        r_eye.quadTo(7.5, 0.5, 2.0, 1.5)  # Curved lower contour back to nose
        r_eye.closeSubpath()

        # Left Eye
        l_eye = QPainterPath()
        l_eye.moveTo(-1.5, -4.0)
        l_eye.lineTo(-8.5, -7.5)  # Top slant up to temple
        l_eye.quadTo(-7.5, 0.5, -2.0, 1.5) # Curved lower contour back to nose
        l_eye.closeSubpath()

        # Black thick outer lens border with bright white lens fill
        painter.setPen(QPen(SPIDY_LENS_BLACK, 1.8, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
        painter.setBrush(QBrush(SPIDY_WEB_WHITE))
        painter.drawPath(r_eye)
        painter.drawPath(l_eye)

        painter.restore()

    def _draw_waveform(self, painter: QPainter, x: float, y: float):
        """Draw 5 vertical pulsing red bars reacting to voice loudness."""
        painter.save()
        painter.translate(x, y)

        bars = 5
        bar_width = 3.0
        gap = 3.0
        total_width = bars * bar_width + (bars - 1) * gap
        start_x = -total_width / 2.0

        painter.setPen(Qt.NoPen)

        # Glow behind waveform
        painter.setBrush(QBrush(QColor(220, 38, 38, 70)))
        painter.drawEllipse(QPointF(0, 0), 16, 16)

        painter.setBrush(QBrush(SPIDY_RED))
        factors = [0.45, 0.75, 1.0, 0.75, 0.45]
        min_height = 4.0
        max_height = 24.0

        for i in range(bars):
            h = min_height + (max_height - min_height) * self.audio_level * factors[i]
            bx = start_x + i * (bar_width + gap)
            by = -h / 2.0
            painter.drawRoundedRect(QRectF(bx, by, bar_width, h), 1.5, 1.5)

        painter.restore()

    def _draw_spiderman_loading(self, painter: QPainter, x: float, y: float):
        """Spider-Sense Tingling radar pulse animation during request processing."""
        painter.save()
        painter.translate(x, y)

        # 1. Spider-Sense Radar Pulse Arcs radiating outward from the temples
        phase = (self.spinner_angle / 360.0)
        for i in range(3):
            wave_phase = (phase + i * 0.33) % 1.0
            r = 16.0 + wave_phase * 22.0
            alpha = int(220 * (1.0 - wave_phase))

            # Left spider-sense arcs (Red to Amber)
            pen_left = QPen(QColor(239, 68, 68, alpha), 1.8, Qt.SolidLine, Qt.RoundCap)
            painter.setPen(pen_left)
            painter.setBrush(Qt.NoBrush)
            painter.drawArc(QRectF(-r - 3.0, -r - 5.0, r * 2, r * 2), 110 * 16, 50 * 16)

            # Right spider-sense arcs (Electric Amber)
            pen_right = QPen(QColor(251, 191, 36, alpha), 1.8, Qt.SolidLine, Qt.RoundCap)
            painter.setPen(pen_right)
            painter.drawArc(QRectF(-r + 3.0, -r - 5.0, r * 2, r * 2), 20 * 16, 50 * 16)

        painter.restore()

        # 2. Draw the Spider-Man mask with gentle breathing pulse
        old_scale = self.flight_scale
        self.flight_scale = 1.0 + 0.08 * math.sin(phase * 2 * math.pi)
        self._draw_spiderman_icon(painter, x, y)
        self.flight_scale = old_scale

    # Aliases for compatibility
    _draw_triangle = _draw_spiderman_icon
    _draw_spinner = _draw_spiderman_loading

    def _draw_speech_bubble(self, painter: QPainter, x: float, y: float):
        """Draw rounded speech bubble in Spidy red with Calibri typography."""
        painter.save()

        font = QFont("Calibri", 10, QFont.Bold)
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
        painter.setBrush(QBrush(QColor(220, 38, 38, 70)))
        painter.setPen(Qt.NoPen)
        painter.drawRoundedRect(shadow_rect, 8, 8)

        # Background bubble (Spidy Red)
        bubble_rect = QRectF(0, 0, bubble_w, bubble_h)
        painter.setBrush(QBrush(SPIDY_RED))
        painter.setPen(QPen(QColor(255, 255, 255, 120), 1.0))
        painter.drawRoundedRect(bubble_rect, 6, 6)

        # Crisp White Text
        painter.setPen(QPen(Qt.white))
        painter.drawText(
            QRectF(padding_x, padding_y, text_width, text_height),
            Qt.AlignCenter,
            self.bubble_text,
        )

        painter.restore()
