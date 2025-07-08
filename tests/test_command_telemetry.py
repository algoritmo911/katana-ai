import unittest
import os
import json
import time
import shutil
import uuid # For checking trace_id
# import getpass # No longer needed for direct mock if testing system user source
from unittest import mock
from datetime import datetime, timezone
from katana.decorators.trace_command import trace_command
from katana.logging.telemetry_logger import LOG_FILE_PATH, ensure_log_directory_exists

# Attempt to import telebot types for mocking, similar to the decorator
try:
    from telebot import types as telebot_types
    TELEBOT_AVAILABLE = True
except ImportError:
    telebot_types = None
    TELEBOT_AVAILABLE = False


# Define a directory for logs specific to these tests
TEST_LOGS_DIR = "test_logs_temp"
TEST_LOG_FILE_PATH = os.path.join(TEST_LOGS_DIR, "command_telemetry.log")

# Helper function to validate ISO format timestamp
def is_iso_timestamp(timestamp_str):
    if not isinstance(timestamp_str, str): return False
    try:
        datetime.fromisoformat(timestamp_str.replace("Z", "+00:00")) # Handle Z for UTC
        return True
    except ValueError:
        return False

def is_uuid(val):
    try:
        uuid.UUID(str(val))
        return True
    except ValueError:
        return False

# --- Mocking for telebot.types.Message ---
class MockTgUser:
    def __init__(self, id, username):
        self.id = id
        self.username = username

class MockTgMessage:
    def __init__(self, user_id, username, text="Default text"):
        self.from_user = MockTgUser(user_id, username)
        self.text = text
        # Add other telebot.types.Message attributes if your decorated functions expect them

# Conditionally set telebot_types.Message if telebot is not installed, for tests to run
if not TELEBOT_AVAILABLE:
    class MockTelebotModule: # Mimic the 'types' module
        Message = MockTgMessage
    telebot_types = MockTelebotModule
# --- End Mocking ---


# Mocked commands for testing purposes
@trace_command
def mock_successful_command_system_user(param1, param2, keyword_param=None):
    """A mock command that succeeds, uses system user."""
    time.sleep(0.01) # Simulate some work
    return {"status": "success", "data": f"{param1}-{param2}-{keyword_param}"}

@trace_command(tags={"category": "test_failure", "severity": "high"})
def mock_failing_command_with_tags(param1):
    """A mock command that fails, with tags."""
    time.sleep(0.01) # Simulate some work
    if param1 == "fail":
        raise ValueError("Mock command failed as requested", {"detail_code": 101})
    return {"status": "unexpected_success"}

@trace_command(tags={"handler_type": "bot"})
def mock_bot_command_handler(message: telebot_types.Message, custom_arg: str):
    """A mock bot command handler."""
    time.sleep(0.01)
    if message.text == "trigger_error":
        raise RuntimeError("Bot command error triggered")
    return {"user_id": message.from_user.id, "custom_arg_received": custom_arg}


class MockedCLIClass:
    def __init__(self, name="TestCLIInstance"):
        self.name = name
        self.internal_status = "initialized"

    @trace_command(tags={"cli_class_method": True})
    def instance_method_no_args(self):
        time.sleep(0.01)
        self.internal_status = "method_called"
        return f"{self.name} status: {self.internal_status}"

    @trace_command
    def instance_method_with_args(self, arg1, kwarg1=None):
        time.sleep(0.01)
        if arg1 == "fail_method":
            raise Exception("Method failed intentionally")
        return {"instance_name": self.name, "arg1": arg1, "kwarg1": kwarg1}


class TestCommandTelemetry(unittest.TestCase):

    @classmethod
    def setUpClass(cls): # Removed mock_getuser and decorator
        # Override the default log file path for testing
        import katana.logging.telemetry_logger
        katana.logging.telemetry_logger.LOG_FILE_PATH = TEST_LOG_FILE_PATH

        # Ensure the test log directory exists
        if os.path.exists(TEST_LOGS_DIR):
            shutil.rmtree(TEST_LOGS_DIR)
        ensure_log_directory_exists() # This will now use TEST_LOG_FILE_PATH
        # cls.mock_getuser is no longer needed here

    @classmethod
    def tearDownClass(cls):
        # Clean up the test log directory
        if os.path.exists(TEST_LOGS_DIR):
            shutil.rmtree(TEST_LOGS_DIR)

        # Restore original log file path if necessary (though tests run in separate process usually)
        import katana.logging.telemetry_logger
        katana.logging.telemetry_logger.LOG_FILE_PATH = "logs/command_telemetry.log"
        # No need to stop mock_getuser here if it's patched at class level for all methods

    def setUp(self):
        # Clear the log file before each test
        if os.path.exists(TEST_LOG_FILE_PATH):
            os.remove(TEST_LOG_FILE_PATH)
        ensure_log_directory_exists() # Ensures dir is there for each test, using the overridden path

    def tearDown(self):
        # Optional: clear log file after each test if preferred over setUp
        pass

    def read_log_entries(self):
        if not os.path.exists(TEST_LOG_FILE_PATH):
            return []
        with open(TEST_LOG_FILE_PATH, "r") as f:
            return [json.loads(line) for line in f]

    def test_01_log_file_creation(self):
        self.assertFalse(os.path.exists(TEST_LOG_FILE_PATH), "Log file should not exist before command execution.")
        # Patch getpass.getuser for the decorator's fallback path
        with mock.patch('katana.decorators.trace_command.getpass.getuser', return_value="mock_system_user"):
            mock_successful_command_system_user("test", "log_creation")
        self.assertTrue(os.path.exists(TEST_LOG_FILE_PATH), "Log file should be created after command execution.")

    def test_02_successful_command_logging_system_user(self):
        expected_system_user = "telemetry_test_user"
        with mock.patch('katana.decorators.trace_command.getpass.getuser', return_value=expected_system_user):
            result = mock_successful_command_system_user("arg1_val", "arg2_val", keyword_param="kw_val")

        expected_result_payload = {"status": "success", "data": "arg1_val-arg2_val-kw_val"}
        self.assertEqual(result, expected_result_payload)

        logs = self.read_log_entries()
        self.assertEqual(len(logs), 1)
        log_entry = logs[0]

        self.assertTrue(is_uuid(log_entry["trace_id"]))
        self.assertEqual(log_entry["user"], {"username": expected_system_user, "source": "system"})
        self.assertTrue(is_iso_timestamp(log_entry["command_start_time_utc"]))
        self.assertTrue(is_iso_timestamp(log_entry["log_event_timestamp_utc"]))
        self.assertEqual(log_entry["command_name"], "mock_successful_command_system_user")
        self.assertEqual(log_entry["arguments"]["args"], ["arg1_val", "arg2_val"])
        self.assertEqual(log_entry["arguments"]["kwargs"], {"keyword_param": "kw_val"})
        self.assertTrue(log_entry["success"])
        self.assertIn("execution_time_seconds", log_entry)
        self.assertTrue(log_entry["execution_time_seconds"] > 0)
        self.assertEqual(log_entry["result"], expected_result_payload) # Check full result
        self.assertNotIn("tags", log_entry) # No tags for this one

    def test_03_failing_command_logging_with_tags(self):
        expected_system_user = "failure_test_user"
        with self.assertRaises(ValueError) as context, \
             mock.patch('katana.decorators.trace_command.getpass.getuser', return_value=expected_system_user):
            mock_failing_command_with_tags("fail")

        self.assertEqual(str(context.exception), "('Mock command failed as requested', {'detail_code': 101})")

        logs = self.read_log_entries()
        self.assertEqual(len(logs), 1)
        log_entry = logs[0]

        self.assertTrue(is_uuid(log_entry["trace_id"]))
        self.assertEqual(log_entry["user"], {"username": expected_system_user, "source": "system"})
        self.assertEqual(log_entry["command_name"], "mock_failing_command_with_tags")
        self.assertEqual(log_entry["arguments"]["args"], ["fail"])
        self.assertFalse(log_entry["success"])
        self.assertIn("error", log_entry)
        self.assertEqual(log_entry["error"]["type"], "ValueError")
        self.assertEqual(log_entry["error"]["message"], "('Mock command failed as requested', {'detail_code': 101})")
        self.assertEqual(log_entry["error"]["details"], ["Mock command failed as requested", {"detail_code": 101}])
        self.assertEqual(log_entry["tags"], {"category": "test_failure", "severity": "high"})

    def test_04_bot_command_handler_successful(self):
        mock_message = MockTgMessage(user_id=12345, username="test_bot_user", text="Process this")
        result = mock_bot_command_handler(mock_message, "custom_val_success")

        expected_result_payload = {"user_id": 12345, "custom_arg_received": "custom_val_success"}
        self.assertEqual(result, expected_result_payload)

        logs = self.read_log_entries()
        self.assertEqual(len(logs), 1)
        log_entry = logs[0]

        self.assertTrue(is_uuid(log_entry["trace_id"]))
        self.assertEqual(log_entry["user"], {"id": 12345, "username": "test_bot_user", "source": "telegram"})
        self.assertEqual(log_entry["command_name"], "mock_bot_command_handler")
        # First arg is the message object, second is "custom_val_success"
        self.assertIsInstance(log_entry["arguments"]["args"][0], str) # Serialized MockTgMessage
        self.assertTrue("MockTgMessage" in log_entry["arguments"]["args"][0]) # Check if it's the stringified version
        self.assertEqual(log_entry["arguments"]["args"][1], "custom_val_success")
        self.assertTrue(log_entry["success"])
        self.assertEqual(log_entry["result"], expected_result_payload)
        self.assertEqual(log_entry["tags"], {"handler_type": "bot"})

    def test_05_bot_command_handler_failure(self):
        mock_message_fail = MockTgMessage(user_id=67890, username="error_bot_user", text="trigger_error")
        with self.assertRaises(RuntimeError) as context:
            mock_bot_command_handler(mock_message_fail, "custom_val_fail")

        self.assertEqual(str(context.exception), "Bot command error triggered")

        logs = self.read_log_entries()
        self.assertEqual(len(logs), 1)
        log_entry = logs[0]

        self.assertTrue(is_uuid(log_entry["trace_id"]))
        self.assertEqual(log_entry["user"], {"id": 67890, "username": "error_bot_user", "source": "telegram"})
        self.assertEqual(log_entry["command_name"], "mock_bot_command_handler")
        self.assertIsInstance(log_entry["arguments"]["args"][0], str) # Serialized MockTgMessage
        self.assertTrue("MockTgMessage" in log_entry["arguments"]["args"][0])
        self.assertEqual(log_entry["arguments"]["args"][1], "custom_val_fail")
        self.assertFalse(log_entry["success"])
        self.assertIn("error", log_entry)
        self.assertEqual(log_entry["error"]["type"], "RuntimeError")
        self.assertEqual(log_entry["error"]["message"], "Bot command error triggered")
        self.assertEqual(log_entry["tags"], {"handler_type": "bot"})

    def test_06_instance_method_no_args_logging(self):
        cli_obj = MockedCLIClass("MyObj1")
        expected_system_user = "cli_method_user"
        with mock.patch('katana.decorators.trace_command.getpass.getuser', return_value=expected_system_user):
            result = cli_obj.instance_method_no_args()

        self.assertEqual(result, "MyObj1 status: method_called")

        logs = self.read_log_entries()
        self.assertEqual(len(logs), 1)
        log_entry = logs[0]

        self.assertTrue(is_uuid(log_entry["trace_id"]))
        self.assertEqual(log_entry["user"], {"username": expected_system_user, "source": "system"})
        self.assertEqual(log_entry["command_name"], "MockedCLIClass.instance_method_no_args")
        self.assertEqual(log_entry["arguments"]["args"], []) # 'self' is excluded
        self.assertEqual(log_entry["arguments"]["kwargs"], {})
        self.assertTrue(log_entry["success"])
        self.assertEqual(log_entry["result"], "MyObj1 status: method_called")
        self.assertEqual(log_entry["tags"], {"cli_class_method": True})

    def test_07_instance_method_with_args_failure(self):
        cli_obj = MockedCLIClass("MyObj2")
        expected_system_user = "cli_method_user_fail"
        with self.assertRaises(Exception) as context, \
             mock.patch('katana.decorators.trace_command.getpass.getuser', return_value=expected_system_user):
            cli_obj.instance_method_with_args("fail_method", kwarg1="problem")

        self.assertEqual(str(context.exception), "Method failed intentionally")

        logs = self.read_log_entries()
        self.assertEqual(len(logs), 1)
        log_entry = logs[0]

        self.assertTrue(is_uuid(log_entry["trace_id"]))
        self.assertEqual(log_entry["user"], {"username": expected_system_user, "source": "system"})
        self.assertEqual(log_entry["command_name"], "MockedCLIClass.instance_method_with_args")
        self.assertEqual(log_entry["arguments"]["args"], ["fail_method"]) # 'self' excluded
        self.assertEqual(log_entry["arguments"]["kwargs"], {"kwarg1": "problem"})
        self.assertFalse(log_entry["success"])
        self.assertIn("error", log_entry)
        self.assertEqual(log_entry["error"]["type"], "Exception")
        self.assertEqual(log_entry["error"]["message"], "Method failed intentionally")
        self.assertNotIn("tags", log_entry) # No tags for this method call

    def test_08_multiple_logs_append(self):
        # Patch getpass.getuser for the decorator's fallback path
        # This mock will apply to all calls within this 'with' block
        with mock.patch('katana.decorators.trace_command.getpass.getuser', return_value="multi_log_user"):
            mock_successful_command_system_user("cmd1", "call1")
            try:
                mock_failing_command_with_tags("fail")
            except ValueError:
                pass # Expected

            # Test bot command within the same multi-log sequence
            mock_message_multi = MockTgMessage(user_id=777, username="multibot", text="multi_text")
            mock_bot_command_handler(mock_message_multi, "multi_custom")

            mock_successful_command_system_user("cmd3", "call3", keyword_param="final_one")

        logs = self.read_log_entries()
        self.assertEqual(len(logs), 4) # Now 4 log entries

        # Basic checks for correct order and some key fields
        self.assertEqual(logs[0]["command_name"], "mock_successful_command_system_user")
        self.assertEqual(logs[0]["user"], {"username": "multi_log_user", "source": "system"})
        self.assertEqual(logs[0]["arguments"]["args"], ["cmd1", "call1"])
        self.assertTrue(logs[0]["success"])

        self.assertEqual(logs[1]["command_name"], "mock_failing_command_with_tags")
        self.assertEqual(logs[1]["user"], {"username": "multi_log_user", "source": "system"})
        self.assertFalse(logs[1]["success"])
        self.assertEqual(logs[1]["tags"], {"category": "test_failure", "severity": "high"})

        self.assertEqual(logs[2]["command_name"], "mock_bot_command_handler")
        self.assertEqual(logs[2]["user"], {"id": 777, "username": "multibot", "source": "telegram"})
        self.assertTrue(logs[2]["success"])
        self.assertEqual(logs[2]["tags"], {"handler_type": "bot"})

        self.assertEqual(logs[3]["command_name"], "mock_successful_command_system_user")
        self.assertEqual(logs[3]["user"], {"username": "multi_log_user", "source": "system"})
        self.assertEqual(logs[3]["arguments"]["kwargs"], {"keyword_param": "final_one"})
        self.assertTrue(logs[3]["success"])


if __name__ == "__main__":
    unittest.main()
