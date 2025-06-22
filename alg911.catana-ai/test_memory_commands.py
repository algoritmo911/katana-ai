import unittest
import json
import os
import shutil
from unittest import mock

# Assuming katana_agent.py is in the same directory or accessible via PYTHONPATH
# For testing, we'll need to import the functions and global variables from it.
# This might require adjusting sys.path or how katana_agent is structured if it's not directly importable.
# For now, let's assume we can import them.
# If katana_agent.py relies on being run as __main__, we might need to refactor parts or use subprocess.

# To make this self-contained for now, we might need to duplicate some path definitions
# or ensure the test runner sets the CWD correctly.
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
TEST_MEMORY_FILE = os.path.join(SCRIPT_DIR, "test_katana_memory.json")
TEST_HISTORY_FILE = os.path.join(SCRIPT_DIR, "test_katana_history.json")
TEST_COMMANDS_FILE = os.path.join(SCRIPT_DIR, "test_katana_commands.json") # Not directly tested by these handlers but good to have

# Mocked versions of functions from katana_agent or the actual ones if importable
# For robust testing, we'd ideally import from katana_agent.
# For now, direct import attempt:
try:
    from katana_agent import (
        agent_memory_state,
        load_memory, save_memory,
        load_history, save_history,
        handle_save_state, handle_load_state, handle_clear_state,
        handle_user_chat_message, get_contextual_nlp_response, # Added new functions
        initialize_katana_files, # May need to call this to ensure agent_memory_state is initialized
        MEMORY_FILE as AGENT_MEMORY_FILE, # Capture original paths
        HISTORY_FILE as AGENT_HISTORY_FILE,
        COMMANDS_FILE as AGENT_COMMANDS_FILE,
        log_event # So we can mock it to suppress log spew during tests if needed
    )
except ImportError:
    print("Failed to import from katana_agent. Ensure it's in PYTHONPATH or same directory.")
    # Provide dummy implementations or raise error if essential
    agent_memory_state = {}
    def load_memory(): pass
    def save_memory(): pass
    def load_history(): pass
    def save_history(h): pass
    def handle_save_state(p): pass
    def handle_load_state(p): pass
    def handle_clear_state(p): pass
    def initialize_katana_files(): pass
    AGENT_MEMORY_FILE = "katana_memory.json"
    AGENT_HISTORY_FILE = "katana.history.json"
    AGENT_COMMANDS_FILE = "katana.commands.json"
    def log_event(msg, level="info"): print(f"LOG_EVENT_MOCK: {msg}")


class TestMemoryCommands(unittest.TestCase):

    def setUp(self):
        # Override file paths used by the agent functions to use test-specific files
        self.mock_memory_file = mock.patch('katana_agent.MEMORY_FILE', TEST_MEMORY_FILE)
        self.mock_history_file = mock.patch('katana_agent.HISTORY_FILE', TEST_HISTORY_FILE)

        self.mock_memory_file.start()
        self.mock_history_file.start()

        # Mock log_event to prevent console spam during tests, unless debugging
        self.mock_log_event = mock.patch('katana_agent.log_event')
        self.mock_log_event.start()

        # Ensure a clean state for agent_memory_state before each test
        # The actual agent_memory_state is global in katana_agent.py
        # We need to reset it or control its state.
        # A simple way is to re-initialize it.
        global agent_memory_state # from katana_agent
        agent_memory_state.clear()
        agent_memory_state.update({
            "name": "Katana Test", # Default test name
            "user_settings": {},
            "dialog_history": []
        })
        # Ensure test files are clean before each test
        if os.path.exists(TEST_MEMORY_FILE):
            os.remove(TEST_MEMORY_FILE)
        if os.path.exists(TEST_HISTORY_FILE):
            os.remove(TEST_HISTORY_FILE)

    def tearDown(self):
        self.mock_memory_file.stop()
        self.mock_history_file.stop()
        self.mock_log_event.stop()

        # Clean up test files
        if os.path.exists(TEST_MEMORY_FILE):
            os.remove(TEST_MEMORY_FILE)
        if os.path.exists(TEST_HISTORY_FILE):
            os.remove(TEST_HISTORY_FILE)

        # Restore agent_memory_state if necessary, though setUp handles reset for next test
        global agent_memory_state # from katana_agent
        agent_memory_state.clear()


    def test_handle_save_state_success(self):
        global agent_memory_state # from katana_agent
        agent_memory_state.update({
            "user_settings": {"theme": "dark", "language": "jp"},
            "dialog_history": [
                {"role": "user", "content": "Hello"},
                {"role": "assistant", "content": "Konbanwa"}
            ],
            "some_other_key": "should_be_saved"
        })

        result = handle_save_state()
        self.assertEqual(result["status"], "success")

        # Verify memory file content
        self.assertTrue(os.path.exists(TEST_MEMORY_FILE))
        with open(TEST_MEMORY_FILE, 'r') as f:
            saved_memory = json.load(f)

        self.assertEqual(saved_memory["user_settings"], {"theme": "dark", "language": "jp"})
        self.assertEqual(saved_memory["dialog_history"], [{"role": "user", "content": "Hello"}, {"role": "assistant", "content": "Konbanwa"}])
        self.assertEqual(saved_memory["name"], "Katana Test") # From setUp default or if it was updated
        self.assertEqual(saved_memory["some_other_key"], "should_be_saved")

        # Verify history file content
        self.assertTrue(os.path.exists(TEST_HISTORY_FILE))
        with open(TEST_HISTORY_FILE, 'r') as f:
            saved_history = json.load(f)
        self.assertEqual(saved_history, [{"role": "user", "content": "Hello"}, {"role": "assistant", "content": "Konbanwa"}])

    def test_handle_load_state_success(self):
        global agent_memory_state # from katana_agent
        initial_memory_content = {
            "name": "Katana Loaded",
            "user_settings": {"notifications": "on"},
            "dialog_history": [{"role": "system", "content": "System ready"}],
            "another_key": "value_from_file"
        }
        with open(TEST_MEMORY_FILE, 'w') as f:
            json.dump(initial_memory_content, f)

        # Clear agent_memory_state before load to ensure it's populated from file
        agent_memory_state.clear()

        self.assertTrue(os.path.exists(TEST_MEMORY_FILE), "TEST_MEMORY_FILE should exist before load_state")

        result = handle_load_state()
        self.assertEqual(result["status"], "success")

        self.assertEqual(agent_memory_state["name"], "Katana Loaded")
        self.assertEqual(agent_memory_state["user_settings"], {"notifications": "on"})
        self.assertEqual(agent_memory_state["dialog_history"], [{"role": "system", "content": "System ready"}])
        self.assertEqual(agent_memory_state["another_key"], "value_from_file")

        # Verify history file is also updated
        self.assertTrue(os.path.exists(TEST_HISTORY_FILE))
        with open(TEST_HISTORY_FILE, 'r') as f:
            history_content = json.load(f)
        self.assertEqual(history_content, [{"role": "system", "content": "System ready"}])

    def test_handle_load_state_from_empty_or_minimal_memory_file(self):
        global agent_memory_state # from katana_agent

        # Scenario 1: Memory file is empty JSON {}
        with open(TEST_MEMORY_FILE, 'w') as f:
            json.dump({}, f)

        agent_memory_state.clear() # Start fresh
        result = handle_load_state()
        self.assertEqual(result["status"], "success") # Should succeed and initialize
        self.assertEqual(agent_memory_state.get("user_settings"), {})
        self.assertEqual(agent_memory_state.get("dialog_history"), [])
        self.assertNotIn("name", agent_memory_state) # Name wouldn't be there if loaded from {}

        # Verify history file is empty list
        with open(TEST_HISTORY_FILE, 'r') as f:
            history_content = json.load(f)
        self.assertEqual(history_content, [])


        # Scenario 2: Memory file exists but is missing specific keys
        minimal_memory_content = {"name": "Katana Minimal"}
        with open(TEST_MEMORY_FILE, 'w') as f:
            json.dump(minimal_memory_content, f)

        agent_memory_state.clear()
        result = handle_load_state()
        self.assertEqual(result["status"], "success")
        self.assertEqual(agent_memory_state["name"], "Katana Minimal")
        self.assertEqual(agent_memory_state.get("user_settings"), {}) # Should be initialized
        self.assertEqual(agent_memory_state.get("dialog_history"), []) # Should be initialized

        with open(TEST_HISTORY_FILE, 'r') as f: # History should be empty
            history_content = json.load(f)
        self.assertEqual(history_content, [])


    def test_handle_clear_state_success(self):
        global agent_memory_state # from katana_agent
        agent_memory_state.update({
            "name": "Katana ToClear",
            "user_settings": {"theme": "light"},
            "dialog_history": [{"role": "user", "content": "stuff to clear"}],
            "katana_config": {"version": "1.0"},
            "persistent_key": "should_remain" # Assuming clear_state is selective
        })
        # Pre-populate files as if state was saved
        with open(TEST_MEMORY_FILE, 'w') as f:
            json.dump(agent_memory_state, f)
        with open(TEST_HISTORY_FILE, 'w') as f:
            json.dump(agent_memory_state["dialog_history"], f)

        result = handle_clear_state()
        self.assertEqual(result["status"], "success")

        # Verify relevant parts of agent_memory_state are cleared
        self.assertEqual(agent_memory_state["user_settings"], {})
        self.assertEqual(agent_memory_state["dialog_history"], [])

        # Verify preserved keys
        self.assertEqual(agent_memory_state["name"], "Katana ToClear") # Name is preserved by clear_state
        self.assertEqual(agent_memory_state["katana_config"], {"version": "1.0"}) # katana_config is preserved
        # self.assertEqual(agent_memory_state["persistent_key"], "should_remain") # Current clear_state doesn't preserve unknown keys

        # Verify memory file content
        self.assertTrue(os.path.exists(TEST_MEMORY_FILE))
        with open(TEST_MEMORY_FILE, 'r') as f:
            cleared_memory = json.load(f)
        self.assertEqual(cleared_memory["user_settings"], {})
        self.assertEqual(cleared_memory["dialog_history"], [])
        self.assertEqual(cleared_memory["name"], "Katana ToClear")
        self.assertEqual(cleared_memory["katana_config"], {"version": "1.0"})
        # self.assertNotIn("persistent_key", cleared_memory) # Or check if it should be preserved

        # Verify history file is cleared
        self.assertTrue(os.path.exists(TEST_HISTORY_FILE))
        with open(TEST_HISTORY_FILE, 'r') as f:
            cleared_history = json.load(f)
        self.assertEqual(cleared_history, [])

    # Tests for user-friendly error message propagation
    @mock.patch('katana_agent.save_json_file')
    def test_handle_save_state_error_messages(self, mock_save_json):
        # Test general save failure
        mock_save_json.return_value = False # Simulate MEMORY_FILE save failure
        result = handle_save_state()
        self.assertEqual(result["status"], "error")
        self.assertEqual(result["message"], "Sorry, I couldn't save your settings and history. Please try again. If the problem continues, please let support know.")

        # Test history save failure (partial success)
        # save_memory() -> save_json_file (first call, for memory) -> True
        # save_history() -> save_json_file (second call, for history) -> False
        mock_save_json.side_effect = [True, False]
        result = handle_save_state()
        self.assertEqual(result["status"], "partial_success")
        self.assertEqual(result["message"], "Your settings were saved, but there was an issue saving the conversation history details. Please try again or contact support if this persists.")

        # Test unexpected exception
        mock_save_json.side_effect = Exception("Unexpected disk full!")
        result = handle_save_state()
        self.assertEqual(result["status"], "error")
        self.assertEqual(result["message"], "An unexpected problem occurred while trying to save your state. Please try again.")


    @mock.patch('katana_agent.load_json_file')
    @mock.patch('katana_agent.save_json_file') # For save_history and the emergency save_memory in load_state
    def test_handle_load_state_error_messages(self, mock_save_json, mock_load_json):
        # Test history sync failure (partial success)
        mock_load_json.return_value = {"name": "TestLoad", "dialog_history": [{"role":"user", "content":"hi"}]} # Successful memory load
        mock_save_json.return_value = False # Simulate history sync failure
        result = handle_load_state()
        self.assertEqual(result["status"], "partial_success")
        self.assertEqual(result["message"], "Your settings were loaded, but there was an issue synchronizing the conversation history. Some past messages might not be up to date.")

        # Test unexpected exception during load
        mock_load_json.side_effect = Exception("Cannot read from disk!")
        # save_memory in except block of handle_load_state will call save_json_file
        mock_save_json.side_effect = [True] # Allow emergency save to succeed
        result = handle_load_state()
        self.assertEqual(result["status"], "error")
        self.assertEqual(result["message"], "An unexpected problem occurred while trying to load your state. Some settings or history might be missing. Please try again or initialize a new state if needed.")


    @mock.patch('katana_agent.save_json_file')
    def test_handle_clear_state_error_messages(self, mock_save_json):
        # Test failure to save cleared state
        # First call to save_json_file is for memory (agent_memory_state)
        # Second call is for history file
        mock_save_json.side_effect = [False, True] # Fail memory save, succeed history save (though history would be from unclear memory)
        result = handle_clear_state()
        self.assertEqual(result["status"], "error")
        self.assertEqual(result["message"], "Sorry, I couldn't save the cleared state. Some settings or history might not be fully cleared. Please try again.")

        # Test failure to clear history file (partial success)
        mock_save_json.side_effect = [True, False] # Succeed memory save, fail history save
        result = handle_clear_state()
        self.assertEqual(result["status"], "partial_success")
        self.assertEqual(result["message"], "Your settings were cleared, but there was an issue clearing the conversation history details. Some past messages might still appear temporarily.")

        # Test unexpected exception
        mock_save_json.side_effect = Exception("Something broke!")
        result = handle_clear_state()
        self.assertEqual(result["status"], "error")
        self.assertEqual(result["message"], "An unexpected problem occurred while trying to clear your state. Please try again.")


    def test_handle_save_state_when_dialog_history_is_missing_in_memory(self):
        global agent_memory_state
        agent_memory_state.clear() # Start with a completely empty memory state
        agent_memory_state.update({
            "name": "Test No History Key",
            "user_settings": {"setting1": "value1"}
            # "dialog_history" key is deliberately missing
        })

        result = handle_save_state()
        self.assertEqual(result["status"], "success")

        # agent_memory_state should now have 'dialog_history' initialized by handle_save_state
        self.assertIn("dialog_history", agent_memory_state)
        self.assertEqual(agent_memory_state["dialog_history"], [])

        # Verify memory file content
        self.assertTrue(os.path.exists(TEST_MEMORY_FILE))
        with open(TEST_MEMORY_FILE, 'r') as f:
            saved_memory = json.load(f)

        self.assertEqual(saved_memory["user_settings"], {"setting1": "value1"})
        self.assertIn("dialog_history", saved_memory)
        self.assertEqual(saved_memory["dialog_history"], []) # Should be saved as empty list
        self.assertEqual(saved_memory["name"], "Test No History Key")

        # Verify history file content (should be an empty list)
        self.assertTrue(os.path.exists(TEST_HISTORY_FILE))
        with open(TEST_HISTORY_FILE, 'r') as f:
            saved_history = json.load(f)
        self.assertEqual(saved_history, [])


if __name__ == '__main__':
    # This allows running the tests directly from this file
    # It's important that katana_agent.py can be imported.
    # If katana_agent.py has an "if __name__ == '__main__':" block that does things,
    # those things will run when it's imported here for the first time.
    # This is generally fine if it's just initialization.

    # Adjust Python path to include the parent directory of katana_agent
    # This assumes test_memory_commands.py is in the same dir as katana_agent.py
    # If katana_agent.py is in 'alg911.catana-ai' and tests are run from repo root,
    # the import 'from katana_agent import ...' would need 'from alg911.catana-ai.katana_agent import ...'
    # or proper PYTHONPATH setup.
    # For the current structure where this file is created inside alg911.catana-ai:

    # suite = unittest.TestSuite()
    # suite.addTest(TestMemoryCommands('test_handle_load_state_from_empty_or_minimal_memory_file'))
    # runner = unittest.TextTestRunner()
    # runner.run(suite)

    unittest.main(argv=['first-arg-is-ignored'], exit=False)


class TestHandleUserChatMessage(unittest.TestCase):
    def setUp(self):
        self.mock_memory_file = mock.patch('katana_agent.MEMORY_FILE', TEST_MEMORY_FILE)
        self.mock_history_file = mock.patch('katana_agent.HISTORY_FILE', TEST_HISTORY_FILE)
        self.mock_memory_file.start()
        self.mock_history_file.start()

        self.patcher_log_event = mock.patch('katana_agent.log_event')
        self.mocked_log_event = self.patcher_log_event.start()

        # Mock save_state to inspect calls without actual file I/O during these specific tests,
        # and to prevent it from interfering with assertions on agent_memory_state before explicit save checks.
        self.patcher_handle_save_state = mock.patch('katana_agent.handle_save_state', return_value={"status": "success", "message": "Mocked save."})
        self.mocked_handle_save_state = self.patcher_handle_save_state.start()

        global agent_memory_state
        agent_memory_state.clear()
        agent_memory_state.update({
            "name": "Katana Chat Test",
            "user_settings": {},
            "dialog_history": []
        })
        if os.path.exists(TEST_MEMORY_FILE): os.remove(TEST_MEMORY_FILE)
        if os.path.exists(TEST_HISTORY_FILE): os.remove(TEST_HISTORY_FILE)

    def tearDown(self):
        self.mock_memory_file.stop()
        self.mock_history_file.stop()
        self.patcher_log_event.stop()
        self.patcher_handle_save_state.stop()

        global agent_memory_state
        agent_memory_state.clear()
        if os.path.exists(TEST_MEMORY_FILE): os.remove(TEST_MEMORY_FILE)
        if os.path.exists(TEST_HISTORY_FILE): os.remove(TEST_HISTORY_FILE)

    def test_chat_message_appends_history_and_calls_save(self):
        global agent_memory_state
        user_id = "test_user_123"
        message1 = "Hello Katana"

        response1 = handle_user_chat_message(user_id, message1)

        self.assertEqual(len(agent_memory_state["dialog_history"]), 2) # user msg + bot response
        self.assertEqual(agent_memory_state["dialog_history"][0]["role"], "user")
        self.assertEqual(agent_memory_state["dialog_history"][0]["content"], message1)
        self.assertEqual(agent_memory_state["dialog_history"][0]["id"], user_id)
        self.assertEqual(agent_memory_state["dialog_history"][1]["role"], "assistant")
        self.assertTrue(isinstance(response1, str))
        self.mocked_handle_save_state.assert_called_once()

        message2 = "How are you?"
        self.mocked_handle_save_state.reset_mock() # Reset mock for the next call
        response2 = handle_user_chat_message(user_id, message2)

        self.assertEqual(len(agent_memory_state["dialog_history"]), 4)
        self.assertEqual(agent_memory_state["dialog_history"][2]["content"], message2)
        self.mocked_handle_save_state.assert_called_once()

    def test_chat_message_contextual_responses(self):
        global agent_memory_state
        user_id = "context_user"

        # Test greeting
        response_hello = handle_user_chat_message(user_id, "Hello")
        self.assertEqual(response_hello, "Hello there! How can I help you today?")

        # Test repeated greeting
        response_hello_again = handle_user_chat_message(user_id, "Hi again")
        self.assertEqual(response_hello_again, "Hello again! What can I do for you?")

        # Test remember last message
        # History now: user:Hello, assist:Hello there..., user:Hi again, assist:Hello again...
        _ = handle_user_chat_message(user_id, "My previous message was about greetings.") # User message 1
        response_recall = handle_user_chat_message(user_id, "What was my last message?") # User message 2
        self.assertIn("My previous message was about greetings.", response_recall)

        # Test remember name
        response_remember_name = handle_user_chat_message(user_id, "Remember my name is Jules.")
        self.assertEqual(response_remember_name, "Got it, I'll try to remember your name is Jules!")
        self.assertEqual(agent_memory_state["user_settings"].get("user_name"), "Jules")

        # Test recall name
        response_what_is_name = handle_user_chat_message(user_id, "What is my name?")
        self.assertEqual(response_what_is_name, "If I remember correctly, your name is Jules.")

        # Test thank you with name
        response_thank_you = handle_user_chat_message(user_id, "Thank you very much.")
        self.assertEqual(response_thank_you, "You're welcome, Jules!")

    def test_chat_message_autosave_failure_logged(self):
        # Test that if handle_save_state fails, it's logged (mocked_log_event will capture this)
        self.patcher_handle_save_state.stop() # Stop the successful mock
        self.mocked_handle_save_state = None # Invalidate old mock object

        # Make handle_save_state simulate a failure
        failing_save_patcher = mock.patch('katana_agent.handle_save_state', return_value={"status": "error", "message": "Simulated save error."})
        mocked_failing_save = failing_save_patcher.start()

        handle_user_chat_message("autosave_fail_user", "Test message")

        self.mocked_log_event.assert_any_call(
            "Failed to automatically save state after chat message: Simulated save error.",
            "error"
        )
        failing_save_patcher.stop()
        # Restore the original successful mock for other tests if any in this class (though none currently follow)
        self.mocked_handle_save_state = self.patcher_handle_save_state.start()
