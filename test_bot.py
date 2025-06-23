import unittest
from unittest.mock import MagicMock, patch, call
import json
from pathlib import Path
import shutil # For robust directory removal

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

        # Mock datetime to control timestamps in filenames
        self.mock_datetime_patcher = patch('bot.datetime')
        self.mock_datetime = self.mock_datetime_patcher.start()
        self.mock_datetime.utcnow.return_value.strftime.return_value = "YYYYMMDD_HHMMSS_ffffff"

        # Patch log_local_bot_event
        self.mock_log_local_event_patcher = patch('bot.log_local_bot_event')
        self.mock_log_local_bot_event = self.mock_log_local_event_patcher.start()

        # Patch log_telegram_message
        self.mock_log_telegram_message_patcher = patch('bot.log_telegram_message')
        self.mock_log_telegram_message = self.mock_log_telegram_message_patcher.start()


    def tearDown(self):
        # Stop patchers
        self.bot_patcher.stop()
        self.mock_datetime_patcher.stop()
        self.mock_log_local_event_patcher.stop()
        self.mock_log_telegram_message_patcher.stop()

        # Clean up: remove dummy directory and its contents
        if self.test_commands_dir.exists():
            shutil.rmtree(self.test_commands_dir) # shutil.rmtree is more robust for non-empty dirs

        # Restore original
        bot.COMMAND_FILE_DIR = self.original_command_file_dir


    def _create_mock_message(self, text_payload, chat_id=12345, user_id=12345, first_name="TestUser"):
        mock_message = MagicMock()
        mock_message.chat.id = chat_id
        mock_message.from_user.id = user_id
        mock_message.from_user.first_name = first_name
        if isinstance(text_payload, dict):
            mock_message.text = json.dumps(text_payload)
        else:
            mock_message.text = text_payload
        return mock_message

    # --- Test Standard Command Handlers ---
    def test_send_welcome_start_command(self):
        mock_message = self._create_mock_message("/start", first_name="Tester")
        bot.send_welcome(mock_message)
        expected_reply = "Привет, Tester! Я Katana, твой Telegram-помощник. Готов к работе!"
        self.mock_bot_module_instance.reply_to.assert_called_with(mock_message, expected_reply)
        self.mock_log_telegram_message.assert_called_with(f"Incoming: /start from 12345. Outgoing: {expected_reply}")

    def test_send_help_command(self):
        mock_message = self._create_mock_message("/help")
        bot.send_help(mock_message)
        expected_reply = (
            "Доступные команды:\n"
            "/start - Начало работы\n"
            "/help - Эта справка\n"
            "/status - Текущий статус бота\n"
            "/stop - Остановить бота\n\n"
            "Также я понимаю некоторые ключевые слова, например, 'привет', 'помощь', 'стоп'."
        )
        self.mock_bot_module_instance.reply_to.assert_called_with(mock_message, expected_reply)
        self.mock_log_telegram_message.assert_called_with(f"Incoming: /help from 12345. Outgoing: {expected_reply}")

    def test_send_status_command(self):
        mock_message = self._create_mock_message("/status")
        bot.send_status(mock_message)
        expected_reply = "Бот жив и работает!"
        self.mock_bot_module_instance.reply_to.assert_called_with(mock_message, expected_reply)
        self.mock_log_telegram_message.assert_called_with(f"Incoming: /status from 12345. Outgoing: {expected_reply}")

    def test_stop_bot_handler_command(self):
        mock_message = self._create_mock_message("/stop")
        bot.stop_bot_handler(mock_message)
        expected_reply = "Останавливаю работу... До встречи!"
        self.mock_bot_module_instance.reply_to.assert_called_with(mock_message, expected_reply)
        self.mock_log_telegram_message.assert_called_with(f"Incoming: /stop from 12345. Outgoing: {expected_reply}")
        self.mock_log_local_bot_event.assert_any_call("Stopping polling as per /stop command.")
        self.mock_bot_module_instance.stop_polling.assert_called_once()

    # --- Test Text Message Handling (Keywords, NLP, JSON, Echo) ---
    def test_handle_text_keyword_privet(self):
        mock_message = self._create_mock_message("Привет, бот!")
        bot.handle_text_message(mock_message)
        expected_reply = "Привет! Чем могу помочь?"
        self.mock_bot_module_instance.reply_to.assert_called_with(mock_message, expected_reply)
        self.mock_log_telegram_message.assert_any_call(f"Incoming text message from 12345: Привет, бот!")
        self.mock_log_telegram_message.assert_any_call(f"Keyword 'привет' detected. Outgoing: {expected_reply}")

    def test_handle_text_keyword_pomosh(self):
        mock_message = self._create_mock_message("Мне нужна помощь")
        # We need to mock send_help as it's called directly
        with patch('bot.send_help') as mock_send_help_func:
            bot.handle_text_message(mock_message)
            mock_send_help_func.assert_called_once_with(mock_message)
        self.mock_log_telegram_message.assert_any_call(f"Incoming text message from 12345: Мне нужна помощь")

    def test_handle_text_keyword_stop_private_chat(self):
        # user_id == chat_id implies private chat for this basic check
        mock_message = self._create_mock_message("стоп", chat_id=777, user_id=777)
        bot.handle_text_message(mock_message)
        expected_reply = "Понял, останавливаюсь по ключевому слову 'стоп'."
        self.mock_bot_module_instance.reply_to.assert_called_with(mock_message, expected_reply)
        self.mock_log_telegram_message.assert_any_call(f"Incoming text message from 777: стоп")
        self.mock_log_telegram_message.assert_any_call(f"Keyword 'стоп' detected. Outgoing: {expected_reply}")
        self.mock_log_local_bot_event.assert_any_call("Stopping polling due to 'стоп' keyword.")
        self.mock_bot_module_instance.stop_polling.assert_called_once()

    def test_handle_text_keyword_stop_group_chat_ignored(self):
        # user_id != chat_id implies group chat or channel, stop keyword should be ignored
        mock_message = self._create_mock_message("стоп", chat_id=12345, user_id=777) # Different chat and user ID
        # Assuming it falls through to echo or NLP. Let's make it fall to echo.
        with patch('bot.interpret', return_value=None) as mock_interpret:
            bot.handle_text_message(mock_message)
            # It should not call stop_polling or reply with the stop message
            self.mock_bot_module_instance.stop_polling.assert_not_called()
            # It should echo back
            expected_echo_reply = "Ты сказал: стоп"
            self.mock_bot_module_instance.reply_to.assert_called_with(mock_message, expected_echo_reply)


    @patch('bot.interpret', return_value="ls -la")
    @patch('bot.run_katana_command', return_value="files list")
    def test_handle_text_nlp_command(self, mock_run_katana, mock_interpret):
        mock_message = self._create_mock_message("покажи файлы")
        bot.handle_text_message(mock_message)
        expected_reply = "🧠 Понял. Выполняю:\n`ls -la`\n\nfiles list"
        self.mock_bot_module_instance.send_message.assert_called_with(12345, expected_reply, parse_mode="Markdown")
        self.mock_log_telegram_message.assert_any_call(f"Incoming text message from 12345: покажи файлы")
        self.mock_log_telegram_message.assert_any_call(f'[NLU] "покажи файлы" → "ls -la"')
        self.mock_log_telegram_message.assert_any_call(f"Outgoing NLP response: {expected_reply}")

    @patch('bot.interpret', return_value=None) # Ensure NLP does not match
    def test_handle_text_json_command_valid(self, mock_interpret):
        json_command = {"type": "test_json", "module": "json_module", "args": {"data": "value"}, "id": "json1"}
        mock_message = self._create_mock_message(json_command) # _create_mock_message auto-dumps dict to json string

        bot.handle_text_message(mock_message)

        expected_reply_part = "✅ JSON Command received and saved as" # Added checkmark and space
        # Check that reply_to was called and the reply text starts with the expected string
        called_args, called_kwargs = self.mock_bot_module_instance.reply_to.call_args
        self.assertEqual(called_args[0], mock_message)
        self.assertTrue(called_args[1].startswith(expected_reply_part))

        self.mock_log_telegram_message.assert_any_call(f"Incoming text message from 12345: {json.dumps(json_command)}")
        self.mock_log_local_bot_event.assert_any_call(f"Successfully validated JSON command from 12345: {json.dumps(json_command)}")
        # Check that the outgoing message (the reply itself) is also logged
        # We need to capture the actual reply text to check the log
        actual_reply_text = called_args[1]
        self.mock_log_telegram_message.assert_any_call(f"Outgoing JSON command response: {actual_reply_text}")


    @patch('bot.interpret', return_value=None) # Ensure NLP does not match
    def test_handle_text_echo_default(self, mock_interpret):
        mock_message = self._create_mock_message("Это просто текст")
        bot.handle_text_message(mock_message)
        expected_reply = "Ты сказал: Это просто текст"
        self.mock_bot_module_instance.reply_to.assert_called_with(mock_message, expected_reply)
        self.mock_log_telegram_message.assert_any_call(f"Incoming text message from 12345: Это просто текст")
        self.mock_log_telegram_message.assert_any_call(f"Not JSON, NLP, or keyword. Outgoing echo: {expected_reply}")
        self.mock_log_local_bot_event.assert_any_call("Invalid JSON, not NLP, and not a keyword from 12345: Это просто текст")

    def test_unknown_slash_command(self):
        mock_message = self._create_mock_message("/неизвестнаякоманда")
        bot.handle_text_message(mock_message)
        expected_reply = "Неизвестная команда: /неизвестнаякоманда"
        self.mock_bot_module_instance.reply_to.assert_called_with(mock_message, expected_reply)
        self.mock_log_telegram_message.assert_any_call(f"Incoming text message from 12345: /неизвестнаякоманда")
        self.mock_log_telegram_message.assert_any_call(f"Unknown command: /неизвестнаякоманда from 12345. Outgoing: {expected_reply}")


    # --- Test JSON Command Validation (adapted from old tests, now part of handle_text_message) ---
    @patch('bot.interpret', return_value=None)
    def test_json_valid_command_gets_saved(self, mock_interpret):
        command = {"type": "test_type", "module": "test_module", "args": {}, "id": "test_id"}
        mock_message = self._create_mock_message(command) # text is json string

        bot.handle_text_message(mock_message)

        expected_module_dir = self.test_commands_dir / "telegram_mod_test_module"
        self.assertTrue(expected_module_dir.exists())
        expected_filename = f"YYYYMMDD_HHMMSS_ffffff_{mock_message.chat.id}.json"
        expected_file_path = expected_module_dir / expected_filename
        self.assertTrue(expected_file_path.exists())

        with open(expected_file_path, "r") as f:
            saved_data = json.load(f)
        self.assertEqual(saved_data, command)

        self.mock_bot_module_instance.reply_to.assert_called_once()
        args, _ = self.mock_bot_module_instance.reply_to.call_args
        self.assertEqual(args[0], mock_message)
        self.assertTrue(args[1].startswith("✅ JSON Command received and saved as"))
        self.assertIn(str(expected_file_path), args[1])
        self.mock_log_local_bot_event.assert_any_call(f"Successfully validated JSON command from {mock_message.chat.id}: {json.dumps(command)}")
        self.mock_log_telegram_message.assert_any_call(f"Outgoing JSON command response: {args[1]}")


    @patch('bot.interpret', return_value=None)
    def test_json_missing_type_field(self, mock_interpret):
        command = {"module": "test_module", "args": {}, "id": "test_id"}
        mock_message = self._create_mock_message(command)
        bot.handle_text_message(mock_message)
        self.mock_bot_module_instance.reply_to.assert_called_with(mock_message, "Error: Missing required field 'type'.")
        self.mock_log_telegram_message.assert_any_call("Outgoing JSON validation error: Error: Missing required field 'type'.")
        self.mock_log_local_bot_event.assert_any_call(f"Validation failed for {mock_message.chat.id}: Error: Missing required field 'type'. (Command: {json.dumps(command)})")


    # --- Logging Verification Tests (Telegram Log specific) ---
    def test_log_telegram_message_format(self):
        # This test checks if log_telegram_message is called with the correct format.
        # We can trigger this through any handler that uses it, e.g., /status
        mock_message = self._create_mock_message("/status")
        bot.send_status(mock_message) # This calls log_telegram_message

        # Expected log string for /status
        expected_log_entry_content = "Incoming: /status from 12345. Outgoing: Бот жив и работает!"

        # Check that log_telegram_message was called with the expected content
        self.mock_log_telegram_message.assert_called_with(expected_log_entry_content)

    # Example of testing a specific JSON validation error log
    @patch('bot.interpret', return_value=None)
    def test_json_validation_failure_logs_details_correctly(self, mock_interpret):
        command = {"type": "test_type", "module": "", "args": {}, "id": "fail_log_id"} # Empty module
        original_command_text = json.dumps(command)
        mock_message = self._create_mock_message(command)

        bot.handle_text_message(mock_message)

        expected_error_msg = "Error: Field 'module' must be a non-empty string. Got value ''."
        self.mock_bot_module_instance.reply_to.assert_called_with(mock_message, expected_error_msg)

        # Check log_telegram_message for the outgoing error
        self.mock_log_telegram_message.assert_any_call(f"Outgoing JSON validation error: {expected_error_msg}")

        # Check log_local_bot_event for the internal validation failure log
        self.mock_log_local_bot_event.assert_any_call(
            f"Validation failed for {mock_message.chat.id}: {expected_error_msg} (Command: {original_command_text})"
        )


if __name__ == '__main__':
    unittest.main()
