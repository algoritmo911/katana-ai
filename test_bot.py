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
        # Since bot is now AsyncTeleBot, its methods will be awaitable.
        # We can use AsyncMock for methods like send_message, reply_to, etc.
        self.mock_bot_instance = MagicMock(spec=telebot.async_telebot.AsyncTeleBot)

        # Specific methods that are awaited need to be AsyncMock or return an awaitable
        self.mock_bot_instance.send_message = AsyncMock()
        self.mock_bot_instance.reply_to = AsyncMock()
        self.mock_bot_instance.edit_message_text = AsyncMock()
        self.mock_bot_instance.send_chat_action = AsyncMock()
        self.mock_bot_instance.get_file = AsyncMock()
        self.mock_bot_instance.download_file = AsyncMock()

        # Patch the bot instance within the 'bot' module
        self.bot_patcher = patch('bot.bot', self.mock_bot_instance)
        self.mock_bot_module_instance = self.bot_patcher.start() # This is the bot instance used by the module

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
        # It's an async function, so patch with AsyncMock if creating a mock instance directly.
        # If just patching the path, the test method will define its return_value or side_effect.
        self.get_text_from_voice_patcher = patch('bot.get_text_from_voice', new_callable=AsyncMock)
        self.mock_get_text_from_voice = None # Will be set when patcher is started by calling .start()

        # Patch for bot.handle_text_message - To be applied selectively if a test needs it as a mock
        # self.handle_text_message_patcher = patch('bot.handle_text_message')
        # self.mock_handle_text_message = None # Will be set if patcher is started

        # Patch for openai.ChatCompletion.create
        self.openai_chat_completion_patcher = patch('openai.ChatCompletion.create')
        self.mock_openai_chat_completion_create = self.openai_chat_completion_patcher.start()

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
        self.openai_chat_completion_patcher.stop() # Stop the new patcher
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
    async def test_valid_command_gets_saved(self): # Async
        command = {"type": "test_type", "module": "test_module", "args": {}, "id": "test_id"}
        mock_message = self._create_mock_message(command)

        # Ensure this path is taken (not NLP, is JSON)
        with patch('bot.interpret', return_value=None):
            await bot.handle_text_message(mock_message) # Await

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


    async def test_text_not_nlp_or_json_goes_to_gpt(self): # Renamed and made async
        mock_message = MagicMock(spec=telebot.types.Message)
        mock_message.chat = MagicMock(spec=telebot.types.Chat)
        mock_message.chat.id = 123
        mock_message.text = "this is plain text, not a command"

        # Mock interpret to return None (not NLP)
        # JSON parsing will also fail for this text
        # So it should fall through to get_gpt_streamed_response

        # Simulate empty stream from GPT for simplicity in this test
        self.mock_openai_chat_completion_create.return_value = iter([])

        with patch('bot.interpret', return_value=None):
            await bot.handle_text_message(mock_message) # Await

        # Assert that openai.ChatCompletion.create was called (indicating GPT path)
        self.mock_openai_chat_completion_create.assert_called_once()
        # We can also check bot.send_chat_action
        self.mock_bot_instance.send_chat_action.assert_called_with(123, 'typing')
        # No specific bot.reply_to for "unknown command" anymore in this path


    async def test_missing_type_field(self): # Async
        command = {"module": "test_module", "args": {}, "id": "test_id"} # type is missing
        mock_message = self._create_mock_message(command)
        with patch('bot.interpret', return_value=None):
            await bot.handle_text_message(mock_message) # Await
        self.mock_bot_instance.reply_to.assert_called_with(mock_message, "Error: Missing required field 'type'.")

    async def test_empty_string_type(self): # Async
        command = {"type": "", "module": "test_module", "args": {}, "id": "1"}
        mock_message = self._create_mock_message(command)
        with patch('bot.interpret', return_value=None):
            await bot.handle_text_message(mock_message) # Await
        self.mock_bot_instance.reply_to.assert_called_with(mock_message, "Error: Field 'type' must be a non-empty string. Got value ''.")

    async def test_whitespace_string_type(self): # Async
        command = {"type": "   ", "module": "test_module", "args": {}, "id": "1"}
        mock_message = self._create_mock_message(command)
        with patch('bot.interpret', return_value=None):
            await bot.handle_text_message(mock_message) # Await
        self.mock_bot_instance.reply_to.assert_called_with(mock_message, "Error: Field 'type' must be a non-empty string. Got value '   '.")

    async def test_missing_module_field(self): # Async
        command = {"type": "test_type", "args": {}, "id": "test_id"} # module is missing
        mock_message = self._create_mock_message(command)
        with patch('bot.interpret', return_value=None):
            await bot.handle_text_message(mock_message) # Await
        self.mock_bot_instance.reply_to.assert_called_with(mock_message, "Error: Missing required field 'module'.")

    async def test_empty_string_module(self): # Async
        command = {"type": "test", "module": "", "args": {}, "id": "1"}
        mock_message = self._create_mock_message(command)
        with patch('bot.interpret', return_value=None):
            await bot.handle_text_message(mock_message) # Await
        self.mock_bot_instance.reply_to.assert_called_with(mock_message, "Error: Field 'module' must be a non-empty string. Got value ''.")

    async def test_whitespace_string_module(self): # Async
        command = {"type": "test", "module": "   ", "args": {}, "id": "1"}
        mock_message = self._create_mock_message(command)
        with patch('bot.interpret', return_value=None):
            await bot.handle_text_message(mock_message) # Await
        self.mock_bot_instance.reply_to.assert_called_with(mock_message, "Error: Field 'module' must be a non-empty string. Got value '   '.")

    async def test_invalid_args_type(self): # Async
        command = {"type": "test_type", "module": "test_module", "args": "not_a_dict", "id": "test_id"}
        mock_message = self._create_mock_message(command)
        with patch('bot.interpret', return_value=None):
            await bot.handle_text_message(mock_message) # Await
        self.mock_bot_instance.reply_to.assert_called_with(mock_message, "Error: Field 'args' must be type dict. Got value 'not_a_dict' of type str.")

    async def test_invalid_id_type(self): # Async
        command = {"type": "test_type", "module": "test_module", "args": {}, "id": [1,2,3]} # id is a list
        mock_message = self._create_mock_message(command)
        with patch('bot.interpret', return_value=None):
            await bot.handle_text_message(mock_message) # Await
        self.mock_bot_instance.reply_to.assert_called_with(mock_message, "Error: Field 'id' must be type str or int. Got value '[1, 2, 3]' of type list.")

    # --- ID field type tests ---
    async def test_valid_command_with_int_id(self): # Async
        command = {"type": "test_type_int_id", "module": "test_module_int_id", "args": {}, "id": 123}
        mock_message = self._create_mock_message(command)
        with patch('bot.interpret', return_value=None):
            await bot.handle_text_message(mock_message) # Await

        expected_module_dir = self.test_commands_dir / "telegram_mod_test_module_int_id"
        self.assertTrue(expected_module_dir.exists())
        expected_filename = f"YYYYMMDD_HHMMSS_ffffff_{mock_message.chat.id}.json"
        expected_file_path = expected_module_dir / expected_filename
        self.assertTrue(expected_file_path.exists())
        with open(expected_file_path, "r") as f:
            saved_data = json.load(f)
        self.assertEqual(saved_data, command)
        self.mock_bot_instance.reply_to.assert_called_once() # mock_bot_module_instance -> mock_bot_instance
        args, kwargs = self.mock_bot_instance.reply_to.call_args # mock_bot_module_instance -> mock_bot_instance
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
    async def test_valid_command_with_empty_args(self): # Async
        command = {"type": "test_empty_args", "module": "test_mod_empty_args", "args": {}, "id": "empty_args_id"}
        mock_message = self._create_mock_message(command)
        with patch('bot.interpret', return_value=None):
            await bot.handle_text_message(mock_message) # Await

        expected_module_dir = self.test_commands_dir / "telegram_mod_test_mod_empty_args"
        self.assertTrue(expected_module_dir.exists())
        expected_filename = f"YYYYMMDD_HHMMSS_ffffff_{mock_message.chat.id}.json"
        expected_file_path = expected_module_dir / expected_filename
        self.assertTrue(expected_file_path.exists())
        self.mock_bot_instance.reply_to.assert_called_once() # mock_bot_module_instance -> mock_bot_instance

    async def test_valid_command_with_simple_args(self): # Async
        command = {"type": "test_simple_args", "module": "test_mod_simple_args", "args": {"key": "value"}, "id": "simple_args_id"}
        mock_message = self._create_mock_message(command)
        with patch('bot.interpret', return_value=None):
            await bot.handle_text_message(mock_message) # Await

        expected_module_dir = self.test_commands_dir / "telegram_mod_test_mod_simple_args"
        self.assertTrue(expected_module_dir.exists())
        expected_filename = f"YYYYMMDD_HHMMSS_ffffff_{mock_message.chat.id}.json"
        expected_file_path = expected_module_dir / expected_filename
        self.assertTrue(expected_file_path.exists())
        self.mock_bot_instance.reply_to.assert_called_once() # mock_bot_module_instance -> mock_bot_instance


    # --- Test Command Routing ---
    @patch('bot.handle_log_event', new_callable=AsyncMock) # Keep this patch local, use AsyncMock for async func
    async def test_routing_log_event(self, mock_handle_log_event_func): # Async
        command = {"type": "log_event", "module": "logging", "args": {"message": "hello"}, "id": "log001"}
        mock_message = self._create_mock_message(command)
        with patch('bot.interpret', return_value=None):
            await bot.handle_text_message(mock_message) # Await

        mock_handle_log_event_func.assert_called_once_with(command, mock_message.chat.id)
        self.mock_bot_instance.reply_to.assert_called_with(mock_message, "✅ 'log_event' processed (placeholder).")


    @patch('bot.handle_mind_clearing', new_callable=AsyncMock) # Keep this patch local, use AsyncMock
    async def test_routing_mind_clearing(self, mock_handle_mind_clearing_func): # Async
        command = {"type": "mind_clearing", "module": "wellness", "args": {"duration": "10m"}, "id": "mind002"}
        mock_message = self._create_mock_message(command)
        with patch('bot.interpret', return_value=None):
            await bot.handle_text_message(mock_message) # Await

        mock_handle_mind_clearing_func.assert_called_once_with(command, mock_message.chat.id)
        self.mock_bot_instance.reply_to.assert_called_with(mock_message, "✅ 'mind_clearing' processed (placeholder).")


    async def test_unknown_command_type_saves_normally(self): # Async
        command = {"type": "unknown_type", "module": "custom_module", "args": {}, "id": "custom003"}
        mock_message = self._create_mock_message(command)
        with patch('bot.interpret', return_value=None):
            await bot.handle_text_message(mock_message) # Await

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
        self.mock_bot_instance.reply_to.assert_called_once() # mock_bot_module_instance -> mock_bot_instance
        args, kwargs = self.mock_bot_instance.reply_to.call_args # mock_bot_module_instance -> mock_bot_instance
        self.assertEqual(args[0], mock_message)
        self.assertTrue(args[1].startswith("✅ Command received and saved as"))
        self.assertIn(str(expected_file_path), args[1])

    # --- Logging Verification Tests ---
    async def test_validation_failure_logs_details(self): # Async
        command = {"type": "test_type", "module": "", "args": {}, "id": "fail_log_id"} # Empty module
        original_command_text = json.dumps(command)
        mock_message = self._create_mock_message(command)
        with patch('bot.interpret', return_value=None):
            await bot.handle_text_message(mock_message) # Await

        self.mock_bot_instance.reply_to.assert_called_with(mock_message, "Error: Field 'module' must be a non-empty string. Got value ''.") # mock_bot_module_instance -> mock_bot_instance

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
    async def test_get_text_from_voice_success(self, mock_open_file): # Async
        self.mock_openai_transcribe.return_value = {'text': 'Hello world'}
        result = await bot.get_text_from_voice("dummy_path.ogg") # Await
        self.assertEqual(result, "Hello world")
        mock_open_file.assert_called_once_with("dummy_path.ogg", "rb")
        self.mock_openai_transcribe.assert_called_once()
        self.mock_log_local_bot_event.assert_any_call("Sending voice file dummy_path.ogg to OpenAI Whisper API...")
        self.mock_log_local_bot_event.assert_any_call("Voice transcribed successfully: 'Hello world'")

    @patch('builtins.open', new_callable=unittest.mock.mock_open, read_data=b"dummy voice data")
    async def test_get_text_from_voice_api_error(self, mock_open_file): # Async
        # This test is for the function bot.get_text_from_voice, so openai.Audio.transcribe is mocked (done in setUp)
        mock_response = MagicMock() # Create a mock response object
        mock_response.status_code = 500
        self.mock_openai_transcribe.side_effect = bot.openai.APIError("API Error", request=MagicMock(), body=None)
        result = await bot.get_text_from_voice("dummy_path.ogg") # Await
        self.assertIsNone(result)
        self.mock_log_local_bot_event.assert_any_call("OpenAI API Error during voice transcription: API Error")

    @patch('builtins.open', new_callable=unittest.mock.mock_open, read_data=b"dummy voice data")
    async def test_get_text_from_voice_no_text_returned(self, mock_open_file): # Async
        # This test is for the function bot.get_text_from_voice, so openai.Audio.transcribe is mocked
        self.mock_openai_transcribe.return_value = {'text': None} # Simulate API returning no text
        result = await bot.get_text_from_voice("dummy_path.ogg") # Await
        self.assertIsNone(result)
        self.mock_log_local_bot_event.assert_any_call("Voice transcription returned no text (text is None).")

    @patch('builtins.open', new_callable=unittest.mock.mock_open, read_data=b"dummy voice data")
    async def test_get_text_from_voice_api_returns_empty_string(self, mock_open_file): # Async
        # Tests bot.get_text_from_voice, so openai.Audio.transcribe is mocked
        self.mock_openai_transcribe.return_value = {'text': ""} # Simulate API returning empty string
        result = await bot.get_text_from_voice("dummy_path.ogg") # Await
        self.assertEqual(result, "") # Should be stripped (no change)
        self.mock_log_local_bot_event.assert_any_call("Voice transcribed successfully: ''")

    @patch('builtins.open', new_callable=unittest.mock.mock_open, read_data=b"dummy voice data")
    async def test_get_text_from_voice_api_returns_whitespace_string(self, mock_open_file): # Async
        # This test is for the function bot.get_text_from_voice, so openai.Audio.transcribe is mocked
        self.mock_openai_transcribe.return_value = {'text': "  "} # Simulate API returning only whitespace
        result = await bot.get_text_from_voice("dummy_path.ogg") # Await
        self.assertEqual(result, "") # Should be stripped
        self.mock_log_local_bot_event.assert_any_call("Voice transcribed successfully: '  '")


    @patch('bot.OPENAI_API_KEY', None) # Temporarily unpatch the class-level patch
    async def test_get_text_from_voice_no_api_key(self): # Async
        result = await bot.get_text_from_voice("dummy_path.ogg") # Await
        self.assertIsNone(result)
        self.mock_log_local_bot_event.assert_any_call("OpenAI API key not configured. Cannot process voice.")
        self.mock_openai_transcribe.assert_not_called()

    @patch('builtins.open', side_effect=IOError("File not found"))
    async def test_get_text_from_voice_file_open_error(self, mock_open_file): # Async
        # Ensure OPENAI_API_KEY is set for this test, otherwise it exits early
        with patch('bot.OPENAI_API_KEY', 'fake_key_for_this_test'):
            result = await bot.get_text_from_voice("dummy_path.ogg") # Await
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
    async def test_handle_voice_message_success(self, mock_open_file): # Async
        # This test is for handle_voice_message, so bot.get_text_from_voice is mocked
        self.mock_get_text_from_voice = self.get_text_from_voice_patcher.start()
        mock_message = self._create_mock_voice_message()

        # Configure AsyncMock returns for awaited calls
        self.mock_bot_instance.get_file.return_value = MagicMock(file_path="voice/file.oga")
        self.mock_bot_instance.download_file.return_value = b"dummy voice data"
        self.mock_get_text_from_voice.return_value = "show disk space" # This is an AsyncMock, direct value

        # Simulate empty stream from GPT for this test, as "show disk space" is not NLP/JSON
        self.mock_openai_chat_completion_create.return_value = iter([])

        await bot.handle_voice_message(mock_message) # Await

        # Check file download and saving
        self.mock_bot_instance.get_file.assert_called_once_with("test_voice_file_id")
        self.mock_bot_instance.download_file.assert_called_once_with("voice/file.oga")
        expected_temp_path = self.test_voice_file_dir / f"{mock_message.voice.file_id}.ogg"
        mock_open_file.assert_called_once_with(expected_temp_path, 'wb') # This is called inside run_in_executor
        mock_open_file().write.assert_called_once_with(b"dummy voice data")

        # Check transcription call
        self.mock_get_text_from_voice.assert_called_once_with(str(expected_temp_path))

        # Check reply to user
        self.mock_bot_instance.reply_to.assert_any_call(mock_message, '🗣️ Распознано: "show disk space"')

        # Now, "show disk space" goes to process_user_message.
        # Assuming "show disk space" is not an NLP command and not JSON, it goes to GPT.
        # Check that ChatCompletion.create was called.
        self.mock_openai_chat_completion_create.assert_called_once()
        args_list = self.mock_openai_chat_completion_create.call_args_list
        self.assertEqual(args_list[0].kwargs['messages'][-1]['content'], "show disk space")


        # Check file cleanup (os.remove is called in executor)
        # To properly test os.remove, we need to ensure the patched mock_os_remove is called.
        # The logic for deletion is now inside _check_and_delete_temp_file run in executor.
        # We assume the executor runs. If mock_path_exists returns true, mock_os_remove should be called.
        self.mock_path_exists.return_value = True # Ensure it thinks file exists
        # To verify os.remove, we'd need to let the executor part run or mock it.
        # For now, we'll trust the executor runs the sync os.remove.
        # Await a short time to allow executor to potentially run (not ideal for unit tests)
        await asyncio.sleep(0.01)
        self.mock_os_remove.assert_called_once_with(expected_temp_path)
        self.get_text_from_voice_patcher.stop()


    @patch('builtins.open', new_callable=unittest.mock.mock_open)
    async def test_handle_voice_message_transcription_fails(self, mock_open_file): # Async
        self.mock_get_text_from_voice = self.get_text_from_voice_patcher.start()
        mock_message = self._create_mock_voice_message()
        self.mock_bot_instance.get_file.return_value = MagicMock(file_path="voice/file.oga")
        self.mock_bot_instance.download_file.return_value = b"dummy voice data"
        self.mock_get_text_from_voice.return_value = None # Simulate transcription failure

        await bot.handle_voice_message(mock_message) # Await

        expected_temp_path = self.test_voice_file_dir / f"{mock_message.voice.file_id}.ogg"
        self.mock_get_text_from_voice.assert_called_once_with(str(expected_temp_path))
        self.mock_bot_instance.reply_to.assert_any_call(mock_message, "Не понял, повтори, пожалуйста. 🎙️")
        # process_user_message should not be called, so no GPT call
        self.mock_openai_chat_completion_create.assert_not_called()

        await asyncio.sleep(0.01) # For os.remove in executor
        self.mock_os_remove.assert_called_once_with(expected_temp_path)
        self.get_text_from_voice_patcher.stop()

    @patch('bot.OPENAI_API_KEY', None)
    async def test_handle_voice_message_no_openai_key(self): # Async
        mock_message = self._create_mock_voice_message()
        await bot.handle_voice_message(mock_message) # Await
        self.mock_bot_instance.reply_to.assert_called_with(mock_message, "⚠️ Распознавание голоса не настроено на сервере.")
        self.mock_bot_instance.get_file.assert_not_called()
        # self.mock_get_text_from_voice is an AsyncMock, check it wasn't called
        if hasattr(self.mock_get_text_from_voice, 'assert_not_called'): # It's only an AsyncMock if patcher was started
            self.mock_get_text_from_voice.assert_not_called()
        self.mock_openai_chat_completion_create.assert_not_called()


    @patch('builtins.open', new_callable=unittest.mock.mock_open)
    async def test_handle_voice_message_download_exception(self, mock_open_file): # Async
        mock_message = self._create_mock_voice_message()
        self.mock_bot_instance.get_file.side_effect = Exception("Download error") # get_file is asyncmock

        await bot.handle_voice_message(mock_message) # Await

        self.mock_bot_instance.reply_to.assert_called_with(mock_message, "Произошла ошибка при обработке голосового сообщения. 😥")
        if hasattr(self.mock_get_text_from_voice, 'assert_not_called'):
            self.mock_get_text_from_voice.assert_not_called()
        self.mock_os_remove.assert_not_called()


    @patch('builtins.open', new_callable=unittest.mock.mock_open)
    @patch('os.remove', side_effect=OSError("Delete failed")) # Standard mock for os.remove
    async def test_handle_voice_message_cleanup_exception(self, mock_os_remove_custom, mock_open_file): # Async
        self.mock_get_text_from_voice = self.get_text_from_voice_patcher.start()
        mock_message = self._create_mock_voice_message()
        self.mock_bot_instance.get_file.return_value = MagicMock(file_path="voice/file.oga")
        self.mock_bot_instance.download_file.return_value = b"dummy voice data"
        self.mock_get_text_from_voice.return_value = "текст" # Russian: "text"

        # "текст" is not NLP/JSON, so it will go to GPT. Mock GPT response.
        self.mock_openai_chat_completion_create.return_value = iter([])


        await bot.handle_voice_message(mock_message) # Await

        expected_temp_path = self.test_voice_file_dir / f"{mock_message.voice.file_id}.ogg"

        # Check GPT was called for "текст"
        self.mock_openai_chat_completion_create.assert_called_once()

        # Check that reply_to was called for "Распознано"
        self.mock_bot_instance.reply_to.assert_any_call(mock_message, '🗣️ Распознано: "текст"')

        await asyncio.sleep(0.01) # For os.remove in executor
        # Check that remove was called (and it's our custom mock that raises error)
        mock_os_remove_custom.assert_called_once_with(expected_temp_path)
        # Check that the error during cleanup was logged
        self.mock_log_local_bot_event.assert_any_call(f"Error deleting temporary voice file {expected_temp_path}: Delete failed")
        self.get_text_from_voice_patcher.stop()

    # --- Additional tests for voice processing stability ---

    @patch('builtins.open', new_callable=unittest.mock.mock_open)
    # Patch process_user_message to check it's called, instead of specific reply_to calls from it
    @patch('bot.process_user_message', new_callable=AsyncMock)
    async def test_handle_voice_message_transcription_returns_empty_string(self, mock_process_user_message, mock_open_file): # Async
        self.mock_get_text_from_voice = self.get_text_from_voice_patcher.start()
        mock_original_voice_message = self._create_mock_voice_message()
        self.mock_bot_instance.get_file.return_value = MagicMock(file_path="voice/file.oga")
        self.mock_bot_instance.download_file.return_value = b"dummy voice data"
        self.mock_get_text_from_voice.return_value = "" # Simulate empty string transcription

        await bot.handle_voice_message(mock_original_voice_message) # Await

        expected_temp_path = self.test_voice_file_dir / f"{mock_original_voice_message.voice.file_id}.ogg"
        self.mock_get_text_from_voice.assert_called_once_with(str(expected_temp_path))

        # Check the first reply: "Распознано"
        self.mock_bot_instance.reply_to.assert_any_call(mock_original_voice_message, '🗣️ Распознано: ""')

        # Check that process_user_message was called with the empty string
        mock_process_user_message.assert_called_once_with(
            mock_original_voice_message.chat.id,
            "",
            mock_original_voice_message
        )

        await asyncio.sleep(0.01) # For os.remove
        self.mock_os_remove.assert_called_once_with(expected_temp_path)
        self.get_text_from_voice_patcher.stop()

    async def test_handle_voice_message_get_file_exception(self): # Async
        mock_message = self._create_mock_voice_message()
        self.mock_bot_instance.get_file.side_effect = Exception("TG API get_file error")

        await bot.handle_voice_message(mock_message) # Await

        self.mock_bot_instance.reply_to.assert_called_with(mock_message, "Произошла ошибка при обработке голосового сообщения. 😥")
        if hasattr(self.mock_get_text_from_voice, 'assert_not_called'):
            self.mock_get_text_from_voice.assert_not_called()
        self.mock_os_remove.assert_not_called()

    @patch('builtins.open', new_callable=unittest.mock.mock_open)
    async def test_handle_voice_message_download_file_exception(self, mock_open_file): # Async
        mock_message = self._create_mock_voice_message()
        self.mock_bot_instance.get_file.return_value = MagicMock(file_path="voice/file.oga")
        self.mock_bot_instance.download_file.side_effect = Exception("TG API download_file error") # download_file is AsyncMock

        await bot.handle_voice_message(mock_message) # Await

        self.mock_bot_instance.reply_to.assert_called_with(mock_message, "Произошла ошибка при обработке голосового сообщения. 😥")
        if hasattr(self.mock_get_text_from_voice, 'assert_not_called'):
            self.mock_get_text_from_voice.assert_not_called()
        self.mock_os_remove.assert_not_called()


    @patch('builtins.open', side_effect=IOError("Disk full error"))
    async def test_handle_voice_message_save_temp_file_ioerror(self, mock_open_file_error): # Async
        mock_message = self._create_mock_voice_message()
        self.mock_bot_instance.get_file.return_value = MagicMock(file_path="voice/file.oga")
        self.mock_bot_instance.download_file.return_value = b"dummy voice data"

        await bot.handle_voice_message(mock_message) # Await

        expected_temp_path = self.test_voice_file_dir / f"{mock_message.voice.file_id}.ogg"
        self.mock_bot_instance.reply_to.assert_called_with(mock_message, "Произошла ошибка при обработке голосового сообщения. 😥")
        if hasattr(self.mock_get_text_from_voice, 'assert_not_called'):
            self.mock_get_text_from_voice.assert_not_called()

        # os.remove is called in finally, even if open() fails for saving the voice file,
        # but only if temp_voice_path.exists() is true.
        # In this test, open() for saving fails, so the file wouldn't exist.
        # The _check_and_delete_temp_file will find it doesn't exist.
        await asyncio.sleep(0.01)
        self.mock_os_remove.assert_not_called()


    # This test is redundant or incorrectly named after previous refactoring.
    # test_get_text_from_voice_api_returns_whitespace_string covers the case of "  " input.
    # @patch('builtins.open', new_callable=unittest.mock.mock_open, read_data=b"dummy voice data")
    # async def test_get_text_from_voice_whitespace_only_transcription(self, mock_open_file): # Async
    #     # Tests bot.get_text_from_voice, so openai.Audio.transcribe is mocked
    #     self.mock_openai_transcribe.return_value = {'text': '   '}
    #     result = await bot.get_text_from_voice("dummy_path.ogg") # Await
    #     self.assertEqual(result, "") # Stripped
    #     self.mock_log_local_bot_event.assert_any_call("Voice transcribed successfully: '  '")

    @patch('builtins.open', new_callable=unittest.mock.mock_open, read_data=b"dummy voice data")
    async def test_get_text_from_voice_simulating_rate_limit_error(self, mock_open_file): # Async
        # Tests bot.get_text_from_voice, so openai.Audio.transcribe is mocked
        mock_response = MagicMock()
        mock_response.status_code = 429

        rate_limit_error_instance = None
        try:
            from openai import RateLimitError as OpenAIRateLimitError
            rate_limit_error_instance = OpenAIRateLimitError(
                "Rate limit exceeded", response=mock_response, body=None
            )
        except ImportError:
             rate_limit_error_instance = bot.openai.APIError(
                 "Simulated Rate Limit Error", request=MagicMock(), body=None
            )
        self.mock_openai_transcribe.side_effect = rate_limit_error_instance

        result = await bot.get_text_from_voice("dummy_path.ogg") # Await
        self.assertIsNone(result)

        # Check for the correct log message based on the actual error type raised
        if isinstance(rate_limit_error_instance, bot.openai.RateLimitError):
            self.mock_log_local_bot_event.assert_any_call("OpenAI API Error during voice transcription: Rate limit exceeded")
        else: # Fallback to generic APIError message
            self.mock_log_local_bot_event.assert_any_call("OpenAI API Error during voice transcription: Simulated Rate Limit Error")


    @patch('builtins.open', new_callable=MagicMock)
    async def test_get_text_from_voice_short_and_long_audio_simulation(self, mock_open): # Async
        # Tests bot.get_text_from_voice, so openai.Audio.transcribe is mocked

        mock_file_short = MagicMock()
        mock_file_short.read.return_value = b"short audio data"
        mock_file_short.__enter__.return_value = mock_file_short
        mock_file_short.__exit__.return_value = None

        mock_file_long = MagicMock()
        mock_file_long.read.return_value = b"very long audio data"
        mock_file_long.__enter__.return_value = mock_file_long
        mock_file_long.__exit__.return_value = None

        mock_open.side_effect = [mock_file_short, mock_file_long]

        # Short audio
        self.mock_openai_transcribe.return_value = {'text': 'Hi'}
        result_short = await bot.get_text_from_voice("short_audio.ogg") # Await
        self.assertEqual(result_short, "Hi")
        mock_open.assert_any_call("short_audio.ogg", "rb")
        # self.mock_openai_transcribe.assert_any_call("whisper-1", mock_file_short) # This mock_file_short is tricky with run_in_executor
                                                                               # The actual file object passed to transcribe
                                                                               # is created inside _transcribe_blocking.
                                                                               # So, just check that transcribe was called.
        self.assertTrue(self.mock_openai_transcribe.called)


        # Long audio
        # Reset the global mock_openai_transcribe if it's stateful from the previous call in a way that affects this sub-test
        self.mock_openai_transcribe.reset_mock() # Reset call count etc.
        self.mock_openai_transcribe.return_value = {'text': 'This is a longer transcription.'} # Set new return value
        result_long = await bot.get_text_from_voice("long_audio.ogg") # Await
        self.assertEqual(result_long, "This is a longer transcription.")
        mock_open.assert_any_call("long_audio.ogg", "rb")
        # self.mock_openai_transcribe.assert_any_call("whisper-1", mock_file_long) # Same reasoning as above
        self.assertTrue(self.mock_openai_transcribe.called)


        self.assertEqual(mock_open.call_count, 2)
        # Transcribe should be called twice, once for each audio file.
        self.assertEqual(self.mock_openai_transcribe.call_count, 1) # It was reset, so 1 for the second call.
                                                                  # Actually, it should be 2 if we want to count both.
                                                                  # Let's adjust:
        # Need to re-evaluate how to count calls when reset_mock is used.
        # If we want to assert total calls across both, don't reset or sum counts.
        # For this test, let's assume we care about each call individually.
        # The first call was checked by self.assertTrue(self.mock_openai_transcribe.called)
        # The second call is also checked by self.assertTrue(self.mock_openai_transcribe.called) after reset.
        # This is fine.


if __name__ == '__main__':
    unittest.main()

# --- New Test Class for Async Specific Tests or just add to existing ---
# For now, adding to existing TestBot class.

# --- New Test Class for Async Specific Tests or just add to existing ---
# For now, adding to existing TestBot class.

    async def test_gpt_streaming_sends_chunks(self):
        # 1. Prepare mock for openai.ChatCompletion.create to simulate a stream
        mock_stream_chunks = [
            {"choices": [{"delta": {"content": "Hello"}}]},
            {"choices": [{"delta": {"content": ", "}}]},
            {"choices": [{"delta": {"content": "world!"}}]},
            {"choices": [{"delta": {}}]} # Simulate end of content
        ]
        # The create method should return an iterator that yields these chunks
        self.mock_openai_chat_completion_create.return_value = iter(mock_stream_chunks)

        # 2. Create a mock message that will trigger the GPT path
        mock_message = self._create_mock_message("some non-command text")
        # Override text to be non-JSON for this specific test path
        mock_message.text = "tell me a joke"
        mock_message.chat.id = 12345 # Ensure chat_id is consistent

        # Mock `interpret` to ensure it doesn't see this as an NLP command
        with patch('bot.interpret', return_value=None):
            await bot.handle_text_message(mock_message)

        # 3. Assertions
        # Check for 'typing' action
        self.mock_bot_instance.send_chat_action.assert_called_once_with(12345, 'typing')

        # Check for initial message send (reply_to is used by process_user_message)
        # The first call to reply_to will have the first chunk
        # Subsequent calls will be edit_message_text

        # Assert reply_to was called for the first chunk.
        # process_user_message uses reply_to for the first message.
        self.mock_bot_instance.reply_to.assert_any_call(mock_message, "Hello")

        # Get the message_id from the (AsyncMock) call to reply_to
        # The actual sent message object is the result of the awaitable.
        # We need to set a return_value for reply_to that has a message_id.
        mock_sent_message = MagicMock()
        mock_sent_message.message_id = 98765
        self.mock_bot_instance.reply_to.return_value = mock_sent_message

        # Re-run with the configured return_value for reply_to
        self.mock_bot_instance.reply_to.reset_mock() # Reset because we called it once to check content
        self.mock_bot_instance.edit_message_text.reset_mock()
        self.mock_openai_chat_completion_create.return_value = iter(mock_stream_chunks) # Reset iterator

        with patch('bot.interpret', return_value=None):
            await bot.handle_text_message(mock_message)

        # Assert reply_to for first chunk again
        self.mock_bot_instance.reply_to.assert_called_once_with(mock_message, "Hello")

        # Assert edit_message_text for subsequent chunks
        calls = [
            call("Hello, ", 12345, 98765),
            call("Hello, world!", 12345, 98765)
        ]
        self.mock_bot_instance.edit_message_text.assert_has_calls(calls, any_order=False)
        self.assertEqual(self.mock_bot_instance.edit_message_text.call_count, 2)

        # Verify that ChatCompletion.create was called correctly
        self.mock_openai_chat_completion_create.assert_called_once_with(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "You are a helpful assistant."},
                {"role": "user", "content": "tell me a joke"}
            ],
            stream=True
        )
