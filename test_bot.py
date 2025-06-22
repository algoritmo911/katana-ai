import unittest
from unittest.mock import MagicMock, patch, call
import json
from pathlib import Path
import shutil # For robust directory removal

# Assuming bot.py is in the same directory or accessible in PYTHONPATH
import bot

class TestBot(unittest.TestCase):

    def setUp(self):
        self.test_commands_dir = Path("test_commands_temp_dir")
        self.test_commands_dir.mkdir(parents=True, exist_ok=True)
        self.original_command_file_dir = bot.COMMAND_FILE_DIR
        bot.COMMAND_FILE_DIR = self.test_commands_dir

        # Mock the telebot.TeleBot instance used by bot.py
        self.mock_telebot_instance = MagicMock()
        self.telebot_patcher = patch('bot.bot', self.mock_telebot_instance)
        self.mock_telebot_instance_in_module = self.telebot_patcher.start()

        self.mock_datetime_patcher = patch('bot.datetime')
        self.mock_datetime = self.mock_datetime_patcher.start()
        self.mock_datetime.utcnow.return_value.strftime.return_value = "YYYYMMDD_HHMMSS_ffffff"

        self.mock_log_event_patcher = patch('bot.log_local_bot_event')
        self.mock_log_local_bot_event = self.mock_log_event_patcher.start()

        # Patch nlp_mapper.interpret used in bot.py
        self.mock_interpret_patcher = patch('bot.interpret')
        self.mock_interpret = self.mock_interpret_patcher.start()

        # Patch run_katana_command used in bot.py
        self.mock_run_katana_patcher = patch('bot.run_katana_command')
        self.mock_run_katana_command = self.mock_run_katana_patcher.start()

    def tearDown(self):
        self.telebot_patcher.stop()
        self.mock_datetime_patcher.stop()
        self.mock_log_event_patcher.stop()
        self.mock_interpret_patcher.stop()
        self.mock_run_katana_patcher.stop()

        if self.test_commands_dir.exists():
            shutil.rmtree(self.test_commands_dir)
        bot.COMMAND_FILE_DIR = self.original_command_file_dir

    def _create_mock_message(self, text_content, chat_id=12345):
        """Creates a mock message object."""
        mock_message = MagicMock()
        mock_message.chat.id = chat_id
        mock_message.text = text_content
        return mock_message

    # --- Test JSON Command Processing (NLP fails/returns None) ---
    def test_valid_json_command_gets_saved_when_nlp_fails(self):
        self.mock_interpret.return_value = None # NLP part fails or does not find a command

        command_payload = {"type": "test_type", "module": "test_module", "args": {}, "id": "test_id"}
        mock_message = self._create_mock_message(json.dumps(command_payload))

        bot.handle_text_message(mock_message)

        self.mock_interpret.assert_called_once_with(json.dumps(command_payload))

        expected_module_dir = self.test_commands_dir / "telegram_mod_test_module"
        self.assertTrue(expected_module_dir.exists())

        expected_filename = f"YYYYMMDD_HHMMSS_ffffff_{mock_message.chat.id}.json"
        expected_file_path = expected_module_dir / expected_filename
        self.assertTrue(expected_file_path.exists())

        with open(expected_file_path, "r") as f:
            saved_data = json.load(f)
        self.assertEqual(saved_data, command_payload)

        # Check reply
        self.mock_telebot_instance_in_module.reply_to.assert_called_once()
        args, kwargs = self.mock_telebot_instance_in_module.reply_to.call_args
        self.assertEqual(args[0], mock_message)
        self.assertTrue(args[1].startswith("✅ JSON-команда получена и сохранена как"))
        self.assertIn(str(expected_file_path), args[1])

        # Check logging for successfully validated command
        found_log = False
        for call_arg in self.mock_log_local_bot_event.call_args_list:
            args_log, _ = call_arg
            if f"Successfully validated command from {mock_message.chat.id}: {json.dumps(command_payload)}" in args_log[0]:
                found_log = True
                break
        self.assertTrue(found_log, "Expected log for successful JSON validation with full command data was not found.")

    def test_invalid_json_format_when_nlp_fails(self):
        self.mock_interpret.return_value = None
        invalid_json_text = "not a valid json"
        mock_message = self._create_mock_message(invalid_json_text, chat_id=123)

        bot.handle_text_message(mock_message)

        self.mock_interpret.assert_called_once_with(invalid_json_text)
        self.mock_telebot_instance_in_module.reply_to.assert_called_with(
            mock_message,
            "🤖 Не понял команду. Попробуй переформулировать или отправь JSON-команду."
        )

    def test_missing_type_field_in_json_when_nlp_fails(self):
        self.mock_interpret.return_value = None
        command_payload = {"module": "test_module", "args": {}, "id": "test_id"} # type is missing
        mock_message = self._create_mock_message(json.dumps(command_payload))
        bot.handle_text_message(mock_message)
        self.mock_telebot_instance_in_module.reply_to.assert_called_with(mock_message, "Ошибка: отсутствует обязательное поле 'type'.")

    def test_empty_string_type_in_json_when_nlp_fails(self):
        self.mock_interpret.return_value = None
        command_payload = {"type": "", "module": "test_module", "args": {}, "id": "1"}
        mock_message = self._create_mock_message(json.dumps(command_payload))
        bot.handle_text_message(mock_message)
        self.mock_telebot_instance_in_module.reply_to.assert_called_with(mock_message, "Ошибка: поле 'type' должно быть непустой строкой. Получено значение ''.")

    def test_whitespace_string_type_in_json_when_nlp_fails(self):
        self.mock_interpret.return_value = None
        command_payload = {"type": "   ", "module": "test_module", "args": {}, "id": "1"}
        mock_message = self._create_mock_message(json.dumps(command_payload))
        bot.handle_text_message(mock_message)
        self.mock_telebot_instance_in_module.reply_to.assert_called_with(mock_message, "Ошибка: поле 'type' должно быть непустой строкой. Получено значение '   '.")

    def test_missing_module_field_in_json_when_nlp_fails(self):
        self.mock_interpret.return_value = None
        command_payload = {"type": "test_type", "args": {}, "id": "test_id"} # module is missing
        mock_message = self._create_mock_message(json.dumps(command_payload))
        bot.handle_text_message(mock_message)
        self.mock_telebot_instance_in_module.reply_to.assert_called_with(mock_message, "Ошибка: отсутствует обязательное поле 'module'.")

    def test_empty_string_module_in_json_when_nlp_fails(self):
        self.mock_interpret.return_value = None
        command_payload = {"type": "test", "module": "", "args": {}, "id": "1"}
        mock_message = self._create_mock_message(json.dumps(command_payload))
        bot.handle_text_message(mock_message)
        self.mock_telebot_instance_in_module.reply_to.assert_called_with(mock_message, "Ошибка: поле 'module' должно быть непустой строкой. Получено значение ''.")

    def test_whitespace_string_module_in_json_when_nlp_fails(self):
        self.mock_interpret.return_value = None
        command_payload = {"type": "test", "module": "   ", "args": {}, "id": "1"}
        mock_message = self._create_mock_message(json.dumps(command_payload))
        bot.handle_text_message(mock_message)
        self.mock_telebot_instance_in_module.reply_to.assert_called_with(mock_message, "Ошибка: поле 'module' должно быть непустой строкой. Получено значение '   '.")

    def test_invalid_args_type_in_json_when_nlp_fails(self):
        self.mock_interpret.return_value = None
        command_payload = {"type": "test_type", "module": "test_module", "args": "not_a_dict", "id": "test_id"}
        mock_message = self._create_mock_message(json.dumps(command_payload))
        bot.handle_text_message(mock_message)
        self.mock_telebot_instance_in_module.reply_to.assert_called_with(mock_message, "Ошибка: поле 'args' должно быть типа dict. Получено значение 'not_a_dict' типа str.")

    def test_invalid_id_type_in_json_when_nlp_fails(self):
        self.mock_interpret.return_value = None
        command_payload = {"type": "test_type", "module": "test_module", "args": {}, "id": [1,2,3]} # id is a list
        mock_message = self._create_mock_message(json.dumps(command_payload))
        bot.handle_text_message(mock_message)
        self.mock_telebot_instance_in_module.reply_to.assert_called_with(mock_message, "Ошибка: поле 'id' должно быть типа str или int. Получено значение '[1, 2, 3]' типа list.")

    # --- ID field type tests (JSON path) ---
    def test_valid_json_command_with_int_id_when_nlp_fails(self):
        self.mock_interpret.return_value = None
        command_payload = {"type": "test_type_int_id", "module": "test_module_int_id", "args": {}, "id": 123}
        mock_message = self._create_mock_message(json.dumps(command_payload))
        bot.handle_text_message(mock_message)

        expected_module_dir = self.test_commands_dir / "telegram_mod_test_module_int_id"
        self.assertTrue(expected_module_dir.exists())
        # ... (rest of file saving checks)
        self.mock_telebot_instance_in_module.reply_to.assert_called_once()
        args, kwargs = self.mock_telebot_instance_in_module.reply_to.call_args
        self.assertTrue(args[1].startswith("✅ JSON-команда получена и сохранена как"))

        # Check logging
        found_log = False
        for call_arg in self.mock_log_local_bot_event.call_args_list:
            args_log, _ = call_arg
            if f"Successfully validated command from {mock_message.chat.id}: {json.dumps(command_payload)}" in args_log[0]:
                found_log = True
                break
        self.assertTrue(found_log, "Expected log for successful JSON validation with int id was not found.")


    # --- Args field tests (JSON path) ---
    def test_valid_json_command_with_empty_args_when_nlp_fails(self):
        self.mock_interpret.return_value = None
        command_payload = {"type": "test_empty_args", "module": "test_mod_empty_args", "args": {}, "id": "empty_args_id"}
        mock_message = self._create_mock_message(json.dumps(command_payload))
        bot.handle_text_message(mock_message)
        # ... (file saving checks)
        self.mock_telebot_instance_in_module.reply_to.assert_called_once()


    def test_valid_json_command_with_simple_args_when_nlp_fails(self):
        self.mock_interpret.return_value = None
        command_payload = {"type": "test_simple_args", "module": "test_mod_simple_args", "args": {"key": "value"}, "id": "simple_args_id"}
        mock_message = self._create_mock_message(json.dumps(command_payload))
        bot.handle_text_message(mock_message)
        # ... (file saving checks)
        self.mock_telebot_instance_in_module.reply_to.assert_called_once()


    # --- Test Command Routing (JSON path) ---
    @patch('bot.handle_log_event')
    def test_routing_log_event_json_when_nlp_fails(self, mock_handle_log_event_func):
        self.mock_interpret.return_value = None
        command_payload = {"type": "log_event", "module": "logging", "args": {"message": "hello"}, "id": "log001"}
        mock_message = self._create_mock_message(json.dumps(command_payload))
        bot.handle_text_message(mock_message)
        mock_handle_log_event_func.assert_called_once_with(command_payload, mock_message.chat.id)
        self.mock_telebot_instance_in_module.reply_to.assert_called_with(mock_message, "✅ Команда 'log_event' обработана (заглушка).")

    @patch('bot.handle_mind_clearing')
    def test_routing_mind_clearing_json_when_nlp_fails(self, mock_handle_mind_clearing_func):
        self.mock_interpret.return_value = None
        command_payload = {"type": "mind_clearing", "module": "wellness", "args": {"duration": "10m"}, "id": "mind002"}
        mock_message = self._create_mock_message(json.dumps(command_payload))
        bot.handle_text_message(mock_message)
        mock_handle_mind_clearing_func.assert_called_once_with(command_payload, mock_message.chat.id)
        self.mock_telebot_instance_in_module.reply_to.assert_called_with(mock_message, "✅ Команда 'mind_clearing' обработана (заглушка).")

    def test_unknown_command_type_saves_normally_json_when_nlp_fails(self):
        self.mock_interpret.return_value = None
        command_payload = {"type": "unknown_type", "module": "custom_module", "args": {}, "id": "custom003"}
        mock_message = self._create_mock_message(json.dumps(command_payload))
        bot.handle_text_message(mock_message)
        # ... (file saving checks)
        # Check reply
        self.mock_telebot_instance_in_module.reply_to.assert_called_once()
        args, kwargs = self.mock_telebot_instance_in_module.reply_to.call_args
        self.assertEqual(args[0], mock_message)
        self.assertTrue(args[1].startswith("✅ JSON-команда получена и сохранена как"))
        # self.assertIn(str(expected_file_path), args[1]) # Need to reconstruct expected_file_path here

    # --- Logging Verification Tests (JSON path) ---
    def test_validation_failure_logs_details_json_when_nlp_fails(self):
        self.mock_interpret.return_value = None
        command_payload = {"type": "test_type", "module": "", "args": {}, "id": "fail_log_id"} # Empty module
        original_command_text_as_json = json.dumps(command_payload)
        mock_message = self._create_mock_message(original_command_text_as_json)
        bot.handle_text_message(mock_message)
        self.mock_telebot_instance_in_module.reply_to.assert_called_with(mock_message, "Ошибка: поле 'module' должно быть непустой строкой. Получено значение ''.")

        # Check logging for validation failure details
        found_log = False
        expected_log_part = "Validation failed for 12345: Ошибка: поле 'module' должно быть непустой строкой. Получено значение ''."
        # In the new code, the log includes the original text, not the parsed command_data as a string
        expected_original_text_part = f"(Original Text: {original_command_text_as_json})"

        for call_arg in self.mock_log_local_bot_event.call_args_list:
            args_log, _ = call_arg
            log_message = args_log[0]
            if expected_log_part in log_message and expected_original_text_part in log_message:
                found_log = True
                break
        self.assertTrue(found_log, f"Expected log with JSON validation failure details was not found. Searched for: '{expected_log_part}' and '{expected_original_text_part}'")

# --- New Tests for NLP Path ---
    def test_nlp_command_successful_execution(self):
        nlp_input_text = "покажи аптайм"
        interpreted_command = "uptime"
        command_output = "system is up for 10 days"
        chat_id = 67890

        self.mock_interpret.return_value = interpreted_command
        self.mock_run_katana_command.return_value = command_output

        mock_message = self._create_mock_message(nlp_input_text, chat_id=chat_id)
        bot.handle_text_message(mock_message)

        self.mock_interpret.assert_called_once_with(nlp_input_text)
        self.mock_run_katana_command.assert_called_once_with(interpreted_command)
        self.mock_telebot_instance_in_module.send_message.assert_called_once_with(
            chat_id,
            f"🧠 Понял. Выполняю:\n`{interpreted_command}`\n\n{command_output}",
            parse_mode="Markdown"
        )
        self.mock_telebot_instance_in_module.reply_to.assert_not_called() # Should not try to reply with JSON errors

    def test_nlp_run_command_successful_execution(self):
        nlp_input_text = "/run ls -l"
        interpreted_command = "ls -l" # Assuming nlp_mapper now passes this through
        command_output = "total 0"
        chat_id = 67890

        self.mock_interpret.return_value = interpreted_command
        self.mock_run_katana_command.return_value = command_output

        mock_message = self._create_mock_message(nlp_input_text, chat_id=chat_id)
        bot.handle_text_message(mock_message)

        self.mock_interpret.assert_called_once_with(nlp_input_text)
        self.mock_run_katana_command.assert_called_once_with(interpreted_command)
        self.mock_telebot_instance_in_module.send_message.assert_called_once_with(
            chat_id,
            f"🧠 Понял. Выполняю:\n`{interpreted_command}`\n\n{command_output}",
            parse_mode="Markdown"
        )

    def test_nlp_command_katana_execution_fails(self):
        nlp_input_text = "сломанная команда"
        interpreted_command = "broken_command"
        error_output = "🚫 Ошибка при выполнении команды 'broken_command':\n`command not found`"
        chat_id = 11223

        self.mock_interpret.return_value = interpreted_command
        self.mock_run_katana_command.return_value = error_output # run_katana_command returns the error string

        mock_message = self._create_mock_message(nlp_input_text, chat_id=chat_id)
        bot.handle_text_message(mock_message)

        self.mock_interpret.assert_called_once_with(nlp_input_text)
        self.mock_run_katana_command.assert_called_once_with(interpreted_command)
        self.mock_telebot_instance_in_module.send_message.assert_called_once_with(
            chat_id,
            f"🧠 Понял. Выполняю:\n`{interpreted_command}`\n\n{error_output}", # Bot sends the error output from run_katana_command
            parse_mode="Markdown"
        )

    def test_unrecognized_command_nlp_and_json_fail(self):
        unrecognized_text = "это точно не команда и не json"
        chat_id = 33445

        self.mock_interpret.return_value = None # NLP fails
        # The text itself is not valid JSON, so json.loads will raise JSONDecodeError

        mock_message = self._create_mock_message(unrecognized_text, chat_id=chat_id)
        bot.handle_text_message(mock_message)

        self.mock_interpret.assert_called_once_with(unrecognized_text)
        self.mock_run_katana_command.assert_not_called() # Should not be called if NLP fails
        self.mock_telebot_instance_in_module.reply_to.assert_called_once_with(
            mock_message,
            "🤖 Не понял команду. Попробуй переформулировать или отправь JSON-команду."
        )
        self.mock_telebot_instance_in_module.send_message.assert_not_called()


if __name__ == '__main__':
    unittest.main()
