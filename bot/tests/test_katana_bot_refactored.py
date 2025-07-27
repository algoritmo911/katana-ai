import unittest
from unittest.mock import MagicMock, patch, mock_open
import os
import sys
from pathlib import Path
import json

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

os.environ['KATANA_TELEGRAM_TOKEN'] = '123456:ABCDEF'
from bot import katana_bot

class TestKatanaBotRefactored(unittest.TestCase):

    def setUp(self):
        # This setup will run before each test
        self.message = MagicMock()
        self.message.chat.id = 12345
        self.message.text = ""
        self.chat_id_str = str(self.message.chat.id)

        # Mock dependencies
        katana_bot.memory_manager = MagicMock()
        katana_bot.data_fusion = MagicMock()

    @patch('bot.katana_bot.bot')
    def test_handle_start(self, mock_bot):
        self.message.text = "/start"
        katana_bot.handle_start(self.message)

        mock_bot.reply_to.assert_called_once()
        args, kwargs = mock_bot.reply_to.call_args
        self.assertEqual(args[0], self.message)
        self.assertIn("Katana", args[1])

        katana_bot.memory_manager.add_message_to_history.assert_called_once_with(
            self.chat_id_str,
            {"role": katana_bot.MESSAGE_ROLE_ASSISTANT, "content": args[1]}
        )

    @patch('bot.katana_bot.bot')
    def test_natural_language_message_success(self, mock_bot):
        self.message.text = "Hello Katana"
        katana_bot.data_fusion.get_response.return_value = "Hello there!"

        katana_bot.handle_message_impl(self.message)

        katana_bot.memory_manager.get_history.assert_called_once_with(self.chat_id_str)
        katana_bot.data_fusion.get_response.assert_called_once()

        mock_bot.reply_to.assert_called_once_with(self.message, "Hello there!")

        self.assertEqual(katana_bot.memory_manager.add_message_to_history.call_count, 2)

    @patch('bot.katana_bot.bot')
    @patch('bot.katana_bot.logger')
    def test_get_katana_response_exception(self, mock_logger, mock_bot):
        self.message.text = "trigger error"
        katana_bot.data_fusion.get_response.side_effect = Exception("Test error")

        katana_bot.handle_message_impl(self.message)

        mock_logger.error.assert_called()
        mock_bot.reply_to.assert_called_once()

    @patch('bot.katana_bot.bot')
    def test_json_command_mind_clearing(self, mock_bot):
        self.message.text = json.dumps({"type": "mind_clearing", "module": "test", "args": {}, "id": "1"})

        katana_bot.handle_message_impl(self.message)

        katana_bot.memory_manager.clear_history.assert_called_once_with(self.chat_id_str)
        mock_bot.reply_to.assert_called_once()
        args, _ = mock_bot.reply_to.call_args
        self.assertIn("Контекст диалога очищен", args[1])

    @patch('builtins.open', new_callable=mock_open)
    @patch('json.dump')
    @patch('bot.katana_bot.Path.mkdir')
    @patch('bot.katana_bot.bot')
    def test_json_command_generic_save(self, mock_bot, mock_mkdir, mock_json_dump, mock_file_open):
        command = {"type": "generic_command", "module": "test_module", "args": {"key": "value"}, "id": "125cmd"}
        self.message.text = json.dumps(command)

        katana_bot.handle_message_impl(self.message)

        mock_mkdir.assert_called_once_with(parents=True, exist_ok=True)
        mock_file_open.assert_called_once()
        mock_json_dump.assert_called_once()
        mock_bot.reply_to.assert_called_once()

if __name__ == '__main__':
    unittest.main()
