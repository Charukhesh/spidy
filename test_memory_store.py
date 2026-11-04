"""Automated Unit Tests for Spidy Persistent Long-Term Memory Store."""

import sys
import unittest
import tempfile
from pathlib import Path

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent))

from spidy.memory_store import MemoryStore


class TestMemoryStore(unittest.TestCase):

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db_path = Path(self.temp_dir.name) / "test_memory.db"
        self.store = MemoryStore(db_path=self.db_path)

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_01_store_and_recall_preferences(self):
        """Verify memory insertion, updating, and recall."""
        # Store preference
        ok = self.store.store_memory("preference", "code_style", "Always use Python type annotations")
        self.assertTrue(ok)

        # Recall by keyword
        memories = self.store.recall_memories("Python")
        self.assertEqual(len(memories), 1)
        self.assertEqual(memories[0]["mem_key"], "code_style")
        self.assertIn("type annotations", memories[0]["content"])

        # Update preference
        ok_update = self.store.store_memory("preference", "code_style", "Use strict typing and docstrings")
        self.assertTrue(ok_update)

        memories_updated = self.store.recall_memories("typing")
        self.assertEqual(len(memories_updated), 1)
        self.assertIn("strict typing", memories_updated[0]["content"])

    def test_02_prompt_formatting_injection(self):
        """Verify prompt formatting context injection."""
        self.store.store_memory("project", "main_repo", "Spidy Desktop Companion with Gemini vision")
        self.store.store_memory("preference", "ui_theme", "Dark glass mode with neon accents")

        prompt_context = self.store.format_memories_for_prompt("What is my main repo?")
        self.assertIn("[REMEMBERED USER PREFERENCES & CONTEXT]", prompt_context)
        self.assertIn("Main_Repo", prompt_context)
        self.assertIn("Spidy Desktop Companion", prompt_context)

    def test_03_session_logs_and_summary(self):
        """Verify session logging and multi-day work summary."""
        self.store.log_interaction("VS Code", "main.py", "Refactor the inference loop", "Cleaned up the threading lock")
        self.store.log_interaction("Spotify", "Chill Beats", "Next track", "Skipped to next track")

        summary = self.store.get_recent_work_summary(limit=2)
        self.assertIn("VS Code", summary)
        self.assertIn("Spotify", summary)


if __name__ == "__main__":
    unittest.main()

