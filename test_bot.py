import unittest
from unittest.mock import MagicMock, patch, call
import json
from pathlib import Path
import shutil # For robust directory removal
from datetime import datetime as dt, timezone as tz, timedelta as td # Import for test setup

# Assuming bot.py is in the same directory or accessible in PYTHONPATH
import bot

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

        # Mock datetime related functions and objects
        # Use our own imported versions for constructing test times
        self.current_test_time = dt(2024, 1, 1, 12, 0, 0, tzinfo=tz.utc)
        self.real_timedelta = td # To be used for advancing time

        # Patch bot.get_utc_now directly as it's the single source of truth for "now" in the bot code
        self.mock_get_utc_now_patcher = patch('bot.get_utc_now')
        self.mock_get_utc_now = self.mock_get_utc_now_patcher.start()
        self.mock_get_utc_now.return_value = self.current_test_time

        # Patch log_local_bot_event
        self.mock_log_event_patcher = patch('bot.log_local_bot_event')
        self.mock_log_local_bot_event = self.mock_log_event_patcher.start()

        # Reset cache and related states for each test
        bot.CACHE.clear()
        bot.CACHE_STATS["hits"] = 0
        bot.CACHE_STATS["misses"] = 0

        # Mock BOT_START_TIME using the controlled time from get_utc_now mock
        # Important: BOT_START_TIME is set at module load time in bot.py.
        # To control it in tests, we must patch it *before* bot.py might be fully imported by test discovery
        # or ensure its value is derived from our mockable get_utc_now().
        # Since BOT_START_TIME = get_utc_now() is at module level, our mock of get_utc_now()
        # should be active when bot module is effectively loaded by the test runner, or we patch BOT_START_TIME itself.
        # For safety, explicitly patch BOT_START_TIME.
        self.mock_bot_start_time_patcher = patch('bot.BOT_START_TIME', self.current_test_time)
        self.mock_bot_start_time_patcher.start()


    def tearDown(self):
        # Stop patchers in reverse order of starting
        self.mock_bot_start_time_patcher.stop()
        self.mock_log_event_patcher.stop()
        self.mock_get_utc_now_patcher.stop()
        self.bot_patcher.stop()

        # Clean up: remove dummy directory and its contents
        if self.test_commands_dir.exists():
            shutil.rmtree(self.test_commands_dir) # shutil.rmtree is more robust for non-empty dirs

        # Restore original
        bot.COMMAND_FILE_DIR = self.original_command_file_dir

    def _create_mock_text_message(self, text_content):
        """Helper to create a mock message for text content (non-JSON)."""
        mock_message = MagicMock()
        mock_message.chat.id = 12345
        mock_message.text = text_content
        return mock_message

    def _create_mock_json_message(self, json_payload):
        """Helper to create a mock message for JSON content."""
        mock_message = MagicMock()
        mock_message.chat.id = 12345
        mock_message.text = json.dumps(json_payload)
        return mock_message

    # --- Test Command Validation (adapted for handle_text_message) ---
    def test_valid_json_command_gets_saved(self):
        command = {"type": "test_type", "module": "test_module", "args": {}, "id": "test_id"}
        mock_message = self._create_mock_json_message(command)

        # Assuming 'interpret' returns None for JSON strings
        with patch('bot.interpret', return_value=None):
            bot.handle_text_message(mock_message)

        # Check file creation
        expected_module_dir = self.test_commands_dir / "telegram_mod_test_module"
        self.assertTrue(expected_module_dir.exists())

        # Filename uses timestamp from the mocked get_utc_now()
        expected_timestamp_str = self.current_test_time.strftime('%Y%m%d_%H%M%S_%f')
        expected_filename = f"{expected_timestamp_str}_{mock_message.chat.id}.json"
        expected_file_path = expected_module_dir / expected_filename
        self.assertTrue(expected_file_path.exists(), msg=f"Expected file {expected_file_path} was not found.")

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
            if f"Successfully validated JSON command from {mock_message.chat.id}: {json.dumps(command)}" in args[0]:
                found_log = True
                break
        self.assertTrue(found_log, "Expected log for successful JSON validation with full command data was not found.")

    def test_invalid_json_string_format(self):
        mock_message = self._create_mock_text_message("not a valid json { definitely not json")
        with patch('bot.interpret', return_value=None): # Not an NLP command
            bot.handle_text_message(mock_message)

        args, _ = self.mock_bot_module_instance.reply_to.call_args
        self.assertEqual(args[0], mock_message)
        self.assertIn("Не понял команду.", args[1])
        self.assertIn("/help", args[1])


    def test_missing_type_field_in_json(self):
        command = {"module": "test_module", "args": {}, "id": "test_id"} # type is missing
        mock_message = self._create_mock_json_message(command)
        with patch('bot.interpret', return_value=None):
            bot.handle_text_message(mock_message)
        self.mock_bot_module_instance.reply_to.assert_called_with(mock_message, "Ошибка валидации JSON: Отсутствует обязательное поле 'type'.")

    def test_empty_string_type_in_json(self):
        command = {"type": "", "module": "test_module", "args": {}, "id": "1"}
        mock_message = self._create_mock_json_message(command)
        with patch('bot.interpret', return_value=None):
            bot.handle_text_message(mock_message)
        self.mock_bot_module_instance.reply_to.assert_called_with(mock_message, "Ошибка валидации JSON: Поле 'type' не должно быть пустым. Получено значение ''.")

    def test_whitespace_string_type_in_json(self):
        command = {"type": "   ", "module": "test_module", "args": {}, "id": "1"}
        mock_message = self._create_mock_json_message(command)
        with patch('bot.interpret', return_value=None):
            bot.handle_text_message(mock_message)
        self.mock_bot_module_instance.reply_to.assert_called_with(mock_message, "Ошибка валидации JSON: Поле 'type' не должно быть пустым. Получено значение '   '.")


    def test_missing_module_field_in_json(self):
        command = {"type": "test_type", "args": {}, "id": "test_id"} # module is missing
        mock_message = self._create_mock_json_message(command)
        with patch('bot.interpret', return_value=None):
            bot.handle_text_message(mock_message)
        self.mock_bot_module_instance.reply_to.assert_called_with(mock_message, "Ошибка валидации JSON: Отсутствует обязательное поле 'module'.")

    def test_empty_string_module_in_json(self):
        command = {"type": "test", "module": "", "args": {}, "id": "1"}
        mock_message = self._create_mock_json_message(command)
        with patch('bot.interpret', return_value=None):
            bot.handle_text_message(mock_message)
        self.mock_bot_module_instance.reply_to.assert_called_with(mock_message, "Ошибка валидации JSON: Поле 'module' не должно быть пустым. Получено значение ''.")

    def test_whitespace_string_module_in_json(self):
        command = {"type": "test", "module": "   ", "args": {}, "id": "1"}
        mock_message = self._create_mock_json_message(command)
        with patch('bot.interpret', return_value=None):
            bot.handle_text_message(mock_message)
        self.mock_bot_module_instance.reply_to.assert_called_with(mock_message, "Ошибка валидации JSON: Поле 'module' не должно быть пустым. Получено значение '   '.")

    def test_invalid_args_type_in_json(self):
        command = {"type": "test_type", "module": "test_module", "args": "not_a_dict", "id": "test_id"}
        mock_message = self._create_mock_json_message(command)
        with patch('bot.interpret', return_value=None):
            bot.handle_text_message(mock_message)
        self.mock_bot_module_instance.reply_to.assert_called_with(mock_message, "Ошибка валидации JSON: Поле 'args' должно быть типа dict. Получено значение 'not_a_dict' типа str.")

    def test_invalid_id_type_in_json(self):
        command = {"type": "test_type", "module": "test_module", "args": {}, "id": [1,2,3]} # id is a list
        mock_message = self._create_mock_json_message(command)
        with patch('bot.interpret', return_value=None):
            bot.handle_text_message(mock_message)
        self.mock_bot_module_instance.reply_to.assert_called_with(mock_message, "Ошибка валидации JSON: Поле 'id' должно быть типа str или int. Получено значение '[1, 2, 3]' типа list.")

    # --- ID field type tests (JSON) ---
    def test_valid_json_command_with_int_id(self):
        command = {"type": "test_type_int_id", "module": "test_module_int_id", "args": {}, "id": 123}
        mock_message = self._create_mock_json_message(command)
        with patch('bot.interpret', return_value=None):
            bot.handle_text_message(mock_message)

        # ... (file saving checks remain the same)
        expected_module_dir = self.test_commands_dir / "telegram_mod_test_module_int_id"
        self.assertTrue(expected_module_dir.exists())
        # ...

        # Check logging for successfully validated command
        found_log = False
        for call_arg in self.mock_log_local_bot_event.call_args_list:
            args, _ = call_arg
            if f"Successfully validated JSON command from {mock_message.chat.id}: {json.dumps(command)}" in args[0]:
                found_log = True
                break
        self.assertTrue(found_log, "Expected log for successful JSON validation with int id was not found.")


    # --- Args field tests (JSON) ---
    def test_valid_json_command_with_empty_args(self):
        command = {"type": "test_empty_args", "module": "test_mod_empty_args", "args": {}, "id": "empty_args_id"}
        mock_message = self._create_mock_json_message(command)
        with patch('bot.interpret', return_value=None):
            bot.handle_text_message(mock_message)
        # ... (file saving checks remain the same)
        self.mock_bot_module_instance.reply_to.assert_called_once()


    def test_valid_json_command_with_simple_args(self):
        command = {"type": "test_simple_args", "module": "test_mod_simple_args", "args": {"key": "value"}, "id": "simple_args_id"}
        mock_message = self._create_mock_json_message(command)
        with patch('bot.interpret', return_value=None):
            bot.handle_text_message(mock_message)
        # ... (file saving checks remain the same)
        self.mock_bot_module_instance.reply_to.assert_called_once()


    # --- Test Command Routing (JSON) ---
    @patch('bot.handle_log_event')
    def test_routing_log_event_json(self, mock_handle_log_event_func):
        command = {"type": "log_event", "module": "logging", "args": {"message": "hello"}, "id": "log001"}
        mock_message = self._create_mock_json_message(command)
        with patch('bot.interpret', return_value=None):
            bot.handle_text_message(mock_message)
        mock_handle_log_event_func.assert_called_once_with(command, mock_message.chat.id)
        self.mock_bot_module_instance.reply_to.assert_called_with(mock_message, "✅ 'log_event' processed (placeholder).")

    @patch('bot.handle_mind_clearing')
    def test_routing_mind_clearing_json(self, mock_handle_mind_clearing_func):
        command = {"type": "mind_clearing", "module": "wellness", "args": {"duration": "10m"}, "id": "mind002"}
        mock_message = self._create_mock_json_message(command)
        with patch('bot.interpret', return_value=None):
            bot.handle_text_message(mock_message)
        mock_handle_mind_clearing_func.assert_called_once_with(command, mock_message.chat.id)
        self.mock_bot_module_instance.reply_to.assert_called_with(mock_message, "✅ 'mind_clearing' processed (placeholder).")

    def test_unknown_json_command_type_saves_normally(self):
        command = {"type": "unknown_type", "module": "custom_module", "args": {}, "id": "custom003"}
        mock_message = self._create_mock_json_message(command)
        with patch('bot.interpret', return_value=None):
            bot.handle_text_message(mock_message)
        # ... (file saving checks remain the same)
        self.assertTrue((self.test_commands_dir / "telegram_mod_custom_module").exists())
        # ...

    # --- Logging Verification Tests (JSON) ---
    def test_json_validation_failure_logs_details(self):
        command = {"type": "test_type", "module": "", "args": {}, "id": "fail_log_id"} # Empty module
        original_command_text = json.dumps(command)
        mock_message = self._create_mock_json_message(command)
        with patch('bot.interpret', return_value=None):
            bot.handle_text_message(mock_message)
        self.mock_bot_module_instance.reply_to.assert_called_with(mock_message, "Ошибка валидации JSON: Поле 'module' не должно быть пустым. Получено значение ''.")

        found_log = False
        # Check that the original text (command_text_for_logging) is in the log
        expected_log_part = "Ошибка валидации JSON: Поле 'module' не должно быть пустым."
        expected_command_part = f"(Command: {original_command_text})" # original_command_text comes from the mock_message.text

        for call_arg in self.mock_log_local_bot_event.call_args_list:
            args, _ = call_arg
            log_message = args[0]
            if expected_log_part in log_message and expected_command_part in log_message:
                found_log = True
                break
        self.assertTrue(found_log, f"Expected log with JSON validation failure details was not found.")

    # --- New Test Cases for Recent Features ---

    def test_unrecognized_text_command_reply(self):
        """Test reply for a text command not recognized by NLP and not JSON."""
        mock_message = self._create_mock_text_message("абвгд не команда")
        with patch('bot.interpret', return_value=None): # NLP does not understand
            bot.handle_text_message(mock_message)

        args, _ = self.mock_bot_module_instance.reply_to.call_args
        self.assertEqual(args[0], mock_message)
        self.assertIn("🤖 Не понял команду.", args[1])
        self.assertIn("принимать команды в формате JSON", args[1]) # Check for part of the new detailed message
        self.assertIn("/help", args[1])

    @patch('bot.run_katana_command')
    @patch('bot.interpret')
    def test_nlp_command_error_feedback(self, mock_interpret, mock_run_katana):
        """Test that errors from run_katana_command for NLP commands are relayed."""
        nlp_input_text = "что-то пошло не так"
        interpreted_command = "error_command"
        error_output = "Произошла ошибка выполнения команды: команда не найдена"

        mock_interpret.return_value = interpreted_command
        mock_run_katana.return_value = error_output

        mock_message = self._create_mock_text_message(nlp_input_text)
        bot.handle_text_message(mock_message)

        mock_interpret.assert_called_once_with(nlp_input_text)
        mock_run_katana.assert_called_once_with(interpreted_command)

        # Check that bot.send_message was called (not reply_to for NLP)
        args, kwargs = self.mock_bot_module_instance.send_message.call_args
        self.assertEqual(args[0], mock_message.chat.id)
        self.assertIn(interpreted_command, args[1])
        self.assertIn(error_output, args[1])
        self.assertEqual(kwargs.get('parse_mode'), "Markdown")

    @patch('bot.run_katana_command')
    @patch('bot.interpret')
    def test_nlp_command_caching(self, mock_interpret, mock_run_katana):
        """Test caching mechanism for NLP commands, including adaptive TTL."""
        # Using 'uptime' which has a specific TTL of 30s in COMMAND_TTLS
        nlp_input_text = "покажи аптайм"
        interpreted_command = "uptime"
        first_output = "10 days, 02:30:00"
        command_specific_ttl = bot.COMMAND_TTLS.get(interpreted_command, bot.DEFAULT_CACHE_TTL_SECONDS)
        self.assertEqual(command_specific_ttl, 30, "TTL for 'uptime' should be 30s for this test")

        mock_interpret.return_value = interpreted_command
        mock_run_katana.return_value = first_output

        mock_message = self._create_mock_text_message(nlp_input_text)

        # First call - should execute and cache
        bot.handle_text_message(mock_message)
        mock_run_katana.assert_called_once_with(interpreted_command)
        args, _ = self.mock_bot_module_instance.send_message.call_args
        self.assertIn(first_output, args[1])
        self.assertNotIn("(из кеша)", args[1])
        self.assertEqual(bot.CACHE_STATS["misses"], 1)
        self.assertEqual(bot.CACHE_STATS["hits"], 0)

        # Second call - should hit cache
        mock_run_katana.reset_mock() # Reset call count for run_katana
        self.mock_bot_module_instance.send_message.reset_mock()

        bot.handle_text_message(mock_message)
        mock_run_katana.assert_not_called() # Should not run command again
        args, _ = self.mock_bot_module_instance.send_message.call_args
        self.assertIn(first_output, args[1]) # Still same output
        self.assertIn("(из кеша)", args[1])  # Indicates cache hit in message
        self.assertEqual(bot.CACHE_STATS["misses"], 1)
        self.assertEqual(bot.CACHE_STATS["hits"], 1)

        # Test cache expiry
        # Advance time beyond the command_specific_ttl
        future_time = self.current_test_time + self.real_timedelta(seconds=command_specific_ttl + 5)

        # Change what bot.get_utc_now() will return for the next part of the test
        self.mock_get_utc_now.return_value = future_time

        mock_run_katana.reset_mock()
        self.mock_bot_module_instance.send_message.reset_mock()
        new_output = "10 days, 02:31:05" # Simulate command output changing
        mock_run_katana.return_value = new_output

        bot.handle_text_message(mock_message) # This call will use future_time via get_utc_now()
        mock_run_katana.assert_called_once_with(interpreted_command) # Called again due to expiry
        args, _ = self.mock_bot_module_instance.send_message.call_args
        self.assertIn(new_output, args[1])
        self.assertNotIn("(из кеша)", args[1])
        self.assertEqual(bot.CACHE_STATS["misses"], 2) # One more miss
        self.assertEqual(bot.CACHE_STATS["hits"], 1)

        # Restore mock_get_utc_now to its initial test time for subsequent tests (if any within the same class instance, though unittest typically isolates)
        self.mock_get_utc_now.return_value = self.current_test_time

    # --- Tests for specific new cacheable NLP commands ---

    def _test_cacheable_nlp_command(self, nlp_input, expected_command, initial_output, cached_output_check_str="(из кеша)"):
        """Helper function to test a cacheable NLP command."""
        with patch('bot.interpret', wraps=bot.interpret) as mock_interpret_spy, \
             patch('bot.run_katana_command') as mock_run_katana:

            mock_run_katana.return_value = initial_output
            mock_message = self._create_mock_text_message(nlp_input)

            # First call: should execute, cache, and increment misses
            bot.handle_text_message(mock_message)
            mock_interpret_spy.assert_called_with(nlp_input)
            # We check the *result* of interpret inside the main logic, so here we ensure run_katana_command got the expected one.
            mock_run_katana.assert_called_once_with(expected_command)

            args, _ = self.mock_bot_module_instance.send_message.call_args
            self.assertIn(initial_output, args[1])
            self.assertNotIn(cached_output_check_str, args[1])
            original_misses = bot.CACHE_STATS["misses"]
            original_hits = bot.CACHE_STATS["hits"]

            # Second call: should hit cache, not execute, and increment hits
            mock_run_katana.reset_mock()
            self.mock_bot_module_instance.send_message.reset_mock()

            bot.handle_text_message(mock_message)
            mock_run_katana.assert_not_called() # Should not run command again
            args, _ = self.mock_bot_module_instance.send_message.call_args
            self.assertIn(initial_output, args[1]) # Still same output
            self.assertIn(cached_output_check_str, args[1])

            # Check specific stats if needed, or rely on the main caching test for detailed stat checks
            self.assertEqual(bot.CACHE_STATS["misses"], original_misses) # Misses should not change
            self.assertEqual(bot.CACHE_STATS["hits"], original_hits + 1) # Hits should increment

    def test_nlp_uptime_p_cached(self):
        self._test_cacheable_nlp_command("дай аптайм подробно", "uptime -p", "up 2 hours, 5 minutes")

    def test_nlp_free_m_cached(self):
        self._test_cacheable_nlp_command("сколько памяти", "free -m", "total used free\nMem: 1024 512 512")

    def test_nlp_whoami_cached(self):
        self._test_cacheable_nlp_command("кто я такой", "whoami", "testuser")

    def test_nlp_date_cached(self):
        # For 'date', the output changes each second. If TTL is very short (e.g., 1s),
        # it's harder to test cache hit reliably without advancing time by less than TTL.
        # Assuming 60s default TTL for now, it will cache.
        self._test_cacheable_nlp_command("какое сегодня число", "date", "Mon Jan  1 12:00:00 UTC 2024")


    @patch('bot.get_help_message')
    def test_start_command(self, mock_get_help):
        """Test /start command."""
        expected_help_text = "Welcome to the bot! Help is here."
        mock_get_help.return_value = expected_help_text
        mock_message = self._create_mock_text_message("/start") # Actual handler uses commands=['start']

        bot.send_welcome(mock_message) # Call the handler directly

        mock_get_help.assert_called_once()
        self.mock_bot_module_instance.reply_to.assert_called_once_with(mock_message, expected_help_text, parse_mode="Markdown")

    @patch('bot.get_help_message')
    def test_help_command(self, mock_get_help):
        """Test /help command."""
        expected_help_text = "Help is available."
        mock_get_help.return_value = expected_help_text
        mock_message = self._create_mock_text_message("/help")

        bot.send_help(mock_message) # Call the handler directly

        mock_get_help.assert_called_once()
        self.mock_bot_module_instance.reply_to.assert_called_once_with(mock_message, expected_help_text, parse_mode="Markdown")

    def test_status_command(self):
        """Test /status command reply content."""
        # Setup some cache activity
        # self.mock_get_utc_now() returns self.current_test_time by default in setUp
        bot.CACHE["uptime"] = {'output': 'some uptime', 'timestamp': self.mock_get_utc_now()}
        bot.CACHE_STATS["hits"] = 5
        bot.CACHE_STATS["misses"] = 2

        mock_message = self._create_mock_text_message("/status")
        bot.send_status(mock_message) # Call directly

        args, kwargs = self.mock_bot_module_instance.reply_to.call_args
        self.assertEqual(args[0], mock_message)
        reply_text = args[1]

        self.assertIn("Статус Бота", reply_text)
        self.assertIn("Время работы:", reply_text)
        self.assertIn("Кеш:", reply_text)
        self.assertIn(f"Стандартный TTL: {bot.DEFAULT_CACHE_TTL_SECONDS} секунд", reply_text)
        self.assertIn("Активных записей в кеше:", reply_text) # Check count if specific logic is complex
        self.assertIn(f"Попаданий в кеш: {bot.CACHE_STATS['hits']}", reply_text)
        self.assertIn(f"Промахов кеша: {bot.CACHE_STATS['misses']}", reply_text)
        self.assertEqual(kwargs.get('parse_mode'), "Markdown")


if __name__ == '__main__':
    unittest.main()
