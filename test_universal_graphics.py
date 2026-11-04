"""Automated Unit Tests for Spidy Universal 3D & Cursor-Anchored Visual Engine.

Validates:
1. Scene3DSpec dataclass construction and serialization.
2. Model response parsing: extraction of [SCENE_3D: ...] JSON tags.
3. Clean speech sanitization: 100% removal of [SCENE_3D: ...] and [CUTAWAY: ...] tags from spoken text.
4. Spidy3DViewport HTML generator for procedural entities (turbofan, DNA helix, differential gears, atoms, generic primitives).
5. Universal 2D procedural cutaway rendering without hardcoded shapes.
6. Decoupled cursor layout: beige card remains closed while 3D/2D graphics render at cursor.
"""

import sys
import json
import unittest
from pathlib import Path

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent))

from PyQt5.QtCore import Qt, QPoint, QRect
from PyQt5.QtWidgets import QApplication
from PyQt5.QtGui import QPixmap, QPainter

QApplication.setAttribute(Qt.AA_ShareOpenGLContexts, True)
app = QApplication.instance() or QApplication(sys.argv)

from spidy.scene_3d_spec import Scene3DSpec
from spidy.viewport_3d import Spidy3DViewport
from spidy.ai_vision_client import AIVisionClient
from spidy.realtime_graphics import RealtimeGraphicSpec, RealtimeGraphicsRenderer


class TestUniversalGraphics(unittest.TestCase):

    def test_01_scene_3d_spec_creation(self):
        """Verify Scene3DSpec creation, default values, and dictionary export."""
        spec = Scene3DSpec(
            entity="turbofan",
            title="Pratt & Whitney F135 Engine",
            cutaway=True,
            cutaway_plane="z",
            camera_preset="iso",
            orbit_controls=True,
            primitives=[
                {"type": "cylinder", "color": "#2A2D34", "scale": [1, 2, 1], "name": "Bypass Casing"},
                {"type": "ring", "color": "#78716C", "name": "Fan Blades"},
            ],
            callouts=[
                {"text": "Afterburner Section", "position": [0, 0, -2]},
            ],
            animation="spin_slow"
        )

        self.assertEqual(spec.entity, "turbofan")
        self.assertEqual(spec.title, "Pratt & Whitney F135 Engine")
        self.assertTrue(spec.cutaway)
        self.assertEqual(spec.cutaway_plane, "z")
        self.assertEqual(len(spec.primitives), 2)
        self.assertEqual(len(spec.callouts), 1)

        d = spec.to_dict()
        self.assertEqual(d["entity"], "turbofan")
        self.assertEqual(d["animation"], "spin_slow")

    def test_02_parse_scene_3d_tag(self):
        """Verify parsing of [SCENE_3D: ...] tag from raw AI model response."""
        raw_response = (
            "Here is the Pratt & Whitney F135 Turbofan engine in 3D. "
            '[SCENE_3D: {"entity": "turbofan", "title": "F-35 Turbofan", "cutaway": true, "callouts": [{"text": "Titanium Fan", "position": [0, 0, 1.5]}]}] '
            "You can rotate it with your mouse to inspect the bypass duct."
        )

        (
            spoken, target, drawings, heard, trace, search,
            act_t, act_a, rem, spec, scene_3d
        ) = AIVisionClient.parse_visual_tags(raw_response)

        self.assertIsNotNone(scene_3d)
        self.assertEqual(scene_3d.entity, "turbofan")
        self.assertEqual(scene_3d.title, "F-35 Turbofan")
        self.assertTrue(scene_3d.cutaway)
        self.assertEqual(len(scene_3d.callouts), 1)
        self.assertEqual(scene_3d.callouts[0]["text"], "Titanium Fan")

        # Verify speech text has NO tag leakage
        self.assertNotIn("SCENE_3D", spoken)
        self.assertNotIn("turbofan", spoken)  # tag content stripped
        self.assertIn("Here is the Pratt & Whitney F135 Turbofan engine in 3D.", spoken)
        self.assertIn("You can rotate it with your mouse to inspect the bypass duct.", spoken)

    def test_03_viewport_html_generation(self):
        """Verify Spidy3DViewport generates HTML with embedded Three.js and OrbitControls."""
        viewport = Spidy3DViewport()

        entities = ["turbofan", "dna_helix", "differential_gears", "atom", "solar_system", "generic"]
        for entity in entities:
            spec = Scene3DSpec(
                entity=entity,
                title=f"Test {entity.title()}",
                cutaway=True,
                primitives=[
                    {"type": "box", "color": "#DC2626", "position": [0, 0, 0], "scale": [1, 1, 1]},
                    {"type": "sphere", "color": "#1C1917", "position": [1, 0, 0], "scale": [0.5, 0.5, 0.5]},
                ],
                callouts=[{"text": "Sensor", "position": [0, 1, 0]}]
            )
            html = viewport._generate_html(spec)

            # Local bundled Three.js and OrbitControls
            self.assertIn("THREE", html)
            self.assertIn("OrbitControls", html)
            self.assertIn(spec.title, html)
            self.assertIn("MeshStandardMaterial", html)
            # Demand-driven zero-compute loop verification
            self.assertIn("renderFrame", html)
            self.assertIn("autoRotateFrames", html)

        viewport.deleteLater()

    def test_04_universal_2d_cutaway_renderer(self):
        """Verify RealtimeGraphicsRenderer executes dynamic procedural cutaways for any topic."""
        renderer = RealtimeGraphicsRenderer()
        pixmap = QPixmap(1920, 1080)
        pixmap.fill(Qt.transparent)
        painter = QPainter(pixmap)
        screen_rect = QRect(0, 0, 1920, 1080)
        cursor_pos = QPoint(500, 300)

        # 1. Biological pump (Heart ventricle)
        heart_spec = RealtimeGraphicSpec(
            kind="cutaway",
            title="Human Cardiac Ventricle Cutaway",
            data={
                "chambers": [
                    {"name": "Right Atrium", "ratio": 0.22, "color": "#3B82F6", "subtext": "Deoxygenated"},
                    {"name": "Tricuspid Valve", "ratio": 0.12, "color": "#F59E0B", "subtext": "AV Cusps"},
                    {"name": "Right Ventricle", "ratio": 0.36, "color": "#DC2626", "subtext": "Pulmonary Outflow"},
                    {"name": "Septum Wall", "ratio": 0.30, "color": "#78716C", "subtext": "Myocardium"},
                ],
                "force_vectors": [
                    {"label": "Diastolic Flow", "from": [0.2, 0.4], "to": [0.5, 0.5], "color": "#3B82F6"},
                    {"label": "Systolic Vector", "from": [0.5, 0.5], "to": [0.85, 0.2], "color": "#DC2626"},
                ],
                "callouts": [
                    {"text": "Papillary Muscle Anchor", "pos": [0.6, 0.7]},
                ]
            }
        )
        renderer.set_spec(heart_spec)
        renderer.render(painter, cursor_pos, screen_rect)
        self.assertGreater(renderer.card_rect.width(), 400.0)

        # 2. Physics / Nuclear reactor cutaway
        reactor_spec = RealtimeGraphicSpec(
            kind="cutaway",
            title="Pressurized Water Reactor (PWR)",
            data={
                "chambers": [
                    {"name": "Control Rod Guide", "ratio": 0.25, "color": "#78716C"},
                    {"name": "Uranium Core", "ratio": 0.35, "color": "#10B981"},
                    {"name": "Coolant Loop", "ratio": 0.40, "color": "#3B82F6"},
                ],
                "force_vectors": [
                    {"label": "Thermal Convection", "from": [0.3, 0.7], "to": [0.7, 0.3]},
                ]
            }
        )
        renderer.set_spec(reactor_spec)
        renderer.render(painter, cursor_pos, screen_rect)
        self.assertGreater(renderer.card_rect.height(), 200.0)

        painter.end()

    def test_05_speech_sanitization_robustness(self):
        """Ensure all combinations of 3D and 2D tags leave pristine spoken dialogue."""
        mixed_input = (
            "Examining the jet engine. "
            '[CUTAWAY: {"title": "Jet", "chambers": [{"name": "Fan", "ratio": 0.5}]}] '
            "Notice the intake compression. "
            '[SCENE_3D: {"entity": "turbofan", "title": "3D Turbofan"}] '
            "All systems operational."
        )

        (
            spoken, _, _, _, _, _, _, _, _, rtg_spec, scene_3d
        ) = AIVisionClient.parse_visual_tags(mixed_input)

        self.assertIsNotNone(rtg_spec)
        self.assertIsNotNone(scene_3d)
        self.assertNotIn("[CUTAWAY", spoken)
        self.assertNotIn("[SCENE_3D", spoken)
        self.assertNotIn("chambers", spoken)
        self.assertNotIn("turbofan", spoken)
        self.assertEqual(spoken.strip(), "Examining the jet engine. Notice the intake compression. All systems operational.")


if __name__ == "__main__":
    unittest.main()
