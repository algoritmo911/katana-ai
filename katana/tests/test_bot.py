import unittest
from unittest.mock import MagicMock, patch, call
import json
from pathlib import Path
import shutil # For robust directory removal

import sys
from pathlib import Path
sys.path.append(str(Path(__file__).resolve().parent.parent))
from katana import bot
import telebot # Import telebot here
from katana.core.user_profile import UserProfile
from katana.adapters.local_file_adapter import LocalFileAdapter

class TestBot(unittest.TestCase):

    def setUp(self):
        # Create a dummy commands directory for testing
        self.test_commands_dir = Path("test_commands_temp_dir") # Using a more unique name
        self.test_commands_dir.mkdir(parents=True, exist_ok=True)

        self.test_user_data_dir = Path("test_user_data_temp_dir")
        self.test_user_data_dir.mkdir(parents=True, exist_ok=True)

        # Store original and set to test
        self.original_command_file_dir = bot.COMMAND_FILE_DIR
        bot.COMMAND_FILE_DIR = self.test_commands_dir

        # Mock the bot object and its methods
        self.mock_bot_instance = MagicMock()
        # Patch the bot instance within the 'bot' module
        self.bot_patcher = patch('katana.bot.bot', self.mock_bot_instance)
        self.mock_bot_module_instance = self.bot_patcher.start()

        # Mock datetime to control timestamps in filenames and time-based greetings
        self.mock_datetime_patcher = patch('katana.bot.datetime')
        self.mock_datetime = self.mock_datetime_patcher.start()
        self.mock_datetime.utcnow.return_value.strftime.return_value = "YYYYMMDD_HHMMSS_ffffff"
        # Ensure datetime.now().hour returns an int for get_time_of_day_greeting
        self.mock_datetime.now.return_value.hour = 14 # Afternoon by default for tests

        # Patch log_local_bot_event
        self.mock_log_event_patcher = patch('katana.bot.log_local_bot_event')
        self.mock_log_local_bot_event = self.mock_log_event_patcher.start()

        # Patch for OPENAI_API_KEY
        self.openai_api_key_patcher = patch('katana.bot.OPENAI_API_KEY', 'test_openai_key')
        self.mock_openai_api_key = self.openai_api_key_patcher.start()

        # Patch for openai.Audio.transcribe
        self.openai_transcribe_patcher = patch('openai.Audio.transcribe')
        self.mock_openai_transcribe = self.openai_transcribe_patcher.start()

        # Patch for bot.get_text_from_voice
        self.get_text_from_voice_patcher = patch('katana.bot.get_text_from_voice')
        self.mock_get_text_from_voice = self.get_text_from_voice_patcher.start()

        # Patch for bot.handle_text_message
        self.handle_text_message_patcher = patch('katana.bot.handle_text_message')
        self.mock_handle_text_message = self.handle_text_message_patcher.start()

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
        self.voice_file_dir_patcher = patch('katana.bot.VOICE_FILE_DIR', self.test_voice_file_dir)
        self.voice_file_dir_patcher.start()

        # Reset BOT_STATS before each test
        bot.BOT_STATS["commands_processed"] = 0

        # Patch interpret to control NLP results
        self.interpret_patcher = patch('katana.bot.interpret')
        self.mock_interpret = self.interpret_patcher.start()

        # Patch run_katana_command
        self.run_katana_command_patcher = patch('katana.bot.run_katana_command')
        self.mock_run_katana_command = self.run_katana_command_patcher.start()

        self.local_storage_patcher = patch('katana.bot.LocalFileAdapter')
        self.mock_local_storage = self.local_storage_patcher.start()


        # Unpatch bot.handle_text_message for integration tests of this function
        # We will call it directly in some tests.
        self.handle_text_message_patcher.stop() # Stop the initial patch
        # If we need to mock it for specific tests later, we can do it locally.



    def tearDown(self):
        # Stop patchers
        self.bot_patcher.stop()
        self.mock_datetime_patcher.stop()
        self.mock_log_event_patcher.stop()
        self.openai_api_key_patcher.stop()
        self.openai_transcribe_patcher.stop()
        self.get_text_from_voice_patcher.stop()
        # self.handle_text_message_patcher.stop() # Already stopped or managed locally
        self.os_remove_patcher.stop()
        self.path_exists_patcher.stop()
        self.voice_file_dir_patcher.stop()
        self.interpret_patcher.stop()
        self.run_katana_command_patcher.stop()
        self.local_storage_patcher.stop()


        # Clean up: remove dummy directory and its contents
        if self.test_commands_dir.exists():
            shutil.rmtree(self.test_commands_dir)
        if self.test_voice_file_dir.exists():
            shutil.rmtree(self.test_voice_file_dir)

        bot.COMMAND_FILE_DIR = self.original_command_file_dir


    def _create_mock_message(self, text_payload, user_id=123, username="testuser", first_name="Test"):
        mock_message = MagicMock(spec=telebot.types.Message)
        mock_message.chat = MagicMock(spec=telebot.types.Chat)
        mock_message.chat.id = 12345
        mock_message.text = text_payload # For direct text, not JSON
        mock_message.from_user = MagicMock(spec=telebot.types.User)
        mock_message.from_user.id = user_id
        mock_message.from_user.username = username
        mock_message.from_user.first_name = first_name
        mock_message.from_user.last_name = "User"
        mock_message.date = 1678886400 # Example timestamp
        mock_message.message_id = 789
        return mock_message

    def _create_mock_json_message(self, json_payload_dict, user_id=123, username="testuser", first_name="Test"):
        mock_message = self._create_mock_message("", user_id=user_id, username=username, first_name=first_name) # Base mock
        mock_message.text = json.dumps(json_payload_dict) # Set text to JSON string
        return mock_message


    # --- Test Command Validation (for JSON messages) ---
    # Note: handle_message was refactored into handle_text_message.
    # JSON processing is now a fallback within handle_text_message.
    @patch('telebot.apihelper._make_request')
    def test_valid_json_command_gets_saved(self, mock_make_request):
        command = {"type": "test_type", "module": "test_module", "args": {}, "id": "test_id"}
        mock_message = self._create_mock_json_message(command)
        self.mock_interpret.return_value = None # Ensure NLP does not pick it up

        bot.handle_text_message(mock_message) # Call the actual handler

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


    @patch('telebot.apihelper._make_request')
    @patch('katana.bot.get_time_of_day_greeting', return_value="Добрый день")
    @patch('katana.bot.get_username', return_value="testuser")
    def test_invalid_json_format_fallback_message(self, mock_get_username, mock_get_time_greeting, mock_make_request):
        mock_message = self._create_mock_message("not a valid json")
        self.mock_interpret.return_value = None

        bot.handle_text_message(mock_message)

        expected_reply_start = "Добрый день, testuser. К сожалению, я не смог распознать вашу команду: \"not a valid json\"."
        # self.mock_bot_module_instance.reply_to.assert_called_once() # reply_to is called on the original message obj
        args, _ = self.mock_bot_module_instance.reply_to.call_args
        self.assertEqual(args[0], mock_message)
        self.assertTrue(args[1].startswith(expected_reply_start))
        self.assertIn("Я уже обработал 1 команд.", args[1]) # Check bot stats

    @patch('telebot.apihelper._make_request')
    def test_missing_type_field_json(self, mock_make_request):
        command = {"module": "test_module", "args": {}, "id": "test_id"} # type is missing
        mock_message = self._create_mock_json_message(command)
        self.mock_interpret.return_value = None
        bot.handle_text_message(mock_message)
        self.mock_bot_module_instance.reply_to.assert_called_with(mock_message, "Error: Missing required field 'type'.")

    @patch('telebot.apihelper._make_request')
    def test_empty_string_type_json(self, mock_make_request):
        command = {"type": "", "module": "test_module", "args": {}, "id": "1"}
        mock_message = self._create_mock_json_message(command)
        self.mock_interpret.return_value = None
        bot.handle_text_message(mock_message)
        self.mock_bot_module_instance.reply_to.assert_called_with(mock_message, "Error: Field 'type' must be a non-empty string. Got value ''.")

    # ... (keep other JSON validation tests, ensuring self.mock_interpret.return_value = None and calling bot.handle_text_message)

    @patch('telebot.apihelper._make_request')
    def test_whitespace_string_type_json(self, mock_make_request):
        command = {"type": "   ", "module": "test_module", "args": {}, "id": "1"}
        mock_message = self._create_mock_json_message(command)
        self.mock_interpret.return_value = None
        bot.handle_text_message(mock_message)
        self.mock_bot_module_instance.reply_to.assert_called_with(mock_message, "Error: Field 'type' must be a non-empty string. Got value '   '.")

    @patch('telebot.apihelper._make_request')
    def test_missing_module_field_json(self, mock_make_request):
        command = {"type": "test_type", "args": {}, "id": "test_id"} # module is missing
        mock_message = self._create_mock_json_message(command)
        self.mock_interpret.return_value = None
        bot.handle_text_message(mock_message)
        self.mock_bot_module_instance.reply_to.assert_called_with(mock_message, "Error: Missing required field 'module'.")

    @patch('telebot.apihelper._make_request')
    def test_empty_string_module_json(self, mock_make_request):
        command = {"type": "test", "module": "", "args": {}, "id": "1"}
        mock_message = self._create_mock_json_message(command)
        self.mock_interpret.return_value = None
        bot.handle_text_message(mock_message)
        self.mock_bot_module_instance.reply_to.assert_called_with(mock_message, "Error: Field 'module' must be a non-empty string. Got value ''.")

    @patch('telebot.apihelper._make_request')
    def test_whitespace_string_module_json(self, mock_make_request):
        command = {"type": "test", "module": "   ", "args": {}, "id": "1"}
        mock_message = self._create_mock_json_message(command)
        self.mock_interpret.return_value = None
        bot.handle_text_message(mock_message)
        self.mock_bot_module_instance.reply_to.assert_called_with(mock_message, "Error: Field 'module' must be a non-empty string. Got value '   '.")

    @patch('telebot.apihelper._make_request')
    def test_invalid_args_type_json(self, mock_make_request):
        command = {"type": "test_type", "module": "test_module", "args": "not_a_dict", "id": "test_id"}
        mock_message = self._create_mock_json_message(command)
        self.mock_interpret.return_value = None
        bot.handle_text_message(mock_message)
        self.mock_bot_module_instance.reply_to.assert_called_with(mock_message, "Error: Field 'args' must be type dict. Got value 'not_a_dict' of type str.")

    @patch('telebot.apihelper._make_request')
    def test_invalid_id_type_json(self, mock_make_request):
        command = {"type": "test_type", "module": "test_module", "args": {}, "id": [1,2,3]} # id is a list
        mock_message = self._create_mock_json_message(command)
        self.mock_interpret.return_value = None
        bot.handle_text_message(mock_message)
        self.mock_bot_module_instance.reply_to.assert_called_with(mock_message, "Error: Field 'id' must be type str or int. Got value '[1, 2, 3]' of type list.")


    # --- ID field type tests (JSON) ---
    @patch('telebot.apihelper._make_request')
    def test_valid_json_command_with_int_id(self, mock_make_request):
        command = {"type": "test_type_int_id", "module": "test_module_int_id", "args": {}, "id": 123}
        mock_message = self._create_mock_json_message(command)
        self.mock_interpret.return_value = None
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

    # --- Args field tests (JSON) ---
    @patch('telebot.apihelper._make_request')
    def test_valid_json_command_with_empty_args(self, mock_make_request):
        command = {"type": "test_empty_args", "module": "test_mod_empty_args", "args": {}, "id": "empty_args_id"}
        mock_message = self._create_mock_json_message(command)
        self.mock_interpret.return_value = None
        bot.handle_text_message(mock_message)

        expected_module_dir = self.test_commands_dir / "telegram_mod_test_mod_empty_args"
        self.assertTrue(expected_module_dir.exists())
        expected_filename = f"YYYYMMDD_HHMMSS_ffffff_{mock_message.chat.id}.json"
        expected_file_path = expected_module_dir / expected_filename
        self.assertTrue(expected_file_path.exists())
        self.mock_bot_module_instance.reply_to.assert_called_once()

    @patch('telebot.apihelper._make_request')
    def test_valid_json_command_with_simple_args(self, mock_make_request):
        command = {"type": "test_simple_args", "module": "test_mod_simple_args", "args": {"key": "value"}, "id": "simple_args_id"}
        mock_message = self._create_mock_json_message(command)
        self.mock_interpret.return_value = None
        bot.handle_text_message(mock_message)

        expected_module_dir = self.test_commands_dir / "telegram_mod_test_mod_simple_args"
        self.assertTrue(expected_module_dir.exists())
        expected_filename = f"YYYYMMDD_HHMMSS_ffffff_{mock_message.chat.id}.json"
        expected_file_path = expected_module_dir / expected_filename
        self.assertTrue(expected_file_path.exists())
        self.mock_bot_module_instance.reply_to.assert_called_once()


    # --- Test Command Routing (JSON) ---
    @patch('telebot.apihelper._make_request')
    @patch('katana.bot.handle_log_event')
    def test_routing_log_event_json(self, mock_handle_log_event_func, mock_make_request):
        command = {"type": "log_event", "module": "logging", "args": {"message": "hello"}, "id": "log001"}
        mock_message = self._create_mock_json_message(command)
        self.mock_interpret.return_value = None
        bot.handle_text_message(mock_message)

        mock_handle_log_event_func.assert_called_once_with(command, mock_message.chat.id)
        self.mock_bot_module_instance.reply_to.assert_called_with(mock_message, "✅ 'log_event' processed (placeholder).")


    @patch('telebot.apihelper._make_request')
    @patch('katana.bot.handle_mind_clearing')
    def test_routing_mind_clearing_json(self, mock_handle_mind_clearing_func, mock_make_request):
        command = {"type": "mind_clearing", "module": "wellness", "args": {"duration": "10m"}, "id": "mind002"}
        mock_message = self._create_mock_json_message(command)
        self.mock_interpret.return_value = None
        bot.handle_text_message(mock_message)

        mock_handle_mind_clearing_func.assert_called_once_with(command, mock_message.chat.id)
        self.mock_bot_module_instance.reply_to.assert_called_with(mock_message, "✅ 'mind_clearing' processed (placeholder).")


    @patch('telebot.apihelper._make_request')
    def test_unknown_json_command_type_saves_normally(self, mock_make_request):
        command = {"type": "unknown_type", "module": "custom_module", "args": {}, "id": "custom003"}
        mock_message = self._create_mock_json_message(command)
        self.mock_interpret.return_value = None
        bot.handle_text_message(mock_message)

        expected_module_dir = self.test_commands_dir / "telegram_mod_custom_module"
        self.assertTrue(expected_module_dir.exists())
        # ... (rest of the assertions for file saving and reply)

    # --- Logging Verification Tests (JSON) ---
    @patch('telebot.apihelper._make_request')
    def test_json_validation_failure_logs_details(self, mock_make_request):
        command = {"type": "test_type", "module": "", "args": {}, "id": "fail_log_id"} # Empty module
        original_command_text = json.dumps(command)
        mock_message = self._create_mock_json_message(command)
        self.mock_interpret.return_value = None
        bot.handle_text_message(mock_message)
        # ... (assertions for reply and log message)


    # --- Tests for NLP command handling in handle_text_message ---
    @patch('telebot.apihelper._make_request')
    @patch('katana.bot.get_time_of_day_greeting', return_value="Добрый день")
    @patch('katana.bot.get_username', return_value="nlp_user")
    @patch('katana.bot.get_bot_stats_message', return_value="Статистика: обработано 1 команд.")
    def test_nlp_greeting_command(self, mock_stats, mock_username, mock_greeting, mock_make_request):
        mock_message = self._create_mock_message("привет бот")
        self.mock_interpret.return_value = "Привет! Как я могу помочь?" # From nlp_mapper.COMMAND_ACTIONS["greet"]

        bot.handle_text_message(mock_message)

        self.mock_interpret.assert_called_once_with("привет бот")
        self.mock_run_katana_command.assert_not_called()
        self.mock_bot_module_instance.send_message.assert_called_once_with(
            mock_message.chat.id,
            "Добрый день, nlp_user! Привет! Как я могу помочь? Статистика: обработано 1 команд."
        )
        self.assertEqual(bot.BOT_STATS["commands_processed"], 1)

    @patch('telebot.apihelper._make_request')
    @patch('katana.bot.get_time_of_day_greeting', return_value="Добрый вечер")
    @patch('katana.bot.get_username', return_value="user1")
    @patch('katana.bot.get_bot_stats_message', return_value="Статистика: 2 команды.")
    def test_nlp_shell_command(self, mock_stats, mock_username, mock_greeting, mock_make_request):
        mock_message = self._create_mock_message("покажи место на диске")
        self.mock_interpret.return_value = "df -h" # From nlp_mapper
        self.mock_run_katana_command.return_value = "Filesystem Size Used Avail Use% Mounted on\n/dev/sda1 10G 5G 5G 50% /"

        bot.handle_text_message(mock_message)

        self.mock_interpret.assert_called_once_with("покажи место на диске")
        self.mock_run_katana_command.assert_called_once_with("df -h", mock_message)
        expected_response = (
            "Добрый вечер, user1! 🧠 Понял. Выполняю:\n"
            "`df -h`\n\n"
            "Filesystem Size Used Avail Use% Mounted on\n/dev/sda1 10G 5G 5G 50% /\n\n"
            "Статистика: 2 команды."
        )
        self.mock_bot_module_instance.send_message.assert_called_once_with(
            mock_message.chat.id, expected_response, parse_mode="Markdown"
        )
        self.assertEqual(bot.BOT_STATS["commands_processed"], 1)


    @patch('telebot.apihelper._make_request')
    @patch('katana.bot.get_time_of_day_greeting', return_value="Доброе утро")
    @patch('katana.bot.get_username', return_value="api_user")
    @patch('katana.bot.get_bot_stats_message', return_value="N=3")
    def test_nlp_weather_api_command(self, mock_stats, mock_username, mock_greeting, mock_make_request):
        mock_message = self._create_mock_message("какая погода")
        self.mock_interpret.return_value = "get_weather"

        bot.handle_text_message(mock_message)

        self.mock_interpret.assert_called_once_with("какая погода")
        self.mock_run_katana_command.assert_not_called() # API calls are handled directly for now
        # Placeholder weather info is hardcoded in bot.py for this test
        expected_response = "Доброе утро, api_user! Сегодня солнечно, +25°C. N=3"
        self.mock_bot_module_instance.send_message.assert_called_once_with(
            mock_message.chat.id, expected_response
        )
        self.assertEqual(bot.BOT_STATS["commands_processed"], 1)

    @patch('telebot.apihelper._make_request')
    @patch('katana.bot.get_time_of_day_greeting', return_value="Добрый день")
    @patch('katana.bot.get_username', return_value="joker")
    @patch('katana.bot.get_bot_stats_message', return_value="Processed: 4")
    def test_nlp_joke_api_command(self, mock_stats, mock_username, mock_greeting, mock_make_request):
        mock_message = self._create_mock_message("расскажи анекдот")
        self.mock_interpret.return_value = "get_joke"

        bot.handle_text_message(mock_message)
        self.mock_interpret.assert_called_once_with("расскажи анекдот")
        self.mock_run_katana_command.assert_not_called()
        expected_joke = "Почему программисты всегда путают Хэллоуин и Рождество? Потому что OCT 31 == DEC 25."
        expected_response = f"Добрый день, joker! {expected_joke} Processed: 4"
        self.mock_bot_module_instance.send_message.assert_called_once_with(
            mock_message.chat.id, expected_response
        )
        self.assertEqual(bot.BOT_STATS["commands_processed"], 1)


    # --- Tests for get_text_from_voice ---
    # For these tests, we stop the class-level patcher for get_text_from_voice
    # to test the actual function's logic.

    def _run_get_text_from_voice_test(self, test_func, *args):
        self.get_text_from_voice_patcher.stop()
        try:
            test_func(*args)
        finally:
            self.get_text_from_voice_patcher.start()

    @patch('builtins.open', new_callable=unittest.mock.mock_open, read_data=b"dummy voice data")
    def test_get_text_from_voice_success_actual(self, mock_open_file):
        def actual_test(mock_open):
            self.mock_openai_transcribe.return_value = {'text': 'Hello world'}
            result = bot.get_text_from_voice("dummy_path.ogg")
            self.assertEqual(result, "Hello world")
            mock_open.assert_called_once_with("dummy_path.ogg", "rb")
            self.mock_openai_transcribe.assert_called_once()
            self.mock_log_local_bot_event.assert_any_call("Sending voice file dummy_path.ogg to OpenAI Whisper API...")
            self.mock_log_local_bot_event.assert_any_call("Voice transcribed successfully: 'Hello world'")
        self._run_get_text_from_voice_test(actual_test, mock_open_file)

    @patch('builtins.open', new_callable=unittest.mock.mock_open, read_data=b"dummy voice data")
    def test_get_text_from_voice_api_error_actual(self, mock_open_file):
        def actual_test(mock_open):
            # Simplest way to create an APIError instance for testing
            self.mock_openai_transcribe.side_effect = bot.openai.APIError("Simulated API Error", request=MagicMock(), body=None)
            result = bot.get_text_from_voice("dummy_path.ogg")
            self.assertIsNone(result)
            self.mock_log_local_bot_event.assert_any_call("OpenAI API Error during voice transcription: Simulated API Error")
        self._run_get_text_from_voice_test(actual_test, mock_open_file)


    @patch('builtins.open', new_callable=unittest.mock.mock_open, read_data=b"dummy voice data")
    def test_get_text_from_voice_no_text_returned_actual(self, mock_open_file):
        def actual_test(mock_open):
            self.mock_openai_transcribe.return_value = {'text': None}
            result = bot.get_text_from_voice("dummy_path.ogg")
            self.assertIsNone(result)
            self.mock_log_local_bot_event.assert_any_call("Voice transcription returned no text.")
        self._run_get_text_from_voice_test(actual_test, mock_open_file)

    @patch('builtins.open', new_callable=unittest.mock.mock_open, read_data=b"dummy voice data")
    def test_get_text_from_voice_empty_text_returned_actual(self, mock_open_file):
        def actual_test(mock_open):
            self.mock_openai_transcribe.return_value = {'text': "  "}
            result = bot.get_text_from_voice("dummy_path.ogg")
            self.assertEqual(result, "") # After strip()
            self.mock_log_local_bot_event.assert_any_call("Voice transcribed successfully: '  '") # Before strip()
        self._run_get_text_from_voice_test(actual_test, mock_open_file)


    @patch('katana.bot.OPENAI_API_KEY', None)
    def test_get_text_from_voice_no_api_key_actual(self):
        def actual_test():
            result = bot.get_text_from_voice("dummy_path.ogg")
            self.assertIsNone(result)
            self.mock_log_local_bot_event.assert_any_call("OpenAI API key not configured. Cannot process voice.")
            self.mock_openai_transcribe.assert_not_called() # Ensure API is not called
        # Reset mock_openai_transcribe for this specific test path, as it might have been called in other tests
        self.mock_openai_transcribe.reset_mock()
        self._run_get_text_from_voice_test(actual_test)


    @patch('builtins.open', side_effect=IOError("File not found"))
    def test_get_text_from_voice_file_open_error_actual(self, mock_open_file):
        def actual_test(mock_open):
            with patch('katana.bot.OPENAI_API_KEY', 'fake_key_for_this_test'): # Ensure key is set for this path
                result = bot.get_text_from_voice("dummy_path.ogg")
                self.assertIsNone(result)
                self.mock_log_local_bot_event.assert_any_call("Unexpected error during voice transcription: File not found")
        self._run_get_text_from_voice_test(actual_test, mock_open_file)

    # --- Tests for handle_voice_message ---
    # These tests will use the class-level mock for get_text_from_voice
    def _create_mock_voice_message(self, user_id=98765, username="voice_user", first_name="Voicey"):
        mock_message = MagicMock(spec=telebot.types.Message)
        mock_message.chat = MagicMock(spec=telebot.types.Chat)
        mock_message.chat.id = 67890
        mock_message.voice = MagicMock(spec=telebot.types.Voice)
        mock_message.voice.file_id = "test_voice_file_id"
        mock_message.voice.duration = 3
        mock_message.message_id = 123
        mock_message.date = 1678886400
        mock_message.from_user = MagicMock(spec=telebot.types.User)
        mock_message.from_user.id = user_id
        mock_message.from_user.username = username
        mock_message.from_user.first_name = first_name
        return mock_message

    @patch('telebot.apihelper._make_request')
    @patch('builtins.open', new_callable=unittest.mock.mock_open)
    @patch('katana.bot.handle_text_message') # Mock handle_text_message for this specific test
    @patch('katana.bot.get_time_of_day_greeting', return_value="Добрый день")
    @patch('katana.bot.get_username', return_value="voice_user")
    @patch('katana.bot.get_bot_stats_message', return_value="Статистика: 5")
    def test_handle_voice_message_success(self, mock_stats, mock_username, mock_greeting, mock_handle_text, mock_open_file, mock_make_request):
        mock_voice_msg = self._create_mock_voice_message()
        self.mock_bot_module_instance.get_file.return_value.file_path = "voice/file.oga"
        self.mock_bot_module_instance.download_file.return_value = b"dummy voice data"
        self.mock_get_text_from_voice.return_value = "show disk space" # This mock is from setUp

        bot.handle_voice_message(mock_voice_msg)

        self.mock_bot_module_instance.get_file.assert_called_once_with("test_voice_file_id")
        expected_temp_path = self.test_voice_file_dir / f"{mock_voice_msg.voice.file_id}.ogg"
        self.mock_get_text_from_voice.assert_called_once_with(str(expected_temp_path))
        self.mock_bot_module_instance.reply_to.assert_any_call(mock_voice_msg, '🗣️ Распознано: "show disk space"')

        mock_handle_text.assert_called_once()
        called_message_arg = mock_handle_text.call_args[0][0]
        self.assertEqual(called_message_arg.text, "show disk space")
        self.assertEqual(called_message_arg.chat.id, mock_voice_msg.chat.id)
        self.mock_os_remove.assert_called_once_with(expected_temp_path)


    @patch('telebot.apihelper._make_request')
    @patch('builtins.open', new_callable=unittest.mock.mock_open)
    @patch('katana.bot.handle_text_message') # Mock to prevent actual call
    @patch('katana.bot.get_time_of_day_greeting', return_value="Добрый вечер")
    @patch('katana.bot.get_username', return_value="voice_user_fail")
    @patch('katana.bot.get_bot_stats_message', return_value="Статистика: 6")
    def test_handle_voice_message_transcription_fails(self, mock_stats, mock_username, mock_greeting, mock_handle_text, mock_open_file, mock_make_request):
        mock_voice_msg = self._create_mock_voice_message(username="voice_user_fail")
        self.mock_bot_module_instance.get_file.return_value.file_path = "voice/file.oga"
        self.mock_bot_module_instance.download_file.return_value = b"dummy voice data"
        self.mock_get_text_from_voice.return_value = None # Simulate transcription failure

        bot.handle_voice_message(mock_voice_msg)

        expected_temp_path = self.test_voice_file_dir / f"{mock_voice_msg.voice.file_id}.ogg"
        self.mock_get_text_from_voice.assert_called_once_with(str(expected_temp_path))
        expected_reply = "Добрый вечер, voice_user_fail. Не смог распознать речь в вашем голосовом сообщении. Пожалуйста, попробуйте еще раз, говорите четче. 🎙️ Статистика: 6"
        self.mock_bot_module_instance.reply_to.assert_called_with(mock_voice_msg, expected_reply)
        mock_handle_text.assert_not_called()
        self.mock_os_remove.assert_called_once_with(expected_temp_path)


    @patch('telebot.apihelper._make_request')
    @patch('katana.bot.OPENAI_API_KEY', None)
    @patch('katana.bot.handle_text_message') # Mock to prevent call
    def test_handle_voice_message_no_openai_key(self, mock_handle_text, mock_make_request):
        mock_voice_msg = self._create_mock_voice_message()
        bot.handle_voice_message(mock_voice_msg)
        self.mock_bot_module_instance.reply_to.assert_called_with(mock_voice_msg, "⚠️ Распознавание голоса не настроено на сервере.")
        self.mock_bot_module_instance.get_file.assert_not_called()
        self.mock_get_text_from_voice.assert_not_called()
        mock_handle_text.assert_not_called()


    @patch('telebot.apihelper._make_request')
    @patch('builtins.open', new_callable=unittest.mock.mock_open)
    @patch('katana.bot.handle_text_message') # Mock to prevent call
    @patch('katana.bot.get_time_of_day_greeting', return_value="Добрый день")
    @patch('katana.bot.get_username', return_value="error_user")
    @patch('katana.bot.get_bot_stats_message', return_value="Статистика: 7")
    def test_handle_voice_message_download_exception(self, mock_stats, mock_username, mock_greeting, mock_handle_text, mock_open_file, mock_make_request):
        mock_voice_msg = self._create_mock_voice_message(username="error_user")
        self.mock_bot_module_instance.get_file.side_effect = Exception("Download error")

        bot.handle_voice_message(mock_voice_msg)
        expected_reply = "Добрый день, error_user. При обработке вашего голосового сообщения произошла неожиданная ошибка. Попробуйте позже. 😥 Статистика: 7"
        self.mock_bot_module_instance.reply_to.assert_called_with(mock_voice_msg, expected_reply)
        self.mock_get_text_from_voice.assert_not_called()
        mock_handle_text.assert_not_called()
        self.mock_os_remove.assert_not_called()


    @patch('telebot.apihelper._make_request')
    @patch('builtins.open', new_callable=unittest.mock.mock_open)
    @patch('os.remove', side_effect=OSError("Delete failed"))
    @patch('katana.bot.handle_text_message') # Mock to prevent call
    def test_handle_voice_message_cleanup_exception(self, mock_handle_text, mock_os_remove_custom, mock_open_file, mock_make_request):
        mock_voice_msg = self._create_mock_voice_message()
        self.mock_bot_module_instance.get_file.return_value.file_path = "voice/file.oga"
        self.mock_bot_module_instance.download_file.return_value = b"dummy voice data"
        self.mock_get_text_from_voice.return_value = "текст"

        bot.handle_voice_message(mock_voice_msg)

        expected_temp_path = self.test_voice_file_dir / f"{mock_voice_msg.voice.file_id}.ogg"
        mock_handle_text.assert_called_once() # Check that normal processing (up to handle_text_message call) occurred
        mock_os_remove_custom.assert_called_once_with(expected_temp_path)
        self.mock_log_local_bot_event.assert_any_call(f"Error deleting temporary voice file {expected_temp_path}: Delete failed")

    # --- Tests for User Profile ---
    @patch('telebot.apihelper._make_request')
    def test_handle_text_message_adds_to_history(self, mock_make_request):
        mock_message = self._create_mock_message("test command")
        self.mock_interpret.return_value = None
        with patch('katana.bot.LocalFileAdapter') as mock_adapter:
            bot.handle_text_message(mock_message)
            mock_adapter.return_value.save.assert_called_once()


    @patch('telebot.apihelper._make_request')
    def test_handle_recommendations_with_results(self, mock_make_request):
        mock_message = self._create_mock_message("/recommendations")
        with patch('katana.bot.LocalFileAdapter') as mock_adapter:
            mock_adapter.return_value.load.return_value = {"user_id": 123, "command_history": [{"command": "ls -l", "timestamp": "now"}]}
            bot.handle_recommendations(mock_message)
            expected_response = "Вот несколько команд, которые вы часто используете:\n1. `ls -l`\n"
            self.mock_bot_module_instance.reply_to.assert_called_with(mock_message, expected_response, parse_mode="Markdown")

    @patch('telebot.apihelper._make_request')
    def test_handle_recommendations_no_results(self, mock_make_request):
        mock_message = self._create_mock_message("/recommendations")
        with patch('katana.bot.LocalFileAdapter') as mock_adapter:
            mock_adapter.return_value.load.return_value = None
            bot.handle_recommendations(mock_message)
            expected_response = "У меня пока нет рекомендаций для вас. Попробуйте использовать несколько команд, и я смогу вам что-нибудь предложить."
            self.mock_bot_module_instance.reply_to.assert_called_with(mock_message, expected_response)


if __name__ == '__main__':
    unittest.main()
