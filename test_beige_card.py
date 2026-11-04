"""Automated Unit Tests for Spidy's Warm Beige Rounded Tab HUD."""

import sys
import unittest
from pathlib import Path

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent))

from PyQt5.QtWidgets import QApplication
app = QApplication.instance() or QApplication(sys.argv)

from athena.beige_card_hud import BeigeCardHUD


class TestBeigeCardHUD(unittest.TestCase):

    def setUp(self):
        self.hud = BeigeCardHUD()

    def tearDown(self):
        self.hud.close()

    def test_01_typography_and_colors(self):
        """Verify Calibri (Body) typography and warm beige styling."""
        self.hud.show_response("Here is how you define a function in Python:\n```python\ndef hello():\n    return 'world'\n```", "Python function")

        # Verify typography is Calibri
        font = self.hud.response_label.font()
        self.assertEqual(font.family(), "Calibri")

        # Verify badge font is Calibri
        badge_font = self.hud.badge_label.font()
        self.assertEqual(badge_font.family(), "Calibri")

        # Verify card styling contains rounded corners 16px and warm beige rgba(245, 242, 235)
        sheet = self.hud.card_frame.styleSheet()
        self.assertIn("245, 242, 235", sheet)
        self.assertIn("border-radius: 16px", sheet)

    def test_02_show_and_copy_flow(self):
        """Verify show_response and clipboard copy action."""
        sample_text = "Extracted table: | Name | Score |\n| Alice | 98 |"
        self.hud.show_response(sample_text, "OCR Table")

        self.assertEqual(self.hud.last_response, sample_text)
        self.assertEqual(self.hud.last_query, "OCR Table")
        self.assertTrue(self.hud.isVisible())

        # Test copy action
        self.hud._on_copy_clicked()
        clipboard_text = QApplication.clipboard().text()
        self.assertEqual(clipboard_text, sample_text)
        self.assertEqual(self.hud.copy_btn.text(), "✓ Copied!")

    def test_03_toggle_visibility(self):
        """Verify toggling on '~' (tilde)."""
        self.hud.hide()
        self.assertFalse(self.hud.isVisible())

        # Toggle on
        self.hud.toggle_visibility()
        self.assertTrue(self.hud.isVisible())

        # Toggle off
        self.hud.toggle_visibility()
        self.assertFalse(self.hud.isVisible())


if __name__ == "__main__":
    unittest.main()

