import unittest
from unittest.mock import MagicMock, patch
import json
from pathlib import Path
import shutil
import io
import sys

import bot
from katana.core.contracts.commands import PingCommand, LogEventCommand
from katana.core.logging import logger as bot_logger

class TestBotCerberus(unittest.TestCase):

    def setUp(self):
        # --- Мокирование зависимостей ---
        self.mock_bot_instance = MagicMock()
        self.bot_patcher = patch('bot.bot', self.mock_bot_instance)
        self.mock_bot_module_instance = self.bot_patcher.start()

        # --- Мокирование файловой системы ---
        self.test_commands_dir = Path("test_commands_temp_dir")
        self.test_commands_dir.mkdir(parents=True, exist_ok=True)
        self.original_command_file_dir = bot.COMMAND_FILE_DIR
        bot.COMMAND_FILE_DIR = self.test_commands_dir

        # --- Перехват stdout/stderr для тестирования логов ---
        self.stdout_capture = io.StringIO()
        self.stderr_capture = io.StringIO()
        self.stdout_patcher = patch('sys.stdout', self.stdout_capture)
        self.stderr_patcher = patch('sys.stderr', self.stderr_capture)
        self.stdout_patcher.start()
        self.stderr_patcher.start()

        # --- Мокирование хендлеров ---
        self.ping_handler_patcher = patch('bot.handle_ping')
        self.mock_ping_handler = self.ping_handler_patcher.start()

        self.log_event_handler_patcher = patch('bot.handle_log_event')
        self.mock_log_event_handler = self.log_event_handler_patcher.start()

        self.mind_clearing_handler_patcher = patch('bot.handle_mind_clearing')
        self.mock_mind_clearing_handler = self.mind_clearing_handler_patcher.start()

    def tearDown(self):
        self.bot_patcher.stop()
        self.stdout_patcher.stop()
        self.stderr_patcher.stop()
        self.ping_handler_patcher.stop()
        self.log_event_handler_patcher.stop()
        self.mind_clearing_handler_patcher.stop()

        if self.test_commands_dir.exists():
            shutil.rmtree(self.test_commands_dir)
        bot.COMMAND_FILE_DIR = self.original_command_file_dir

    def _create_mock_message(self, text_payload):
        mock_message = MagicMock()
        mock_message.chat.id = 12345
        mock_message.text = json.dumps(text_payload) if isinstance(text_payload, dict) else text_payload
        return mock_message

    def _get_log_events(self, stream):
        """Извлекает и парсит JSON-логи из перехваченного потока."""
        log_lines = stream.getvalue().strip().split('\n')
        if not log_lines or not log_lines[0]:
            return []
        return [json.loads(line) for line in log_lines]

    def test_valid_ping_command_routes_correctly(self):
        command = {"type": "ping", "module": "system", "id": "test_ping_001", "args": {}}
        mock_message = self._create_mock_message(command)
        self.mock_ping_handler.return_value = "Ping Handled"
        bot.handle_message(mock_message)

        self.mock_ping_handler.assert_called_once()
        args, _ = self.mock_ping_handler.call_args
        self.assertIsInstance(args[0], PingCommand)
        self.assertEqual(args[0].id, "test_ping_001")
        self.mock_bot_module_instance.reply_to.assert_called_with(mock_message, "Ping Handled")

        log_events = self._get_log_events(self.stdout_capture)
        self.assertTrue(any(log['message'] == 'Command validated successfully' and log['command_id'] == 'test_ping_001' for log in log_events))

    def test_valid_log_event_command_routes_correctly(self):
        command = {"type": "log_event", "module": "audit", "id": 123, "args": {"level": "info", "message": "User logged in"}}
        mock_message = self._create_mock_message(command)
        bot.handle_message(mock_message)

        self.mock_log_event_handler.assert_called_once()
        args, _ = self.mock_log_event_handler.call_args
        self.assertIsInstance(args[0], LogEventCommand)
        self.assertEqual(args[0].args.message, "User logged in")
        self.mock_bot_module_instance.reply_to.assert_called_with(mock_message, "✅ 'log_event' processed.")

    def test_invalid_json_format_fails(self):
        mock_message = self._create_mock_message("this is not json")
        bot.handle_message(mock_message)

        self.mock_bot_module_instance.reply_to.assert_called_with(mock_message, "Error: Invalid JSON format.")
        log_events = self._get_log_events(self.stderr_capture)
        self.assertTrue(any(log['message'] == 'Invalid JSON format' and log['extra']['command_text'] == 'this is not json' for log in log_events))

    def test_unknown_command_type_fails(self):
        command = {"type": "non_existent_command", "module": "test", "id": 1}
        mock_message = self._create_mock_message(command)
        bot.handle_message(mock_message)

        self.mock_bot_module_instance.reply_to.assert_called_with(mock_message, "Error: Unknown command type 'non_existent_command'.")
        log_events = self._get_log_events(self.stderr_capture)
        self.assertTrue(any(log['message'] == 'Unknown command type' and log['command_type'] == 'non_existent_command' for log in log_events))

    def test_missing_required_field_fails(self):
        command = {"type": "ping", "module": "system", "args": {}}
        mock_message = self._create_mock_message(command)
        bot.handle_message(mock_message)

        self.mock_bot_module_instance.reply_to.assert_called_once()
        reply_arg = self.mock_bot_module_instance.reply_to.call_args[0][1]
        self.assertIn("Validation Error", reply_arg)
        self.assertIn("- id: Field required", reply_arg)

        log_events = self._get_log_events(self.stderr_capture)
        self.assertTrue(any(log['message'] == 'Command validation failed' and log['command_type'] == 'ping' for log in log_events))

    def test_invalid_arg_type_fails(self):
        command = {"type": "log_event", "module": "audit", "id": 456, "args": {"level": 123, "message": "A message"}}
        mock_message = self._create_mock_message(command)
        bot.handle_message(mock_message)

        self.mock_bot_module_instance.reply_to.assert_called_once()
        reply_arg = self.mock_bot_module_instance.reply_to.call_args[0][1]
        self.assertIn("Validation Error", reply_arg)
        # Проверяем обновленный, более точный формат ошибки
        self.assertIn("- args -> level: Input should be a valid string", reply_arg)

    def test_missing_required_arg_fails(self):
        command = {"type": "log_event", "module": "audit", "id": 789, "args": {"level": "warning"}}
        mock_message = self._create_mock_message(command)
        bot.handle_message(mock_message)

        self.mock_bot_module_instance.reply_to.assert_called_once()
        reply_arg = self.mock_bot_module_instance.reply_to.call_args[0][1]
        self.assertIn("Validation Error", reply_arg)
        # Проверяем обновленный, более точный формат ошибки
        self.assertIn("- args -> message: Field required", reply_arg)


if __name__ == '__main__':
    unittest.main(argv=['first-arg-is-ignored'], exit=False)
