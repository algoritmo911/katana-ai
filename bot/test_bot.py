import unittest
from unittest.mock import MagicMock, patch, call
import json
from pathlib import Path
import shutil
import openai # For APIConnectionError

from bot import katana_bot # Assuming katana_bot.py is in the 'bot' directory and runnable
# from bot.katana_state import ChatHistory # Not strictly needed for mocking katana_state object

# Try to import nlp_processor, if it exists (for future integration)
try:
    from bot import nlp_processor
except ImportError:
    nlp_processor = None


class TestBotWithKatanaState(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        # Set a dummy token BEFORE katana_bot is imported by test discovery/methods
        # This prevents the ValueError during module import if tests are run in a way
        # that causes katana_bot to be loaded before patches can be applied.
        import os
        os.environ['KATANA_TELEGRAM_TOKEN'] = '123456:ABCDEF_test_token'


    @classmethod
    def tearDownClass(cls):
        import os
        del os.environ['KATANA_TELEGRAM_TOKEN']

    def setUp(self):
        # Create a dummy commands directory for testing (for file saving part)
        self.test_commands_dir = Path("test_commands_temp_dir_katana")
        self.test_commands_dir.mkdir(parents=True, exist_ok=True)

        # Store original and set to test
        self.original_command_file_dir = katana_bot.COMMAND_FILE_DIR
        katana_bot.COMMAND_FILE_DIR = self.test_commands_dir

        # Mock the telebot.TeleBot instance used by katana_bot
        self.mock_telebot_instance = MagicMock()
        self.telebot_patcher = patch('bot.katana_bot.bot', self.mock_telebot_instance)
        self.mock_telebot_instance_patched = self.telebot_patcher.start()

        # Mock datetime to control timestamps in filenames
        self.mock_datetime_patcher = patch('bot.katana_bot.datetime')
        self.mock_datetime = self.mock_datetime_patcher.start()
        self.mock_datetime.utcnow.return_value.strftime.return_value = "YYYYMMDD_HHMMSS_ffffff"

        # --- KatanaState Mocking ---
        # Mock the KatanaState instance directly within the katana_bot module
        self.mock_katana_state_global_instance = MagicMock()
        self.katana_state_patcher = patch('bot.katana_bot.katana_state', self.mock_katana_state_global_instance)
        self.mock_katana_state_global_instance_patched = self.katana_state_patcher.start()
        # --- End KatanaState Mocking ---

    def tearDown(self):
        self.telebot_patcher.stop()
        self.mock_datetime_patcher.stop()
        self.katana_state_patcher.stop()

        if self.test_commands_dir.exists():
            shutil.rmtree(self.test_commands_dir)
        katana_bot.COMMAND_FILE_DIR = self.original_command_file_dir

    def _create_mock_message(self, text_payload, chat_id=12345):
        mock_message = MagicMock()
        # telebot message.chat.id is an int. katana_bot internally converts it to str for state keys.
        mock_message.chat.id = int(chat_id)
        if isinstance(text_payload, dict):
            mock_message.text = json.dumps(text_payload)
        else:
            mock_message.text = text_payload
        return mock_message

    # --- Test Basic Commands with KatanaState ---

    def test_start_command(self):
        """ Test /start command - should not interact with KatanaState history directly, but bot should reply."""
        chat_id = 789
        mock_message = self._create_mock_message("/start", chat_id=chat_id)
        # Note: handle_start is a separate handler in telebot, not part of the main handle_message
        katana_bot.handle_start_impl(mock_message) # Call the implementation
        self.mock_telebot_instance_patched.reply_to.assert_called_with(mock_message, "Привет! Я — Katana. Отправь JSON-команду, чтобы начать.")
        # Ensure no history calls for /start itself
        self.mock_katana_state_global_instance_patched.add_chat_message.assert_not_called()

    # --- Test Message Handling with KatanaState ---

    def test_invalid_json_format_records_history(self):
        chat_id = 123
        mock_message = self._create_mock_message("not a valid json", chat_id=chat_id)
        chat_id_str = str(chat_id)

        katana_bot.handle_message_impl(mock_message) # Call the implementation

        expected_reply = "❌ Error: Invalid JSON format. Please send commands in correct JSON."
        self.mock_telebot_instance_patched.reply_to.assert_called_with(mock_message, expected_reply)

        self.mock_katana_state_global_instance_patched.add_chat_message.assert_any_call(chat_id_str, "user", mock_message.text)
        self.mock_katana_state_global_instance_patched.add_chat_message.assert_any_call(chat_id_str, "katana", expected_reply)

    def test_missing_field_records_history(self):
        chat_id = 456
        command = {"module": "test_module", "args": {}, "id": "test_id"} # type is missing
        mock_message = self._create_mock_message(command, chat_id=chat_id)
        chat_id_str = str(chat_id)

        katana_bot.handle_message_impl(mock_message) # Call the implementation

        expected_reply = "❌ Error: Missing required field 'type'."
        self.mock_telebot_instance_patched.reply_to.assert_called_with(mock_message, expected_reply)

        self.mock_katana_state_global_instance_patched.add_chat_message.assert_any_call(chat_id_str, "user", mock_message.text)
        self.mock_katana_state_global_instance_patched.add_chat_message.assert_any_call(chat_id_str, "katana", expected_reply)

    def test_general_command_placeholder_response_and_history(self):
        chat_id = 111
        command = {"type": "general_command", "module": "test_general", "args": {"data": "example"}, "id": "gen001"}
        mock_message = self._create_mock_message(command, chat_id=chat_id)
        chat_id_str = str(chat_id)

        mock_history_obj = MagicMock()
        mock_history_obj.messages = [{"sender": "user", "text": "previous message", "timestamp": "ts"}]
        self.mock_katana_state_global_instance_patched.get_chat_history.return_value = mock_history_obj

        katana_bot.handle_message_impl(mock_message) # Call the implementation

        self.mock_katana_state_global_instance_patched.add_chat_message.assert_any_call(chat_id_str, "user", mock_message.text)
        self.mock_katana_state_global_instance_patched.get_chat_history.assert_called_with(chat_id_str)

        self.mock_telebot_instance_patched.reply_to.assert_called_once()
        args, _ = self.mock_telebot_instance_patched.reply_to.call_args
        self.assertEqual(args[0], mock_message)
        self.assertIn("Katana Placeholder Response", args[1])
        self.assertIn(f"command '{command['type']}'", args[1])
        # Based on mock_history_obj.messages having 1 message, get_katana_response gets this list.
        # num_past_messages = len(current_history_messages) -> 1
        # phrase: "This is our first command message exchange." because num_past_messages <=1
        self.assertIn("This is our first command message exchange.", args[1])

        self.mock_katana_state_global_instance_patched.add_chat_message.assert_any_call(chat_id_str, "katana", args[1])

        # File saving is no longer expected for commands handled by get_katana_response
        # as the function now returns after Katana's reply.

    def test_log_event_command_with_katana_state(self):
        chat_id = 222
        event_details_text = "System rebooted successfully"
        command = {"type": "log_event", "module": "system", "args": {"details": event_details_text}, "id": "log002"}
        mock_message = self._create_mock_message(command, chat_id=chat_id)
        chat_id_str = str(chat_id)

        katana_bot.handle_message_impl(mock_message) # Call the implementation

        self.mock_katana_state_global_instance_patched.add_chat_message.assert_any_call(chat_id_str, "user", mock_message.text)
        self.mock_katana_state_global_instance_patched.add_chat_message.assert_any_call(chat_id_str, "system_event", f"Event logged: {event_details_text}")

        expected_reply = f"✅ Event '{event_details_text}' logged to my memory for chat {chat_id_str}."
        self.mock_telebot_instance_patched.reply_to.assert_called_with(mock_message, expected_reply)
        self.mock_katana_state_global_instance_patched.add_chat_message.assert_any_call(chat_id_str, "katana", expected_reply)

    def test_mind_clearing_command_with_katana_state(self):
        chat_id = 333
        command = {"type": "mind_clearing", "module": "maintenance", "args": {}, "id": "clear003"}
        mock_message = self._create_mock_message(command, chat_id=chat_id)
        chat_id_str = str(chat_id)

        katana_bot.handle_message_impl(mock_message) # Call the implementation

        self.mock_katana_state_global_instance_patched.add_chat_message.assert_any_call(chat_id_str, "user", mock_message.text)
        self.mock_katana_state_global_instance_patched.clear_chat_history.assert_called_once_with(chat_id_str)

        expected_reply = f"🧠✨ Katana's mind for chat {chat_id_str} has been cleared. We start anew."
        self.mock_telebot_instance_patched.reply_to.assert_called_with(mock_message, expected_reply)
        self.mock_katana_state_global_instance_patched.add_chat_message.assert_any_call(chat_id_str, "katana", expected_reply)

    # --- Test Context Preservation (Interaction with KatanaState) ---
    def test_context_preservation_via_get_katana_response(self):
        chat_id = 555
        chat_id_str = str(chat_id)

        # --- First message ---
        command1 = {"type": "query", "module": "knowledge", "args": {"q": "first question"}, "id": "q1"}
        mock_message1 = self._create_mock_message(command1, chat_id=chat_id)

        # Mock history for first call (empty before this message)
        history_for_call1 = MagicMock()
        history_for_call1.messages = []
        self.mock_katana_state_global_instance_patched.get_chat_history.return_value = history_for_call1

        katana_bot.handle_message_impl(mock_message1) # Call the implementation

        args1, _ = self.mock_telebot_instance_patched.reply_to.call_args
        self.assertIn("This is our first command message exchange.", args1[1])
        katana_reply1_text = args1[1] # Save Katana's first reply

        # --- Second message ---
        self.mock_telebot_instance_patched.reply_to.reset_mock() # Reset for the next call check

        command2 = {"type": "follow_up", "module": "knowledge", "args": {"q": "second question"}, "id": "q2"}
        mock_message2 = self._create_mock_message(command2, chat_id=chat_id)

        # Mock history for second call (should contain user's first message and Katana's first reply)
        history_for_call2 = MagicMock()
        history_for_call2.messages = [
            {"sender": "user", "text": mock_message1.text, "timestamp": "ts1"},
            {"sender": "katana", "text": katana_reply1_text, "timestamp": "ts2"}
        ]
        self.mock_katana_state_global_instance_patched.get_chat_history.return_value = history_for_call2

        katana_bot.handle_message_impl(mock_message2) # Call the implementation

        args2, _ = self.mock_telebot_instance_patched.reply_to.call_args
        # current_history_messages for get_katana_response will be history_for_call2.messages (length 2)
        # num_past_messages = 2. Phrase is "I see we have {2-1} prior messages" -> "1 prior messages"
        self.assertIn("I see we have 1 prior messages", args2[1])

        # Check calls to add_chat_message:
        # user_msg1, katana_reply1, user_msg2, katana_reply2
        self.assertEqual(self.mock_katana_state_global_instance_patched.add_chat_message.call_count, 4)
        calls = self.mock_katana_state_global_instance_patched.add_chat_message.call_args_list

        self.assertEqual(calls[0], call(chat_id_str, "user", mock_message1.text))
        self.assertEqual(calls[1], call(chat_id_str, "katana", katana_reply1_text))
        self.assertEqual(calls[2], call(chat_id_str, "user", mock_message2.text))
        self.assertEqual(calls[3], call(chat_id_str, "katana", args2[1])) # args2[1] is katana_reply2_text

    # --- Test Backup Mechanism ---
    def test_backup_triggered_after_interval(self):
        original_backup_interval = katana_bot.BACKUP_INTERVAL_MESSAGES
        katana_bot.BACKUP_INTERVAL_MESSAGES = 3 # Set a small interval for test
        chat_id = 666
        chat_id_str = str(chat_id)

        # Mock get_chat_history to return an empty history for simplicity for these calls
        mock_history_obj = MagicMock()
        mock_history_obj.messages = []
        self.mock_katana_state_global_instance_patched.get_chat_history.return_value = mock_history_obj

        # Send 2 messages (backup should not trigger)
        for i in range(2):
            cmd = {"type": "msg", "module": "test", "args": {"text": f"message {i+1}"}, "id": f"m{i+1}"}
            msg = self._create_mock_message(cmd, chat_id=chat_id)
            katana_bot.handle_message_impl(msg)

        self.mock_katana_state_global_instance_patched.backup_state.assert_not_called()
        self.assertEqual(katana_bot.message_counter_for_backup, 2)

        # Send 3rd message (backup should trigger)
        cmd3 = {"type": "msg", "module": "test", "args": {"text": "message 3"}, "id": "m3"}
        msg3 = self._create_mock_message(cmd3, chat_id=chat_id)

        # Mock datetime for consistent backup filename
        with patch('bot.katana_bot.datetime') as mock_datetime_backup:
            mock_datetime_backup.now.return_value.strftime.return_value = "BACKUP_TIMESTAMP"
            katana_bot.handle_message_impl(msg3)

        expected_backup_path = katana_bot.BACKUP_DIR / "katana_state_backup_BACKUP_TIMESTAMP.json"
        self.mock_katana_state_global_instance_patched.backup_state.assert_called_once_with(expected_backup_path)
        self.assertEqual(katana_bot.message_counter_for_backup, 0) # Counter should reset

        # Send 1 more message (counter should be 1)
        cmd4 = {"type": "msg", "module": "test", "args": {"text": "message 4"}, "id": "m4"}
        msg4 = self._create_mock_message(cmd4, chat_id=chat_id)
        katana_bot.handle_message_impl(msg4)
        self.assertEqual(katana_bot.message_counter_for_backup, 1)
        # backup_state should still only have been called once
        self.mock_katana_state_global_instance_patched.backup_state.assert_called_once_with(expected_backup_path)


        # Restore original interval
        katana_bot.BACKUP_INTERVAL_MESSAGES = original_backup_interval

    # --- Test NLP Provider Integration (Mocked) ---
    @patch('bot.katana_bot.openai.OpenAI') # Patch the OpenAI client constructor
    def test_openai_integration_success(self, MockOpenAIClient):
        chat_id = 777
        prompt_text = "Tell me a joke about cats."
        command = {"type": "chat", "module": "openai_chat", "args": {"prompt": prompt_text}, "id": "ai001"}
        mock_message = self._create_mock_message(command, chat_id=chat_id)

        # Configure the mock OpenAI client and its response
        mock_openai_instance = MockOpenAIClient.return_value
        mock_completion = MagicMock()
        mock_completion.choices = [MagicMock(message=MagicMock(content="Why was the cat sitting on the computer? To keep an eye on the mouse!"))]
        mock_openai_instance.chat.completions.create.return_value = mock_completion

        # Mock KatanaState's get_chat_history to provide some history
        mock_history_obj = MagicMock()
        previous_messages = [
            {"sender": "user", "text": "Hi Katana", "timestamp": "ts1"},
            {"sender": "katana", "text": "Hello there!", "timestamp": "ts2"}
        ]
        mock_history_obj.messages = list(previous_messages) # Use a copy
        # current_raw_history_messages in get_katana_response will include the current command
        # so, when get_chat_history is called, it's to get the state *before* current command was added to history by handle_message_impl
        # but handle_message_impl adds current message to state *then* calls get_chat_history.
        # For this test, we assume get_chat_history returns the history *including* the current user command.
        # The get_katana_response then slices it (history_before_current_prompt).
        current_command_as_history_item = {"sender": "user", "text": json.dumps(command), "timestamp": "ts_now"}
        mock_history_obj.messages.append(current_command_as_history_item)
        self.mock_katana_state_global_instance_patched.get_chat_history.return_value = mock_history_obj

        # Store original API key and set a dummy one for the test
        original_openai_key = katana_bot.OPENAI_API_KEY
        katana_bot.OPENAI_API_KEY = "test_dummy_key_openai"

        katana_bot.handle_message_impl(mock_message)

        # 1. Check if OpenAI client was called with correct parameters
        expected_api_messages = [
            {"role": "user", "content": "Hi Katana"},
            {"role": "assistant", "content": "Hello there!"},
            {"role": "user", "content": prompt_text} # Current prompt
        ]
        mock_openai_instance.chat.completions.create.assert_called_once()
        _, kwargs = mock_openai_instance.chat.completions.create.call_args
        self.assertEqual(kwargs['model'], "gpt-3.5-turbo")
        self.assertEqual(kwargs['messages'], expected_api_messages)

        # 2. Check bot's reply (should be the mocked OpenAI response)
        self.mock_telebot_instance_patched.reply_to.assert_called_with(mock_message, "Why was the cat sitting on the computer? To keep an eye on the mouse!")

        # 3. Check KatanaState history calls (user prompt + OpenAI response)
        # add_chat_message called for user's JSON command, and then for Katana's OpenAI reply.
        self.mock_katana_state_global_instance_patched.add_chat_message.assert_any_call(str(chat_id), "user", mock_message.text)
        self.mock_katana_state_global_instance_patched.add_chat_message.assert_any_call(str(chat_id), "katana", "Why was the cat sitting on the computer? To keep an eye on the mouse!")

        # Restore original key
        katana_bot.OPENAI_API_KEY = original_openai_key


    def test_openai_integration_no_api_key(self):
        chat_id = 778
        prompt_text = "This won't work."
        command = {"type": "chat", "module": "openai_chat", "args": {"prompt": prompt_text}, "id": "ai002"}
        mock_message = self._create_mock_message(command, chat_id=chat_id)

        original_openai_key = katana_bot.OPENAI_API_KEY
        katana_bot.OPENAI_API_KEY = None # Simulate no API key

        # Mock history for consistency, though not strictly needed for this error path
        mock_history_obj = MagicMock()
        mock_history_obj.messages = [{"sender": "user", "text": json.dumps(command), "timestamp": "ts_now"}]
        self.mock_katana_state_global_instance_patched.get_chat_history.return_value = mock_history_obj

        katana_bot.handle_message_impl(mock_message)

        self.mock_telebot_instance_patched.reply_to.assert_called_with(mock_message, "🤖 OpenAI API key not configured. Please ask an admin to set it up.")

        katana_bot.OPENAI_API_KEY = original_openai_key


    @patch('bot.katana_bot.openai.OpenAI')
    def test_openai_integration_api_error(self, MockOpenAIClient):
        chat_id = 779
        prompt_text = "Trigger an API error."
        command = {"type": "chat", "module": "openai_chat", "args": {"prompt": prompt_text}, "id": "ai003"}
        mock_message = self._create_mock_message(command, chat_id=chat_id)

        mock_openai_instance = MockOpenAIClient.return_value
        mock_openai_instance.chat.completions.create.side_effect = openai.APIConnectionError(request=MagicMock())

        original_openai_key = katana_bot.OPENAI_API_KEY
        katana_bot.OPENAI_API_KEY = "test_dummy_key_openai_error"

        mock_history_obj = MagicMock()
        mock_history_obj.messages = [{"sender": "user", "text": json.dumps(command), "timestamp": "ts_now"}]
        self.mock_katana_state_global_instance_patched.get_chat_history.return_value = mock_history_obj

        katana_bot.handle_message_impl(mock_message)

        self.mock_telebot_instance_patched.reply_to.assert_called_with(mock_message, "🤖 Sorry, I couldn't connect to OpenAI. Please try again later.")

        katana_bot.OPENAI_API_KEY = original_openai_key


if __name__ == '__main__':
    unittest.main()
