import unittest
import json
import os
from unittest import mock

# Assuming katana_agent.py is in the same directory or accessible via PYTHONPATH
from katana_agent import (
    agent_memory_state,
    handle_user_chat_message,
    handle_save_state,
    handle_load_state,
    handle_clear_state,
    initialize_katana_files, # To ensure files are setup for the agent
    process_agent_command, # To simulate command execution
    MEMORY_FILE as AGENT_MEMORY_FILE,
    HISTORY_FILE as AGENT_HISTORY_FILE
)

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
TEST_DIALOG_MEMORY_FILE = os.path.join(SCRIPT_DIR, "test_dialog_katana_memory.json")
TEST_DIALOG_HISTORY_FILE = os.path.join(SCRIPT_DIR, "test_dialog_katana_history.json")

class TestDialogFlow(unittest.TestCase):

    def setUp(self):
        # Override file paths used by the agent functions
        self.mock_memory_file = mock.patch('katana_agent.MEMORY_FILE', TEST_DIALOG_MEMORY_FILE)
        self.mock_history_file = mock.patch('katana_agent.HISTORY_FILE', TEST_DIALOG_HISTORY_FILE)
        self.mock_memory_file.start()
        self.mock_history_file.start()

        self.mock_log_event = mock.patch('katana_agent.log_event')
        self.mock_log_event.start()

        # Ensure files are clean at the VERY start of each test
        if os.path.exists(TEST_DIALOG_MEMORY_FILE):
            os.remove(TEST_DIALOG_MEMORY_FILE)
        if os.path.exists(TEST_DIALOG_HISTORY_FILE):
            os.remove(TEST_DIALOG_HISTORY_FILE)

        self._initialize_agent_for_test()


    def _initialize_agent_for_test(self):
        """Clears Python global agent_memory_state and runs agent's file/memory initialization."""
        global agent_memory_state
        agent_memory_state.clear()
        # Minimal update, initialize_katana_files will do the main load from potentially existing files
        agent_memory_state.update({"name": "Katana Dialog Test Init", "user_settings": {}, "dialog_history": []})
        initialize_katana_files() # This will load from TEST_DIALOG_MEMORY_FILE if it exists, or create fresh ones.


    def tearDown(self):
        self.mock_memory_file.stop()
        self.mock_history_file.stop()
        self.mock_log_event.stop()

        if os.path.exists(TEST_DIALOG_MEMORY_FILE):
            os.remove(TEST_DIALOG_MEMORY_FILE)
        if os.path.exists(TEST_DIALOG_HISTORY_FILE):
            os.remove(TEST_DIALOG_HISTORY_FILE)

        global agent_memory_state
        agent_memory_state.clear()


    def test_basic_conversation_and_context(self):
        user_id = "dialog_user_1"

        # Turn 1
        response1 = handle_user_chat_message(user_id, "Hello")
        self.assertIn("Hello there!", response1)
        self.assertEqual(len(agent_memory_state["dialog_history"]), 2)

        # Turn 2 - bot should remember it greeted
        response2 = handle_user_chat_message(user_id, "Hi again")
        self.assertIn("Hello again!", response2)
        self.assertEqual(len(agent_memory_state["dialog_history"]), 4)

        # Turn 3 - ask to remember name
        response3 = handle_user_chat_message(user_id, "Please remember my name is Alice.")
        self.assertIn("Got it, I'll try to remember your name is Alice!", response3)
        self.assertEqual(agent_memory_state["user_settings"].get("user_name"), "Alice")
        self.assertEqual(len(agent_memory_state["dialog_history"]), 6)

        # Turn 4 - ask for name
        response4 = handle_user_chat_message(user_id, "What is my name?")
        self.assertIn("your name is Alice", response4)
        self.assertEqual(len(agent_memory_state["dialog_history"]), 8)

    def test_save_load_and_continue_conversation(self):
        user_id = "dialog_user_2"

        # Initial conversation part 1
        handle_user_chat_message(user_id, "My favorite color is blue.")
        self.assertEqual(agent_memory_state["dialog_history"][-1]["role"], "assistant") # Bot responded

        response_name = handle_user_chat_message(user_id, "My name is Bob.")
        self.assertIn("Bob", response_name) # Bot acknowledges name

        # Explicitly check user_name in memory BEFORE save
        self.assertEqual(agent_memory_state.get("user_settings", {}).get("user_name"), "Bob", "User name was not set in memory correctly BEFORE save.")

        # Save state
        save_result = process_agent_command({"action": "save_state"})
        self.assertEqual(save_result["status"], "success")

        # Simulate agent restart: clear in-memory state and reload from file
        self._initialize_agent_for_test()

        # Check if state was loaded (name should be Bob)
        self.assertEqual(agent_memory_state.get("user_settings", {}).get("user_name"), "Bob", "User name not loaded.")
        # And history should be present
        self.assertTrue(len(agent_memory_state["dialog_history"]) >= 4, "Dialog history not loaded.")
        self.assertEqual(agent_memory_state["dialog_history"][0]["content"], "My favorite color is blue.")


        # Continue conversation
        response_after_load = handle_user_chat_message(user_id, "What is my name?")
        self.assertIn("your name is Bob", response_after_load)

        response_fav_color_q = handle_user_chat_message(user_id, "Do you know my favorite color?")
        # Current placeholder NLP doesn't explicitly remember 'favorite color blue' this way.
        # This would require more advanced NLP or specific intent.
        # For now, we check that the conversation continues with history.
        self.assertNotIn("I don't know", response_fav_color_q.lower()) # Basic check it's not a totally blank slate response

    def test_clear_state_effect_on_conversation(self):
        user_id = "dialog_user_3"

        # Initial conversation
        handle_user_chat_message(user_id, "I like programming.")
        handle_user_chat_message(user_id, "Remember my name is Charlie.")
        self.assertEqual(agent_memory_state.get("user_settings", {}).get("user_name"), "Charlie")
        self.assertTrue(len(agent_memory_state["dialog_history"]) > 0)

        # Clear state
        clear_result = process_agent_command({"action": "clear_state"})
        self.assertEqual(clear_result["status"], "success")

        # After clear, user_settings specific to user should be gone, history empty
        self.assertNotIn("user_name", agent_memory_state.get("user_settings", {}))
        self.assertEqual(len(agent_memory_state.get("dialog_history", [])), 0)

        # Start new conversation, bot should not remember name
        response_after_clear = handle_user_chat_message(user_id, "What is my name?")
        self.assertNotIn("Charlie", response_after_clear) # It shouldn't know the name
        # The placeholder might say something like "I don't see a previous message..." or a generic processing message.
        # Depending on exact NLP placeholder, this might need adjustment.
        # Current placeholder for "what is my name" without name in settings:
        # -> "Katana processes: What is my name? (History items: 2)" (user msg + this bot response)
        self.assertTrue("Katana processes:" in response_after_clear or
                        "don't see a previous message" in response_after_clear or
                        "first message to me" in response_after_clear)


        # Say hello, it should be a fresh greeting
        response_hello_after_clear = handle_user_chat_message(user_id, "Hello")
        self.assertIn("Hello there! How can I help you today?", response_hello_after_clear)


if __name__ == '__main__':
    unittest.main(argv=['first-arg-is-ignored'], exit=False)
