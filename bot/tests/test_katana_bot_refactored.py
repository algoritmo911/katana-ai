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
        self.patcher_datafusion = patch('bot.katana_bot.DataFusion', MagicMock())
        self.mock_fusion = self.patcher_datafusion.start()

        self.patcher_reply = patch('bot.katana_bot.bot.reply_to', MagicMock())
        self.mock_reply = self.patcher_reply.start()

        self.patcher_memory_manager = patch('bot.katana_bot.memory_manager', MagicMock())
        self.mock_memory_manager = self.patcher_memory_manager.start()

        self.message = MagicMock()
        self.message.chat.id = 12345
        self.message.text = ""
        self.chat_id_str = str(self.message.chat.id)

        katana_bot.init_dependencies()

        # Reset the mocks before each test
        self.mock_fusion.reset_mock()
        self.mock_reply.reset_mock()
        self.mock_memory_manager.reset_mock()
        katana_bot.data_fusion = self.mock_fusion()

    def tearDown(self):
        self.patcher_datafusion.stop()
        self.patcher_reply.stop()
        self.patcher_memory_manager.stop()

    def test_handle_start(self):
        self.message.text = "/start"
        katana_bot.handle_start(self.message)

        self.mock_reply.assert_called_once()
        args, kwargs = self.mock_reply.call_args
        self.assertEqual(args[0], self.message)
        self.assertIn("Katana", args[1])

        self.mock_memory_manager.add_message_to_history.assert_called_once_with(
            self.chat_id_str,
            {"role": katana_bot.MESSAGE_ROLE_ASSISTANT, "content": args[1]}
        )

    def test_natural_language_message_success(self):
        self.message.text = "Hello Katana"
        self.mock_fusion.return_value.get_response.return_value = "Hello there!"

        katana_bot.handle_message_impl(self.message)

        self.mock_memory_manager.get_history.assert_called_once_with(self.chat_id_str)
        self.mock_fusion.return_value.get_response.assert_called_once()

        self.mock_reply.assert_called_once_with(self.message, "Hello there!")

        self.assertEqual(self.mock_memory_manager.add_message_to_history.call_count, 2)

    @patch('bot.katana_bot.logger')
    def test_get_katana_response_exception(self, mock_logger):
        self.message.text = "trigger error"
        self.mock_fusion.return_value.get_response.side_effect = Exception("Test error")

        katana_bot.handle_message_impl(self.message)

        mock_logger.error.assert_called()
        self.mock_reply.assert_called_once()

    def test_json_command_mind_clearing(self):
        self.message.text = json.dumps({"type": "mind_clearing", "module": "test", "args": {}, "id": "1"})

        katana_bot.handle_message_impl(self.message)

        self.mock_memory_manager.clear_history.assert_called_once_with(self.chat_id_str)
        self.mock_reply.assert_called_once()
        args, _ = self.mock_reply.call_args
        self.assertIn("Контекст диалога очищен", args[1])

    @patch('builtins.open', new_callable=mock_open)
    @patch('json.dump')
    @patch('bot.katana_bot.Path.mkdir')
    def test_json_command_generic_save(self, mock_mkdir, mock_json_dump, mock_file_open):
        command = {"type": "generic_command", "module": "test_module", "args": {"key": "value"}, "id": "125cmd"}
        self.message.text = json.dumps(command)

        katana_bot.handle_message_impl(self.message)

        mock_mkdir.assert_called_once_with(parents=True, exist_ok=True)
        mock_file_open.assert_called_once()
        mock_json_dump.assert_called_once()
        self.mock_reply.assert_called_once()

    def test_command_routing(self):
        self.message.text = json.dumps({"type": "some_other_command", "module": "test", "args": {}, "id": "1"})

        katana_bot.handle_message_impl(self.message)

        # Check that the default command handler was called
        self.mock_reply.assert_called_once()
        args, _ = self.mock_reply.call_args
        self.assertIn("Команда принята и сохранена как", args[1])

if __name__ == '__main__':
    unittest.main()
