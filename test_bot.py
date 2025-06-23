import unittest
from unittest.mock import MagicMock, patch, call
import json
from pathlib import Path
import shutil # For robust directory removal

# Assuming bot.py is in the same directory or accessible in PYTHONPATH
import bot
import telebot # Added import

class TestBot(unittest.TestCase):

    def setUp(self):
        # Create a dummy commands directory for testing
        self.test_commands_dir = Path("test_commands_temp_dir") # Using a more unique name
        self.test_commands_dir.mkdir(parents=True, exist_ok=True)

        # Store original and set to test
        self.original_command_file_dir = bot.COMMAND_FILE_DIR
        bot.COMMAND_FILE_DIR = self.test_commands_dir

        # Mock the bot object and its methods
        self.mock_bot_instance = MagicMock()
        # Patch the bot instance within the 'bot' module
        self.bot_patcher = patch('bot.bot', self.mock_bot_instance)
        self.mock_bot_module_instance = self.bot_patcher.start()

        # Mock datetime to control timestamps in filenames
        self.mock_datetime_patcher = patch('bot.datetime')
        self.mock_datetime = self.mock_datetime_patcher.start()
        self.mock_datetime.utcnow.return_value.strftime.return_value = "YYYYMMDD_HHMMSS_ffffff"

        # Patch log_local_bot_event
        self.mock_log_event_patcher = patch('bot.log_local_bot_event')
        self.mock_log_local_bot_event = self.mock_log_event_patcher.start()

        # Patch for OPENAI_API_KEY
        self.openai_api_key_patcher = patch('bot.OPENAI_API_KEY', 'test_openai_key')
        self.mock_openai_api_key = self.openai_api_key_patcher.start()

        # Patch for openai.Audio.transcribe
        self.openai_transcribe_patcher = patch('openai.Audio.transcribe')
        self.mock_openai_transcribe = self.openai_transcribe_patcher.start()

        # Patch for bot.get_text_from_voice - will be started selectively in tests for handle_voice_message
        self.get_text_from_voice_patcher = patch('bot.get_text_from_voice')
        self.mock_get_text_from_voice = None # Will be set when patcher is started

        # Patch for bot.handle_text_message - To be applied selectively if a test needs it as a mock
        # self.handle_text_message_patcher = patch('bot.handle_text_message')
        # self.mock_handle_text_message = None # Will be set if patcher is started

        # Patch for os.remove
        self.os_remove_patcher = patch('os.remove')
        self.mock_os_remove = self.os_remove_patcher.start()

        # Patch for Path.exists
        self.path_exists_patcher = patch('pathlib.Path.exists')
        self.mock_path_exists = self.path_exists_patcher.start()
        self.mock_path_exists.return_value = True # Assume file exists for cleanup by default

        # Temporary directory for voice files
        self.test_voice_file_dir = Path("test_voice_temp_dir")
        self.test_voice_file_dir.mkdir(parents=True, exist_ok=True)
        self.voice_file_dir_patcher = patch('bot.VOICE_FILE_DIR', self.test_voice_file_dir)
        self.voice_file_dir_patcher.start()


    def tearDown(self):
        # Stop patchers
        self.bot_patcher.stop()
        self.mock_datetime_patcher.stop()
        self.mock_log_event_patcher.stop()
        self.openai_api_key_patcher.stop()
        self.openai_transcribe_patcher.stop()
        # Stop get_text_from_voice_patcher only if it was started
        if self.mock_get_text_from_voice is not None: # Check if it was started
            try:
                self.get_text_from_voice_patcher.stop()
            except RuntimeError: # Already stopped or not started
                pass
        # Stop handle_text_message_patcher only if it was started (currently it's not started in setUp)
        # if hasattr(self, 'handle_text_message_patcher') and self.handle_text_message_patcher.is_started:
        #     self.handle_text_message_patcher.stop()
        self.os_remove_patcher.stop()
        self.path_exists_patcher.stop()
        self.voice_file_dir_patcher.stop()


        # Clean up: remove dummy directory and its contents
        if self.test_commands_dir.exists():
            try:
                shutil.rmtree(self.test_commands_dir) # shutil.rmtree is more robust for non-empty dirs
            except FileNotFoundError:
                pass # Already deleted or never created
        if self.test_voice_file_dir.exists():
            try:
                shutil.rmtree(self.test_voice_file_dir)
            except FileNotFoundError:
                pass # Already deleted or never created

        # Restore original
        # There was a duplicate rmtree here, removing it.
        # bot.COMMAND_FILE_DIR should be restored.
        bot.COMMAND_FILE_DIR = self.original_command_file_dir


    def _create_mock_message(self, text_payload):
        mock_message = MagicMock()
        mock_message.chat.id = 12345
        mock_message.text = json.dumps(text_payload)
        return mock_message

    # --- Test Command Validation ---
    def test_valid_command_gets_saved(self):
        command = {"type": "test_type", "module": "test_module", "args": {}, "id": "test_id"}
        mock_message = self._create_mock_message(command)

        bot.handle_text_message(mock_message) # Changed to handle_text_message

        # Check file creation
        expected_module_dir = self.test_commands_dir / "telegram_mod_test_module"
        self.assertTrue(expected_module_dir.exists())

        expected_filename = f"YYYYMMDD_HHMMSS_ffffff_{mock_message.chat.id}.json"
        expected_file_path = expected_module_dir / expected_filename
        self.assertTrue(expected_file_path.exists())

        with open(expected_file_path, "r") as f:
            saved_data = json.load(f)
        self.assertEqual(saved_data, command)

        # Check reply
        self.mock_bot_module_instance.reply_to.assert_called_once()
        args, kwargs = self.mock_bot_module_instance.reply_to.call_args
        self.assertEqual(args[0], mock_message)
        self.assertTrue(args[1].startswith("✅ Command received and saved as"))
        self.assertIn(str(expected_file_path), args[1])

        # Check logging for successfully validated command
        found_log = False
        for call_arg in self.mock_log_local_bot_event.call_args_list:
            args, _ = call_arg
            if f"Successfully validated command from {mock_message.chat.id}: {json.dumps(command)}" in args[0]:
                found_log = True
                break
        self.assertTrue(found_log, "Expected log for successful validation with full command data was not found.")


    def test_invalid_json_format(self):
        mock_message = MagicMock() # Simpler mock for this case
        mock_message.chat.id = 123
        mock_message.text = "not a valid json"
        # This test was for the old handle_message which only handled JSON.
        # handle_text_message now tries NLP first.
        # To test this specific scenario (invalid JSON), we'd need to ensure it's not an NLP command.
        # For now, let's assume "not a valid json" is not an NLP command.
        with patch('bot.interpret', return_value=None): # Ensure NLP does not interpret this
            bot.handle_text_message(mock_message)
        self.mock_bot_module_instance.reply_to.assert_called_with(mock_message, "🤖 Не понял команду. Попробуй переформулировать или отправь JSON-команду.")


    def test_missing_type_field(self):
        command = {"module": "test_module", "args": {}, "id": "test_id"} # type is missing
        mock_message = self._create_mock_message(command)
        with patch('bot.interpret', return_value=None):
            bot.handle_text_message(mock_message)
        self.mock_bot_module_instance.reply_to.assert_called_with(mock_message, "Error: Missing required field 'type'.")

    def test_empty_string_type(self):
        command = {"type": "", "module": "test_module", "args": {}, "id": "1"}
        mock_message = self._create_mock_message(command)
        with patch('bot.interpret', return_value=None):
            bot.handle_text_message(mock_message)
        self.mock_bot_module_instance.reply_to.assert_called_with(mock_message, "Error: Field 'type' must be a non-empty string. Got value ''.")

    def test_whitespace_string_type(self):
        command = {"type": "   ", "module": "test_module", "args": {}, "id": "1"}
        mock_message = self._create_mock_message(command)
        with patch('bot.interpret', return_value=None):
            bot.handle_text_message(mock_message)
        self.mock_bot_module_instance.reply_to.assert_called_with(mock_message, "Error: Field 'type' must be a non-empty string. Got value '   '.")

    def test_missing_module_field(self):
        command = {"type": "test_type", "args": {}, "id": "test_id"} # module is missing
        mock_message = self._create_mock_message(command)
        with patch('bot.interpret', return_value=None):
            bot.handle_text_message(mock_message)
        self.mock_bot_module_instance.reply_to.assert_called_with(mock_message, "Error: Missing required field 'module'.")

    def test_empty_string_module(self):
        command = {"type": "test", "module": "", "args": {}, "id": "1"}
        mock_message = self._create_mock_message(command)
        with patch('bot.interpret', return_value=None):
            bot.handle_text_message(mock_message)
        self.mock_bot_module_instance.reply_to.assert_called_with(mock_message, "Error: Field 'module' must be a non-empty string. Got value ''.")

    def test_whitespace_string_module(self):
        command = {"type": "test", "module": "   ", "args": {}, "id": "1"}
        mock_message = self._create_mock_message(command)
        with patch('bot.interpret', return_value=None):
            bot.handle_text_message(mock_message)
        self.mock_bot_module_instance.reply_to.assert_called_with(mock_message, "Error: Field 'module' must be a non-empty string. Got value '   '.")

    def test_invalid_args_type(self):
        command = {"type": "test_type", "module": "test_module", "args": "not_a_dict", "id": "test_id"}
        mock_message = self._create_mock_message(command)
        with patch('bot.interpret', return_value=None):
            bot.handle_text_message(mock_message)
        self.mock_bot_module_instance.reply_to.assert_called_with(mock_message, "Error: Field 'args' must be type dict. Got value 'not_a_dict' of type str.")

    def test_invalid_id_type(self):
        command = {"type": "test_type", "module": "test_module", "args": {}, "id": [1,2,3]} # id is a list
        mock_message = self._create_mock_message(command)
        with patch('bot.interpret', return_value=None):
            bot.handle_text_message(mock_message)
        self.mock_bot_module_instance.reply_to.assert_called_with(mock_message, "Error: Field 'id' must be type str or int. Got value '[1, 2, 3]' of type list.")

    # --- ID field type tests ---
    def test_valid_command_with_int_id(self):
        command = {"type": "test_type_int_id", "module": "test_module_int_id", "args": {}, "id": 123}
        mock_message = self._create_mock_message(command)
        with patch('bot.interpret', return_value=None):
            bot.handle_text_message(mock_message)

        expected_module_dir = self.test_commands_dir / "telegram_mod_test_module_int_id"
        self.assertTrue(expected_module_dir.exists())
        expected_filename = f"YYYYMMDD_HHMMSS_ffffff_{mock_message.chat.id}.json"
        expected_file_path = expected_module_dir / expected_filename
        self.assertTrue(expected_file_path.exists())
        with open(expected_file_path, "r") as f:
            saved_data = json.load(f)
        self.assertEqual(saved_data, command)
        self.mock_bot_module_instance.reply_to.assert_called_once()
        args, kwargs = self.mock_bot_module_instance.reply_to.call_args
        self.assertTrue(args[1].startswith("✅ Command received and saved as"))

        # Check logging for successfully validated command
        found_log = False
        for call_arg in self.mock_log_local_bot_event.call_args_list:
            args, _ = call_arg
            if f"Successfully validated command from {mock_message.chat.id}: {json.dumps(command)}" in args[0]:
                found_log = True
                break
        self.assertTrue(found_log, "Expected log for successful validation with full command data (int id) was not found.")

    # --- Args field tests ---
    def test_valid_command_with_empty_args(self):
        command = {"type": "test_empty_args", "module": "test_mod_empty_args", "args": {}, "id": "empty_args_id"}
        mock_message = self._create_mock_message(command)
        with patch('bot.interpret', return_value=None):
            bot.handle_text_message(mock_message)

        expected_module_dir = self.test_commands_dir / "telegram_mod_test_mod_empty_args"
        self.assertTrue(expected_module_dir.exists())
        expected_filename = f"YYYYMMDD_HHMMSS_ffffff_{mock_message.chat.id}.json"
        expected_file_path = expected_module_dir / expected_filename
        self.assertTrue(expected_file_path.exists())
        self.mock_bot_module_instance.reply_to.assert_called_once()

    def test_valid_command_with_simple_args(self):
        command = {"type": "test_simple_args", "module": "test_mod_simple_args", "args": {"key": "value"}, "id": "simple_args_id"}
        mock_message = self._create_mock_message(command)
        with patch('bot.interpret', return_value=None):
            bot.handle_text_message(mock_message)

        expected_module_dir = self.test_commands_dir / "telegram_mod_test_mod_simple_args"
        self.assertTrue(expected_module_dir.exists())
        expected_filename = f"YYYYMMDD_HHMMSS_ffffff_{mock_message.chat.id}.json"
        expected_file_path = expected_module_dir / expected_filename
        self.assertTrue(expected_file_path.exists())
        self.mock_bot_module_instance.reply_to.assert_called_once()


    # --- Test Command Routing ---
    @patch('bot.handle_log_event') # Keep this patch local as it's specific to this test
    def test_routing_log_event(self, mock_handle_log_event_func):
        command = {"type": "log_event", "module": "logging", "args": {"message": "hello"}, "id": "log001"}
        mock_message = self._create_mock_message(command)
        with patch('bot.interpret', return_value=None):
            bot.handle_text_message(mock_message)

        mock_handle_log_event_func.assert_called_once_with(command, mock_message.chat.id)
        self.mock_bot_module_instance.reply_to.assert_called_with(mock_message, "✅ 'log_event' processed (placeholder).")


    @patch('bot.handle_mind_clearing') # Keep this patch local
    def test_routing_mind_clearing(self, mock_handle_mind_clearing_func):
        command = {"type": "mind_clearing", "module": "wellness", "args": {"duration": "10m"}, "id": "mind002"}
        mock_message = self._create_mock_message(command)
        with patch('bot.interpret', return_value=None):
            bot.handle_text_message(mock_message)

        mock_handle_mind_clearing_func.assert_called_once_with(command, mock_message.chat.id)
        self.mock_bot_module_instance.reply_to.assert_called_with(mock_message, "✅ 'mind_clearing' processed (placeholder).")


    def test_unknown_command_type_saves_normally(self):
        command = {"type": "unknown_type", "module": "custom_module", "args": {}, "id": "custom003"}
        mock_message = self._create_mock_message(command)
        with patch('bot.interpret', return_value=None):
            bot.handle_text_message(mock_message)

        # Check file creation
        expected_module_dir = self.test_commands_dir / "telegram_mod_custom_module"
        self.assertTrue(expected_module_dir.exists())

        expected_filename = f"YYYYMMDD_HHMMSS_ffffff_{mock_message.chat.id}.json"
        expected_file_path = expected_module_dir / expected_filename
        self.assertTrue(expected_file_path.exists())

        with open(expected_file_path, "r") as f:
            saved_data = json.load(f)
        self.assertEqual(saved_data, command)

        # Check reply
        self.mock_bot_module_instance.reply_to.assert_called_once()
        args, kwargs = self.mock_bot_module_instance.reply_to.call_args
        self.assertEqual(args[0], mock_message)
        self.assertTrue(args[1].startswith("✅ Command received and saved as"))
        self.assertIn(str(expected_file_path), args[1])

    # --- Logging Verification Tests ---
    def test_validation_failure_logs_details(self):
        command = {"type": "test_type", "module": "", "args": {}, "id": "fail_log_id"} # Empty module
        original_command_text = json.dumps(command)
        mock_message = self._create_mock_message(command)
        with patch('bot.interpret', return_value=None):
            bot.handle_text_message(mock_message)

        self.mock_bot_module_instance.reply_to.assert_called_with(mock_message, "Error: Field 'module' must be a non-empty string. Got value ''.")

        found_log = False
        expected_log_part = "Validation failed for 12345: Error: Field 'module' must be a non-empty string. Got value ''."
        expected_command_part = f"(Command: {original_command_text})"

        for call_arg in self.mock_log_local_bot_event.call_args_list:
            args, _ = call_arg
            log_message = args[0] # The first positional argument to log_local_bot_event
            if expected_log_part in log_message and expected_command_part in log_message:
                found_log = True
                break
        self.assertTrue(found_log, f"Expected log with validation failure details was not found. Searched for: '{expected_log_part}' and '{expected_command_part}'")

    # --- Tests for get_text_from_voice ---
    @patch('builtins.open', new_callable=unittest.mock.mock_open, read_data=b"dummy voice data")
    def test_get_text_from_voice_success(self, mock_open_file):
        self.mock_openai_transcribe.return_value = {'text': 'Hello world'}
        result = bot.get_text_from_voice("dummy_path.ogg")
        self.assertEqual(result, "Hello world")
        mock_open_file.assert_called_once_with("dummy_path.ogg", "rb")
        self.mock_openai_transcribe.assert_called_once()
        self.mock_log_local_bot_event.assert_any_call("Sending voice file dummy_path.ogg to OpenAI Whisper API...")
        self.mock_log_local_bot_event.assert_any_call("Voice transcribed successfully: 'Hello world'")

    @patch('builtins.open', new_callable=unittest.mock.mock_open, read_data=b"dummy voice data")
    def test_get_text_from_voice_api_error(self, mock_open_file):
        # This test is for the function bot.get_text_from_voice, so openai.Audio.transcribe is mocked (done in setUp)
        mock_response = MagicMock() # Create a mock response object
        mock_response.status_code = 500
        self.mock_openai_transcribe.side_effect = bot.openai.APIError("API Error", request=MagicMock(), body=None)
        result = bot.get_text_from_voice("dummy_path.ogg")
        self.assertIsNone(result)
        self.mock_log_local_bot_event.assert_any_call("OpenAI API Error during voice transcription: API Error")

    @patch('builtins.open', new_callable=unittest.mock.mock_open, read_data=b"dummy voice data")
    def test_get_text_from_voice_no_text_returned(self, mock_open_file):
        # This test is for the function bot.get_text_from_voice, so openai.Audio.transcribe is mocked
        self.mock_openai_transcribe.return_value = {'text': None} # Simulate API returning no text
        result = bot.get_text_from_voice("dummy_path.ogg")
        self.assertIsNone(result)
        self.mock_log_local_bot_event.assert_any_call("Voice transcription returned no text (text is None).")

    @patch('builtins.open', new_callable=unittest.mock.mock_open, read_data=b"dummy voice data")
    def test_get_text_from_voice_api_returns_empty_string(self, mock_open_file):
        # Tests bot.get_text_from_voice, so openai.Audio.transcribe is mocked
        self.mock_openai_transcribe.return_value = {'text': ""} # Simulate API returning empty string
        result = bot.get_text_from_voice("dummy_path.ogg")
        self.assertEqual(result, "") # Should be stripped (no change)
        self.mock_log_local_bot_event.assert_any_call("Voice transcribed successfully: ''")

    @patch('builtins.open', new_callable=unittest.mock.mock_open, read_data=b"dummy voice data")
    def test_get_text_from_voice_api_returns_whitespace_string(self, mock_open_file):
        # This test is for the function bot.get_text_from_voice, so openai.Audio.transcribe is mocked
        self.mock_openai_transcribe.return_value = {'text': "  "} # Simulate API returning only whitespace
        result = bot.get_text_from_voice("dummy_path.ogg")
        self.assertEqual(result, "") # Should be stripped
        self.mock_log_local_bot_event.assert_any_call("Voice transcribed successfully: '  '")


    @patch('bot.OPENAI_API_KEY', None) # Temporarily unpatch the class-level patch
    def test_get_text_from_voice_no_api_key(self):
        result = bot.get_text_from_voice("dummy_path.ogg")
        self.assertIsNone(result)
        self.mock_log_local_bot_event.assert_any_call("OpenAI API key not configured. Cannot process voice.")
        self.mock_openai_transcribe.assert_not_called()

    @patch('builtins.open', side_effect=IOError("File not found"))
    def test_get_text_from_voice_file_open_error(self, mock_open_file):
        # Ensure OPENAI_API_KEY is set for this test, otherwise it exits early
        with patch('bot.OPENAI_API_KEY', 'fake_key_for_this_test'):
            result = bot.get_text_from_voice("dummy_path.ogg")
            self.assertIsNone(result)
            self.mock_log_local_bot_event.assert_any_call("Unexpected error during voice transcription: File not found")

    # --- Tests for handle_voice_message ---
    def _create_mock_voice_message(self):
        mock_message = MagicMock(spec=telebot.types.Message) # Use spec for better mocking
        mock_message.chat = MagicMock(spec=telebot.types.Chat)
        mock_message.chat.id = 67890
        mock_message.voice = MagicMock(spec=telebot.types.Voice)
        mock_message.voice.file_id = "test_voice_file_id"
        mock_message.voice.duration = 3 # seconds
        mock_message.message_id = 123
        mock_message.date = 1678886400 # Example timestamp
        mock_message.from_user = MagicMock(spec=telebot.types.User)
        mock_message.from_user.id = 98765
        return mock_message

    @patch('builtins.open', new_callable=unittest.mock.mock_open)
    def test_handle_voice_message_success(self, mock_open_file):
        # This test is for handle_voice_message, so bot.get_text_from_voice is mocked
        self.mock_get_text_from_voice = self.get_text_from_voice_patcher.start() # Start patcher
        mock_message = self._create_mock_voice_message()
        self.mock_bot_module_instance.get_file.return_value.file_path = "voice/file.oga"
        self.mock_bot_module_instance.download_file.return_value = b"dummy voice data"
        self.mock_get_text_from_voice.return_value = "show disk space"

        bot.handle_voice_message(mock_message)

        # Check file download and saving
        self.mock_bot_module_instance.get_file.assert_called_once_with("test_voice_file_id")
        self.mock_bot_module_instance.download_file.assert_called_once_with("voice/file.oga")
        expected_temp_path = self.test_voice_file_dir / f"{mock_message.voice.file_id}.ogg"
        mock_open_file.assert_called_once_with(expected_temp_path, 'wb')
        mock_open_file().write.assert_called_once_with(b"dummy voice data")

        # Check transcription call
        self.mock_get_text_from_voice.assert_called_once_with(str(expected_temp_path))

        # Check reply to user
        self.mock_bot_module_instance.reply_to.assert_any_call(mock_message, '🗣️ Распознано: "show disk space"')
        # The real handle_text_message is called, so we don't assert the mock of it here.
        # Instead, we'd assert the *effects* of handle_text_message if needed,
        # e.g., further bot replies or calls to run_katana_command.
        # For this specific test, "show disk space" is likely to result in "Не понял команду"
        # from the JSON parsing path after NLP miss.
        # Let's find that second reply.

        # Find the "Не понял команду" reply. This is tricky because the message object is different.
        # We can check the call list of reply_to.
        found_unrecognized_command_reply = False
        unrecognized_text = "🤖 Не понял команду. Попробуй переформулировать или отправь JSON-команду."
        for call_obj in self.mock_bot_module_instance.reply_to.call_args_list:
            # call_obj is a unittest.mock.call object
            # call_obj.args is the tuple of positional arguments
            # call_obj.kwargs is the dict of keyword arguments
            if len(call_obj.args) > 1 and call_obj.args[1] == unrecognized_text: # Check the text of the reply
                found_unrecognized_command_reply = True
                break
        self.assertTrue(found_unrecognized_command_reply, f"Expected to find reply: {unrecognized_text}")


        # Check file cleanup
        self.mock_path_exists.assert_called_with() # Will be called on expected_temp_path due to how Path.exists() works when patched on class
        self.mock_os_remove.assert_called_once_with(expected_temp_path)


    @patch('builtins.open', new_callable=unittest.mock.mock_open)
    def test_handle_voice_message_transcription_fails(self, mock_open_file):
        self.mock_get_text_from_voice = self.get_text_from_voice_patcher.start()
        mock_message = self._create_mock_voice_message()
        self.mock_bot_module_instance.get_file.return_value.file_path = "voice/file.oga"
        self.mock_bot_module_instance.download_file.return_value = b"dummy voice data"
        self.mock_get_text_from_voice.return_value = None # Simulate transcription failure

        bot.handle_voice_message(mock_message)

        expected_temp_path = self.test_voice_file_dir / f"{mock_message.voice.file_id}.ogg"
        self.mock_get_text_from_voice.assert_called_once_with(str(expected_temp_path))
        self.mock_bot_module_instance.reply_to.assert_called_with(mock_message, "Не понял, повтори, пожалуйста. 🎙️")
        # self.mock_handle_text_message.assert_not_called() # Real handle_text_message is called
        self.mock_os_remove.assert_called_once_with(expected_temp_path)
        self.get_text_from_voice_patcher.stop() # Stop patcher

    @patch('bot.OPENAI_API_KEY', None)
    def test_handle_voice_message_no_openai_key(self):
        # No need to mock get_text_from_voice as it should not be called if key is missing
        mock_message = self._create_mock_voice_message()
        bot.handle_voice_message(mock_message)
        self.mock_bot_module_instance.reply_to.assert_called_with(mock_message, "⚠️ Распознавание голоса не настроено на сервере.")
        self.mock_bot_module_instance.get_file.assert_not_called()
        if self.mock_get_text_from_voice:
            self.mock_get_text_from_voice.assert_not_called()
        # self.mock_handle_text_message.assert_not_called() # Real handle_text_message is not reached


    @patch('builtins.open', new_callable=unittest.mock.mock_open)
    def test_handle_voice_message_download_exception(self, mock_open_file):
        # No need to mock get_text_from_voice as it should not be called if download fails
        mock_message = self._create_mock_voice_message()
        self.mock_bot_module_instance.get_file.side_effect = Exception("Download error")

        bot.handle_voice_message(mock_message)

        self.mock_bot_module_instance.reply_to.assert_called_with(mock_message, "Произошла ошибка при обработке голосового сообщения. 😥")
        if self.mock_get_text_from_voice:
            self.mock_get_text_from_voice.assert_not_called()
        # self.mock_handle_text_message.assert_not_called() # Real handle_text_message is not reached
        # Ensure cleanup is not attempted if download fails before file is written,
        # as temp_voice_path would not be defined in the try-block's scope for open().
        self.mock_os_remove.assert_not_called()


    @patch('builtins.open', new_callable=unittest.mock.mock_open)
    @patch('os.remove', side_effect=OSError("Delete failed"))
    def test_handle_voice_message_cleanup_exception(self, mock_os_remove_custom, mock_open_file):
        self.mock_get_text_from_voice = self.get_text_from_voice_patcher.start()
        mock_message = self._create_mock_voice_message()
        self.mock_bot_module_instance.get_file.return_value.file_path = "voice/file.oga"
        self.mock_bot_module_instance.download_file.return_value = b"dummy voice data"
        self.mock_get_text_from_voice.return_value = "текст" # Russian: "text"

        # We need Path(..).exists() to return True for the os.remove to be called
        # The class-level mock_path_exists is already True.

        bot.handle_voice_message(mock_message)

        expected_temp_path = self.test_voice_file_dir / f"{mock_message.voice.file_id}.ogg"
        # Check that normal processing occurred (real handle_text_message is called)
        # We can check for the reply that handle_text_message would generate for "текст"
        # Assuming "текст" is not an NLP command and not valid JSON:
        unrecognized_text = "🤖 Не понял команду. Попробуй переформулировать или отправь JSON-команду."
        # Check that reply_to was called at least for the "Распознано" message and potentially for the "Не понял" message.
        # A more specific check for the "Не понял" might be needed if other replies are also made.
        self.assertTrue(self.mock_bot_module_instance.reply_to.called, "bot.reply_to should have been called.")
        # Check that remove was called
        mock_os_remove_custom.assert_called_once_with(expected_temp_path)
        # Check that the error during cleanup was logged
        self.mock_log_local_bot_event.assert_any_call(f"Error deleting temporary voice file {expected_temp_path}: Delete failed")
        self.get_text_from_voice_patcher.stop()

    # --- Additional tests for voice processing stability ---

    @patch('builtins.open', new_callable=unittest.mock.mock_open)
    @patch('bot.bot.reply_to') # Patch reply_to specifically for this test
    def test_handle_voice_message_transcription_returns_empty_string(self, mock_specific_reply_to, mock_open_file):
        self.mock_get_text_from_voice = self.get_text_from_voice_patcher.start()
        mock_original_voice_message = self._create_mock_voice_message() # Renamed for clarity
        self.mock_bot_module_instance.get_file.return_value.file_path = "voice/file.oga"
        self.mock_bot_module_instance.download_file.return_value = b"dummy voice data"
        self.mock_get_text_from_voice.return_value = "" # Simulate empty string transcription

        bot.handle_voice_message(mock_original_voice_message)

        expected_temp_path = self.test_voice_file_dir / f"{mock_original_voice_message.voice.file_id}.ogg"
        self.mock_get_text_from_voice.assert_called_once_with(str(expected_temp_path))

        # Check the first reply: "Распознано"
        # self.mock_bot_module_instance.reply_to was the global mock, now use mock_specific_reply_to
        mock_specific_reply_to.assert_any_call(mock_original_voice_message, '🗣️ Распознано: ""')

        # Check the second reply from handle_text_message (after JSONDecodeError for empty string)
        unrecognized_text = "🤖 Не понял команду. Попробуй переформулировать или отправь JSON-команду."

        found_unrecognized_command_reply = False
        # The message object for the second reply is a new mock_text_message, not mock_original_voice_message
        for call_obj in mock_specific_reply_to.call_args_list:
            if len(call_obj.args) > 1 and call_obj.args[1] == unrecognized_text:
                # args[0] would be the mock_text_message object. We can check its text attribute.
                self.assertEqual(call_obj.args[0].text, "")
                found_unrecognized_command_reply = True
                break
        self.assertTrue(found_unrecognized_command_reply, f"Expected to find reply: '{unrecognized_text}' after processing empty string.")

        self.assertEqual(mock_specific_reply_to.call_count, 2) # Expect two replies

        self.mock_os_remove.assert_called_once_with(expected_temp_path)
        self.get_text_from_voice_patcher.stop()

    def test_handle_voice_message_get_file_exception(self):
        # No need to mock get_text_from_voice
        mock_message = self._create_mock_voice_message()
        self.mock_bot_module_instance.get_file.side_effect = Exception("TG API get_file error")

        bot.handle_voice_message(mock_message)

        self.mock_bot_module_instance.reply_to.assert_called_with(mock_message, "Произошла ошибка при обработке голосового сообщения. 😥")
        if self.mock_get_text_from_voice:
            self.mock_get_text_from_voice.assert_not_called()
        # self.mock_handle_text_message.assert_not_called() # Real handle_text_message is not reached
        self.mock_os_remove.assert_not_called() # File was not saved

    @patch('builtins.open', new_callable=unittest.mock.mock_open)
    def test_handle_voice_message_download_file_exception(self, mock_open_file):
        # No need to mock get_text_from_voice
        mock_message = self._create_mock_voice_message()
        self.mock_bot_module_instance.get_file.return_value.file_path = "voice/file.oga"
        self.mock_bot_module_instance.download_file.side_effect = Exception("TG API download_file error")

        bot.handle_voice_message(mock_message)

        expected_temp_path = self.test_voice_file_dir / f"{mock_message.voice.file_id}.ogg"
        self.mock_bot_module_instance.reply_to.assert_called_with(mock_message, "Произошла ошибка при обработке голосового сообщения. 😥")
        if self.mock_get_text_from_voice:
            self.mock_get_text_from_voice.assert_not_called()
        # self.mock_handle_text_message.assert_not_called() # Real handle_text_message is not reached
        # If download_file fails, temp_voice_path is not defined, so os.remove is not called.
        self.mock_os_remove.assert_not_called()


    @patch('builtins.open', side_effect=IOError("Disk full error"))
    def test_handle_voice_message_save_temp_file_ioerror(self, mock_open_file_error):
        # No need to mock get_text_from_voice
        mock_message = self._create_mock_voice_message()
        self.mock_bot_module_instance.get_file.return_value.file_path = "voice/file.oga"
        self.mock_bot_module_instance.download_file.return_value = b"dummy voice data"

        bot.handle_voice_message(mock_message)

        expected_temp_path = self.test_voice_file_dir / f"{mock_message.voice.file_id}.ogg"
        self.mock_bot_module_instance.reply_to.assert_called_with(mock_message, "Произошла ошибка при обработке голосового сообщения. 😥")
        if self.mock_get_text_from_voice:
            self.mock_get_text_from_voice.assert_not_called()
        # self.mock_handle_text_message.assert_not_called() # Real handle_text_message is not reached
        self.mock_os_remove.assert_called_once_with(expected_temp_path)

    # This test is redundant or incorrectly named after previous refactoring.
    # test_get_text_from_voice_api_returns_whitespace_string covers the case of "  " input.
    # @patch('builtins.open', new_callable=unittest.mock.mock_open, read_data=b"dummy voice data")
    # def test_get_text_from_voice_whitespace_only_transcription(self, mock_open_file):
    #     # Tests bot.get_text_from_voice, so openai.Audio.transcribe is mocked
    #     self.mock_openai_transcribe.return_value = {'text': '   '}
    #     result = bot.get_text_from_voice("dummy_path.ogg")
    #     self.assertEqual(result, "") # Stripped
    #     self.mock_log_local_bot_event.assert_any_call("Voice transcribed successfully: '  '") # Corrected expected log

    @patch('builtins.open', new_callable=unittest.mock.mock_open, read_data=b"dummy voice data")
    def test_get_text_from_voice_simulating_rate_limit_error(self, mock_open_file):
        # Tests bot.get_text_from_voice, so openai.Audio.transcribe is mocked
        mock_response = MagicMock()
        mock_response.status_code = 429
        # Use the specific RateLimitError if available and it fits this signature
        # from openai.error import RateLimitError # Check if this path is correct
        # For now, using APIError as a placeholder if RateLimitError has different constructor
        try:
            # Attempt to use specific error if library provides it and it fits this structure
            from openai import RateLimitError as OpenAIRateLimitError # Alias to avoid conflict if defined locally
            self.mock_openai_transcribe.side_effect = OpenAIRateLimitError(
                "Rate limit exceeded", response=mock_response, body=None
            )
        except ImportError: # Fallback if RateLimitError is not directly importable or has different init
             self.mock_openai_transcribe.side_effect = bot.openai.APIError(
                 "Simulated Rate Limit Error", request=MagicMock(), body=None # request needs to be a mock of a request object
            )
        result = bot.get_text_from_voice("dummy_path.ogg")
        self.assertIsNone(result)
        self.mock_log_local_bot_event.assert_any_call("OpenAI API Error during voice transcription: Rate limit exceeded" if isinstance(self.mock_openai_transcribe.side_effect, bot.openai.RateLimitError) else "OpenAI API Error during voice transcription: Simulated Rate Limit Error")


    @patch('builtins.open', new_callable=MagicMock) # Use MagicMock directly for more control over side_effect
    def test_get_text_from_voice_short_and_long_audio_simulation(self, mock_open):
        # Tests bot.get_text_from_voice, so openai.Audio.transcribe is mocked

        # Setup mock files to be returned by open()
        mock_file_short = MagicMock()
        mock_file_short.read.return_value = b"short audio data"
        mock_file_short.__enter__.return_value = mock_file_short # For context manager
        mock_file_short.__exit__.return_value = None

        mock_file_long = MagicMock()
        mock_file_long.read.return_value = b"very long audio data"
        mock_file_long.__enter__.return_value = mock_file_long # For context manager
        mock_file_long.__exit__.return_value = None

        mock_open.side_effect = [mock_file_short, mock_file_long]

        # Short audio
        self.mock_openai_transcribe.return_value = {'text': 'Hi'}
        result_short = bot.get_text_from_voice("short_audio.ogg")
        self.assertEqual(result_short, "Hi")
        mock_open.assert_any_call("short_audio.ogg", "rb")
        self.mock_openai_transcribe.assert_any_call("whisper-1", mock_file_short)

        # Reset shared mock if it's not reset by multiple calls to the main function
        # self.mock_openai_transcribe.reset_mock() # Already called once

        # Long audio
        self.mock_openai_transcribe.return_value = {'text': 'This is a longer transcription.'}
        result_long = bot.get_text_from_voice("long_audio.ogg")
        self.assertEqual(result_long, "This is a longer transcription.")
        mock_open.assert_any_call("long_audio.ogg", "rb")
        self.mock_openai_transcribe.assert_any_call("whisper-1", mock_file_long)

        self.assertEqual(mock_open.call_count, 2)
        self.assertEqual(self.mock_openai_transcribe.call_count, 2)


if __name__ == '__main__':
    unittest.main()
