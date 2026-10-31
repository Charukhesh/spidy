"""Automated Unit Tests for Athena Desktop Actions & System Controller."""

import sys
import unittest
from pathlib import Path

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent))

from PyQt5.QtWidgets import QApplication
app = QApplication.instance() or QApplication(sys.argv)

from athena.desktop_actions import desktop_actions, DesktopActionController


class TestDesktopActions(unittest.TestCase):

    def test_01_app_aliases_mapping(self):
        """Verify alias resolution maps common names to launch commands."""
        self.assertIn("spotify", DesktopActionController.APP_ALIASES)
        self.assertIn("vscode", DesktopActionController.APP_ALIASES)
        self.assertIn("chrome", DesktopActionController.APP_ALIASES)
        self.assertIn("notepad", DesktopActionController.APP_ALIASES)
        self.assertIn("calculator", DesktopActionController.APP_ALIASES)

    def test_02_clipboard_get_and_set(self):
        """Verify reliable clipboard read and write."""
        test_payload = "ATHENA_DESKTOP_ACTION_TEST_STRING_7788"
        success = desktop_actions.set_clipboard_text(test_payload)
        self.assertTrue(success)

        read_back = desktop_actions.get_clipboard_text()
        self.assertEqual(read_back, test_payload)

    def test_03_execute_action_dispatcher(self):
        """Verify dispatcher processes clipboard actions cleanly."""
        clipboard_msg = "Dispatched clipboard update text"
        success, msg = desktop_actions.execute_action("clipboard", clipboard_msg)
        self.assertTrue(success)
        self.assertIn("clipboard", msg.lower())
        self.assertEqual(desktop_actions.get_clipboard_text(), clipboard_msg)

    def test_04_window_management_syntax(self):
        """Verify window manager rejects invalid commands cleanly."""
        success, msg = desktop_actions.manage_window("nonexistent_command_xyz")
        self.assertFalse(success)
        self.assertIn("Unknown window command", msg)


if __name__ == "__main__":
    unittest.main()

