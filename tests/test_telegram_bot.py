# tests/test_telegram_bot.py
import unittest
from unittest.mock import AsyncMock, MagicMock, patch
import pytest # Using pytest for async support if needed, or can stick to unittest with async test runners

# Modules to test
import telegram_bot
import nlp_module
import katana_agent
import config

# Need to ensure that the bot's main() doesn't actually run when importing
# One way is to guard it with if __name__ == '__main__', which is already done.

@pytest.mark.asyncio
class TestTelegramBotHandlers(unittest.IsolatedAsyncioTestCase):

    async def asyncSetUp(self):
        self.update = AsyncMock(spec=['message', 'effective_user'])
        self.context = AsyncMock(spec=['bot', 'args'])

        # Mock update.message and its methods
        self.update.message = AsyncMock(spec=['reply_text', 'reply_html'])
        self.update.message.reply_text = AsyncMock()
        self.update.message.reply_html = AsyncMock()

        # Mock effective_user
        self.update.effective_user = MagicMock(spec=['id', 'username', 'mention_html'])
        self.update.effective_user.id = 12345
        self.update.effective_user.username = "testuser"
        self.update.effective_user.mention_html.return_value = "<a href='tg://user?id=12345'>testuser</a>"

        # Mock context.bot and its methods if needed, e.g. context.bot.send_message
        self.context.bot = AsyncMock(spec=['send_message'])
        self.context.bot.send_message = AsyncMock()

        # Mock context.args
        self.context.args = []

    @patch('telegram_bot.help_command', new_callable=AsyncMock) # Also mock help_command called by start
    async def test_start_command(self, mock_help_command):
        await telegram_bot.start_command(self.update, self.context)
        self.update.message.reply_html.assert_called_once_with(
            rf"Hi {self.update.effective_user.mention_html()}!",
            reply_markup=None
        )
        mock_help_command.assert_called_once_with(self.update, self.context)

    async def test_help_command(self):
        await telegram_bot.help_command(self.update, self.context)
        self.update.message.reply_text.assert_called_once()
        call_args = self.update.message.reply_text.call_args[0][0]
        self.assertIn("I can help you interact with the Katana system.", call_args)
        self.assertIn("/run <command_for_katana>", call_args)

    @patch('telegram_bot.katana_agent.execute_command')
    async def test_run_command_handler_with_args(self, mock_execute_katana):
        self.context.args = ["uptime", "--verbose"]
        mock_execute_katana.return_value = "Katana says: uptime is good"

        await telegram_bot.run_command_handler(self.update, self.context)

        mock_execute_katana.assert_called_once_with("uptime --verbose", params={"source": "/run command"})
        self.update.message.reply_text.assert_called_once_with("Katana says: uptime is good")

    async def test_run_command_handler_no_args(self):
        self.context.args = []
        await telegram_bot.run_command_handler(self.update, self.context)
        self.update.message.reply_text.assert_called_once_with(
            "Please specify a command to run. Usage: `/run <command_text>`"
        )

    @patch('telegram_bot.katana_agent.execute_command')
    async def test_run_command_handler_katana_error(self, mock_execute_katana):
        self.context.args = ["failing_command"]
        mock_execute_katana.side_effect = Exception("Katana exploded")

        await telegram_bot.run_command_handler(self.update, self.context)

        mock_execute_katana.assert_called_once_with("failing_command", params={"source": "/run command"})
        self.update.message.reply_text.assert_called_once_with(
            "Sorry, an error occurred while trying to run the command: `failing_command`."
        )

    @patch('telegram_bot.nlp_module.recognize_intent')
    @patch('telegram_bot.katana_agent.execute_command')
    async def test_handle_message_get_uptime_intent(self, mock_execute_katana, mock_recognize_intent):
        self.update.message.text = "what is the uptime"
        mock_recognize_intent.return_value = ("get_uptime", {})
        mock_execute_katana.return_value = "Katana: Uptime is 100 days."

        await telegram_bot.handle_message(self.update, self.context)

        mock_recognize_intent.assert_called_once_with("what is the uptime")
        mock_execute_katana.assert_called_once_with("uptime", {})
        self.update.message.reply_text.assert_called_once_with("Katana: Uptime is 100 days.")

    @patch('telegram_bot.nlp_module.recognize_intent')
    @patch('telegram_bot.katana_agent.execute_command')
    async def test_handle_message_greet_user_intent(self, mock_execute_katana, mock_recognize_intent):
        self.update.message.text = "greet Test Person"
        params = {"name": "Test Person"}
        mock_recognize_intent.return_value = ("greet_user", params)
        mock_execute_katana.return_value = "Katana: Hello Test Person!"

        await telegram_bot.handle_message(self.update, self.context)

        mock_recognize_intent.assert_called_once_with("greet Test Person")
        mock_execute_katana.assert_called_once_with("greet_user", params)
        self.update.message.reply_text.assert_called_once_with("Katana: Hello Test Person!")

    @patch('telegram_bot.nlp_module.recognize_intent')
    @patch('telegram_bot.katana_agent.execute_command')
    async def test_handle_message_get_status_intent(self, mock_execute_katana, mock_recognize_intent):
        self.update.message.text = "what is the status"
        mock_recognize_intent.return_value = ("get_status", {})
        mock_execute_katana.return_value = "Katana: All systems nominal."

        await telegram_bot.handle_message(self.update, self.context)

        mock_recognize_intent.assert_called_once_with("what is the status")
        mock_execute_katana.assert_called_once_with("get_status", {})
        self.update.message.reply_text.assert_called_once_with("Katana: All systems nominal.")

    @patch('telegram_bot.nlp_module.recognize_intent')
    @patch('telegram_bot.katana_agent.execute_command')
    async def test_handle_message_run_command_intent(self, mock_execute_katana, mock_recognize_intent):
        # This tests if /run command text makes it through general message handler
        # if not caught by CommandHandler (e.g. if CommandHandler for /run was removed)
        # or if NLP is made to recognize "run command xyz" as run_command intent.
        # Current nlp_module.py recognizes "/run actual_cmd" as ("run_command", {"command": "actual_cmd"})
        self.update.message.text = "/run do_something"
        params = {"command": "do_something"}
        mock_recognize_intent.return_value = ("run_command", params)
        mock_execute_katana.return_value = "Katana: Did something."

        await telegram_bot.handle_message(self.update, self.context)

        mock_recognize_intent.assert_called_once_with("/run do_something")
        mock_execute_katana.assert_called_once_with("do_something", params)
        self.update.message.reply_text.assert_called_once_with("Katana: Did something.")

    @patch('telegram_bot.nlp_module.recognize_intent')
    async def test_handle_message_run_command_intent_no_command_text(self, mock_recognize_intent):
        # Test the specific error message if NLP returns run_command but command is empty
        self.update.message.text = "/run" # Assume NLP somehow parsed this
        params = {"command": ""} # NLP returns empty command string
        mock_recognize_intent.return_value = ("run_command", params)

        await telegram_bot.handle_message(self.update, self.context)

        mock_recognize_intent.assert_called_once_with("/run")
        self.update.message.reply_text.assert_called_once_with(
            "Please specify a command to run with /run. Usage: /run <command>"
        )

    @patch('telegram_bot.nlp_module.recognize_intent')
    async def test_handle_message_no_intent(self, mock_recognize_intent):
        self.update.message.text = "gibberish"
        mock_recognize_intent.return_value = (None, {})

        await telegram_bot.handle_message(self.update, self.context)

        mock_recognize_intent.assert_called_once_with("gibberish")
        self.update.message.reply_text.assert_called_once_with(
            "Sorry, I couldn't understand: 'gibberish'. Try `/help`."
        )

    @patch('telegram_bot.nlp_module.recognize_intent')
    async def test_handle_message_unknown_recognized_intent(self, mock_recognize_intent):
        self.update.message.text = "some weird query"
        mock_recognize_intent.return_value = ("unknown_but_recognized_intent", {})

        await telegram_bot.handle_message(self.update, self.context)

        mock_recognize_intent.assert_called_once_with("some weird query")
        self.update.message.reply_text.assert_called_once_with(
            "I understood the intent as 'unknown_but_recognized_intent', but I don't know how to handle it yet."
        )

    @patch('telegram_bot.nlp_module.recognize_intent')
    async def test_handle_message_nlp_exception(self, mock_recognize_intent):
        self.update.message.text = "trigger nlp error"
        mock_recognize_intent.side_effect = Exception("NLP failed spectacularly")

        await telegram_bot.handle_message(self.update, self.context)

        mock_recognize_intent.assert_called_once_with("trigger nlp error")
        self.update.message.reply_text.assert_called_once_with(
            "Sorry, something went wrong while processing your request."
        )

    @patch('telegram_bot.nlp_module.recognize_intent')
    @patch('telegram_bot.katana_agent.execute_command')
    async def test_handle_message_katana_exception(self, mock_execute_katana, mock_recognize_intent):
        self.update.message.text = "trigger katana error"
        mock_recognize_intent.return_value = ("get_uptime", {})
        mock_execute_katana.side_effect = Exception("Katana is down")

        await telegram_bot.handle_message(self.update, self.context)

        mock_recognize_intent.assert_called_once_with("trigger katana error")
        mock_execute_katana.assert_called_once_with("uptime", {})
        self.update.message.reply_text.assert_called_once_with(
            "Sorry, something went wrong while processing your request."
        )

# We are not testing main() directly here as it involves Application.run_polling()
# which is for actual bot execution.
# Testing the Application setup (add_handlers) would be more of an integration test
# or would require more complex mocking of the ApplicationBuilder.

if __name__ == '__main__':
    # If using pytest, run with `pytest tests/test_telegram_bot.py`
    # If running with unittest directly, it might need an async test runner for IsolatedAsyncioTestCase
    # For example, `python -m unittest tests.test_telegram_bot`
    unittest.main()
