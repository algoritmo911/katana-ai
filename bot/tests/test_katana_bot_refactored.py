import unittest
from unittest.mock import MagicMock, patch, mock_open
import os
import sys
from pathlib import Path
import json

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

# Set a dummy token to allow the module to be imported without raising an error
os.environ['KATANA_TELEGRAM_TOKEN'] = '123456:ABCDEF'
from bot import katana_bot

class TestKatanaBotRefactored(unittest.TestCase):

    def setUp(self):
        """Set up mocks for every test."""
        # We patch the dependencies of katana_bot so we can isolate our tests.
        self.patcher_datafusion = patch('bot.katana_bot.DataFusion', MagicMock())
        self.mock_fusion_class = self.patcher_datafusion.start()
        self.mock_fusion_instance = self.mock_fusion_class.return_value

        self.patcher_reply = patch('bot.katana_bot.bot.reply_to', MagicMock())
        self.mock_reply = self.patcher_reply.start()

        # Mock the entire memory_manager module instance in katana_bot
        self.patcher_memory_manager = patch('bot.katana_bot.memory_manager', MagicMock())
        self.mock_memory_manager = self.patcher_memory_manager.start()

        # Create a mock for the redis client that the memory_manager would return
        self.mock_redis_client = MagicMock()
        self.mock_memory_manager.get_redis_client.return_value = self.mock_redis_client

        # A standard message object to be used in tests
        self.message = MagicMock()
        self.message.chat.id = 12345
        self.message.text = ""
        self.chat_id_str = str(self.message.chat.id)

        # Initialize dependencies in katana_bot, which will now use our mocks
        katana_bot.init_dependencies()
        # Explicitly set the global data_fusion to our mock instance
        katana_bot.data_fusion = self.mock_fusion_instance

    def tearDown(self):
        """Clean up patches after each test."""
        self.patcher_datafusion.stop()
        self.patcher_reply.stop()
        self.patcher_memory_manager.stop()

    def test_handle_start(self):
        """Test the /start command handler."""
        self.message.text = "/start"
        katana_bot.handle_start(self.message)

        self.mock_reply.assert_called_once()
        args, _ = self.mock_reply.call_args
        self.assertEqual(args[0], self.message)
        self.assertIn("Katana", args[1])

        self.mock_memory_manager.add_message_to_history.assert_called_once_with(
            self.chat_id_str,
            {"role": katana_bot.MESSAGE_ROLE_ASSISTANT, "content": args[1]}
        )

    def test_natural_language_message_success(self):
        """Test that a normal text message is processed by DataFusion."""
        self.message.text = "Hello Katana"
        self.mock_fusion_instance.get_response.return_value = "Hello there!"

        katana_bot.handle_message_impl(self.message)

        self.mock_memory_manager.get_history.assert_called_once_with(self.chat_id_str)
        self.mock_fusion_instance.get_response.assert_called_once()
        self.mock_reply.assert_called_once_with(self.message, "Hello there!")
        self.assertEqual(self.mock_memory_manager.add_message_to_history.call_count, 2)

    @patch('bot.katana_bot.logger')
    def test_get_katana_response_exception(self, mock_logger):
        """Test that an error during NLP processing is handled gracefully."""
        self.message.text = "trigger error"
        self.mock_fusion_instance.get_response.side_effect = Exception("Test error")

        katana_bot.handle_message_impl(self.message)

        mock_logger.error.assert_called()
        self.mock_reply.assert_called_once()
        args, _ = self.mock_reply.call_args
        self.assertIn("Произошла внутренняя ошибка", args[1])

    def test_json_command_mind_clearing(self):
        """Test that the 'mind_clearing' command clears user history."""
        self.message.text = json.dumps({"type": "mind_clearing", "module": "test", "args": {}, "id": "1"})

        katana_bot.handle_message_impl(self.message)

        self.mock_memory_manager.clear_history.assert_called_once_with(self.chat_id_str)
        self.mock_reply.assert_called_once()
        args, _ = self.mock_reply.call_args
        self.assertIn("Контекст диалога очищен", args[1])

    def test_json_command_is_queued(self):
        """Test that a generic JSON command is pushed to the Redis queue."""
        command = {"type": "generic_command", "module": "test_module", "args": {"key": "value"}, "id": "125cmd"}
        self.message.text = json.dumps(command)

        # Define the expected queue name
        task_queue_name = os.getenv('REDIS_TASK_QUEUE_NAME', 'katana:task_queue')

        katana_bot.handle_message_impl(self.message)

        # Verify the command was pushed to Redis
        self.mock_redis_client.rpush.assert_called_once_with(
            task_queue_name,
            json.dumps(command, ensure_ascii=False)
        )

        # Verify the user received the correct confirmation message
        self.mock_reply.assert_called_once()
        args, _ = self.mock_reply.call_args
        self.assertIn("принята и поставлена в очередь", args[1])

    def test_command_routing_sends_to_queue(self):
        """Test that any unhandled command type is routed to the queue."""
        command_text = {"type": "some_other_command", "module": "test", "args": {}, "id": "1"}
        self.message.text = json.dumps(command_text)

        katana_bot.handle_message_impl(self.message)

        # Check that the default command handler (queuing) was called
        self.mock_redis_client.rpush.assert_called_once()
        self.mock_reply.assert_called_once()
        args, _ = self.mock_reply.call_args
        self.assertIn("принята и поставлена в очередь", args[1])
        self.assertIn("'some_other_command'", args[1])

if __name__ == '__main__':
    unittest.main()
