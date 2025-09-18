import unittest
from unittest.mock import patch, MagicMock, call
import json
import os
from importlib import reload, import_module

# Ensures that the root of the project (the parent directory of 'bot') is in sys.path
import sys
from pathlib import Path
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

class TestKatanaBot(unittest.TestCase):

    @patch('bot.katana_bot.init_dependencies')
    @patch('bot.katana_bot.create_bot')
    def setUp(self, mock_create_bot, mock_init_dependencies):
        # This setup method is now much cleaner. It patches the two functions
        # that cause side effects at the module level of `run_bot_locally`.

        # 1. Mock the bot instance
        self.mock_bot_instance = MagicMock()
        self.mock_bot_instance.message_handlers = []

        def message_handler_decorator(*args, **kwargs):
            def decorator(handler_func):
                self.mock_bot_instance.message_handlers.append({
                    'function': handler_func,
                    'filters': kwargs
                })
                return handler_func
            return decorator

        self.mock_bot_instance.message_handler.side_effect = message_handler_decorator
        mock_create_bot.return_value = self.mock_bot_instance

        # 2. To test the handlers, we need to get a reference to them.
        #    The `register_handlers` function in katana_bot.py now takes the bot instance.
        #    We can import it and call it with our mock bot.
        from bot.katana_bot import register_handlers, handle_message_impl

        # We also need a mock memory manager for the handlers to use.
        self.mock_memory_manager = MagicMock()

        # We need to patch the global `memory_manager` object inside the `katana_bot` module
        # so that when handlers are called, they use our mock.
        self.patch_mm = patch('bot.katana_bot.memory_manager', self.mock_memory_manager)
        self.patch_mm.start()
        self.addCleanup(self.patch_mm.stop)

        # Register the handlers on our mock bot instance.
        # This will populate `self.mock_bot_instance.message_handlers`.
        register_handlers(self.mock_bot_instance)

        # Store a direct reference to the implementation for easier calling in tests
        self.handle_message_impl = handle_message_impl

        # 3. Create a common mock message object
        self.message = MagicMock()
        self.message.chat.id = 123
        self.chat_id_str = str(self.message.chat.id)
        self.message.from_user.username = "testuser"

    def test_start_command_handler(self):
        """Tests that the /start command handler replies and updates memory."""
        self.message.text = "/start"

        # Find the start handler and execute it
        start_handler = next(h for h in self.mock_bot_instance.message_handlers if h['filters'].get('commands') == ['start'])
        start_handler['function'](self.message)

        expected_reply = "Привет! Я — Katana. Готов к диалогу или JSON-команде."
        self.mock_bot_instance.reply_to.assert_called_once_with(self.message, expected_reply)

        # Check that the welcome message was added to memory
        self.mock_memory_manager.add_message_to_history.assert_called_once()


    @patch('bot.katana_bot.get_katana_response', return_value="NLP says hi")
    def test_natural_language_handler(self, mock_get_response):
        """Tests that a simple text message is processed as natural language."""
        self.message.text = "Hello"

        # Find the generic handler and execute it
        generic_handler = next(h for h in self.mock_bot_instance.message_handlers if h['filters'].get('func'))

        # We need to simulate the memory manager returning some history
        self.mock_memory_manager.get_history.return_value = []

        generic_handler['function'](self.message)

        # Check that the user's message and the bot's response were added to history
        self.assertEqual(self.mock_memory_manager.add_message_to_history.call_count, 2)

        # Check that the bot replied with the NLP response
        self.mock_bot_instance.reply_to.assert_called_once_with(self.message, "NLP says hi")


if __name__ == '__main__':
    unittest.main()
