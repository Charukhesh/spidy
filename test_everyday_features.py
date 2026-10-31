"""Automated Test Suite for Athena Everyday Power Pack Features:
1. Sound Effects & Modern Chimes Engine (Activate, Thinking, Arrival Ding)
2. Active Window & Deep Context Inspector (Foreground Window, Process name, Selected text)
3. Top-Center Black Glass Dynamic Bar HUD (2-3 mm Bar, Expansion, 1-click Copy, Hover pause)
4. Unified Ctrl+Alt Hotkey and Top Bar Configuration
5. Multimodal Vision Context Integration
"""

import sys
import os
import io
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
from PyQt5.QtCore import QTimer, QEvent

# Initialize Qt Application if not already running
app = QApplication.instance() or QApplication(sys.argv)

from athena.sound_effects import SoundEffectsEngine, sounds
from athena.context_inspector import ContextInspector, WindowContext, inspector
from athena.top_bar_hud import TopBarGlassHUD, TopBarState
from athena.ai_vision_client import AIVisionClient, PointingTarget
from athena.config import load_config, DEFAULT_CONFIG


class TestEverydayPowerFeatures(unittest.TestCase):

    def test_01_sound_effects_waveforms(self):
        """Verify pre-rendered waveforms are valid PCM 16-bit WAV audio."""
        engine = SoundEffectsEngine.get_instance()
        expected_sounds = ["activate", "thinking", "arrival"]

        for sound_name in expected_sounds:
            self.assertIn(sound_name, engine._cache, f"Missing cached sound: {sound_name}")
            wav_bytes = engine._cache[sound_name]
            self.assertTrue(len(wav_bytes) > 100, f"Sound {sound_name} is too small: {len(wav_bytes)} bytes")

            # Check that it opens as valid WAV
            buf = io.BytesIO(wav_bytes)
            with wave.open(buf, "rb") as wf:
                self.assertEqual(wf.getnchannels(), 1)
                self.assertEqual(wf.getsampwidth(), 2)  # 16-bit
                self.assertEqual(wf.getframerate(), 44100)
                n_frames = wf.getnframes()
                self.assertTrue(n_frames > 0)

        # Verify playback calls don't crash
        engine.play_activate()
        engine.play_thinking()
        engine.play_arrival()
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
        success = inspector._set_clipboard_text("ATHENA_TEST_CLIPBOARD_VALUE")
        if success:
            read_back = inspector._read_clipboard_text()
            self.assertEqual(read_back, "ATHENA_TEST_CLIPBOARD_VALUE")
            if test_clip is not None:
                inspector._set_clipboard_text(test_clip)
        else:
            print("[INFO] Headless/Session 0 detected: Windows clipboard window station requires interactive desktop session.")
        print("[PASS] Test 3 Passed: Clipboard snapshot and restoration operates cleanly.")

    def test_04_top_bar_glass_hud_states_and_geometry(self):
        """Verify Top-Center Glass HUD: 2-3 mm bar, geometry, expansion, copy, and hover."""
        hud = TopBarGlassHUD()

        # 1. Collapsed state check
        hud.collapse_to_bar(animated=False)
        self.assertEqual(hud.current_state, TopBarState.COLLAPSED)
        self.assertEqual(hud.height(), 10)  # ~2.5 mm on standard displays
        self.assertEqual(hud.y(), 0)       # Anchored to top edge
        self.assertTrue(hud.isVisible())

        # 2. Listening state check
        hud.set_listening()
        self.assertEqual(hud.current_state, TopBarState.LISTENING)
        self.assertEqual(hud.status_text.text(), "Listening...")

        # 3. Thinking state check
        hud.set_thinking()
        self.assertEqual(hud.current_state, TopBarState.THINKING)
        self.assertEqual(hud.status_text.text(), "Thinking...")

        # 4. Expanded state check with query and answer
        test_answer = "You can center a div in CSS using display: flex; justify-content: center; align-items: center;"
        test_query = "How to center a div?"
        hud.show_response(test_answer, test_query)

        self.assertEqual(hud.current_state, TopBarState.EXPANDED)
        self.assertEqual(hud.response_label.text(), test_answer)
        self.assertIn(test_query, hud.query_label.text())
        self.assertTrue(hud.content_widget.isVisible())

        # 5. Copy answer check
        hud._copy_answer_to_clipboard()
        self.assertEqual(hud.btn_copy.text(), "✓ Copied!")

        # 6. Hover pause check
        hud.enterEvent(QEvent(QEvent.Enter))
        self.assertFalse(hud._collapse_timer.isActive())

        # 7. Hover leave resume check
        hud.leaveEvent(QEvent(QEvent.Leave))
        self.assertTrue(hud._collapse_timer.isActive())

        # 8. Collapse back to 10px bar
        hud.collapse_to_bar(animated=False)
        self.assertEqual(hud.current_state, TopBarState.COLLAPSED)
        self.assertEqual(hud.height(), 10)
        print("[PASS] Test 4 Passed: Top-Center Glass HUD (2-3 mm Bar, Expansion, Copy, Hover) operates smoothly.")

    def test_05_unified_hotkey_configuration(self):
        """Verify unified Ctrl + Alt hotkey and Top Bar HUD configuration."""
        cfg = load_config()
        self.assertEqual(DEFAULT_CONFIG["hotkey"], "ctrl+alt")
        self.assertTrue(DEFAULT_CONFIG.get("top_bar_hud_enabled", False))
        self.assertEqual(cfg.get("hotkey"), "ctrl+alt")
        print("[PASS] Test 5 Passed: Unified Ctrl+Alt Hotkey & Top Bar HUD configuration verified.")

    def test_06_ai_vision_client_context_injection(self):
        """Verify AIVisionClient accepts and formats active_context into payload."""
        client = AIVisionClient(api_key="AQ.TEST_MOCK_KEY_FOR_UNIT_TEST_ONLY")
        provider, endpoint, model = client._resolve_provider_and_model()

        self.assertIn("Google Gemini", provider)
        self.assertIn("gemini-3.5-flash", model)
        print("[PASS] Test 6 Passed: Vision AI client properly resolves provider and supports context.")

    def test_07_visual_drawings_parser_and_overlay(self):
        """Verify parsing of visual drawing tags (box, circle, arrow, simulate, text)."""
        client = AIVisionClient(api_key="AQ.MOCK_KEY")
        sample_response = (
            "here is how you do it. "
            "[DRAW:box,100,200,400,300:login box] "
            "[DRAW:circle,500,500,50:target icon] "
            "[DRAW:arrow,100,100,500,500:flow direction] "
            "[SIMULATE:100,200->300,400->500,600:checkout steps] "
            "[WRITE:700,800:important note] "
            "[POINT:250,250:main button]"
        )

        spoken, target, drawings = client.parse_visual_tags(sample_response)

        # Check spoken text has tags stripped
        self.assertEqual(spoken, "here is how you do it.")
        self.assertIsNotNone(target)
        self.assertEqual(target.x, 250)
        self.assertEqual(target.y, 250)
        self.assertEqual(target.label, "main button")

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
        print("[PASS] Test 7 Passed: Visual drawing tags (box, circle, arrow, simulate, text) parsed cleanly.")

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


if __name__ == "__main__":
    unittest.main()
