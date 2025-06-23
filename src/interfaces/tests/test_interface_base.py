import unittest
from unittest.mock import patch, AsyncMock, MagicMock
import asyncio

from ..interface_base import InterfaceBase
from ..telegram_interface import TelegramInterface
from ..gemma_interface import GemmaInterface # Corrected class name

# Required for TelegramInterface instantiation
import os
os.environ['KATANA_TELEGRAM_TOKEN'] = "123456:ABCDEF_test_token" # Mock token

class TestInterfaceImplementations(unittest.IsolatedAsyncioTestCase):

    def test_interface_base_is_abc(self):
        """Verify InterfaceBase cannot be instantiated directly."""
        with self.assertRaises(TypeError):
            InterfaceBase()

    def test_gemma_interface_implements_base(self):
        """Verify GemmaInterface is a subclass and implements abstract methods."""
        self.assertTrue(issubclass(GemmaInterface, InterfaceBase))
        # Instantiation itself will fail if abstract methods are not implemented
        try:
            gemma_api_key = "test_gemma_key_abc"
            interface = GemmaInterface(api_key=gemma_api_key)
            self.assertIsNotNone(interface)
            self.assertTrue(hasattr(interface, "receive"))
            self.assertTrue(hasattr(interface, "send"))
            self.assertTrue(callable(interface.receive))
            self.assertTrue(callable(interface.send))
        except Exception as e:
            self.fail(f"GemmaInterface instantiation or method check failed: {e}")

    @patch('src.interfaces.telegram_interface.telebot.TeleBot') # Mock TeleBot
    @patch('src.interfaces.telegram_interface.threading.Thread') # Mock Thread
    def test_telegram_interface_implements_base(self, MockThread, MockTeleBot):
        """Verify TelegramInterface is a subclass and implements abstract methods."""
        # Mock the bot instance within TelegramInterface
        mock_bot_instance = MockTeleBot.return_value
        mock_bot_instance.send_message = MagicMock()
        mock_bot_instance.polling = MagicMock() # Mock the polling call

        # Mock the thread behavior
        mock_thread_instance = MockThread.return_value
        mock_thread_instance.start = MagicMock()

        self.assertTrue(issubclass(TelegramInterface, InterfaceBase))

        api_token = os.getenv('KATANA_TELEGRAM_TOKEN', "fallback_token_if_not_set")
        if not api_token:
             self.fail("Mock KATANA_TELEGRAM_TOKEN not set for TelegramInterface test")

        try:
            interface = TelegramInterface(api_token=api_token)
            self.assertIsNotNone(interface)
            self.assertTrue(hasattr(interface, "receive"))
            self.assertTrue(hasattr(interface, "send"))
            self.assertTrue(callable(interface.receive))
            self.assertTrue(callable(interface.send))
            MockThread.assert_called_once() # Check that polling thread was initiated
            mock_thread_instance.start.assert_called_once() # Check that thread was started
        except Exception as e:
            self.fail(f"TelegramInterface instantiation or method check failed: {e}")

    @patch('src.interfaces.telegram_interface.telebot.TeleBot')
    @patch('src.interfaces.telegram_interface.threading.Thread')
    async def test_telegram_interface_send_mocked(self, MockThread, MockTeleBot):
        """Test TelegramInterface.send() calls bot.send_message."""
        mock_bot_instance = MockTeleBot.return_value
        mock_bot_instance.send_message = MagicMock() # This mock will be checked

        mock_thread_instance = MockThread.return_value # from @patch
        mock_thread_instance.start = MagicMock()


        api_token = os.getenv('KATANA_TELEGRAM_TOKEN')
        interface = TelegramInterface(api_token=api_token)

        test_chat_id = 12345
        test_text = "Hello from test"
        response_payload = {"chat_id": test_chat_id, "text": test_text}

        await interface.send(response_payload)

        mock_bot_instance.send_message.assert_called_once_with(test_chat_id, test_text)

    @patch('src.interfaces.telegram_interface.telebot.TeleBot')
    @patch('src.interfaces.telegram_interface.threading.Thread')
    async def test_telegram_interface_receive_mocked(self, MockThread, MockTeleBot):
        """Test TelegramInterface.receive() gets from queue."""
        MockTeleBot.return_value # Keep TeleBot mocked
        MockThread.return_value # Keep Thread mocked

        api_token = os.getenv('KATANA_TELEGRAM_TOKEN')
        interface = TelegramInterface(api_token=api_token)

        # Mock the internal asyncio.Queue
        mock_queue_payload = {
            "interface_type": "telegram",
            "chat_id": 67890,
            "user_id": "test_user",
            "text": "Test message from queue",
            "raw_telegram_payload": {"original": "message_obj"}
        }
        # Override the actual queue with a mock that has an async get method
        interface.message_queue = AsyncMock()
        interface.message_queue.get = AsyncMock(return_value=mock_queue_payload)

        # The receive method in TelegramInterface was modified to no longer include history.
        # It now returns the direct payload from the queue.
        # The main loop is responsible for adding history from the global chat_histories.

        # The TelegramInterface.receive() method's current implementation for the return value is:
        # return {
        #     "interface_type": "telegram",
        #     "chat_id": chat_id,
        #     "user_id": queued_payload.get("user_id"),
        #     "text": user_message_text,
        #     "raw_telegram_payload": queued_payload
        # }
        # So, the mock_queue_payload should be what's put onto the queue by _handle_all_messages
        # and then `receive` processes it into the above structure.

        # Let's refine the mock_queue_payload to be what _handle_all_messages puts on queue
        original_queued_message = {
            "chat_id": 67890,
            "user_id": "test_user_telegram",
            "username": "testusername",
            "text": "Hello from Telegram queue",
            "original_message": "mock_telegram_message_object"
        }
        interface.message_queue.get = AsyncMock(return_value=original_queued_message)

        expected_receive_output = {
            "interface_type": "telegram",
            "chat_id": original_queued_message["chat_id"],
            "user_id": original_queued_message["user_id"],
            "text": original_queued_message["text"],
            "raw_telegram_payload": original_queued_message
        }

        received_data = await interface.receive()

        interface.message_queue.get.assert_called_once()
        self.assertEqual(received_data, expected_receive_output)


if __name__ == '__main__':
    unittest.main()
