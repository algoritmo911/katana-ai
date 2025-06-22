# tests/test_integration.py
import unittest
from unittest.mock import AsyncMock, MagicMock, patch
import pytest

# Import the modules that will be integrated
import telegram_bot # Main bot file with handlers
# nlp_module and katana_agent are used by telegram_bot, so no direct import needed here
# unless we want to spy on them, but for integration, we let them run.

@pytest.mark.asyncio
class TestBotIntegration(unittest.IsolatedAsyncioTestCase):

    async def asyncSetUp(self):
        self.update = AsyncMock(spec=['message', 'effective_user'])
        self.context = AsyncMock(spec=['bot', 'args'])

        self.update.message = AsyncMock(spec=['reply_text', 'reply_html', 'text'])
        self.update.message.reply_text = AsyncMock()
        self.update.message.reply_html = AsyncMock()

        self.update.effective_user = MagicMock(spec=['id', 'username', 'mention_html'])
        self.update.effective_user.id = 12345
        self.update.effective_user.username = "integration_user"
        self.update.effective_user.mention_html.return_value = "<a href='tg://user?id=12345'>integration_user</a>"

        self.context.bot = AsyncMock(spec=['send_message'])
        self.context.bot.send_message = AsyncMock()
        self.context.args = []

        # It's important that nlp_module and katana_agent use the main log file
        # when called from telegram_bot. For these tests, we don't re-init logging.
        # We are testing the handlers from telegram_bot directly.

    async def test_integration_start_command(self):
        # /start calls help_command, so we expect two replies or one combined.
        # Current start_command sends a greeting then calls help_command.
        await telegram_bot.start_command(self.update, self.context)

        self.update.message.reply_html.assert_called_once_with(
            rf"Hi {self.update.effective_user.mention_html()}!",
            reply_markup=None
        )
        # help_command is called after reply_html
        self.update.message.reply_text.assert_called_once()
        help_call_args = self.update.message.reply_text.call_args[0][0]
        self.assertIn("I can help you interact with the Katana system.", help_call_args)

    async def test_integration_help_command(self):
        await telegram_bot.help_command(self.update, self.context)
        self.update.message.reply_text.assert_called_once()
        call_args = self.update.message.reply_text.call_args[0][0]
        self.assertIn("You can use commands like:", call_args)
        self.assertIn("/run <command_for_katana>", call_args)

    async def test_integration_run_uptime_command_direct(self):
        self.context.args = ["uptime"] # Simulates user typing "/run uptime"

        await telegram_bot.run_command_handler(self.update, self.context)

        self.update.message.reply_text.assert_called_once_with(
            "Katana system uptime: 10 days, 5 hours, 30 minutes (simulated)"
        )

    async def test_integration_run_unknown_katana_command_direct(self):
        self.context.args = ["nonexistent_tool", "--debug"]

        await telegram_bot.run_command_handler(self.update, self.context)

        self.update.message.reply_text.assert_called_once_with(
            "Error: Katana does not recognize the command 'nonexistent_tool --debug' (simulated)."
        )

    async def test_integration_run_command_no_args_direct(self):
        self.context.args = []
        await telegram_bot.run_command_handler(self.update, self.context)
        self.update.message.reply_text.assert_called_once_with(
            "Please specify a command to run. Usage: `/run <command_text>`"
        )

    async def test_integration_handle_message_uptime_natural_language(self):
        self.update.message.text = "tell me the system uptime"

        await telegram_bot.handle_message(self.update, self.context)

        self.update.message.reply_text.assert_called_once_with(
            "Katana system uptime: 10 days, 5 hours, 30 minutes (simulated)"
        )

    async def test_integration_handle_message_greet_user_natural_language(self):
        self.update.message.text = "Hello to Integration Test User"

        await telegram_bot.handle_message(self.update, self.context)

        # nlp_module extracts "Integration Test User"
        # katana_agent formats "Hello, Integration Test User! Welcome..."
        self.update.message.reply_text.assert_called_once_with(
            "Hello, Integration Test User! Welcome to the Katana interface (simulated)."
        )

    async def test_integration_handle_message_greet_user_no_name_natural_language(self):
        self.update.message.text = "hi there" # Should trigger greet_user with no name

        await telegram_bot.handle_message(self.update, self.context)

        self.update.message.reply_text.assert_called_once_with(
            "Hello, User! Welcome to the Katana interface (simulated)."
        )

    async def test_integration_handle_message_run_command_via_nlp(self):
        # This tests if a message like "/run actual_command" is processed by NLP
        # and then Katana, via the general message handler.
        self.update.message.text = "/run uptime" # nlp_module identifies this

        await telegram_bot.handle_message(self.update, self.context)

        self.update.message.reply_text.assert_called_once_with(
            "Katana system uptime: 10 days, 5 hours, 30 minutes (simulated)"
        )

    async def test_integration_handle_message_unknown_intent(self):
        self.update.message.text = "what is the color of the sky today?"

        await telegram_bot.handle_message(self.update, self.context)

        self.update.message.reply_text.assert_called_once_with(
            "Sorry, I couldn't understand: 'what is the color of the sky today?'. Try `/help`."
        )

    # Example of how you might patch config for a specific test, if needed
    # @patch('telegram_bot.config.SOME_SETTING', 'new_value')
    # async def test_with_modified_config(self, mock_config_val_is_now_new_value):
    #     pass

if __name__ == '__main__':
    unittest.main()
