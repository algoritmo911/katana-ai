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
        mock_execute_katana.return_value = {"status": "success", "message": "Katana says: uptime is good"}

        await telegram_bot.run_command_handler(self.update, self.context)

        mock_execute_katana.assert_called_once_with(
            "uptime --verbose",
            params={"source": "/run command", "user": "testuser"}
        )
        self.update.message.reply_text.assert_called_once_with("Katana says: uptime is good")

    async def test_run_command_handler_no_args(self):
        self.context.args = []
        await telegram_bot.run_command_handler(self.update, self.context)
        self.update.message.reply_text.assert_called_once_with("Usage: `/run <command_text>`")

    @patch('telegram_bot.katana_agent.execute_command')
    async def test_run_command_handler_katana_error(self, mock_execute_katana):
        self.context.args = ["failing_command"]
        mock_execute_katana.side_effect = Exception("Katana exploded")

        await telegram_bot.run_command_handler(self.update, self.context)

        mock_execute_katana.assert_called_once_with(
            "failing_command",
            params={"source": "/run command", "user": "testuser"}
        )
        self.update.message.reply_text.assert_called_once_with(
            "Sorry, an error occurred while trying to run the command: `failing_command`."
        )

    @patch('telegram_bot.nlp_module.recognize_intent')
    @patch('telegram_bot.katana_agent.execute_command')
    async def test_handle_message_get_uptime_intent(self, mock_execute_katana, mock_recognize_intent):
        self.update.message.text = "what is the uptime"
        mock_recognize_intent.return_value = ("get_uptime", {})
        mock_execute_katana.return_value = {"status": "success", "message": "Katana: Uptime is 100 days."}

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
        mock_execute_katana.return_value = {"status": "success", "message": "Katana: Hello Test Person!"}

        await telegram_bot.handle_message(self.update, self.context)

        mock_recognize_intent.assert_called_once_with("greet Test Person")
        mock_execute_katana.assert_called_once_with("greet_user", params)
        self.update.message.reply_text.assert_called_once_with("Katana: Hello Test Person!")

    @patch('telegram_bot.nlp_module.recognize_intent')
    @patch('telegram_bot.katana_agent.execute_command')
    async def test_handle_message_run_command_intent(self, mock_execute_katana, mock_recognize_intent):
        self.update.message.text = "/run do_something"
        params = {"command": "do_something"}
        mock_recognize_intent.return_value = ("run_command", params)
        mock_execute_katana.return_value = {"status": "success", "message": "Katana: Did something."}

        await telegram_bot.handle_message(self.update, self.context)

        mock_recognize_intent.assert_called_once_with("/run do_something")
        mock_execute_katana.assert_called_once_with("do_something", params)
        self.update.message.reply_text.assert_called_once_with("Katana: Did something.")

    @patch('telegram_bot.nlp_module.recognize_intent')
    async def test_handle_message_run_command_intent_no_command_text(self, mock_recognize_intent):
        self.update.message.text = "/run"
        params = {"command": None}
        mock_recognize_intent.return_value = ("run_command", params)

        await telegram_bot.handle_message(self.update, self.context)

        mock_recognize_intent.assert_called_once_with("/run")
        self.update.message.reply_text.assert_called_once_with(
            "I understood 'run_command', but I don't know what to do."
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
        mock_recognize_intent.return_value = ("unknown_intent", {})

        await telegram_bot.handle_message(self.update, self.context)

        mock_recognize_intent.assert_called_once_with("some weird query")
        self.update.message.reply_text.assert_called_once_with(
            "I understood 'unknown_intent', but I don't know what to do."
        )

    @patch('telegram_bot.nlp_module.recognize_intent')
    async def test_handle_message_nlp_exception(self, mock_recognize_intent):
        self.update.message.text = "trigger nlp error"
        mock_recognize_intent.side_effect = Exception("NLP failed spectacularly")

        await telegram_bot.handle_message(self.update, self.context)

        mock_recognize_intent.assert_called_once_with("trigger nlp error")
        self.update.message.reply_text.assert_called_once_with(
            "An error occurred. Please try again later."
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
            "An error occurred. Please try again later."
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
