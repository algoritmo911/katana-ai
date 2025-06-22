import unittest
from unittest.mock import AsyncMock, patch, MagicMock, call
import logging

from katana.bot import katana_bot
from telegram import Update, User, Message, Chat
from telegram.ext import ContextTypes
from openai import OpenAI

# Using the same mock logger strategy as in unit tests
# to verify logging behavior during the E2E-like flow.

class TestKatanaBotE2ELikeFlow(unittest.IsolatedAsyncioTestCase):

    def setUp(self):
        self.mock_logger = MagicMock(spec=logging.Logger)
        self.logger_patcher = patch('katana.bot.katana_bot.logger', self.mock_logger)
        self.logger_patcher.start()

        self.mock_openai_client = MagicMock(spec=OpenAI)
        self.client_patcher = patch('katana.bot.katana_bot.client', self.mock_openai_client)
        self.client_patcher.start()

        self.original_openai_api_key = katana_bot.OPENAI_API_KEY
        katana_bot.OPENAI_API_KEY = "test_key_e2e" # Ensure client is considered initialized

        # Common user and chat details for the flow
        self.user = User(id=201, first_name="E2EUser", is_bot=False, username="e2e_user")
        self.chat = Chat(id=301, type="private")
        self.mock_context = MagicMock(spec=ContextTypes.DEFAULT_TYPE)


    def tearDown(self):
        self.logger_patcher.stop()
        self.client_patcher.stop()
        katana_bot.OPENAI_API_KEY = self.original_openai_api_key

    def _create_mock_update(self, text_content: str | None, message_id: int) -> MagicMock:
        """Helper to create a mock Update object."""
        mock_update = MagicMock(spec=Update)
        mock_update.effective_user = self.user
        mock_update.effective_chat = self.chat

        mock_message = AsyncMock(spec=Message)
        mock_message.text = text_content
        mock_message.message_id = message_id
        mock_message.reply_text = AsyncMock() # Each message can be replied to

        mock_update.message = mock_message
        return mock_update

    async def test_user_interaction_flow(self):
        """Simulate a user flow: /start, send message, send another message."""

        # 1. User sends /start
        mock_update_start = self._create_mock_update(text_content="/start", message_id=1001)
        # For CommandHandler, the text is not directly in update.message.text for handler logic,
        # but the mock setup is fine. The handler itself doesn't use the text for /start.

        await katana_bot.start(mock_update_start, self.mock_context)

        # Assertions for /start
        mock_update_start.message.reply_text.assert_called_once_with(
            "⚔️ Katana (AI Chat Mode) is online. Send me a message and I'll try to respond using OpenAI."
        )
        self.mock_logger.info.assert_any_call(
            "Received /start command.", extra={"user_id": self.user.id, "chat_id": self.chat.id}
        )

        # Clear mocks for the next interaction if asserting call counts precisely per step.
        # For this E2E test, we can also check for a sequence of calls on the logger.
        # For simplicity, let's reset reply_text mock for each step.
        mock_update_start.message.reply_text.reset_mock()
        # Logger calls will accumulate, which is fine for checking sequences or any_call.

        # 2. User sends the first message
        first_message_text = "Tell me a joke."
        mock_update_msg1 = self._create_mock_update(text_content=first_message_text, message_id=1002)

        # Mock OpenAI response for the first message
        mock_completion_choice1 = MagicMock()
        mock_completion_choice1.message.content = "Why did the scarecrow win an award? Because he was outstanding in his field!"
        mock_completion_choice1.finish_reason = "stop"
        mock_completion1 = MagicMock()
        mock_completion1.choices = [mock_completion_choice1]
        mock_completion1.id = "cmpl-joke1"
        self.mock_openai_client.chat.completions.create.return_value = mock_completion1

        await katana_bot.handle_message(mock_update_msg1, self.mock_context)

        # Assertions for the first message
        self.mock_openai_client.chat.completions.create.assert_called_with(
            model="gpt-4", messages=[{"role": "user", "content": first_message_text}]
        )
        mock_update_msg1.message.reply_text.assert_called_once_with(
            "Why did the scarecrow win an award? Because he was outstanding in his field!"
        )
        self.mock_logger.info.assert_any_call(
            f"Received message (ID: 1002, Length: {len(first_message_text)}). Preview: '{first_message_text[:100]}'",
            extra={"user_id": self.user.id, "chat_id": self.chat.id, "message_id": 1002, "message_length": len(first_message_text)}
        )
        self.mock_logger.info.assert_any_call(
            "Successfully sent AI reply to user.",
            extra={"user_id": self.user.id, "chat_id": self.chat.id, "message_id": 1002}
        )

        # Reset for next call
        self.mock_openai_client.chat.completions.create.reset_mock()
        mock_update_msg1.message.reply_text.reset_mock()

        # 3. User sends the second message
        second_message_text = "What's the weather like?"
        mock_update_msg2 = self._create_mock_update(text_content=second_message_text, message_id=1003)

        # Mock OpenAI response for the second message
        mock_completion_choice2 = MagicMock()
        mock_completion_choice2.message.content = "I am an AI and cannot check the weather. Please use a weather app!"
        mock_completion_choice2.finish_reason = "stop"
        mock_completion2 = MagicMock()
        mock_completion2.choices = [mock_completion_choice2]
        mock_completion2.id = "cmpl-weather1"
        self.mock_openai_client.chat.completions.create.return_value = mock_completion2

        await katana_bot.handle_message(mock_update_msg2, self.mock_context)

        # Assertions for the second message
        self.mock_openai_client.chat.completions.create.assert_called_with(
            model="gpt-4", messages=[{"role": "user", "content": second_message_text}]
        )
        mock_update_msg2.message.reply_text.assert_called_once_with(
            "I am an AI and cannot check the weather. Please use a weather app!"
        )
        self.mock_logger.info.assert_any_call(
            f"Received message (ID: 1003, Length: {len(second_message_text)}). Preview: '{second_message_text[:100]}'",
            extra={"user_id": self.user.id, "chat_id": self.chat.id, "message_id": 1003, "message_length": len(second_message_text)}
        )
        self.mock_logger.info.assert_any_call(
            "Successfully sent AI reply to user.",
            extra={"user_id": self.user.id, "chat_id": self.chat.id, "message_id": 1003}
        )

        # Overall logging call checks (examples)
        # Check that debug entry/exit logs occurred for each handler
        expected_start_entry_log = call.debug(
            "Entering start command handler.",
            extra={"user_id": self.user.id, "user_name": self.user.username, "chat_id": self.chat.id}
        )
        expected_start_exit_log = call.debug(
            "Exiting start command handler.",
            extra={"user_id": self.user.id, "chat_id": self.chat.id}
        )

        expected_handle_entry_log_1 = call.debug(
            "Entering handle_message.",
            extra={"user_id": self.user.id, "user_name": self.user.username, "chat_id": self.chat.id}
        )
        # Note: message_id is added later in the handle_message logs
        expected_handle_exit_log_1 = call.debug(
            "Exiting handle_message.",
            extra={"user_id": self.user.id, "chat_id": self.chat.id, "message_id": 1002}
        )
        expected_handle_exit_log_2 = call.debug(
            "Exiting handle_message.",
            extra={"user_id": self.user.id, "chat_id": self.chat.id, "message_id": 1003}
        )

        # Check if these specific calls were made in order (or present among all calls)
        # Using assert_has_calls with any_order=False can be tricky if other debug logs exist.
        # A simpler check is to ensure they were called at all.
        self.mock_logger.debug.assert_any_call(*expected_start_entry_log[1], **expected_start_entry_log[2])
        self.mock_logger.debug.assert_any_call(*expected_start_exit_log[1], **expected_start_exit_log[2])

        # For handle_message, entry log is the same, exit logs differ by message_id
        # We expect two entry calls for handle_message
        self.assertEqual(
            len([c for c in self.mock_logger.debug.call_args_list if c[0][0] == "Entering handle_message."]),
            2
        )
        self.mock_logger.debug.assert_any_call(*expected_handle_exit_log_1[1], **expected_handle_exit_log_1[2])
        self.mock_logger.debug.assert_any_call(*expected_handle_exit_log_2[1], **expected_handle_exit_log_2[2])


if __name__ == '__main__':
    unittest.main()
