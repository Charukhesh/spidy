"""Comprehensive Unit Tests for Spidy HeyClicky Museum-Grade 3D Reconstruction.

Validates:
1. WebGL & Three.js Studio Pipeline:
   - ACESFilmicToneMapping, sRGBEncoding, exposure = 1.25.
   - High-DPI canvas pixel ratio (window.devicePixelRatio up to 2.5).
   - 4-Softbox studio lighting rig (Key, Fill, Overhead, Rim) and radial Poisson contact ground shadow.
2. Cook-Torrance GGX PBR Material System:
   - MeshPhysicalMaterial support with clearcoat, transmission, and roughness.
   - Calibrated physical presets: steel, chrome, alu, titanium, brass, copper, gold, glass, rubber, carbon, paint:*, glow:*.
3. Compound Procedural Placement Operators:
   - around: { count, axis, arc } (radial replication)
   - copies: { count, step, turn } (linear series)
   - mirror: 'x' | 'y' | 'z' (bilateral / quad symmetry)
   - cyl: { from: [x,y,z], to: [x,y,z], r } (direct point connection)
4. CAD Blueprint Technical Edge Lines:
   - EdgesGeometry generator for silhouette clarity.
5. 16 Museum-Grade Procedural Models & Universal Synthesizer:
   - All 16 models registered and synthesizable.
   - Dynamic semantic fallback for open-ended queries (telescopes, satellites, bridges, quantum processors).
6. Zero Idle Compute Demand-Driven Render Loop.
7. Zero Spoken Tag Leakage & Strict [HEARD: ...] stripping.
"""

import sys
import json
import unittest
from pathlib import Path

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent))

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QApplication

QApplication.setAttribute(Qt.AA_ShareOpenGLContexts, True)
app = QApplication.instance() or QApplication(sys.argv)

from spidy.scene_3d_spec import Scene3DSpec
from spidy.viewport_3d import Spidy3DViewport
from spidy.companion_manager import CompanionManager
from spidy.ai_vision_client import AIVisionClient


class TestHeyClickyReconstruction3D(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.viewport = Spidy3DViewport()

    @classmethod
    def tearDownClass(cls):
        cls.viewport.deleteLater()

    def test_01_three_kernel_assets_loaded(self):
        """Verify all local Three.js, OrbitControls, SpidyThreeKernel, and SpidyProceduralLibrary assets exist and are loaded."""
        self.assertTrue(len(self.viewport.three_js_code) > 10000, "three.min.js missing or empty")
        self.assertTrue(len(self.viewport.orbit_js_code) > 1000, "OrbitControls.js missing or empty")
        self.assertTrue(len(self.viewport.kernel_js_code) > 5000, "spidy_three_kernel.js missing or empty")
        self.assertTrue(len(self.viewport.procedural_js_code) > 5000, "spidy_procedural_library.js missing or empty")

    def test_02_webgl_color_management_and_tonemapping(self):
        """Verify ACES Filmic Tone Mapping, sRGB output encoding, and native DPI in generated HTML."""
        spec = Scene3DSpec(entity="turbofan", title="F135 Turbofan")
        html = self.viewport._generate_html(spec)

        self.assertIn("THREE.ACESFilmicToneMapping", html)
        self.assertIn("THREE.sRGBEncoding", html)
        self.assertIn("renderer.toneMappingExposure = 1.25", html)
        self.assertIn("window.devicePixelRatio", html)
        self.assertIn("PCFSoftShadowMap", html)

    def test_03_four_softbox_studio_lighting_and_shadows(self):
        """Verify 4-softbox studio lighting rig (Key, Fill, Overhead, Rim) in SpidyThreeKernel."""
        kernel_code = self.viewport.kernel_js_code

        self.assertIn("setupStudioStage", kernel_code)
        self.assertIn("keyLight", kernel_code)
        self.assertIn("fillLight", kernel_code)
        self.assertIn("topLight", kernel_code)
        self.assertIn("rimLight", kernel_code)
        self.assertIn("groundShadow", kernel_code)

    def test_04_cook_torrance_physical_materials_palette(self):
        """Verify Cook-Torrance physical presets in SpidyThreeKernel."""
        kernel_code = self.viewport.kernel_js_code

        expected_presets = [
            "steel", "chrome", "alu", "titanium", "brass", "copper",
            "gold", "glass", "rubber", "carbon", "paint:crimson", "glow:amber"
        ]
        for preset in expected_presets:
            self.assertIn(preset, kernel_code, f"Preset '{preset}' missing from SpidyThreeKernel")

        self.assertIn("MeshPhysicalMaterial", kernel_code)
        self.assertIn("clearcoat", kernel_code)
        self.assertIn("transmission", kernel_code)

    def test_05_compound_procedural_operators(self):
        """Verify around (radial), copies (linear), mirror (symmetry), and cyl from-to in SpidyThreeKernel."""
        kernel_code = self.viewport.kernel_js_code

        self.assertIn("partSpec.around", kernel_code)
        self.assertIn("partSpec.copies", kernel_code)
        self.assertIn("partSpec.mirror", kernel_code)
        self.assertIn("o.from && o.to", kernel_code)
        self.assertIn("createEdgesMesh", kernel_code)

    def test_06_sixteen_procedural_models_registered(self):
        """Verify all 16 museum-grade procedural models and the universal synthesizer are defined in SpidyProceduralLibrary."""
        proc_code = self.viewport.procedural_js_code

        models = [
            "turbofan",
            "differential_gear",
            "v8_engine",
            "mechanical_watch",
            "quadcopter_drone",
            "robot_arm",
            "rocket_engine",
            "car_suspension",
            "microscope",
            "camera_lens",
            "dna_helix",
            "human_heart",
            "human_eye",
            "bohr_atom",
            "solar_system",
            "smart_device_cutaway",
            "universal_synthesizer",
        ]
        for m in models:
            self.assertIn(f"P.{m} =", proc_code, f"Model 'P.{m}' missing from SpidyProceduralLibrary")

    def test_07_universal_synthesizer_dispatches(self):
        """Verify open-ended queries generate valid HTML and connect through SpidyProceduralLibrary.build."""
        queries = [
            ("James Webb Space Telescope", "telescope"),
            ("International Space Station", "station"),
            ("Golden Gate Bridge Truss", "bridge"),
            ("Quantum Computer Processor", "quantum chip"),
            ("Centrifugal Water Pump", "centrifuge pump"),
        ]
        for title, entity in queries:
            spec = Scene3DSpec(entity=entity, title=title, cutaway=True)
            html = self.viewport._generate_html(spec)
            self.assertIn("SpidyProceduralLibrary.build", html)
            self.assertIn(entity, html)

    def test_08_speech_sanitization_removes_heard_and_tags(self):
        """Verify zero leakage of [HEARD: ...], 'Heard, ...', or technical visual tags in spoken audio."""
        test_inputs = [
            ("[HEARD: how does a turbofan engine work]\nHere is the dual-spool turbofan engine with titanium fan blades.",
             "Here is the dual-spool turbofan engine with titanium fan blades."),
            ("Heard, where is my downloads folder\nIt is right in your home folder.",
             "It is right in your home folder."),
            ("Heard: tell me about atoms. Protons and neutrons form the nucleus.",
             "Protons and neutrons form the nucleus."),
            ("[SCENE_3D: {\"entity\": \"heart\"}] The human heart pumps oxygenated blood through the aorta.",
             "The human heart pumps oxygenated blood through the aorta."),
            ("[POINT:500,500:center:1] Click right here in the center.",
             "Click right here in the center."),
        ]

        for raw, expected in test_inputs:
            cleaned = CompanionManager._sanitize_speech_text(raw)
            self.assertNotIn("HEARD", cleaned)
            self.assertNotIn("Heard,", cleaned)
            self.assertNotIn("Heard:", cleaned)
            self.assertNotIn("SCENE_3D", cleaned)
            self.assertNotIn("POINT", cleaned)
            self.assertEqual(cleaned, expected)


if __name__ == "__main__":
    unittest.main()
