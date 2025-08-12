import unittest
from unittest.mock import patch, AsyncMock, MagicMock, ANY
import os
import sys
from pathlib import Path
import importlib # For reloading the module

# Set environment variables BEFORE importing the module to be tested
os.environ['TELEGRAM_TOKEN'] = 'test_telegram_token_long_enough'
os.environ['OPENAI_API_KEY'] = 'test_openai_api_key_long_enough'
# KATANA_LOG_LEVEL will be set in setUpClass if not present

project_root = Path(__file__).resolve().parent.parent.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

katan_bot_module_path = 'katana.bot.katana_bot' # For patching string references

# Attempt to import the module and necessary exception types
katana_bot = None
APIError, AuthenticationError, RateLimitError = None, None, None

try:
    from katana.bot import katana_bot
    from openai import APIError, AuthenticationError, RateLimitError
except KeyError as e:
    if 'KATANA_LOG_LEVEL' in str(e):
        print(f"Warning: KATANA_LOG_LEVEL env var not set during initial import. Details: {e}")
        os.environ['KATANA_LOG_LEVEL'] = 'INFO' # Set default and retry
        from katana.bot import katana_bot
        from openai import APIError, AuthenticationError, RateLimitError
    else:
        print(f"A non-KATANA_LOG_LEVEL KeyError occurred during initial import: {e}")
        raise # Re-raise if it's a different KeyError
except ImportError as e:
    print(f"An ImportError occurred during initial import: {e}. This might be due to missing dependencies.")
    # Define dummy classes for error types if openai itself failed to import, to allow test definitions
    if 'openai' in str(e) and APIError is None: # Check if not already defined
        class APIError(Exception): pass
        class AuthenticationError(Exception): pass
        class RateLimitError(Exception): pass
        print("Defined dummy OpenAI error classes for test structure.")
    # katana_bot will remain None; tests needing it should be skipped.

class TestKatanaBot(unittest.IsolatedAsyncioTestCase):

    @classmethod
    def setUpClass(cls):
        os.environ['TELEGRAM_TOKEN'] = 'test_telegram_token_long_enough'
        os.environ['OPENAI_API_KEY'] = 'test_openai_api_key_long_enough'
        if 'KATANA_LOG_LEVEL' not in os.environ:
             os.environ['KATANA_LOG_LEVEL'] = 'INFO'

        global katana_bot, APIError, AuthenticationError, RateLimitError
        try:
            # Ensure katana_bot module is loaded/reloaded with current env vars
            if 'katana.bot.katana_bot' in sys.modules:
                katana_bot = importlib.reload(sys.modules['katana.bot.katana_bot'])
            else:
                from katana.bot import katana_bot as kb_module
                katana_bot = kb_module

            # Ensure OpenAI error types are loaded
            if APIError is None: # If initial import failed for these
                from openai import APIError as OA_APIError, \
                                   AuthenticationError as OA_AuthenticationError, \
                                   RateLimitError as OA_RateLimitError
                APIError, AuthenticationError, RateLimitError = OA_APIError, OA_AuthenticationError, OA_RateLimitError
        except ImportError as e:
            print(f"Critical error: Failed to import katana_bot or OpenAI errors in setUpClass: {e}")
            katana_bot = None # Mark as unavailable

    @classmethod
    def tearDownClass(cls):
        for var in ['TELEGRAM_TOKEN', 'OPENAI_API_KEY', 'KATANA_LOG_LEVEL']:
            if var in os.environ:
                del os.environ[var]

    def setUp(self):
        if not katana_bot or not APIError: # Skip if essential imports failed
            self.skipTest("katana_bot module or OpenAI error types could not be loaded.")

        # Reload module for clean state, especially for its global 'client'
        globals()['katana_bot'] = importlib.reload(katana_bot)

        self.logger_patch = patch(f'{katan_bot_module_path}.logger', new_callable=MagicMock)
        self.mock_logger = self.logger_patch.start()
        self.addCleanup(self.logger_patch.stop)

        self.mock_update = AsyncMock()
        self.mock_update.effective_user.id = 12345
        self.mock_update.message.text = "Hello AI"
        self.mock_update.message.reply_text = AsyncMock()
        self.mock_context = MagicMock()

    async def test_start_command(self):
        await katana_bot.start(self.mock_update, self.mock_context)
        self.mock_update.message.reply_text.assert_called_once_with(
            "⚔️ Katana (AI Chat Mode) is online. Send me a message and I'll try to respond using OpenAI."
        )
        self.mock_logger.info.assert_any_call("Received /start command", extra={'user_id': 12345})

    @patch(f'{katan_bot_module_path}.client')
    async def test_handle_message_success(self, mock_openai_client):
        mock_completion = MagicMock()
        mock_completion.choices[0].message.content = "AI Response"
        mock_openai_client.chat.completions.create = AsyncMock(return_value=mock_completion)

        await katana_bot.handle_message(self.mock_update, self.mock_context)

        mock_openai_client.chat.completions.create.assert_called_once_with(
            model="gpt-4",
            messages=[{"role": "user", "content": "Hello AI"}]
        )
        self.mock_update.message.reply_text.assert_called_once_with("AI Response")
        self.mock_logger.info.assert_any_call(f"Received message: {self.mock_update.message.text[:100]}", extra={'user_id': 12345})

    async def test_handle_message_openai_client_not_initialized(self):
        with patch(f'{katan_bot_module_path}.client', None):
            await katana_bot.handle_message(self.mock_update, self.mock_context)
            self.mock_update.message.reply_text.assert_called_once_with(
                "I apologize, but my connection to the AI core (OpenAI) is not configured. Please contact the administrator."
            )
            self.mock_logger.error.assert_any_call("OpenAI client not initialized. Cannot process message.", extra={'user_id': 12345})

    @patch(f'{katan_bot_module_path}.client')
    async def test_handle_message_openai_authentication_error(self, mock_openai_client):
        # For openai > 1.0, AuthenticationError requires response and body args
        mock_response = MagicMock()
        mock_response.status_code = 401
        auth_error = AuthenticationError("auth error", response=mock_response, body=None)
        mock_openai_client.chat.completions.create = AsyncMock(side_effect=auth_error)
        await katana_bot.handle_message(self.mock_update, self.mock_context)
        self.mock_update.message.reply_text.assert_called_once_with(
            "Error: OpenAI authentication failed. Please check the API key configuration with the administrator."
        )
        self.mock_logger.error.assert_any_call("OpenAI Authentication Error: auth error. Check your API key.", extra={'user_id': 12345})

    @patch(f'{katan_bot_module_path}.client')
    async def test_handle_message_openai_rate_limit_error(self, mock_openai_client):
        # For openai > 1.0, RateLimitError requires response and body args
        mock_response = MagicMock()
        mock_response.status_code = 429
        rate_limit_error = RateLimitError("rate limit error", response=mock_response, body=None)
        mock_openai_client.chat.completions.create = AsyncMock(side_effect=rate_limit_error)
        await katana_bot.handle_message(self.mock_update, self.mock_context)
        self.mock_update.message.reply_text.assert_called_once_with("Error: OpenAI rate limit exceeded. Please try again later.")
        self.mock_logger.error.assert_any_call("OpenAI Rate Limit Error: rate limit error.", extra={'user_id': 12345})

    @patch(f'{katan_bot_module_path}.client')
    async def test_handle_message_openai_api_error(self, mock_openai_client):
        # For openai > 1.0, APIError requires request and body args
        mock_request = MagicMock()
        api_error = APIError("api error", request=mock_request, body=None)
        mock_openai_client.chat.completions.create = AsyncMock(side_effect=api_error)
        await katana_bot.handle_message(self.mock_update, self.mock_context)
        self.mock_update.message.reply_text.assert_called_once_with("An error occurred with the OpenAI API: api error")
        self.mock_logger.error.assert_any_call("OpenAI API Error: api error", extra={'user_id': 12345})

    @patch(f'{katan_bot_module_path}.client')
    async def test_handle_message_unexpected_error(self, mock_openai_client):
        mock_openai_client.chat.completions.create = AsyncMock(side_effect=Exception("unexpected error"))
        await katana_bot.handle_message(self.mock_update, self.mock_context)
        self.mock_update.message.reply_text.assert_called_once_with("Sorry, an unexpected error occurred while processing your message.")
        self.mock_logger.error.assert_any_call("An unexpected error occurred in handle_message: unexpected error", extra={'user_id': 12345}, exc_info=True)

    @patch(f'{katan_bot_module_path}.ApplicationBuilder')
    @patch.dict(os.environ, {'TELEGRAM_TOKEN': 'valid_token_for_main', 'OPENAI_API_KEY': 'valid_openai_key_for_main'})
    def test_main_success(self, mock_app_builder):
        globals()['katana_bot'] = importlib.reload(katana_bot)
        mock_app = MagicMock()
        mock_app_builder.return_value.token.return_value.build.return_value = mock_app

        katana_bot.main()

        mock_app_builder.return_value.token.assert_called_once_with('valid_token_for_main')
        self.assertEqual(mock_app.add_handler.call_count, 2)
        mock_app.run_polling.assert_called_once()
        self.mock_logger.info.assert_any_call(f"Initializing Katana Telegram Bot (AI Chat Mode) with token ending: ...{'main'[-4:]}")
        self.mock_logger.info.assert_any_call("Katana Telegram Bot (AI Chat Mode) is running. Press Ctrl-C to stop.")

    @patch.dict(os.environ, {'TELEGRAM_TOKEN': 'valid_token_for_main_no_openai', 'OPENAI_API_KEY': ''})
    @patch(f'{katan_bot_module_path}.ApplicationBuilder')
    def test_main_no_openai_key(self, mock_app_builder):
        globals()['katana_bot'] = importlib.reload(katana_bot)
        mock_app = MagicMock()
        mock_app_builder.return_value.token.return_value.build.return_value = mock_app

        katana_bot.main()
        self.mock_logger.warning.assert_any_call("OPENAI_API_KEY not found, OpenAI client not initialized. OpenAI features will be disabled.")
        self.mock_logger.error.assert_any_call("OpenAI API Key not set. Message handling will fail.")

    @patch.dict(os.environ, {'TELEGRAM_TOKEN': '', 'OPENAI_API_KEY': 'valid_openai_key_for_main_no_tg'})
    def test_main_no_telegram_token(self):
        globals()['katana_bot'] = importlib.reload(katana_bot)
        katana_bot.main()
        self.mock_logger.error.assert_any_call("Telegram bot cannot start: KATANA_TELEGRAM_TOKEN environment variable not set.")

    @patch.dict(os.environ, {'TELEGRAM_TOKEN': 'valid_token_for_main_polling_err', 'OPENAI_API_KEY': 'valid_openai_key_for_main_polling_err'})
    @patch(f'{katan_bot_module_path}.ApplicationBuilder')
    def test_main_polling_exception(self, mock_app_builder):
        globals()['katana_bot'] = importlib.reload(katana_bot)
        mock_app = MagicMock()
        mock_app_builder.return_value.token.return_value.build.return_value = mock_app
        mock_app.run_polling.side_effect = Exception("Polling error")

        katana_bot.main()

        self.mock_logger.error.assert_any_call("Error during bot polling: Polling error", exc_info=True)
        self.mock_logger.info.assert_any_call("Katana Telegram Bot (AI Chat Mode) stopped.")

if __name__ == '__main__':
    unittest.main()
