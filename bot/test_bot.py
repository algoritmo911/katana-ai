import unittest
from unittest.mock import MagicMock, patch, call
import json
import os # <--- ADDED IMPORT
import importlib # <--- ADDED IMPORT
from pathlib import Path
import shutil # For robust directory removal

# Assuming bot.py is in the same directory or accessible in PYTHONPATH
# import bot # Старый импорт, который может вызывать проблемы при тестировании
# from bot import katana_bot # MOVED: Import moved into setUp methods after patching os.environ
# Это позволяет избежать запуска всего bot.py как скрипта при импорте

# Попытка импортировать nlp_processor, если он существует (для будущей интеграции)
# try:
#     from bot import nlp_processor # Предполагаемое имя для NLP модуля/объекта
# except ImportError:
#     nlp_processor = None # Если его нет, то None

# It's generally better to import the module under test within test methods or setUp,
# especially if module-level code relies on patched environments.
# For now, we will adjust setUp methods.

# Global patch for KATANA_TELEGRAM_TOKEN to ensure it's set before module import
# The class-specific patches for NLP API keys will still apply for TestKatanaBotNLPIntegration
telegram_token_patch = patch.dict(os.environ, {"KATANA_TELEGRAM_TOKEN": "123456:ABCDEF_GLOBAL_TEST_TOKEN"})
telegram_token_patch.start() # Start it globally

# No decorator needed for TestBot anymore regarding this specific token, as it's globally patched.
# However, if TestBot needed *different* env vars than TestKatanaBotNLPIntegration, class decorators would still be useful.
# For KATANA_TELEGRAM_TOKEN, one global mock is fine for import.
class TestBot(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        # Import here after os.environ is patched for the class
        global katana_bot
        from bot import katana_bot as kb_module
        cls.katana_bot = kb_module

    def setUp(self):
        # Create a dummy commands directory for testing
        self.test_commands_dir = Path("test_commands_temp_dir") # Using a more unique name
        self.test_commands_dir.mkdir(parents=True, exist_ok=True)

        # Store original and set to test
        self.original_command_file_dir = self.katana_bot.COMMAND_FILE_DIR
        self.katana_bot.COMMAND_FILE_DIR = self.test_commands_dir

        # Mock the bot object and its methods
        # self.mock_bot_instance = MagicMock() # This was for mocking the TeleBot instance if it was a module global
        # self.bot_patcher = patch('bot.katana_bot.bot', self.mock_bot_instance)
        # self.mock_bot_module_instance = self.bot_patcher.start()
        # The actual bot instance used by handlers is now self.katana_bot.bot, so we patch that if needed,
        # or more likely, we mock the methods on self.katana_bot.bot directly if it's an instance.
        # For now, the self.mock_telebot_instance in TestKatanaBotNLPIntegration is more direct.
        # The original TestBot mocks katana_bot.bot which is correct for its context.
        # Let's ensure TestBot's self.mock_bot_module_instance is correctly patching self.katana_bot.bot.

        self.mock_bot_instance_for_TestBot = MagicMock()
        self.bot_patcher = patch.object(self.katana_bot, 'bot', self.mock_bot_instance_for_TestBot)
        self.mock_bot_module_instance = self.bot_patcher.start() # This will be self.mock_bot_instance_for_TestBot

        # Mock datetime to control timestamps in filenames
        self.mock_datetime_patcher = patch.object(self.katana_bot, 'datetime')
        self.mock_datetime = self.mock_datetime_patcher.start()
        self.mock_datetime.utcnow.return_value.strftime.return_value = "YYYYMMDD_HHMMSS_ffffff"


    def tearDown(self):
        # Stop patchers
        self.bot_patcher.stop()
        self.mock_datetime_patcher.stop()

        # Clean up: remove dummy directory and its contents
        if self.test_commands_dir.exists():
            shutil.rmtree(self.test_commands_dir) # shutil.rmtree is more robust for non-empty dirs

        # Restore original
        self.katana_bot.COMMAND_FILE_DIR = self.original_command_file_dir


    def _create_mock_message(self, text_payload):
        mock_message = MagicMock()
        mock_message.chat.id = 12345
        mock_message.text = json.dumps(text_payload)
        return mock_message

    # --- Test Command Validation ---
    def test_valid_command_gets_saved(self):
        command = {"type": "test_type", "module": "test_module", "args": {}, "id": "test_id"}
        mock_message = self._create_mock_message(command)
        
        self.katana_bot.handle_message(mock_message)
        
        # Check file creation
        expected_module_dir = self.test_commands_dir / "telegram_mod_test_module"
        self.assertTrue(expected_module_dir.exists())
        
        expected_filename = f"YYYYMMDD_HHMMSS_ffffff_{mock_message.chat.id}.json"
        expected_file_path = expected_module_dir / expected_filename
        self.assertTrue(expected_file_path.exists())

        with open(expected_file_path, "r") as f:
            saved_data = json.load(f)
        self.assertEqual(saved_data, command)

        # Check reply
        self.mock_bot_module_instance.reply_to.assert_called_once()
        args, kwargs = self.mock_bot_module_instance.reply_to.call_args
        self.assertEqual(args[0], mock_message)
        self.assertTrue(args[1].startswith("✅ Command received and saved as"))
        self.assertIn(str(expected_file_path), args[1])


    def test_invalid_json_format(self):
        mock_message = MagicMock() # Simpler mock for this case
        mock_message.chat.id = 123
        mock_message.text = "not a valid json"
        self.katana_bot.handle_message(mock_message)
        self.mock_bot_module_instance.reply_to.assert_called_with(mock_message, "❌ Error: Invalid JSON format.")

    def test_missing_type_field(self):
        command = {"module": "test_module", "args": {}, "id": "test_id"} # type is missing
        mock_message = self._create_mock_message(command)
        self.katana_bot.handle_message(mock_message)
        self.mock_bot_module_instance.reply_to.assert_called_with(mock_message, "❌ Error: Missing required field 'type'.")

    def test_invalid_args_type(self):
        command = {"type": "test_type", "module": "test_module", "args": "not_a_dict", "id": "test_id"}
        mock_message = self._create_mock_message(command)
        self.katana_bot.handle_message(mock_message)
        self.mock_bot_module_instance.reply_to.assert_called_with(mock_message, "❌ Error: Field 'args' must be type dict. Got str.")

    def test_invalid_id_type(self):
        command = {"type": "test_type", "module": "test_module", "args": {}, "id": [1,2,3]} # id is a list
        mock_message = self._create_mock_message(command)
        self.katana_bot.handle_message(mock_message)
        self.mock_bot_module_instance.reply_to.assert_called_with(mock_message, "❌ Error: Field 'id' must be type str or int. Got list.")


    # --- Test Command Routing ---
    @patch('bot.katana_bot.handle_log_event') # Patching the function in the already imported katana_bot
    def test_routing_log_event(self, mock_handle_log_event_func):
        command = {"type": "log_event", "module": "logging", "args": {"message": "hello"}, "id": "log001"}
        mock_message = self._create_mock_message(command)

        self.katana_bot.handle_message(mock_message)

        mock_handle_log_event_func.assert_called_once_with(command, mock_message.chat.id)
        self.mock_bot_module_instance.reply_to.assert_called_with(mock_message, "✅ 'log_event' processed (placeholder).")


    @patch('bot.katana_bot.handle_mind_clearing') # Patching the function in the already imported katana_bot
    def test_routing_mind_clearing(self, mock_handle_mind_clearing_func):
        command = {"type": "mind_clearing", "module": "wellness", "args": {"duration": "10m"}, "id": "mind002"}
        mock_message = self._create_mock_message(command)

        self.katana_bot.handle_message(mock_message)
        
        mock_handle_mind_clearing_func.assert_called_once_with(command, mock_message.chat.id)
        self.mock_bot_module_instance.reply_to.assert_called_with(mock_message, "✅ 'mind_clearing' processed (placeholder).")

    # --- Test NLP and Logging Integration (Initial Structure) ---
    # This test seems outdated given the new NLP integration. It mocks 'log_local_bot_event'
    # which has been replaced by the standard logger. It also mocks a non-existent 'handle_nlp_command'.
    # I will remove this test or adapt it significantly if there's a relevant scenario.
    # For now, removing it as its purpose is covered by TestKatanaBotNLPIntegration.
    # @patch('bot.katana_bot.log_local_bot_event')
    # @patch('bot.katana_bot.handle_nlp_command', create=True)
    # def test_nlp_command_integration(self, mock_handle_nlp_command, mock_log_local_bot_event):
    #     ... (rest of the old test_nlp_command_integration code)


    # This test also uses the old log_local_bot_event. It should be updated to use the new logger.
    # However, the core functionality (saving command, reply) is already tested in test_valid_command_gets_saved.
    # Logging specific to this path can be checked by patching self.katana_bot.logger.
    @patch('bot.katana_bot.logger') # Patch the new logger
    def test_logging_on_standard_command_save(self, mock_logger_instance):
        command = {"type": "test_log", "module": "logging_test", "args": {}, "id": "log_test_001"}
        mock_message = self._create_mock_message(command)

        self.katana_bot.handle_message(mock_message)

        expected_module_dir = self.test_commands_dir / "telegram_mod_logging_test"
        expected_filename = f"YYYYMMDD_HHMMSS_ffffff_{mock_message.chat.id}.json"
        expected_file_path = expected_module_dir / expected_filename

        self.assertTrue(expected_file_path.exists())
        self.mock_bot_module_instance.reply_to.assert_called_once()
        args, kwargs = self.mock_bot_module_instance.reply_to.call_args
        self.assertTrue(args[1].startswith("✅ Command received and saved as"))

        # Check specific log calls related to this path
        mock_logger_instance.info.assert_any_call(f"Received message from {mock_message.chat.id}: {mock_message.text}")
        # The exact message for "not specifically handled" might change based on module presence
        # For a command with a module that's not NLP and no specific type handler:
        mock_logger_instance.info.assert_any_call(f"Command type 'test_log' for module 'logging_test' not specifically handled by NLP or other handlers, proceeding with default save.")
        mock_logger_instance.info.assert_any_call(f"Saved command from {mock_message.chat.id} to {str(expected_file_path)}")


    def test_unknown_command_type_saves_normally(self):
        command = {"type": "unknown_type", "module": "custom_module", "args": {}, "id": "custom003"}
        mock_message = self._create_mock_message(command)

        self.katana_bot.handle_message(mock_message)

        # Check file creation
        expected_module_dir = self.test_commands_dir / "telegram_mod_custom_module"
        self.assertTrue(expected_module_dir.exists())
        
        expected_filename = f"YYYYMMDD_HHMMSS_ffffff_{mock_message.chat.id}.json"
        expected_file_path = expected_module_dir / expected_filename
        self.assertTrue(expected_file_path.exists())

        with open(expected_file_path, "r") as f:
            saved_data = json.load(f)
        self.assertEqual(saved_data, command)

        # Check reply
        self.mock_bot_module_instance.reply_to.assert_called_once()
        args, kwargs = self.mock_bot_module_instance.reply_to.call_args
        self.assertEqual(args[0], mock_message)
        self.assertTrue(args[1].startswith("✅ Command received and saved as"))
        self.assertIn(str(expected_file_path), args[1])


if __name__ == '__main__':
    unittest.main()

def tearDownModule():
    telegram_token_patch.stop() # Stop the global patch


# --- New Test Class for NLP Integration ---
# KATANA_TELEGRAM_TOKEN is now patched globally.
# We only need to patch the specific API keys for this test class if they differ or need ensuring.
# Removing @patch.dict for API keys here, will patch directly in setUp.
class TestKatanaBotNLPIntegration(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # KATANA_TELEGRAM_TOKEN is patched globally.
        # Import katana_bot here.
        from bot import katana_bot as kb_module_nlp
        cls.katana_bot = kb_module_nlp

    def setUp(self):
        # Mock the bot TeleBot instance itself for .reply_to assertions
        self.mock_telebot_instance = MagicMock()
        # Patching the bot instance on the already loaded self.katana_bot module
        self.telebot_patcher = patch.object(self.katana_bot, 'bot', self.mock_telebot_instance)
        self.mock_telebot_instance_for_module = self.telebot_patcher.start()

        # Directly patch the API key constants on the loaded katana_bot module for this test class
        self.anthropic_key_patcher = patch.object(self.katana_bot, 'ANTHROPIC_API_KEY', "test_anthropic_key_direct_patch")
        self.openai_key_patcher = patch.object(self.katana_bot, 'OPENAI_API_KEY', "test_openai_key_direct_patch")
        self.PatchedAnthropicKey = self.anthropic_key_patcher.start()
        self.PatchedOpenAIKey = self.openai_key_patcher.start()

        # Mock the NLP Clients
        self.mock_anthropic_client_instance = MagicMock()
        self.anthropic_client_patcher = patch.object(self.katana_bot, 'AnthropicClient', return_value=self.mock_anthropic_client_instance)
        self.MockAnthropicClientClass = self.anthropic_client_patcher.start()

        self.mock_openai_client_instance = MagicMock()
        self.openai_client_patcher = patch.object(self.katana_bot, 'OpenAIClient', return_value=self.mock_openai_client_instance)
        self.MockOpenAIClientClass = self.openai_client_patcher.start()

        # Patch the logger within katana_bot module
        self.logger_patcher = patch.object(self.katana_bot, 'logger')
        self.mock_logger = self.logger_patcher.start()

        # Ensure COMMAND_FILE_DIR is also mocked if any fallback to file saving occurs
        self.test_commands_dir_nlp = Path("test_commands_temp_dir_nlp")
        self.test_commands_dir_nlp.mkdir(parents=True, exist_ok=True)
        self.original_command_file_dir_nlp = self.katana_bot.COMMAND_FILE_DIR
        self.katana_bot.COMMAND_FILE_DIR = self.test_commands_dir_nlp

        # Mock datetime for consistent file naming if any non-NLP command is tested
        self.mock_datetime_patcher_nlp = patch.object(self.katana_bot, 'datetime')
        self.mock_datetime_nlp = self.mock_datetime_patcher_nlp.start()
        self.mock_datetime_nlp.utcnow.return_value.strftime.return_value = "NLP_TEST_TIME"


    def tearDown(self):
        self.telebot_patcher.stop()
        self.anthropic_key_patcher.stop()
        self.openai_key_patcher.stop()
        self.anthropic_client_patcher.stop()
        self.openai_client_patcher.stop()
        self.logger_patcher.stop()
        self.mock_datetime_patcher_nlp.stop()

        if self.test_commands_dir_nlp.exists():
            shutil.rmtree(self.test_commands_dir_nlp)
        self.katana_bot.COMMAND_FILE_DIR = self.original_command_file_dir_nlp

    def _create_mock_message(self, text_payload):
        mock_message = MagicMock()
        mock_message.chat.id = 67890
        mock_message.text = json.dumps(text_payload)
        return mock_message

    def test_anthropic_chat_success(self):
        prompt_text = "Hello Anthropic!"
        command = {
            "type": "nlp_query",
            "module": self.katana_bot.NLP_MODULE_ANTHROPIC,
            "args": {"prompt": prompt_text},
            "id": "anthropic001"
        }
        mock_message = self._create_mock_message(command)

        expected_response = "Anthropic says: Hello there!"
        self.mock_anthropic_client_instance.generate_text.return_value = expected_response

        self.katana_bot.handle_message(mock_message)

        self.MockAnthropicClientClass.assert_called_once_with(api_key="test_anthropic_key_direct_patch")
        self.mock_anthropic_client_instance.generate_text.assert_called_once_with(prompt=prompt_text, scenario="success")
        self.mock_telebot_instance_for_module.reply_to.assert_called_once_with(mock_message, expected_response)

        # Check logs
        self.mock_logger.info.assert_any_call(f"Received message from {mock_message.chat.id}: {mock_message.text}")
        self.mock_logger.info.assert_any_call(f"Attempting to get NLP response for module: {self.katana_bot.NLP_MODULE_ANTHROPIC}")
        self.mock_logger.info.assert_any_call(f"Using Anthropic client. Prompt: '{prompt_text[:50]}...'")
        self.mock_logger.info.assert_any_call(f"Anthropic client success. Response: '{expected_response[:50]}...'")
        self.mock_logger.info.assert_any_call(f"Sent NLP response to {mock_message.chat.id} for module {self.katana_bot.NLP_MODULE_ANTHROPIC}.")

    def test_openai_chat_success(self):
        prompt_text = "Hello OpenAI!"
        command = {
            "type": "nlp_query",
            "module": self.katana_bot.NLP_MODULE_OPENAI,
            "args": {"prompt": prompt_text},
            "id": "openai001"
        }
        mock_message = self._create_mock_message(command)

        expected_response = "OpenAI says: Greetings!"
        self.mock_openai_client_instance.generate_text.return_value = expected_response

        self.katana_bot.handle_message(mock_message)

        self.MockOpenAIClientClass.assert_called_once_with(api_key="test_openai_key_direct_patch")
        self.mock_openai_client_instance.generate_text.assert_called_once_with(prompt=prompt_text, scenario="success")
        self.mock_telebot_instance_for_module.reply_to.assert_called_once_with(mock_message, expected_response)

        # Check logs
        self.mock_logger.info.assert_any_call(f"Received message from {mock_message.chat.id}: {mock_message.text}")
        self.mock_logger.info.assert_any_call(f"Attempting to get NLP response for module: {self.katana_bot.NLP_MODULE_OPENAI}")
        self.mock_logger.info.assert_any_call(f"Using OpenAI client. Prompt: '{prompt_text[:50]}...'")
        self.mock_logger.info.assert_any_call(f"OpenAI client success. Response: '{expected_response[:50]}...'")
        self.mock_logger.info.assert_any_call(f"Sent NLP response to {mock_message.chat.id} for module {self.katana_bot.NLP_MODULE_OPENAI}.")

    def test_anthropic_authentication_error(self):
        prompt_text = "Test auth error"
        command = {
            "type": "nlp_query",
            "module": self.katana_bot.NLP_MODULE_ANTHROPIC,
            "args": {"prompt": prompt_text},
            "id": "anthropic_auth_fail"
        }
        mock_message = self._create_mock_message(command)

        user_facing_error_msg = "Anthropic auth failed."
        original_err = RuntimeError("Original API auth error")

        from bot.nlp_clients.anthropic_client import AnthropicAuthenticationError # Import here to ensure it's from the right context
        self.mock_anthropic_client_instance.generate_text.side_effect = AnthropicAuthenticationError(
            user_message=user_facing_error_msg, original_error=original_err
        )

        self.katana_bot.handle_message(mock_message)

        self.MockAnthropicClientClass.assert_called_once_with(api_key="test_anthropic_key_direct_patch")
        self.mock_anthropic_client_instance.generate_text.assert_called_once_with(prompt=prompt_text, scenario="success")
        self.mock_telebot_instance_for_module.reply_to.assert_called_once_with(mock_message, user_facing_error_msg)

        self.mock_logger.error.assert_any_call(
            f"NLPServiceError caught for module {self.katana_bot.NLP_MODULE_ANTHROPIC}. User Message: '{user_facing_error_msg}'. Original Error: {type(original_err).__name__} - {original_err}",
            exc_info=True
        )

    def test_openai_api_error(self):
        prompt_text = "Test API error"
        command = {
            "type": "nlp_query",
            "module": self.katana_bot.NLP_MODULE_OPENAI,
            "args": {"prompt": prompt_text},
            "id": "openai_api_fail"
        }
        mock_message = self._create_mock_message(command)

        user_facing_error_msg = "OpenAI API has a problem."
        original_err = ConnectionError("Service unavailable")
        from bot.nlp_clients.openai_client import OpenAIAPIError
        self.mock_openai_client_instance.generate_text.side_effect = OpenAIAPIError(
            user_message=user_facing_error_msg, original_error=original_err
        )

        self.katana_bot.handle_message(mock_message)

        self.MockOpenAIClientClass.assert_called_once_with(api_key="test_openai_key_direct_patch")
        self.mock_openai_client_instance.generate_text.assert_called_once_with(prompt=prompt_text, scenario="success")
        self.mock_telebot_instance_for_module.reply_to.assert_called_once_with(mock_message, user_facing_error_msg)

        self.mock_logger.error.assert_any_call(
            f"NLPServiceError caught for module {self.katana_bot.NLP_MODULE_OPENAI}. User Message: '{user_facing_error_msg}'. Original Error: {type(original_err).__name__} - {original_err}",
            exc_info=True
        )

    def test_nlp_command_missing_prompt(self):
        command = {
            "type": "nlp_query",
            "module": self.katana_bot.NLP_MODULE_ANTHROPIC,
            "args": {},
            "id": "anthropic_no_prompt"
        }
        mock_message = self._create_mock_message(command)

        self.katana_bot.handle_message(mock_message)

        expected_error_msg = "❌ Error: Missing 'prompt' in 'args' for NLP command or it's not a string."
        self.mock_telebot_instance_for_module.reply_to.assert_called_once_with(mock_message, expected_error_msg)
        self.mock_logger.warning.assert_any_call(
            f"NLP command validation failed for {mock_message.chat.id}: {expected_error_msg} (Command: {mock_message.text})"
        )
        self.MockAnthropicClientClass.assert_not_called()

    def test_unknown_nlp_module(self):
        prompt_text = "Test unknown module"
        command = {
            "type": "nlp_query",
            "module": "future_nlp_chat_module",
            "args": {"prompt": prompt_text},
            "id": "unknown_nlp_module_id"
        }
        mock_message = self._create_mock_message(command)

        self.katana_bot.handle_message(mock_message)

        expected_response = "❌ Error: Unknown NLP module 'future_nlp_chat_module'. Cannot process request."
        self.mock_telebot_instance_for_module.reply_to.assert_called_once_with(mock_message, expected_response)
        self.mock_logger.warning.assert_any_call("Unknown NLP module specified: future_nlp_chat_module")
        self.MockAnthropicClientClass.assert_not_called()
        self.MockOpenAIClientClass.assert_not_called()

    def test_unexpected_error_in_get_nlp_response(self):
        prompt_text = "Test unexpected error"
        command = {
            "type": "nlp_query",
            "module": self.katana_bot.NLP_MODULE_OPENAI,
            "args": {"prompt": prompt_text},
            "id": "openai_unexpected_fail"
        }
        mock_message = self._create_mock_message(command)

        original_err_msg = "Something totally unexpected broke!"
        self.mock_openai_client_instance.generate_text.side_effect = Exception(original_err_msg)

        self.katana_bot.handle_message(mock_message)

        expected_user_response = "❌ An unexpected system error occurred while trying to process your request. Please try again later."
        self.mock_telebot_instance_for_module.reply_to.assert_called_once_with(mock_message, expected_user_response)

        self.mock_logger.critical.assert_any_call(
            f"Unexpected critical error during NLP processing for module {self.katana_bot.NLP_MODULE_OPENAI}! Error: Exception - {original_err_msg}",
            exc_info=True
        )

if __name__ == '__main__':
    unittest.main()
