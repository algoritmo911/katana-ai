import unittest
from unittest.mock import MagicMock, patch, call
import json
from pathlib import Path
import shutil # For robust directory removal
import os # For main execution context

# Assuming bot.py is in the same directory or accessible in PYTHONPATH
import bot
from command_graph import Command, CommandGraph

class TestBot(unittest.TestCase):

    def setUp(self):
        # Create a dummy commands directory for testing
        self.test_commands_dir = Path("test_commands_temp_dir")
        self.test_commands_dir.mkdir(parents=True, exist_ok=True)

        # Store original and set to test
        self.original_command_file_dir = bot.COMMAND_FILE_DIR
        bot.COMMAND_FILE_DIR = self.test_commands_dir

        # Mock the TeleBot class
        self.mock_telebot_patcher = patch('telebot.TeleBot')
        self.mock_telebot = self.mock_telebot_patcher.start()
        self.mock_bot_instance = self.mock_telebot.return_value
        bot.bot = self.mock_bot_instance

        # Mock datetime to control timestamps in filenames
        self.mock_datetime_patcher = patch('bot.datetime')
        self.mock_datetime = self.mock_datetime_patcher.start()
        self.mock_datetime.utcnow.return_value.strftime.return_value = "YYYYMMDD_HHMMSS_ffffff"

        # Patch the logger
        self.mock_logger_patcher = patch('bot.katana_logger')
        self.mock_logger = self.mock_logger_patcher.start()

        # Patch CommandGraph
        self.mock_command_graph_patcher = patch('bot.command_graph', MagicMock(spec=CommandGraph))
        self.mock_command_graph = self.mock_command_graph_patcher.start()


    def tearDown(self):
        # Stop patchers
        self.mock_telebot_patcher.stop()
        self.mock_datetime_patcher.stop()
        self.mock_logger_patcher.stop() # Stop logger patcher
        self.mock_command_graph_patcher.stop()

        # Clean up: remove dummy directory and its contents
        if self.test_commands_dir.exists():
            shutil.rmtree(self.test_commands_dir) # shutil.rmtree is more robust for non-empty dirs

        # Restore original
        bot.COMMAND_FILE_DIR = self.original_command_file_dir


    def _create_mock_message(self, text_payload_dict_or_str):
        mock_message = MagicMock()
        mock_message.chat.id = 12345
        if isinstance(text_payload_dict_or_str, dict):
            mock_message.text = json.dumps(text_payload_dict_or_str)
        else: # It's a string (for invalid JSON test)
            mock_message.text = text_payload_dict_or_str
        return mock_message

    def _test_validation_failure_scenario(self, command_payload, expected_reply_message_part):
        """Helper to test common validation failure scenarios."""
        mock_message = self._create_mock_message(command_payload)
        bot.handle_message(mock_message)

        # Check reply to user
        self.mock_bot_instance.reply_to.assert_called_with(
            mock_message,
            expected_reply_message_part # The error_msg from _validate_command is directly used for reply
        )

        # Check detailed error log
        # The logged message includes "(Command: {original_command_text})"
        self.mock_logger.error.assert_called_with(
            f"Validation failed for {mock_message.chat.id}: {expected_reply_message_part} (Command: {mock_message.text})"
        )
        # Also check that the initial "Received message" log was made
        self.mock_logger.info.assert_any_call(f"Received message from {mock_message.chat.id}: {mock_message.text}")


    # --- Test Command Validation ---
    def test_valid_command_gets_saved(self):
        command = {"type": "test_type", "module": "test_module", "args": {"data": "value"}, "id": "test_id_valid"}
        mock_message = self._create_mock_message(command)

        bot.handle_message(mock_message)

        expected_module_dir = self.test_commands_dir / "telegram_mod_test_module"
        self.assertTrue(expected_module_dir.exists())
        expected_filename = f"YYYYMMDD_HHMMSS_ffffff_{mock_message.chat.id}.json"
        expected_file_path = expected_module_dir / expected_filename
        self.assertTrue(expected_file_path.exists())

        with open(expected_file_path, "r") as f:
            saved_data = json.load(f)
        self.assertEqual(saved_data, command)

        self.mock_bot_instance.reply_to.assert_called_once()
        args, _ = self.mock_bot_instance.reply_to.call_args # Use _ for kwargs if not used
        self.assertEqual(args[0], mock_message)
        self.assertTrue(args[1].startswith("✅ Command received and saved as"))
        self.assertIn(str(expected_file_path), args[1])

        # Check for log messages
        # Using assert_any_call for logger calls as other log messages might occur (like received message)
        self.mock_logger.info.assert_any_call(f"Received message from {mock_message.chat.id}: {mock_message.text}")
        self.mock_logger.info.assert_any_call(f"Command type '{command['type']}' for chat_id {mock_message.chat.id} not specifically handled, proceeding with default save.")
        self.mock_logger.info.assert_any_call(f"Saved command from {mock_message.chat.id} to {str(expected_file_path)}")


    def test_invalid_json_format(self):
        invalid_json_string = "not a valid json"
        mock_message = self._create_mock_message(invalid_json_string)

        bot.handle_message(mock_message)
        self.mock_bot_instance.reply_to.assert_called_with(mock_message, "Error: Invalid JSON format.")
        # Check initial "Received message" log
        self.mock_logger.info.assert_any_call(f"Received message from {mock_message.chat.id}: {invalid_json_string}")
        # Check the specific error log from _parse_command
        self.mock_logger.error.assert_called_with(f"Invalid JSON from {mock_message.chat.id}: {invalid_json_string}")

    def test_missing_type_field(self):
        command = {"module": "test_module", "args": {}, "id": "test_id_missing_type"}
        self._test_validation_failure_scenario(command, "Error: Missing required field 'type'.")

    def test_missing_module_field(self):
        command = {"type": "test_type", "args": {}, "id": "test_id_missing_module"}
        self._test_validation_failure_scenario(command, "Error: Missing required field 'module'.")

    def test_invalid_args_type(self):
        command = {"type": "test_type", "module": "test_module", "args": "not_a_dict", "id": "test_id_invalid_args"}
        self._test_validation_failure_scenario(command, "Error: Field 'args' must be type dict. Got str.")

    def test_invalid_id_type(self):
        command = {"type": "test_type", "module": "test_module", "args": {}, "id": [1,2,3]}
        self._test_validation_failure_scenario(command, "Error: Field 'id' must be type str or int. Got list.")

    def test_missing_args_field(self):
        command = {"type": "test_type", "module": "test_module", "id": "test_id_missing_args"}
        self._test_validation_failure_scenario(command, "Error: Missing required field 'args'.")

    def test_missing_id_field(self):
        command = {"type": "test_type", "module": "test_module", "args": {}}
        self._test_validation_failure_scenario(command, "Error: Missing required field 'id'.")

    def test_invalid_type_for_type_field(self):
        command = {"type": 123, "module": "test_module", "args": {}, "id": "test_id_invalid_type_type"}
        self._test_validation_failure_scenario(command, "Error: Field 'type' must be type str. Got int.")

    def test_invalid_type_for_module_field(self):
        command = {"type": "test_type", "module": 123, "args": {}, "id": "test_id_invalid_module_type"}
        self._test_validation_failure_scenario(command, "Error: Field 'module' must be type str. Got int.")


    # --- Test Command Routing & Specific Handler Logging ---
    # Note: We do NOT patch 'bot.handle_log_event' here because we want to test its internal logging.
    def test_routing_log_event_with_detailed_logging(self):
        command = {
            "type": "log_event",
            "module": "user_activity_module",
            "args": {"action": "login", "status": "success", "user_id": "user123"},
            "id": "evt_login_success_001"
        }
        mock_message = self._create_mock_message(command)

        # We need to patch handle_log_event if other tests rely on it being mocked.
        # For this test, we want the real one. If it's globally patched by another decorator,
        # this test might need to be in a separate class or use with self.subTest and specific patching.
        # Assuming no overarching patch for bot.handle_log_event for now.
        # If bot.handle_log_event is called by bot.handle_message, this test will cover its internal logging.

        bot.handle_message(mock_message) # This will call the actual handle_log_event

        self.mock_bot_instance.reply_to.assert_called_with(mock_message, "✅ 'log_event' processed (placeholder).")

        # Check for standard logs from handle_message
        self.mock_logger.info.assert_any_call(f"Received message from {mock_message.chat.id}: {mock_message.text}")
        self.mock_logger.info.assert_any_call(f"Successfully processed command for {mock_message.chat.id}: log_event")

        # Check for the new detailed log message from within handle_log_event
        expected_log_args_detail = command['args']
        self.mock_logger.info.assert_any_call(
            f"EVENT LOGGED by {mock_message.chat.id} for module {command['module']}: {expected_log_args_detail}"
        )

    def test_log_event_missing_module_validation(self): # New test for log_event type specific validation
        command = {"type": "log_event", "args": {"message": "missing module test"}, "id": "log002_missing_module"}
        mock_message = self._create_mock_message(command)

        # We patch bot.handle_log_event to ensure it's NOT called if validation fails
        with patch('bot.handle_log_event') as mock_handle_log_event_func_local:
            bot.handle_message(mock_message)
            mock_handle_log_event_func_local.assert_not_called()

        expected_error_msg = "Error: Missing required field 'module'."
        self.mock_bot_instance.reply_to.assert_called_with(mock_message, expected_error_msg)
        # The logger call for "Received message" would have happened.
        self.mock_logger.info.assert_any_call(f"Received message from {mock_message.chat.id}: {mock_message.text}")
        self.mock_logger.error.assert_called_with(f"Validation failed for {mock_message.chat.id}: {expected_error_msg} (Command: {mock_message.text})")

    @patch('bot.handle_mind_clearing') # Mock the actual handler
    def test_routing_mind_clearing_with_logging(self, mock_handle_mind_clearing_func): # Renamed & updated
        command = {"type": "mind_clearing", "module": "wellness_module", "args": {"duration": "15m"}, "id": "mind002_event"}
        mock_message = self._create_mock_message(command)

        bot.handle_message(mock_message)

        mock_handle_mind_clearing_func.assert_called_once_with(command, mock_message.chat.id)
        self.mock_bot_instance.reply_to.assert_called_with(mock_message, "✅ 'mind_clearing' processed (placeholder).")
        self.mock_logger.info.assert_any_call(f"Received message from {mock_message.chat.id}: {mock_message.text}")
        self.mock_logger.info.assert_any_call(f"Successfully processed command for {mock_message.chat.id}: mind_clearing")

    def test_unknown_command_type_saves_normally_with_logging(self): # Renamed & updated
        command = {"type": "unknown_type", "module": "custom_module_unknown", "args": {"param": "value"}, "id": "custom003_unknown"}
        mock_message = self._create_mock_message(command)

        bot.handle_message(mock_message)

        expected_module_dir = self.test_commands_dir / "telegram_mod_custom_module_unknown"
        self.assertTrue(expected_module_dir.exists())
        expected_filename = f"YYYYMMDD_HHMMSS_ffffff_{mock_message.chat.id}.json"
        expected_file_path = expected_module_dir / expected_filename
        self.assertTrue(expected_file_path.exists())

        with open(expected_file_path, "r") as f:
            saved_data = json.load(f)
        self.assertEqual(saved_data, command)

        self.mock_bot_instance.reply_to.assert_called_once()
        args, _ = self.mock_bot_instance.reply_to.call_args # Use _ if kwargs not needed
        self.assertEqual(args[0], mock_message)
        self.assertTrue(args[1].startswith("✅ Command received and saved as"))
        self.assertIn(str(expected_file_path), args[1])

        # Check for log messages
        self.mock_logger.info.assert_any_call(f"Received message from {mock_message.chat.id}: {mock_message.text}")
        self.mock_logger.info.assert_any_call(f"Command type '{command['type']}' for chat_id {mock_message.chat.id} not specifically handled, proceeding with default save.")
        self.mock_logger.info.assert_any_call(f"Saved command from {mock_message.chat.id} to {str(expected_file_path)}")

    @patch('builtins.open', new_callable=MagicMock) # Patch 'open' in the scope where bot.py uses it
    def test_unknown_command_save_io_error(self, mock_open):
        mock_open.side_effect = IOError("Simulated disk full error")

        command = {"type": "unknown_type_io_error", "module": "custom_module_io", "args": {"param": "value"}, "id": "custom004_io_error"}
        mock_message = self._create_mock_message(command)

        bot.handle_message(mock_message)

        # Check that reply indicates an error
        self.mock_bot_instance.reply_to.assert_called_with(
            mock_message,
            "Error: Could not save command. Please contact administrator."
        )

        # Check that error was logged
        # The file path would be constructed before the open fails.
        # We need to reconstruct it or be less specific if it's hard to get.
        # For now, let's check parts of the message.
        # Expected path: self.test_commands_dir / "telegram_mod_custom_module_io" / f"YYYYMMDD_HHMMSS_ffffff_{mock_message.chat.id}.json"
        # Since strftime is mocked, it's predictable.
        expected_filename = f"YYYYMMDD_HHMMSS_ffffff_{mock_message.chat.id}.json"
        expected_command_file_path = self.test_commands_dir / "telegram_mod_custom_module_io" / expected_filename

        self.mock_logger.error.assert_any_call(
            f"Failed to save command for {mock_message.chat.id} to {str(expected_command_file_path)}. Reason: Simulated disk full error"
        )
        # Also check that the "Saved command..." info log was NOT called
        # This requires checking all calls to info or being more specific.
        # A simple way is to check call_args_list if needed, or ensure error is the last relevant log.
        # For now, asserting the error is the main goal.

    def test_routing_log_event_with_complex_args(self):
        command = {
            "type": "log_event",
            "module": "complex_event_module",
            "args": {
                "action": "data_update",
                "status": "partial_success",
                "details": {
                    "items_processed": 100,
                    "items_failed": 5,
                    "errors": [
                        {"code": "E101", "item_id": "item_X"},
                        {"code": "E102", "item_id": "item_Y"}
                    ]
                }
            },
            "id": "evt_complex_args_001"
        }
        mock_message = self._create_mock_message(command)

        bot.handle_message(mock_message)

        self.mock_bot_instance.reply_to.assert_called_with(mock_message, "✅ 'log_event' processed (placeholder).")

        self.mock_logger.info.assert_any_call(f"Received message from {mock_message.chat.id}: {mock_message.text}")
        self.mock_logger.info.assert_any_call(f"Successfully processed command for {mock_message.chat.id}: log_event")

        expected_log_args_detail = command['args']
        self.mock_logger.info.assert_any_call(
            f"EVENT LOGGED by {mock_message.chat.id} for module {command['module']}: {expected_log_args_detail}"
        )

    def test_get_command_graph(self):
        command = {"type": "get_command_graph", "module": "graph_module", "args": {}, "id": "get_graph_cmd"}
        mock_message = self._create_mock_message(command)

        # Mock the to_dot method to return a predictable string
        self.mock_command_graph.to_dot.return_value = "digraph G {}"

        bot.handle_message(mock_message)

        # Verify that the bot sends a message with the DOT string
        self.mock_bot_instance.send_message.assert_called_once_with(
            mock_message.chat.id,
            "```dot\ndigraph G {}\n```",
            parse_mode="MarkdownV2"
        )
        self.mock_logger.info.assert_any_call(f"Successfully processed command for {mock_message.chat.id}: get_command_graph")


if __name__ == '__main__':
    # Added os import for this class, ensure bot.py gets API_TOKEN if main is tested more directly.
    # For now, the startup/shutdown tests are specific about what they patch and call.
    unittest.main()
