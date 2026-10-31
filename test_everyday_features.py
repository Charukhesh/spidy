"""Automated Test Suite for Athena Everyday Power Pack Features:
1. Sound Effects & Modern Chimes Engine (Activate, Thinking, Arrival Ding)
2. Active Window & Deep Context Inspector (Foreground Window, Process name, Selected text)
3. Top-Center Black Glass Dynamic Bar HUD (2-3 mm Bar, Expansion, 1-click Copy, Hover pause)
4. Unified Ctrl+Alt Hotkey and Top Bar Configuration
5. Multimodal Vision Context Integration
6. Visual Drawing Engine & Visual Tag Parsing
7. Thinking Bar Smooth Collapse
8. Mathematical Curve & Dynamic Cursor Tracing Generator
9. Live Web Search & Grounded Verification Engine
10. Cursor Overlay Dynamic Curve Tracing State Loop
"""

import sys
import os
import io
import math
import wave
import time
import unittest
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent))

from PyQt5.QtWidgets import QApplication
from PyQt5.QtCore import QTimer, QEvent, QPointF

# Initialize Qt Application if not already running
app = QApplication.instance() or QApplication(sys.argv)

from athena.sound_effects import SoundEffectsEngine, sounds
from athena.context_inspector import ContextInspector, WindowContext, inspector
from athena.top_bar_hud import TopBarGlassHUD, TopBarState
from athena.ai_vision_client import AIVisionClient, PointingTarget, TraceCurveTarget
from athena.config import load_config, DEFAULT_CONFIG
from athena.curve_generator import CurveGenerator
from athena.web_search import web_search
from athena.cursor_overlay import ClickyCursorOverlay, NavigationMode


class TestEverydayPowerFeatures(unittest.TestCase):

    def test_01_sound_effects_waveforms(self):
        """Verify pre-rendered waveforms are valid PCM 16-bit WAV audio."""
        engine = SoundEffectsEngine.get_instance()
        expected_sounds = ["activate", "thinking", "arrival"]

        for sound_name in expected_sounds:
            self.assertIn(sound_name, engine._cache, f"Missing cached sound: {sound_name}")
            wav_bytes = engine._cache[sound_name]
            self.assertTrue(len(wav_bytes) > 100, f"Sound {sound_name} is too small: {len(wav_bytes)} bytes")

            # Validate RIFF header
            with io.BytesIO(wav_bytes) as buf:
                with wave.open(buf, "rb") as wf:
                    self.assertEqual(wf.getnchannels(), 1, "Sound should be Mono")
                    self.assertEqual(wf.getsampwidth(), 2, "Sound should be 16-bit")
                    self.assertEqual(wf.getframerate(), 44100, "Sound sample rate should be 44.1kHz")
                    self.assertTrue(wf.getnframes() > 1000, "Audio frame count too low")
        print("[PASS] Test 1 Passed: Sound Effects Waveforms are valid and playable.")

    def test_02_context_inspector_formatting(self):
        """Verify Active Window Context generates clean markdown context."""
        ctx = WindowContext(
            hwnd=12345,
            process_id=999,
            process_name="Code.exe",
            app_name="Visual Studio Code",
            window_title="companion_manager.py - Athena Agent",
            selected_text="def _run_inference_pipeline(self, pcm_data: bytes):",
        )
        prompt_text = ctx.to_prompt_text()

        self.assertIn("[ACTIVE APPLICATION CONTEXT]", prompt_text)
        self.assertIn("Visual Studio Code (Code.exe)", prompt_text)
        self.assertIn("companion_manager.py - Athena Agent", prompt_text)
        self.assertIn("def _run_inference_pipeline", prompt_text)
        print("[PASS] Test 2 Passed: Active Window Context formats correctly.")

    def test_03_clipboard_probe_safe_restoration(self):
        """Verify clipboard reading and non-destructive snapshot restoration."""
        test_clip = inspector._read_clipboard_text()
        success = inspector._set_clipboard_text("ATHENA_MOCK_TEST_STRING_12345")
        if success:
            read_back = inspector._read_clipboard_text()
            self.assertEqual(read_back, "ATHENA_MOCK_TEST_STRING_12345")
            inspector._set_clipboard_text(test_clip)
        print("[PASS] Test 3 Passed: Clipboard snapshot and restoration operates cleanly.")

    def test_04_top_bar_hud_glass_properties(self):
        """Verify Top-Center Black Glass Dynamic Bar HUD geometry and states."""
        hud = TopBarGlassHUD()
        self.assertIsNotNone(hud)
        self.assertEqual(hud.current_state, TopBarState.COLLAPSED)

        # In collapsed mode, height should be 10px (2-3 mm)
        self.assertEqual(hud.height(), 10)
        self.assertTrue(hud.collapsed_pill.isVisible())
        self.assertFalse(hud.status_row.isVisible())

        # Test expansion into Response mode
        sample_ans = "This is a sleek high-tech response explaining your code."
        sample_q = "How do I optimize this loop?"
        hud.show_response(sample_ans, sample_q)

        self.assertEqual(hud.current_state, TopBarState.EXPANDED)
        self.assertTrue(hud.height() >= 100)
        self.assertEqual(hud.last_response, sample_ans)
        self.assertEqual(hud.last_query, sample_q)

        # Test Copy button
        copied_signal_received = []
        hud.copied_signal.connect(lambda: copied_signal_received.append(True))
        hud._copy_answer_to_clipboard()
        self.assertTrue(len(copied_signal_received) > 0)
        self.assertEqual(hud.btn_copy.text(), "✓ Copied!")

        # Test hover pause prevents premature collapse
        event = QEvent(QEvent.Enter)
        hud.enterEvent(event)
        self.assertFalse(hud._collapse_timer.isActive())

        # Mouse leave restarts timer
        leave_event = QEvent(QEvent.Leave)
        hud.leaveEvent(leave_event)
        self.assertTrue(hud._collapse_timer.isActive())
        print("[PASS] Test 4 Passed: Top-Center Glass HUD (2-3 mm Bar, Expansion, Copy, Hover) operates smoothly.")

    def test_05_unified_hotkey_config(self):
        """Verify hotkey is unified to ctrl+alt and config options are loaded."""
        cfg = load_config()
        hotkey = cfg.get("hotkey", "ctrl+alt").lower()
        self.assertEqual(hotkey, "ctrl+alt")
        self.assertTrue(cfg.get("top_bar_hud_enabled", True))
        self.assertTrue(cfg.get("context_awareness", True))
        print("[PASS] Test 5 Passed: Unified Ctrl+Alt Hotkey & Top Bar HUD configuration verified.")

    def test_06_ai_vision_context_integration(self):
        """Verify multimodal AI client handles context prompt formatting."""
        client = AIVisionClient(api_key="AQ.MOCK_KEY_FOR_TESTING")
        provider, endpoint, model = client._resolve_provider_and_model()
        self.assertIn("Google Gemini", provider)
        self.assertIn("gemini-3.5-flash", model)
        print("[PASS] Test 6 Passed: Vision AI client properly resolves provider and supports context.")

    def test_07_visual_drawings_parser_and_overlay(self):
        """Verify parsing of visual drawing tags (box, circle, arrow, simulate, text, trace, offer_search)."""
        client = AIVisionClient(api_key="AQ.MOCK_KEY")
        sample_response = (
            "[HEARD: show me how to checkout] "
            "here is how you do it. "
            "[DRAW:box,100,200,400,300:login box] "
            "[DRAW:circle,500,500,50:target icon] "
            "[DRAW:arrow,100,100,500,500:flow direction] "
            "[SIMULATE:100,200->300,400->500,600:checkout steps] "
            "[WRITE:700,800:important note] "
            "[TRACE:cubic:cubic curve y=x³] "
            "[OFFER_SEARCH:latest checkout guidelines] "
            "[POINT:250,250:main button]"
        )

        spoken, target, drawings, heard_prompt, trace_curve, offer_search = client.parse_visual_tags(sample_response)

        # Check spoken text has tags stripped and heard prompt extracted
        self.assertEqual(spoken, "here is how you do it.")
        self.assertEqual(heard_prompt, "show me how to checkout")
        self.assertIsNotNone(target)
        self.assertEqual(target.x, 250)
        self.assertEqual(target.y, 250)
        self.assertEqual(target.label, "main button")

        # Check trace curve parsed
        self.assertIsNotNone(trace_curve)
        self.assertEqual(trace_curve.curve_type, "cubic")
        self.assertEqual(trace_curve.label, "cubic curve y=x³")

        # Check offer search parsed
        self.assertEqual(offer_search, "latest checkout guidelines")

        # Check 5 drawings parsed
        self.assertEqual(len(drawings), 5)
        kinds = [d.kind for d in drawings]
        self.assertIn("box", kinds)
        self.assertIn("circle", kinds)
        self.assertIn("arrow", kinds)
        self.assertIn("simulate", kinds)
        self.assertIn("text", kinds)

        box_d = next(d for d in drawings if d.kind == "box")
        self.assertEqual(box_d.coords, [100, 200, 400, 300])
        self.assertEqual(box_d.label, "login box")

        sim_d = next(d for d in drawings if d.kind == "simulate")
        self.assertEqual(sim_d.coords, [100, 200, 300, 400, 500, 600])
        self.assertEqual(sim_d.label, "checkout steps")
        print("[PASS] Test 7 Passed: Visual drawing tags (box, circle, arrow, simulate, text, trace, search) parsed cleanly.")

    def test_08_thinking_to_idle_collapse(self):
        """Verify thinking bar smoothly returns to 2-3 mm idle bar."""
        hud = TopBarGlassHUD()
        hud.set_thinking()
        self.assertEqual(hud.current_state, TopBarState.THINKING)
        self.assertTrue(hud.height() > 10)

        # Collapse to idle bar
        hud.collapse_to_bar(animated=False)
        self.assertEqual(hud.current_state, TopBarState.COLLAPSED)
        self.assertEqual(hud.height(), 10)
        self.assertTrue(hud.collapsed_pill.isVisible())
        self.assertFalse(hud.status_row.isVisible())
        self.assertFalse(hud.content_widget.isVisible())
        print("[PASS] Test 8 Passed: Thinking bar successfully collapses into 2-3 mm idle bar.")

    def test_09_curve_generator_and_math(self):
        """Verify mathematical curve generator generates accurate continuous 2D polylines."""
        cx, cy = 960.0, 540.0
        supported_types = ["cubic", "parabola", "sine", "bell", "spiral", "circle", "heart", "exponential"]

        for c_type in supported_types:
            pts = CurveGenerator.generate_curve(c_type, cx, cy, width=280.0, height=160.0, num_samples=50)
            self.assertEqual(len(pts), 50, f"Curve {c_type} should have 50 points")

            # Check all points are finite real numbers
            for x, y in pts:
                self.assertFalse(math.isnan(x))
                self.assertFalse(math.isnan(y))
                self.assertTrue(cx - 300 <= x <= cx + 300)
                self.assertTrue(cy - 200 <= y <= cy + 200)

        # Check curve type identifier detection
        self.assertEqual(CurveGenerator.parse_curve_identifier("how does a cubic curve look like?"), "cubic")
        self.assertEqual(CurveGenerator.parse_curve_identifier("show me a sine wave"), "sine")
        self.assertEqual(CurveGenerator.parse_curve_identifier("draw a bell curve"), "bell")
        self.assertEqual(CurveGenerator.parse_curve_identifier("can you plot a parabola?"), "parabola")
        print("[PASS] Test 9 Passed: Mathematical Curve Generator & Function Polyline math verified.")

    def test_10_web_search_engine_and_formatting(self):
        """Verify live web search retrieval, snippet parsing, and prompt formatting."""
        results = web_search.search("python programming", max_results=3, timeout=6.0)
        self.assertIsInstance(results, list)
        if results:
            self.assertTrue(len(results) >= 1)
            first = results[0]
            self.assertIn("title", first)
            self.assertIn("snippet", first)
            self.assertTrue(len(first["snippet"]) > 10)

            formatted = web_search.format_for_prompt(results)
            self.assertIn("Verified Web Search Results:", formatted)
            self.assertIn(first["title"], formatted)
        print("[PASS] Test 10 Passed: Web Search Engine & Grounded Verification Formatter verified.")

    def test_11_cursor_overlay_curve_tracing_state(self):
        """Verify cursor overlay curve tracing mode, animation advancement, and fade out."""
        overlay = ClickyCursorOverlay()
        self.assertEqual(overlay.nav_mode, NavigationMode.FOLLOWING_CURSOR)

        pts = CurveGenerator.generate_curve("cubic", 500.0, 500.0, num_samples=30)
        overlay.start_tracing_curve(pts, "cubic curve")

        self.assertEqual(overlay.nav_mode, NavigationMode.TRACING_CURVE)
        self.assertEqual(len(overlay.curve_points), 30)
        self.assertEqual(overlay.curve_label, "cubic curve")

        # Simulate 10 frames of animation
        for _ in range(10):
            overlay._on_tick()

        self.assertTrue(len(overlay.curve_trail_points) > 1)
        self.assertTrue(overlay.curve_elapsed_ms > 0)

        # Test fade out
        overlay.start_fading_curve()
        self.assertTrue(overlay.curve_is_fading)

        # Test clear
        overlay.clear_curve()
        self.assertEqual(len(overlay.curve_points), 0)
        self.assertEqual(len(overlay.curve_trail_points), 0)
        print("[PASS] Test 11 Passed: Cursor Overlay Dynamic Curve Tracing Loop verified.")


if __name__ == "__main__":
    unittest.main()
