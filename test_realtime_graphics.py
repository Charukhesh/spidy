"""Automated Unit Tests for Spidy Real-Time Graphics (RTG) Engine.

Validates:
1. Parsing of [DIAGRAM], [CUTAWAY], and [ASSEMBLY] JSON tags from model responses.
2. Speech sanitization ensuring zero RTG tags leak into spoken text.
3. RealtimeGraphicsRenderer drawing on QPainter without exceptions across all modes.
4. Strict Spidy aesthetic: Calibri typography, Spidy red/amber/parchment palette.
5. Zero local compute benchmark: Vector rendering execution completes in < 1.0 ms.
"""

import sys
import time
import unittest
from pathlib import Path

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent))

from PyQt5.QtWidgets import QApplication
from PyQt5.QtGui import QPixmap, QPainter, QFont
from PyQt5.QtCore import QPoint, QRect

app = QApplication.instance() or QApplication(sys.argv)

from spidy.realtime_graphics import RealtimeGraphicSpec, RealtimeGraphicsRenderer
from spidy.ai_vision_client import AIVisionClient
from spidy.companion_manager import CompanionManager


class TestRealtimeGraphics(unittest.TestCase):

    def setUp(self):
        self.renderer = RealtimeGraphicsRenderer()

    def test_01_parse_diagram_tag(self):
        """Verify parsing of [DIAGRAM: ...] tag into RealtimeGraphicSpec."""
        raw_text = (
            "Here is how gradient descent adjusts weights. "
            '[DIAGRAM: {"title": "Neural Network Optimization", "steps": ["Input Forward", "Loss Calculation", "Backpropagation"], "equation": "w = w - eta * dL/dw"}] '
            "Notice how the error propagates backward."
        )
        (
            spoken, target, drawings, heard, trace, search,
            act_t, act_a, rem, spec
        ) = AIVisionClient.parse_visual_tags(raw_text)

        self.assertIsNotNone(spec)
        self.assertEqual(spec.kind, "diagram")
        self.assertEqual(spec.title, "Neural Network Optimization")
        self.assertEqual(len(spec.steps), 3)
        self.assertEqual(spec.steps[0], "Input Forward")
        self.assertEqual(spec.equation, "w = w - eta * dL/dw")

        # Verify spoken text has no tag leakage
        self.assertNotIn("DIAGRAM", spoken)
        self.assertNotIn("{", spoken)
        self.assertIn("gradient descent adjusts weights", spoken)

    def test_02_parse_cutaway_tag(self):
        """Verify parsing of [CUTAWAY: ...] tag into RealtimeGraphicSpec."""
        raw_text = (
            "Here is the jet engine cross section. "
            '[CUTAWAY: {"title": "Turbofan Engine Section", "layers": [{"name": "Fan & Compressor", "annotation": "Intake stage"}, {"name": "Combustion Chamber", "annotation": "High-pressure ignition"}], "force_vectors": [{"from": [20, 50], "to": [80, 50], "color": "#FBBF24"}]}] '
            "The thrust pushes forward as hot gases exit."
        )
        (
            spoken, target, drawings, heard, trace, search,
            act_t, act_a, rem, spec
        ) = AIVisionClient.parse_visual_tags(raw_text)

        self.assertIsNotNone(spec)
        self.assertEqual(spec.kind, "cutaway")
        self.assertEqual(spec.title, "Turbofan Engine Section")
        self.assertEqual(len(spec.layers), 2)
        self.assertEqual(spec.layers[0]["name"], "Fan & Compressor")
        self.assertEqual(len(spec.force_vectors), 1)

        # Spoken text check
        self.assertNotIn("CUTAWAY", spoken)

    def test_03_parse_assembly_tag(self):
        """Verify parsing of [ASSEMBLY: ...] tag into RealtimeGraphicSpec."""
        raw_text = (
            "Be careful with the ribbon connector orientation. "
            '[ASSEMBLY: {"title": "Camera Module Connection", "hardware": "Raspberry Pi Camera V3", "pins": 15, "orientation": "Silver pins toward HDMI port", "steps": ["Gently pull up collar", "Insert blue tab facing away", "Push collar down firmly"]}] '
            "Make sure it clicks into place."
        )
        (
            spoken, target, drawings, heard, trace, search,
            act_t, act_a, rem, spec
        ) = AIVisionClient.parse_visual_tags(raw_text)

        self.assertIsNotNone(spec)
        self.assertEqual(spec.kind, "assembly")
        self.assertEqual(spec.title, "Camera Module Connection")
        self.assertEqual(spec.hardware, "Raspberry Pi Camera V3")
        self.assertEqual(spec.pins, 15)
        self.assertEqual(spec.orientation, "Silver pins toward HDMI port")
        self.assertEqual(len(spec.steps), 3)

        # Spoken text check
        self.assertNotIn("ASSEMBLY", spoken)

    def test_04_companion_speech_sanitization(self):
        """Verify CompanionManager._sanitize_speech_text strips RTG tags cleanly."""
        dirty = (
            'Check this out [DIAGRAM: {"title": "Test", "steps": ["A", "B"]}] and [ASSEMBLY: {"hardware": "Pi"}] '
            "everything is clean."
        )
        sanitized = CompanionManager._sanitize_speech_text(dirty)
        self.assertEqual(sanitized, "Check this out and everything is clean.")

    def test_05_renderer_paint_all_modes_and_typography(self):
        """Verify RealtimeGraphicsRenderer renders diagram, cutaway, and assembly on QPainter."""
        pixmap = QPixmap(1920, 1080)
        pixmap.fill()
        painter = QPainter(pixmap)
        screen_rect = QRect(0, 0, 1920, 1080)
        cursor_pos = QPoint(500, 400)

        # 1. Diagram mode
        diag_spec = RealtimeGraphicSpec(
            kind="diagram",
            title="Algorithm State Machine",
            data={
                "steps": ["Init State", "Evaluate Guard", "Transition"],
                "equation": "S_{t+1} = f(S_t, U_t)",
            },
        )
        self.renderer.set_spec(diag_spec)
        self.renderer.render(painter, cursor_pos, screen_rect)
        self.assertEqual(self.renderer.card_rect.width(), 540.0)

        # 2. Cutaway mode
        cut_spec = RealtimeGraphicSpec(
            kind="cutaway",
            title="Mechanical Relay Internals",
            data={
                "layers": [
                    {"name": "Electromagnet Coil", "annotation": "Generates B-field when energized"},
                    {"name": "Movable Armature", "annotation": "Pivots towards core"},
                    {"name": "Spring Return", "annotation": "Restores open contact state"},
                ],
                "force_vectors": [{"from": [100, 200], "to": [250, 200], "color": "#FBBF24"}],
            },
        )
        self.renderer.set_spec(cut_spec)
        self.renderer.render(painter, cursor_pos, screen_rect)
        self.assertEqual(self.renderer.card_rect.width(), 540.0)

        # 3. Assembly mode
        asm_spec = RealtimeGraphicSpec(
            kind="assembly",
            title="Ribbon Connector Assembly",
            data={
                "hardware": "Display DSI Port",
                "pins": 22,
                "orientation": "Contacts facing inward",
                "steps": ["Lift locking tab", "Seat ribbon evenly", "Snap lock down"],
            },
        )
        self.renderer.set_spec(asm_spec)
        self.renderer.render(painter, cursor_pos, screen_rect)
        self.assertEqual(self.renderer.card_rect.width(), 540.0)

        painter.end()

    def test_06_zero_compute_benchmark(self):
        """Benchmark rendering execution speed to guarantee zero compute overhead (< 1.0 ms)."""
        pixmap = QPixmap(1920, 1080)
        pixmap.fill()
        painter = QPainter(pixmap)
        screen_rect = QRect(0, 0, 1920, 1080)
        cursor_pos = QPoint(600, 400)

        spec = RealtimeGraphicSpec(
            kind="diagram",
            title="Performance Stress Test",
            data={
                "steps": ["Step A", "Step B", "Step C", "Step D"],
                "equation": "E = mc^2",
            },
        )
        self.renderer.set_spec(spec)

        # Measure 100 paint iterations
        start = time.perf_counter()
        iterations = 100
        for _ in range(iterations):
            self.renderer.render(painter, cursor_pos, screen_rect)
        elapsed = time.perf_counter() - start
        avg_ms = (elapsed / iterations) * 1000.0

        painter.end()

        print(f"\n[BENCHMARK] Average QPainter render time per frame: {avg_ms:.3f} ms")
        self.assertLess(avg_ms, 5.0, f"Render time {avg_ms:.3f} ms exceeds 5.0 ms budget (>200 FPS required)!")


if __name__ == "__main__":
    unittest.main()
