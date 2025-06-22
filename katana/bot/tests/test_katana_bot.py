import unittest
from unittest.mock import AsyncMock, patch, MagicMock, call
import logging
from pathlib import Path

# Ensure the bot's logger is configured for testing if necessary,
# or that logs are captured/asserted in a way that doesn't depend on file output for unit tests.
# For unit tests, we might primarily rely on asserting calls to logger methods.
from katana.bot import katana_bot
from katana.utils.logging_config import setup_logger

from telegram import Update, User, Message, Chat
from telegram.ext import ContextTypes
from openai import OpenAI, APIError, AuthenticationError, RateLimitError

# Configure a test logger to capture log outputs if needed for assertions
# For simplicity in these unit tests, we'll mostly mock the logger instance
# used by katana_bot and assert its calls.

# It's good practice to ensure the module-level logger in katana_bot is patched
# for tests, so it doesn't interfere with global logging config or write actual log files.
# We can patch 'katana.bot.katana_bot.logger' for this.

class TestKatanaBotHandlers(unittest.IsolatedAsyncioTestCase):

    def setUp(self):
        # Create a mock logger to be injected or patched
        self.mock_logger = MagicMock(spec=logging.Logger)

        # Patch the logger instance within the katana_bot module
        self.logger_patcher = patch('katana.bot.katana_bot.logger', self.mock_logger)
        self.logger_patcher.start()

        # Mock OpenAI client
        self.mock_openai_client = MagicMock(spec=OpenAI)
        self.client_patcher = patch('katana.bot.katana_bot.client', self.mock_openai_client)
        self.client_patcher.start()

        # Reset TELEGRAM_TOKEN and OPENAI_API_KEY for a clean slate in tests
        # that might depend on their presence for specific behaviors (like client initialization logging).
        # For handler tests, we primarily care about the 'client' object being mocked.
        self.original_openai_api_key = katana_bot.OPENAI_API_KEY
        katana_bot.OPENAI_API_KEY = "test_key" # Assume key is present for most tests unless specified

    def tearDown(self):
        self.logger_patcher.stop()
        self.client_patcher.stop()
        katana_bot.OPENAI_API_KEY = self.original_openai_api_key


    async def test_start_command(self):
        """Test the /start command handler."""
        mock_update = MagicMock(spec=Update)
        mock_update.effective_user = User(id=123, first_name="Test", is_bot=False, username="testuser")
        mock_update.effective_chat = Chat(id=456, type="private")
        mock_update.message = AsyncMock(spec=Message)
        mock_update.message.reply_text = AsyncMock()

        mock_context = MagicMock(spec=ContextTypes.DEFAULT_TYPE)

        await katana_bot.start(mock_update, mock_context)

        mock_update.message.reply_text.assert_called_once_with(
            "⚔️ Katana (AI Chat Mode) is online. Send me a message and I'll try to respond using OpenAI."
        )
        self.mock_logger.info.assert_any_call(
            "Received /start command.", extra={"user_id": 123, "chat_id": 456}
        )
        self.mock_logger.info.assert_any_call(
            "Welcome message sent.",
            extra={"user_id": 123, "chat_id": 456, "message_length": len("⚔️ Katana (AI Chat Mode) is online. Send me a message and I'll try to respond using OpenAI.")}
        )
        self.mock_logger.debug.assert_any_call(
            "Entering start command handler.",
            extra={"user_id": 123, "user_name": "testuser", "chat_id": 456}
        )
        self.mock_logger.debug.assert_any_call(
            "Exiting start command handler.",
            extra={"user_id": 123, "chat_id": 456}
        )

    async def test_handle_message_success(self):
        """Test successful message handling with OpenAI."""
        mock_update = MagicMock(spec=Update)
        mock_update.effective_user = User(id=123, first_name="Test", is_bot=False, username="testuser")
        mock_update.effective_chat = Chat(id=456, type="private")
        mock_update.message = AsyncMock(spec=Message)
        mock_update.message.text = "Hello AI"
        mock_update.message.message_id = 789
        mock_update.message.reply_text = AsyncMock()

        mock_context = MagicMock(spec=ContextTypes.DEFAULT_TYPE)

        # Mock OpenAI response
        mock_completion_choice = MagicMock()
        mock_completion_choice.message.content = "Hello from AI!"
        mock_completion_choice.finish_reason = "stop"
        mock_completion = MagicMock()
        mock_completion.choices = [mock_completion_choice]
        mock_completion.id = "cmpl-mockid123"
        self.mock_openai_client.chat.completions.create.return_value = mock_completion

        await katana_bot.handle_message(mock_update, mock_context)

        self.mock_openai_client.chat.completions.create.assert_called_once_with(
            model="gpt-4", messages=[{"role": "user", "content": "Hello AI"}]
        )
        mock_update.message.reply_text.assert_called_once_with("Hello from AI!")


        # Assertions for logging
        # 1. Received message
        expected_received_msg_text = "Hello AI"
        expected_received_msg_log = f"Received message (ID: 789, Length: {len(expected_received_msg_text)}). Preview: '{expected_received_msg_text[:100]}'"
        self.mock_logger.info.assert_any_call(
            expected_received_msg_log,
            extra={"user_id": 123, "chat_id": 456, "message_id": 789, "message_length": len(expected_received_msg_text)}
        )

        # 2. Sending to OpenAI
        expected_sending_msg_preview = "Hello AI" # user_text[:50]
        expected_sending_log = f"Sending to OpenAI (model: gpt-4). User text preview: '{expected_sending_msg_preview[:50]}...'"
        self.mock_logger.info.assert_any_call(
            expected_sending_log,
            extra={"user_id": 123, "chat_id": 456, "message_id": 789, "model": "gpt-4"}
        )

        # 3. OpenAI reply received (This was the failing one)
        mock_ai_reply_text = "Hello from AI!"
        reply_len = len(mock_ai_reply_text)
        reply_preview = mock_ai_reply_text[:50]
        expected_reply_log = f"OpenAI reply received (Length: {reply_len}). Preview: '{reply_preview}...'"
        self.mock_logger.info.assert_any_call(
            expected_reply_log,
            extra={"user_id": 123, "chat_id": 456, "message_id": 789, "reply_length": reply_len, "openai_finish_reason": "stop"}
        )

        # 4. Successfully sent AI reply
        self.mock_logger.info.assert_any_call(
            "Successfully sent AI reply to user.",
            extra={"user_id": 123, "chat_id": 456, "message_id": 789}
        )

    async def test_handle_message_no_text(self):
        """Test handling of a message with no text."""
        mock_update = MagicMock(spec=Update)
        mock_update.effective_user = User(id=123, first_name="Test", is_bot=False, username="testuser")
        mock_update.effective_chat = Chat(id=456, type="private")
        mock_update.message = AsyncMock(spec=Message)
        mock_update.message.text = None # No text
        mock_update.message.message_id = 789
        mock_update.message.reply_text = AsyncMock()

        mock_context = MagicMock(spec=ContextTypes.DEFAULT_TYPE)

        await katana_bot.handle_message(mock_update, mock_context)

        mock_update.message.reply_text.assert_not_called()
        self.mock_openai_client.chat.completions.create.assert_not_called()
        self.mock_logger.warning.assert_called_once_with(
            "Received message with no text content.",
            extra={"user_id": 123, "chat_id": 456, "update_has_message": True}
        )

    async def test_handle_message_openai_client_not_initialized(self):
        """Test message handling when OpenAI client is not initialized."""
        # Temporarily set client to None for this test
        with patch('katana.bot.katana_bot.client', None):
            mock_update = MagicMock(spec=Update)
            mock_update.effective_user = User(id=123, first_name="Test", is_bot=False, username="testuser")
            mock_update.effective_chat = Chat(id=456, type="private")
            mock_update.message = AsyncMock(spec=Message)
            mock_update.message.text = "Test message"
            mock_update.message.message_id = 789
            mock_update.message.reply_text = AsyncMock()

            mock_context = MagicMock(spec=ContextTypes.DEFAULT_TYPE)

            await katana_bot.handle_message(mock_update, mock_context)

            mock_update.message.reply_text.assert_called_once_with(
                "I apologize, but my connection to the AI core (OpenAI) is not configured. Please contact the administrator."
            )
            self.mock_logger.error.assert_called_once_with(
                "OpenAI client not initialized. Cannot process message.",
                extra={"user_id": 123, "chat_id": 456, "message_id": 789},
            )

    async def test_handle_message_openai_authentication_error(self):
        """Test OpenAI AuthenticationError handling."""
        self.mock_openai_client.chat.completions.create.side_effect = AuthenticationError(
            message="Auth error", response=MagicMock(), body=None
        )

        mock_update = MagicMock(spec=Update)
        mock_update.effective_user = User(id=123, first_name="Test", is_bot=False, username="testuser")
        mock_update.effective_chat = Chat(id=456, type="private")
        mock_update.message = AsyncMock(spec=Message)
        mock_update.message.text = "Test auth error"
        mock_update.message.message_id = 789
        mock_update.message.reply_text = AsyncMock()
        mock_context = MagicMock(spec=ContextTypes.DEFAULT_TYPE)

        await katana_bot.handle_message(mock_update, mock_context)

        mock_update.message.reply_text.assert_called_once_with(
            "Error: OpenAI authentication failed. Please check the API key configuration with the administrator."
        )
        self.mock_logger.error.assert_called_once_with(
            "OpenAI Authentication Error: Auth error. Ensure the API key is correctly configured and valid.",
            exc_info=True,
            extra={"user_id": 123, "chat_id": 456, "message_id": 789, "error_type": "AuthenticationError"},
        )

    async def test_handle_message_openai_rate_limit_error(self):
        """Test OpenAI RateLimitError handling."""
        self.mock_openai_client.chat.completions.create.side_effect = RateLimitError(
            message="Rate limit exceeded", response=MagicMock(), body=None
        )

        mock_update = MagicMock(spec=Update)
        mock_update.effective_user = User(id=123, first_name="Test", is_bot=False, username="testuser")
        mock_update.effective_chat = Chat(id=456, type="private")
        mock_update.message = AsyncMock(spec=Message)
        mock_update.message.text = "Test rate limit"
        mock_update.message.message_id = 789
        mock_update.message.reply_text = AsyncMock()
        mock_context = MagicMock(spec=ContextTypes.DEFAULT_TYPE)

        await katana_bot.handle_message(mock_update, mock_context)

        mock_update.message.reply_text.assert_called_once_with(
            "Error: OpenAI rate limit exceeded. Please try again later."
        )
        self.mock_logger.error.assert_called_once_with(
            "OpenAI Rate Limit Error: Rate limit exceeded. The bot may be sending requests too frequently or has exceeded its quota.",
            exc_info=True,
            extra={"user_id": 123, "chat_id": 456, "message_id": 789, "error_type": "RateLimitError"},
        )

    async def test_handle_message_openai_api_error(self):
        """Test OpenAI APIError handling."""
        self.mock_openai_client.chat.completions.create.side_effect = APIError(
            message="Generic API error", request=MagicMock(), body=None
        )

        mock_update = MagicMock(spec=Update)
        mock_update.effective_user = User(id=123, first_name="Test", is_bot=False, username="testuser")
        mock_update.effective_chat = Chat(id=456, type="private")
        mock_update.message = AsyncMock(spec=Message)
        mock_update.message.text = "Test API error"
        mock_update.message.message_id = 789
        mock_update.message.reply_text = AsyncMock()
        mock_context = MagicMock(spec=ContextTypes.DEFAULT_TYPE)

        await katana_bot.handle_message(mock_update, mock_context)

        mock_update.message.reply_text.assert_called_once_with(
            "An error occurred with the OpenAI API: Generic API error"
        )
        self.mock_logger.error.assert_called_once_with(
            "OpenAI API Error: Generic API error. This could be due to various issues with the OpenAI service or the request.",
            exc_info=True,
            extra={"user_id": 123, "chat_id": 456, "message_id": 789, "error_type": "APIError"},
        )

    async def test_handle_message_unexpected_error(self):
        """Test handling of an unexpected error during message processing."""
        self.mock_openai_client.chat.completions.create.side_effect = Exception("Unexpected issue")

        mock_update = MagicMock(spec=Update)
        mock_update.effective_user = User(id=123, first_name="Test", is_bot=False, username="testuser")
        mock_update.effective_chat = Chat(id=456, type="private")
        mock_update.message = AsyncMock(spec=Message)
        mock_update.message.text = "Test unexpected error"
        mock_update.message.message_id = 789
        mock_update.message.reply_text = AsyncMock()
        mock_context = MagicMock(spec=ContextTypes.DEFAULT_TYPE)

        await katana_bot.handle_message(mock_update, mock_context)

        mock_update.message.reply_text.assert_called_once_with(
            "Sorry, an unexpected error occurred while processing your message."
        )
        self.mock_logger.error.assert_called_once_with(
            "An unexpected error occurred in handle_message: Unexpected issue",
            exc_info=True,
            extra={"user_id": 123, "chat_id": 456, "message_id": 789, "error_type": "Exception"},
        )

    async def test_handle_message_long_input(self):
        """Test handling of a very long input message."""
        long_text = "A" * 5000 # Example long text
        mock_update = MagicMock(spec=Update)
        mock_update.effective_user = User(id=123, first_name="Test", is_bot=False, username="testuser")
        mock_update.effective_chat = Chat(id=456, type="private")
        mock_update.message = AsyncMock(spec=Message)
        mock_update.message.text = long_text
        mock_update.message.message_id = 790
        mock_update.message.reply_text = AsyncMock()
        mock_context = MagicMock(spec=ContextTypes.DEFAULT_TYPE)

        # Mock OpenAI response
        mock_completion_choice = MagicMock()
        mock_completion_choice.message.content = "Response to long text."
        mock_completion_choice.finish_reason = "stop"
        mock_completion = MagicMock()
        mock_completion.choices = [mock_completion_choice]
        mock_completion.id = "cmpl-mockid-long"
        self.mock_openai_client.chat.completions.create.return_value = mock_completion

        await katana_bot.handle_message(mock_update, mock_context)

        self.mock_openai_client.chat.completions.create.assert_called_once_with(
            model="gpt-4", messages=[{"role": "user", "content": long_text}]
        )
        mock_update.message.reply_text.assert_called_once_with("Response to long text.")
        self.mock_logger.info.assert_any_call(
            f"Received message (ID: 790, Length: {len(long_text)}). Preview: '{long_text[:100]}'",
            extra={"user_id": 123, "chat_id": 456, "message_id": 790, "message_length": len(long_text)}
        )
        # Ensure the log for sending to OpenAI also uses the truncated preview
        self.mock_logger.info.assert_any_call(
            f"Sending to OpenAI (model: gpt-4). User text preview: '{long_text[:50]}...'",
            extra={"user_id": 123, "chat_id": 456, "message_id": 790, "model": "gpt-4"}
        )


    async def test_handle_message_special_chars(self):
        """Test handling of messages with special characters."""
        special_text = "Hello with !@#$%^&*()_+-=[]{};':\",./<>?`~ and emojis 😊🚀"
        mock_update = MagicMock(spec=Update)
        mock_update.effective_user = User(id=123, first_name="Test", is_bot=False, username="testuser")
        mock_update.effective_chat = Chat(id=456, type="private")
        mock_update.message = AsyncMock(spec=Message)
        mock_update.message.text = special_text
        mock_update.message.message_id = 791
        mock_update.message.reply_text = AsyncMock()
        mock_context = MagicMock(spec=ContextTypes.DEFAULT_TYPE)

        # Mock OpenAI response
        mock_completion_choice = MagicMock()
        mock_completion_choice.message.content = "Response to special chars."
        mock_completion_choice.finish_reason = "stop"
        mock_completion = MagicMock()
        mock_completion.choices = [mock_completion_choice]
        mock_completion.id = "cmpl-mockid-special"
        self.mock_openai_client.chat.completions.create.return_value = mock_completion

        await katana_bot.handle_message(mock_update, mock_context)

        self.mock_openai_client.chat.completions.create.assert_called_once_with(
            model="gpt-4", messages=[{"role": "user", "content": special_text}]
        )
        mock_update.message.reply_text.assert_called_once_with("Response to special chars.")
        self.mock_logger.info.assert_any_call(
            f"Received message (ID: 791, Length: {len(special_text)}). Preview: '{special_text[:100]}'",
            extra={"user_id": 123, "chat_id": 456, "message_id": 791, "message_length": len(special_text)}
        )

if __name__ == '__main__':
    unittest.main()
