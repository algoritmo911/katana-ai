import unittest
from unittest.mock import MagicMock, patch, call
import json
from pathlib import Path
import shutil # For robust directory removal

# Assuming bot.py is in the same directory or accessible in PYTHONPATH
from bot import katana_bot as bot

class TestBot(unittest.TestCase):

    def setUp(self):
        # Create a dummy commands directory for testing
        self.test_commands_dir = Path("test_commands_temp_dir") # Using a more unique name
        self.test_commands_dir.mkdir(parents=True, exist_ok=True)

        # Store original and set to test
        self.original_command_file_dir = bot.COMMAND_FILE_DIR
        bot.COMMAND_FILE_DIR = self.test_commands_dir

        # Mock the bot object and its methods
        self.mock_bot_instance = MagicMock()
        # Patch the bot instance within the 'bot' module
        self.bot_patcher = patch('bot.katana_bot.bot', self.mock_bot_instance)
        self.mock_bot_module_instance = self.bot_patcher.start()

        # Mock datetime to control timestamps in filenames
        self.mock_datetime_patcher = patch('bot.katana_bot.datetime')
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
        bot.COMMAND_FILE_DIR = self.original_command_file_dir


    def _create_mock_message(self, text_payload):
        mock_message = MagicMock()
        mock_message.chat.id = 12345
        mock_message.text = json.dumps(text_payload)
        return mock_message

    # --- Test Command Validation ---
    def test_valid_command_gets_saved(self):
        command = {"type": "test_type", "module": "test_module", "args": {}, "id": "test_id"}
        mock_message = self._create_mock_message(command)

        bot.handle_message(mock_message)

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
        bot.handle_message(mock_message)
        self.mock_bot_module_instance.reply_to.assert_called_with(mock_message, "Error: Invalid JSON format.")

    def test_missing_type_field(self):
        command = {"module": "test_module", "args": {}, "id": "test_id"} # type is missing
        mock_message = self._create_mock_message(command)
        bot.handle_message(mock_message)
        self.mock_bot_module_instance.reply_to.assert_called_with(mock_message, "Error: Missing required field 'type'.")

    def test_missing_module_field(self):
        command = {"type": "test_type", "args": {}, "id": "test_id"} # module is missing
        mock_message = self._create_mock_message(command)
        bot.handle_message(mock_message)
        self.mock_bot_module_instance.reply_to.assert_called_with(mock_message, "Error: Missing required field 'module'.")

    def test_invalid_args_type(self):
        command = {"type": "test_type", "module": "test_module", "args": "not_a_dict", "id": "test_id"}
        mock_message = self._create_mock_message(command)
        bot.handle_message(mock_message)
        self.mock_bot_module_instance.reply_to.assert_called_with(mock_message, "Error: Field 'args' must be type dict. Got str.")

    def test_invalid_id_type(self):
        command = {"type": "test_type", "module": "test_module", "args": {}, "id": [1,2,3]} # id is a list
        mock_message = self._create_mock_message(command)
        bot.handle_message(mock_message)
        self.mock_bot_module_instance.reply_to.assert_called_with(mock_message, "Error: Field 'id' must be type str or int. Got list.")


    # --- Test Command Routing ---

    @patch('bot.katana_bot.log_local_bot_event')
    def test_handle_log_event_calls_logger(self, mock_log_local_bot_event_func):
        from bot_components.handlers.log_event_handler import handle_log_event # Updated import path
        command_data = {'type': 'log_event', 'module': 'test', 'args': {'message': 'hello test'}, 'id': 'test001'}
        chat_id = 98765

        handle_log_event(command_data, chat_id, mock_log_local_bot_event_func) # Pass mock logger

        mock_log_local_bot_event_func.assert_called_once()
        expected_log_message = f"handle_log_event called for chat_id {chat_id} with data: {command_data}"
        mock_log_local_bot_event_func.assert_called_with(expected_log_message)

    def test_handle_ping_calls_logger(self):
        from bot_components.handlers.ping_handler import handle_ping # Direct import for direct test
        command_data = {'type': 'ping', 'module': 'test', 'args': {}, 'id': 'ping_test_002'}
        chat_id = 54321
        mock_logger = MagicMock()

        reply = handle_ping(command_data, chat_id, mock_logger)

        mock_logger.assert_called_once_with(f"handle_ping called for chat_id {chat_id} with data: {command_data}")
        self.assertEqual(reply, "✅ 'ping' received.")

    def test_handle_mind_clearing_calls_logger(self):
        from bot_components.handlers.mind_clearing_handler import handle_mind_clearing
        command_data = {'type': 'mind_clearing', 'module': 'test_wellness', 'args': {'duration': '5m'}, 'id': 'mc_test_003'}
        chat_id = 13579
        mock_logger = MagicMock()

        reply = handle_mind_clearing(command_data, chat_id, mock_logger)

        mock_logger.assert_called_once_with(f"handle_mind_clearing called for chat_id {chat_id} with data: {command_data}")
        self.assertEqual(reply, "✅ 'mind_clearing' processed (placeholder).")

    def test_log_event_success(self):
        command_data = {"type": "log_event", "module": "logging_module", "args": {"level": "info", "message": "Successful event"}, "id": "log_success_001"}
        mock_message = self._create_mock_message(command_data)

        # We need to patch handle_log_event because we are testing the reply from handle_message,
        # not the full execution of handle_log_event itself here.
        with patch('bot.katana_bot.handle_log_event') as mock_actual_handler: # Corrected patch path
            bot.handle_message(mock_message)
            # Assert that the mock_actual_handler (the moved handle_log_event) is called with the command_data, chat_id, AND the actual log_local_bot_event from bot.py
            mock_actual_handler.assert_called_once_with(command_data, mock_message.chat.id, bot.log_local_bot_event)

        self.mock_bot_module_instance.reply_to.assert_called_with(mock_message, "✅ 'log_event' processed (placeholder).")

    @patch('bot.katana_bot.handle_log_event') # Corrected patch path
    def test_routing_log_event(self, mock_handle_log_event_func):
        command = {"type": "log_event", "module": "logging", "args": {"message": "hello"}, "id": "log001"}
        mock_message = self._create_mock_message(command)

        bot.handle_message(mock_message)

        # Assert that the mock_handle_log_event_func is called with command, chat_id, AND the actual log_local_bot_event from bot.py
        mock_handle_log_event_func.assert_called_once_with(command, mock_message.chat.id, bot.log_local_bot_event)
        self.mock_bot_module_instance.reply_to.assert_called_with(mock_message, "✅ 'log_event' processed (placeholder).")

    @patch('bot.katana_bot.handle_ping') # Patching where it's used in bot.py
    def test_routing_ping(self, mock_handle_ping_func):
        command = {"type": "ping", "module": "system", "args": {}, "id": "ping001"}
        mock_message = self._create_mock_message(command)

        # Define a specific return value for the mock
        mock_handle_ping_func.return_value = "Ping success from mock"

        bot.handle_message(mock_message)

        mock_handle_ping_func.assert_called_once_with(command, mock_message.chat.id, bot.log_local_bot_event)
        self.mock_bot_module_instance.reply_to.assert_called_with(mock_message, "Ping success from mock")

    @patch('bot.katana_bot.handle_mind_clearing')
    def test_routing_mind_clearing(self, mock_handle_mind_clearing_func):
        command = {"type": "mind_clearing", "module": "wellness", "args": {"duration": "10m"}, "id": "mind002"}
        mock_message = self._create_mock_message(command)

        # Set the mock's return value, as bot.py now uses it for the reply
        mock_handle_mind_clearing_func.return_value = "✅ 'mind_clearing' processed (placeholder)."

        bot.handle_message(mock_message)

        # Assert that the mock is called with the logger function as the third argument
        mock_handle_mind_clearing_func.assert_called_once_with(command, mock_message.chat.id, bot.log_local_bot_event)
        # This assertion should still pass as bot.py uses the return value from the handler
        self.mock_bot_module_instance.reply_to.assert_called_with(mock_message, "✅ 'mind_clearing' processed (placeholder).")


    def test_unknown_command_type_saves_normally(self):
        command = {"type": "unknown_type", "module": "custom_module", "args": {}, "id": "custom003"}
        mock_message = self._create_mock_message(command)

        bot.handle_message(mock_message)

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
