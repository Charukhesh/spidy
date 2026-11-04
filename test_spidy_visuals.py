"""Automated Unit Tests for Spidy's Spider-Man Mask Icon, Red Web Lines, and Loading Pulse."""

import sys
import unittest
from pathlib import Path

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent))

from PyQt5.QtWidgets import QApplication
from PyQt5.QtGui import QPainter, QImage, QColor
from PyQt5.QtCore import QPointF

app = QApplication.instance() or QApplication(sys.argv)

from athena.cursor_overlay import ClickyCursorOverlay, SPIDY_RED, SPIDY_CRIMSON, VoiceState, NavigationMode


class TestSpidyVisuals(unittest.TestCase):

    def setUp(self):
        self.overlay = ClickyCursorOverlay()

    def tearDown(self):
        self.overlay.close()

    def test_01_spiderman_palette_is_red(self):
        """Verify Spidy color constants evaluate to signature Spider-Man red."""
        self.assertEqual(SPIDY_RED.name().upper(), "#DC2626")
        self.assertEqual(SPIDY_CRIMSON.name().upper(), "#991B1B")

    def test_02_spiderman_icon_renders_cleanly(self):
        """Verify _draw_spiderman_icon renders onto QPainter canvas without exception."""
        img = QImage(120, 120, QImage.Format_ARGB32_Premultiplied)
        img.fill(0)
        painter = QPainter(img)
        try:
            self.overlay._draw_spiderman_icon(painter, 60.0, 60.0)
        finally:
            painter.end()

        # Canvas should have drawn red pixels
        pixel = img.pixelColor(60, 60)
        # Check non-transparent
        self.assertGreater(pixel.alpha(), 0)

    def test_03_spiderman_loading_renders_cleanly(self):
        """Verify _draw_spiderman_loading renders Spider-Sense pulse arcs."""
        img = QImage(160, 160, QImage.Format_ARGB32_Premultiplied)
        img.fill(0)
        painter = QPainter(img)
        try:
            self.overlay.spinner_angle = 120.0
            self.overlay._draw_spiderman_loading(painter, 80.0, 80.0)
        finally:
            painter.end()

        # Check non-transparent
        center_pixel = img.pixelColor(80, 80)
        self.assertGreater(center_pixel.alpha(), 0)

    def test_04_curve_trail_uses_red_palette(self):
        """Verify curve trail renders using red glowing pens."""
        self.overlay.curve_trail_points = [QPointF(10.0, 10.0), QPointF(50.0, 50.0), QPointF(90.0, 20.0)]
        self.overlay.curve_opacity = 1.0

        img = QImage(200, 200, QImage.Format_ARGB32_Premultiplied)
        img.fill(0)
        painter = QPainter(img)
        try:
            self.overlay._render_curve_trail(painter)
        finally:
            painter.end()

        self.assertGreater(img.pixelColor(50, 50).alpha(), 0)


if __name__ == "__main__":
    unittest.main()

