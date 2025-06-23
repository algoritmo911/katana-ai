import unittest
from unittest.mock import MagicMock, patch, call
import json
from pathlib import Path
import shutil # For robust directory removal
import os # Import os as it's used by patch.dict(os.environ, ...)
import logging # For checking log levels in tests
import signal # For signal related tests

# Imports for NLP client testing
from nlp_services.base_nlp_client import NLPServiceError, NLPAuthenticationError # For simulating errors

# katana_bot will be imported in setUpClass after patching os.environ
katana_bot = None

class TestBot(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.env_patcher = patch.dict(os.environ, {'KATANA_TELEGRAM_TOKEN': '123456:ABCDEF_mocked_for_tests'})
        cls.env_patcher.start()

        # Import katana_bot module here, after environment is patched
        global katana_bot # So that test methods can access it if they were using global
        from bot import katana_bot as kb_module
        cls.katana_bot = kb_module # Make it a class attribute
        katana_bot = kb_module # also update global if tests relied on it (less ideal)


    @classmethod
    def tearDownClass(cls):
        cls.env_patcher.stop()

    def setUp(self):
        # Create a dummy commands directory for testing
        self.test_commands_dir = Path("test_commands_temp_dir_bot") # Using a more unique name
        self.test_commands_dir.mkdir(parents=True, exist_ok=True)

        # Store original and set to test using cls.katana_bot
        self.original_command_file_dir = self.katana_bot.COMMAND_FILE_DIR
        katana_bot.COMMAND_FILE_DIR = self.test_commands_dir

        # Mock the bot object and its methods (already instantiated in the reloaded katana_bot)
        self.mock_bot_instance = MagicMock()
        # Patch the bot instance within the 'katana_bot' module (which is now self.katana_bot)
        self.bot_patcher = patch.object(self.katana_bot, 'bot', self.mock_bot_instance)
        self.mock_bot_module_instance = self.bot_patcher.start() # This is the mocked bot instance

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
            shutil.rmtree(self.test_commands_dir)

        # Restore original using cls.katana_bot
        self.katana_bot.COMMAND_FILE_DIR = self.original_command_file_dir


    def _create_mock_message(self, text_payload):
        mock_message = MagicMock()
        mock_message.chat.id = 12345
        mock_message.text = json.dumps(text_payload)
        # Add from_user mock if UserID is logged and checked
        mock_message.from_user = MagicMock()
        mock_message.from_user.id = 67890
        return mock_message

    # --- Test Command Validation ---
    def test_valid_command_gets_saved(self):
        command = {"type": "test_type", "module": "test_module", "args": {}, "id": "test_id"}
        mock_message = self._create_mock_message(command)
        
        self.katana_bot.handle_message(mock_message)
        
        expected_module_dir = self.test_commands_dir / "telegram_mod_test_module"
        self.assertTrue(expected_module_dir.exists())
        expected_filename = f"YYYYMMDD_HHMMSS_ffffff_{mock_message.chat.id}.json"
        expected_file_path = expected_module_dir / expected_filename
        self.assertTrue(expected_file_path.exists())
        with open(expected_file_path, "r") as f:
            saved_data = json.load(f)
        self.assertEqual(saved_data, command)
        self.mock_bot_module_instance.reply_to.assert_called_once()
        args, kwargs = self.mock_bot_module_instance.reply_to.call_args
        self.assertEqual(args[0], mock_message)
        self.assertTrue(args[1].startswith("✅ Command received and saved as"))
        self.assertIn(str(expected_file_path), args[1])

    def test_invalid_json_format(self):
        mock_message = MagicMock()
        mock_message.chat.id = 123
        mock_message.text = "not a valid json"
        mock_message.from_user = MagicMock()
        mock_message.from_user.id = 67890
        self.katana_bot.handle_message(mock_message)
        self.mock_bot_module_instance.reply_to.assert_called_with(mock_message, "❌ Error: Invalid JSON format.")

    def test_missing_type_field(self):
        command = {"module": "test_module", "args": {}, "id": "test_id"}
        mock_message = self._create_mock_message(command)
        self.katana_bot.handle_message(mock_message)
        self.mock_bot_module_instance.reply_to.assert_called_with(mock_message, "❌ Error: Missing required field 'type'.")

    def test_invalid_args_type(self):
        command = {"type": "test_type", "module": "test_module", "args": "not_a_dict", "id": "test_id"}
        mock_message = self._create_mock_message(command)
        self.katana_bot.handle_message(mock_message)
        self.mock_bot_module_instance.reply_to.assert_called_with(mock_message, "❌ Error: Field 'args' must be type dict. Got str.")

    def test_invalid_id_type(self):
        command = {"type": "test_type", "module": "test_module", "args": {}, "id": [1,2,3]}
        mock_message = self._create_mock_message(command)
        self.katana_bot.handle_message(mock_message)
        self.mock_bot_module_instance.reply_to.assert_called_with(mock_message, "❌ Error: Field 'id' must be type str or int. Got list.")

    # --- Test Command Routing ---
    @patch('bot.katana_bot.handle_log_event')
    def test_routing_log_event(self, mock_handle_log_event_func):
        command = {"type": "log_event", "module": "logging", "args": {"message": "hello"}, "id": "log001"}
        mock_message = self._create_mock_message(command)
        self.katana_bot.handle_message(mock_message)
        mock_handle_log_event_func.assert_called_once_with(command, mock_message.chat.id)
        self.mock_bot_module_instance.reply_to.assert_called_with(mock_message, "✅ 'log_event' processed (placeholder).")

    @patch('bot.katana_bot.handle_mind_clearing')
    def test_routing_mind_clearing(self, mock_handle_mind_clearing_func):
        command = {"type": "mind_clearing", "module": "wellness", "args": {"duration": "10m"}, "id": "mind002"}
        mock_message = self._create_mock_message(command)
        self.katana_bot.handle_message(mock_message)
        mock_handle_mind_clearing_func.assert_called_once_with(command, mock_message.chat.id)
        self.mock_bot_module_instance.reply_to.assert_called_with(mock_message, "✅ 'mind_clearing' processed (placeholder).")

    @patch('bot.katana_bot.log_local_bot_event')
    @patch('bot.katana_bot.handle_nlp_command', create=True)
    def test_nlp_command_integration(self, mock_handle_nlp_command, mock_log_local_bot_event):
        command_text = "Проанализируй этот текст"
        command_payload = {"type": "nlp_process", "module": "nlp", "args": {"text": command_text}, "id": "nlp001"}
        mock_message = self._create_mock_message(command_payload)
        self.katana_bot.handle_message(mock_message)
        expected_module_dir = self.test_commands_dir / "telegram_mod_nlp"
        self.assertTrue(expected_module_dir.exists())
        expected_filename = f"YYYYMMDD_HHMMSS_ffffff_{mock_message.chat.id}.json"
        expected_file_path = expected_module_dir / expected_filename
        self.assertTrue(expected_file_path.exists())
        with open(expected_file_path, "r") as f:
            saved_data = json.load(f)
        self.assertEqual(saved_data, command_payload)
        self.mock_bot_module_instance.reply_to.assert_called_with(mock_message, f"✅ Command received and saved as `{str(expected_file_path)}`.")
        mock_handle_nlp_command.assert_not_called()
        actual_log_calls = [call_item[0][0] for call_item in mock_log_local_bot_event.call_args_list if call_item[0]]
        received_log_found = any(f"Received message. ChatID: {mock_message.chat.id}" in log_msg and f"UserID: " in log_msg and f"Text: \"{mock_message.text}\"" in log_msg for log_msg in actual_log_calls)
        self.assertTrue(received_log_found)
        self.assertIn(f"Command type 'nlp_process' with module 'nlp' not specifically handled by NLP, proceeding with default save.", actual_log_calls)
        self.assertIn(f"Saved command from {mock_message.chat.id} to {str(expected_file_path)}", actual_log_calls)

    @patch('bot.katana_bot.log_local_bot_event')
    def test_logging_on_standard_command(self, mock_log_local_bot_event):
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
        actual_log_calls = [call_item[0][0] for call_item in mock_log_local_bot_event.call_args_list if call_item[0]]
        received_log_found = any(f"Received message. ChatID: {mock_message.chat.id}" in log_msg and f"UserID: " in log_msg and f"Text: \"{mock_message.text}\"" in log_msg for log_msg in actual_log_calls)
        self.assertTrue(received_log_found)
        self.assertIn(f"Command type 'test_log' with module 'logging_test' not specifically handled by NLP, proceeding with default save.", actual_log_calls)
        self.assertIn(f"Saved command from {mock_message.chat.id} to {str(expected_file_path)}", actual_log_calls)

    # --- Tests for NLP Integration ---
    @patch('bot.katana_bot.get_anthropic_chat_response')
    @patch('bot.katana_bot.log_local_bot_event')
    def test_handle_message_anthropic_chat_success(self, mock_log_event, mock_get_anthropic_response):
        mock_get_anthropic_response.return_value = "Anthropic says hello!"
        command_payload = {"type": "chat_query", "module": "anthropic_chat", "args": {"prompt": "Hello Anthropic", "history": [{"role": "user", "content": "Previous q"}], "model_name": "claude-test-model", "system_prompt": "Be brief.", "max_tokens": 50}, "id": "anthropic001"}
        mock_message = self._create_mock_message(command_payload)
        self.katana_bot.handle_message(mock_message)
        mock_get_anthropic_response.assert_called_once_with(history=command_payload["args"]["history"], user_prompt=command_payload["args"]["prompt"], model_name="claude-test-model", system_prompt="Be brief.", max_tokens_to_sample=50)
        self.mock_bot_module_instance.reply_to.assert_called_once_with(mock_message, "🤖: Anthropic says hello!")
        log_messages = [args[0] for args, kwargs in mock_log_event.call_args_list]
        self.assertIn(f"Processing 'anthropic_chat' for {mock_message.chat.id}. Prompt: '{command_payload['args']['prompt'][:50]}...'", log_messages)
        self.assertIn(f"Successfully replied to 'anthropic_chat' for {mock_message.chat.id}. Response: '{mock_get_anthropic_response.return_value[:50]}...'", log_messages)

    @patch('bot.katana_bot.get_openai_chat_response')
    @patch('bot.katana_bot.log_local_bot_event')
    def test_handle_message_openai_chat_success(self, mock_log_event, mock_get_openai_response):
        mock_get_openai_response.return_value = "OpenAI says hello!"
        command_payload = {"type": "chat_query", "module": "openai_chat", "args": {"prompt": "Hello OpenAI", "history": [], "model_name": "gpt-test-model", "system_prompt": "Be very helpful.", "max_tokens": 100}, "id": "openai001"}
        mock_message = self._create_mock_message(command_payload)
        self.katana_bot.handle_message(mock_message)
        mock_get_openai_response.assert_called_once_with(history=[], user_prompt="Hello OpenAI", model_name="gpt-test-model", system_prompt="Be very helpful.", max_tokens=100)
        self.mock_bot_module_instance.reply_to.assert_called_once_with(mock_message, "🤖: OpenAI says hello!")
        log_messages = [args[0] for args, kwargs in mock_log_event.call_args_list]
        self.assertIn(f"Processing 'openai_chat' for {mock_message.chat.id}. Prompt: '{command_payload['args']['prompt'][:50]}...'", log_messages)
        self.assertIn(f"Successfully replied to 'openai_chat' for {mock_message.chat.id}. Response: '{mock_get_openai_response.return_value[:50]}...'", log_messages)

    @patch('bot.katana_bot.get_anthropic_chat_response')
    @patch('bot.katana_bot.log_local_bot_event')
    def test_handle_message_anthropic_chat_nlp_error(self, mock_log_event, mock_get_anthropic_response):
        error_user_message = "Anthropic сервис временно недоступен."
        simulated_error = NLPAuthenticationError(message="Original Anthropic Auth Error", original_error=Exception("Original low-level exception"), user_message=error_user_message)
        mock_get_anthropic_response.side_effect = simulated_error
        command_payload = {"type": "chat_query", "module": "anthropic_chat", "args": {"prompt": "Hello failed Anthropic"}, "id": "anthropic_err_001"}
        mock_message = self._create_mock_message(command_payload)
        self.katana_bot.handle_message(mock_message)
        mock_get_anthropic_response.assert_called_once()
        self.mock_bot_module_instance.reply_to.assert_called_once_with(mock_message, f"🤖⚠️: {error_user_message}")
        error_log_found = False
        for call_args, call_kwargs in mock_log_event.call_args_list:
            log_message = call_args[0]
            log_level = call_kwargs.get('level')
            if log_level == logging.ERROR and "NLP Error for module anthropic_chat" in log_message and "Original Anthropic Auth Error" in log_message:
                self.assertTrue(call_kwargs.get('exc_info', False))
                error_log_found = True
                break
        self.assertTrue(error_log_found, "Specific NLP error log message not found.")

    @patch('bot.katana_bot.get_openai_chat_response')
    @patch('bot.katana_bot.log_local_bot_event')
    def test_handle_message_openai_chat_nlp_error(self, mock_log_event, mock_get_openai_response):
        error_user_message = "OpenAI сервис сейчас недоступен."
        simulated_error = NLPServiceError(message="Original OpenAI Some Error", original_error=RuntimeError("Original runtime error from OpenAI client"), user_message=error_user_message)
        mock_get_openai_response.side_effect = simulated_error
        command_payload = {"type": "chat_query", "module": "openai_chat", "args": {"prompt": "Hello failed OpenAI"}, "id": "openai_err_001"}
        mock_message = self._create_mock_message(command_payload)
        self.katana_bot.handle_message(mock_message)
        mock_get_openai_response.assert_called_once()
        self.mock_bot_module_instance.reply_to.assert_called_once_with(mock_message, f"🤖⚠️: {error_user_message}")
        error_log_found = False
        for call_args, call_kwargs in mock_log_event.call_args_list:
            log_message = call_args[0]
            log_level = call_kwargs.get('level')
            if log_level == logging.ERROR and "NLP Error for module openai_chat" in log_message and "Original OpenAI Some Error" in log_message:
                self.assertTrue(call_kwargs.get('exc_info', False))
                error_log_found = True
                break
        self.assertTrue(error_log_found, "Specific NLP error log message not found.")

    @patch('bot.katana_bot.log_local_bot_event')
    def test_handle_message_anthropic_chat_missing_prompt(self, mock_log_event):
        command_payload = {"type": "chat_query", "module": "anthropic_chat", "args": {}, "id": "anthropic_missing_prompt"}
        mock_message = self._create_mock_message(command_payload)
        self.katana_bot.handle_message(mock_message)
        self.mock_bot_module_instance.reply_to.assert_called_once_with(mock_message, "❌ Error: 'prompt' is a required argument in 'args' for module 'anthropic_chat'.")
        error_log_found = False
        for call_args, call_kwargs in mock_log_event.call_args_list:
            if call_kwargs.get('level') == logging.ERROR and "Missing 'prompt' for anthropic_chat" in call_args[0]:
                error_log_found = True; break
        self.assertTrue(error_log_found)

    @patch('bot.katana_bot.log_local_bot_event')
    def test_handle_message_openai_chat_missing_prompt(self, mock_log_event):
        command_payload = {"type": "chat_query", "module": "openai_chat", "args": {}, "id": "openai_missing_prompt"}
        mock_message = self._create_mock_message(command_payload)
        self.katana_bot.handle_message(mock_message)
        self.mock_bot_module_instance.reply_to.assert_called_once_with(mock_message, "❌ Error: 'prompt' is a required argument in 'args' for module 'openai_chat'.")
        error_log_found = False
        for call_args, call_kwargs in mock_log_event.call_args_list:
            if call_kwargs.get('level') == logging.ERROR and "Missing 'prompt' for openai_chat" in call_args[0]:
                error_log_found = True; break
        self.assertTrue(error_log_found)

    @patch('bot.katana_bot.get_anthropic_chat_response')
    @patch('bot.katana_bot.log_local_bot_event')
    def test_handle_message_nlp_unexpected_error(self, mock_log_event, mock_get_anthropic_response):
        simulated_error = KeyError("A very unexpected key error!")
        mock_get_anthropic_response.side_effect = simulated_error
        command_payload = {"type": "chat_query", "module": "anthropic_chat", "args": {"prompt": "This will cause an unexpected error"}, "id": "unexpected_err_001"}
        mock_message = self._create_mock_message(command_payload)
        self.katana_bot.handle_message(mock_message)
        mock_get_anthropic_response.assert_called_once()
        self.mock_bot_module_instance.reply_to.assert_called_once_with(mock_message, "🤖⚠️: Произошла внутренняя ошибка при обработке вашего запроса.")
        error_log_found = False
        for call_args, call_kwargs in mock_log_event.call_args_list:
            log_message = call_args[0]; log_level = call_kwargs.get('level')
            if log_level == logging.ERROR and "Unexpected error processing anthropic_chat" in log_message and str(simulated_error) in log_message:
                self.assertTrue(call_kwargs.get('exc_info', False)); error_log_found = True; break
        self.assertTrue(error_log_found)

    def test_unknown_command_type_saves_normally(self):
        command = {"type": "unknown_type", "module": "custom_module", "args": {}, "id": "custom003"}
        mock_message = self._create_mock_message(command)
        self.katana_bot.handle_message(mock_message)
        expected_module_dir = self.test_commands_dir / "telegram_mod_custom_module"
        self.assertTrue(expected_module_dir.exists())
        expected_filename = f"YYYYMMDD_HHMMSS_ffffff_{mock_message.chat.id}.json"
        expected_file_path = expected_module_dir / expected_filename
        self.assertTrue(expected_file_path.exists())
        with open(expected_file_path, "r") as f:
            saved_data = json.load(f)
        self.assertEqual(saved_data, command)
        self.mock_bot_module_instance.reply_to.assert_called_once()
        args, kwargs = self.mock_bot_module_instance.reply_to.call_args
        self.assertEqual(args[0], mock_message)
        self.assertTrue(args[1].startswith("✅ Command received and saved as"))
        self.assertIn(str(expected_file_path), args[1])

    # --- Tests for Graceful Shutdown ---
    @patch('bot.katana_bot.logger')
    def test_graceful_shutdown_handler_stops_polling_and_sets_flag(self, mock_logger):
        self.katana_bot.shutdown_requested = False
        self.katana_bot.graceful_shutdown_handler(signal.SIGINT, None)
        self.assertTrue(self.katana_bot.shutdown_requested)
        self.mock_bot_module_instance.stop_polling.assert_called_once()
        mock_logger.warning.assert_any_call(f"Shutdown signal {signal.Signals(signal.SIGINT).name} received. Attempting graceful shutdown...")
        mock_logger.info.assert_any_call("Calling bot.stop_polling()...")

    @patch('bot.katana_bot.logger')
    def test_graceful_shutdown_handler_called_twice(self, mock_logger):
        self.katana_bot.shutdown_requested = False
        self.katana_bot.graceful_shutdown_handler(signal.SIGINT, None)
        self.assertTrue(self.katana_bot.shutdown_requested)
        self.mock_bot_module_instance.stop_polling.assert_called_once()
        mock_logger.warning.assert_any_call(f"Shutdown signal {signal.Signals(signal.SIGINT).name} received. Attempting graceful shutdown...")
        self.mock_bot_module_instance.stop_polling.reset_mock()
        mock_logger.reset_mock()
        self.katana_bot.graceful_shutdown_handler(signal.SIGINT, None)
        self.mock_bot_module_instance.stop_polling.assert_not_called()
        mock_logger.warning.assert_any_call(f"Repeated shutdown signal {signal.Signals(signal.SIGINT).name} received. Already shutting down.")

    @patch('bot.katana_bot.logger')
    @patch('bot.katana_bot.bot', None)
    def test_graceful_shutdown_handler_no_bot_object(self, mock_logger_no_bot):
        original_shutdown_requested = self.katana_bot.shutdown_requested
        self.katana_bot.shutdown_requested = False
        try:
            self.katana_bot.graceful_shutdown_handler(signal.SIGTERM, None)
            self.assertTrue(self.katana_bot.shutdown_requested)
            mock_logger_no_bot.warning.assert_any_call(f"Shutdown signal {signal.Signals(signal.SIGTERM).name} received. Attempting graceful shutdown...")
            mock_logger_no_bot.warning.assert_any_call("Bot object not available for stop_polling(). Exiting directly.")
        finally:
            self.katana_bot.shutdown_requested = original_shutdown_requested

    # --- Test for Heartbeat Generation in Polling Loop ---
    @patch('bot.katana_bot.time')
    @patch('builtins.open', new_callable=unittest.mock.mock_open)
    def test_run_bot_polling_loop_heartbeat_and_restart(self, mock_file_open, mock_time):
        mock_bot_polling = self.mock_bot_module_instance.polling

        mock_time.time.side_effect = [1000.0, 1015.0]
        mock_time.sleep.return_value = None

        self.stop_flag_call_count = 0
        def controlled_stop_flag_side_effect():
            self.stop_flag_call_count += 1
            if self.stop_flag_call_count >= 20:
                return True
            return False
        mock_stop_flag_check = MagicMock(side_effect=controlled_stop_flag_side_effect)

        polling_effects = [Exception("Simulated polling crash"), None]
        mock_bot_polling.side_effect = polling_effects

        mock_project_root = Path("/fake/project/root")
        mock_hb_file_path = mock_project_root / "katana_heartbeat.txt"

        self.katana_bot.run_bot_polling_loop(
            bot_instance=self.mock_bot_module_instance,
            current_project_root=mock_project_root,
            hb_file_path_obj=mock_hb_file_path,
            stop_flag_check_func=mock_stop_flag_check
        )

        self.assertEqual(mock_file_open.call_count, 2)
        self.assertEqual(mock_file_open.call_args_list[0], call(mock_hb_file_path, "w"))
        self.assertEqual(mock_file_open.call_args_list[1], call(mock_hb_file_path, "w"))

        handle = mock_file_open.return_value
        expected_writes = [call(str(1000.0)), call(str(1015.0))]
        handle.write.assert_has_calls(expected_writes, any_order=False)

        self.assertEqual(mock_bot_polling.call_count, 2)
        self.assertEqual(self.stop_flag_call_count, 20)


if __name__ == '__main__':
    unittest.main()
