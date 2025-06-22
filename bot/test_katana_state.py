import unittest
import json
from pathlib import Path
import os
import time # For unique file names if needed, or just cleanup

from bot.katana_state import KatanaState, ChatHistory

TEST_STATE_FILE_NAME = "test_katana_state_runtime.json"

class TestKatanaState(unittest.TestCase):

    def setUp(self):
        """Ensure a clean state file for each test."""
        self.test_state_file = Path(TEST_STATE_FILE_NAME)
        if self.test_state_file.exists():
            os.remove(self.test_state_file)
        self.state = KatanaState(state_file_path=self.test_state_file)

    def tearDown(self):
        """Clean up the state file after each test."""
        if self.test_state_file.exists():
            os.remove(self.test_state_file)

    def test_initialization_creates_file(self):
        self.assertTrue(self.test_state_file.exists())
        with open(self.test_state_file, "r") as f:
            data = json.load(f)
        self.assertIn("global_metrics", data)
        self.assertIn("chat_histories", data)
        self.assertIn("user_settings", data)
        self.assertEqual(data["global_metrics"]["version"], "1.0")

    def test_add_chat_message(self):
        self.state.add_chat_message("chat1", "user", "Hello")
        self.state.add_chat_message("chat1", "katana", "Hi there")

        history = self.state.get_chat_history("chat1")
        self.assertEqual(len(history.messages), 2)
        self.assertEqual(history.messages[0]["sender"], "user")
        self.assertEqual(history.messages[0]["text"], "Hello")
        self.assertEqual(history.messages[1]["sender"], "katana")
        self.assertEqual(history.messages[1]["text"], "Hi there")

        # Verify persistence
        loaded_state = KatanaState(state_file_path=self.test_state_file)
        loaded_history = loaded_state.get_chat_history("chat1")
        self.assertEqual(len(loaded_history.messages), 2)
        self.assertEqual(loaded_history.messages[1]["text"], "Hi there")

    def test_get_chat_history_creates_new(self):
        history = self.state.get_chat_history("chat_new")
        self.assertIsInstance(history, ChatHistory)
        self.assertEqual(len(history.messages), 0)
        self.assertIn("chat_new", self.state.chat_histories)

    def test_clear_chat_history(self):
        self.state.add_chat_message("chat_to_clear", "user", "Message 1")
        self.state.add_chat_message("chat_to_clear", "user", "Message 2")

        self.state.clear_chat_history("chat_to_clear")
        history = self.state.get_chat_history("chat_to_clear")
        self.assertEqual(len(history.messages), 0)

        # Verify persistence
        loaded_state = KatanaState(state_file_path=self.test_state_file)
        loaded_history = loaded_state.get_chat_history("chat_to_clear")
        self.assertEqual(len(loaded_history.messages), 0)

        # Test clearing non-existent history (should not error)
        self.state.clear_chat_history("non_existent_chat")
        history_non_existent = self.state.get_chat_history("non_existent_chat")
        self.assertEqual(len(history_non_existent.messages),0)


    def test_user_settings(self):
        default_settings = self.state.get_user_settings("user1")
        self.assertEqual(default_settings["language"], "ru") # Default

        self.state.update_user_setting("user1", "language", "en")
        updated_settings = self.state.get_user_settings("user1")
        self.assertEqual(updated_settings["language"], "en")

        # Verify persistence
        loaded_state = KatanaState(state_file_path=self.test_state_file)
        loaded_settings = loaded_state.get_user_settings("user1")
        self.assertEqual(loaded_settings["language"], "en")

        # Test getting settings for a new user creates defaults
        settings_new_user = self.state.get_user_settings("user2")
        self.assertEqual(settings_new_user["notifications"], True)


    def test_global_metrics(self):
        self.state.update_global_metric("test_metric", 123)
        self.assertEqual(self.state.global_metrics["test_metric"], 123)

        # Verify persistence
        loaded_state = KatanaState(state_file_path=self.test_state_file)
        self.assertEqual(loaded_state.global_metrics["test_metric"], 123)
        self.assertIn("version", loaded_state.global_metrics)


    def test_load_from_nonexistent_file(self):
        temp_file = Path("non_existent_for_load_test.json")
        if temp_file.exists():
            os.remove(temp_file)

        local_state = KatanaState(state_file_path=temp_file)
        self.assertTrue(temp_file.exists()) # Should create it
        self.assertEqual(local_state.global_metrics.get("version"), "1.0")
        if temp_file.exists(): # cleanup
            os.remove(temp_file)

    def test_load_from_corrupted_file(self):
        corrupted_file = Path("corrupted_state_test.json")
        with open(corrupted_file, "w") as f:
            f.write("this is not json")

        # Capture print output to check for error messages (optional, advanced)
        local_state = KatanaState(state_file_path=corrupted_file)
        self.assertTrue(corrupted_file.exists())
        # Should re-initialize to a valid empty state
        self.assertEqual(local_state.global_metrics.get("version"), "1.0")
        self.assertEqual(len(local_state.chat_histories), 0)

        if corrupted_file.exists(): # cleanup
            os.remove(corrupted_file)

if __name__ == '__main__':
    unittest.main()
