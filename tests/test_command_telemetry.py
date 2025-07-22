import unittest
import os
import json
import time
import shutil
from unittest import mock
from datetime import datetime
from katana.decorators.trace_command import trace_command
from katana.logging.telemetry_logger import (
    ensure_log_directory_exists,
    write_to_local_log,
    write_to_supabase,
    make_serializable,
)

# Define a directory for logs specific to these tests
TEST_LOGS_DIR = "test_logs_temp"
TEST_LOG_FILE_PATH = os.path.join(TEST_LOGS_DIR, "command_telemetry.log")


# Helper function to validate ISO format timestamp
def is_iso_timestamp(timestamp_str):
    try:
        datetime.fromisoformat(timestamp_str.replace("Z", "+00:00"))
        return True
    except (ValueError, TypeError):
        return False


# Mocked commands for testing purposes
@trace_command
def mock_successful_command(param1, param2, keyword_param=None):
    """A mock command that succeeds."""
    time.sleep(0.01)
    return {"status": "success", "data": f"{param1}-{param2}-{keyword_param}"}


@trace_command
def mock_failing_command(param1):
    """A mock command that fails."""
    time.sleep(0.01)
    if param1 == "fail":
        raise ValueError("Mock command failed as requested")
    return {"status": "unexpected_success"}


class MockTraderCLI:
    def __init__(self, instance_name="test_instance"):
        self.instance_name = instance_name
        self.status = "initial"

    @trace_command
    def reset(self, user_arg=None):
        """Simulates a reset command for the trader."""
        time.sleep(0.01)
        if user_arg == "fail_reset":
            self.status = "reset_failed"
            raise RuntimeError("Reset failed due to an internal error")
        self.status = "reset_complete"
        return {
            "instance": self.instance_name,
            "status": self.status,
            "user_arg": user_arg,
        }

    @trace_command
    def get_status(self):
        """Simulates a get_status command."""
        time.sleep(0.01)
        return {"instance": self.instance_name, "current_status": self.status}


class TestCommandTelemetry(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Override the default log file path for testing
        import katana.logging.telemetry_logger

        katana.logging.telemetry_logger.LOG_FILE_PATH = TEST_LOG_FILE_PATH
        cls.mock_supabase_patch = mock.patch(
            "katana.logging.telemetry_logger.supabase", autospec=True
        )
        cls.mock_supabase = cls.mock_supabase_patch.start()

        if os.path.exists(TEST_LOGS_DIR):
            shutil.rmtree(TEST_LOGS_DIR)
        ensure_log_directory_exists()

    @classmethod
    def tearDownClass(cls):
        cls.mock_supabase_patch.stop()
        if os.path.exists(TEST_LOGS_DIR):
            shutil.rmtree(TEST_LOGS_DIR)
        import katana.logging.telemetry_logger

        katana.logging.telemetry_logger.LOG_FILE_PATH = "logs/command_telemetry.log"

    def setUp(self):
        if os.path.exists(TEST_LOG_FILE_PATH):
            os.remove(TEST_LOG_FILE_PATH)
        ensure_log_directory_exists()
        self.mock_supabase.reset_mock()

    def read_log_entries(self):
        if not os.path.exists(TEST_LOG_FILE_PATH):
            return []
        with open(TEST_LOG_FILE_PATH, "r") as f:
            return [json.loads(line) for line in f]

    def test_01_log_file_creation_and_supabase_call(self):
        with mock.patch(
            "katana.decorators.trace_command.getpass.getuser", return_value="test_user"
        ):
            mock_successful_command("test", "log_creation")

        self.assertTrue(os.path.exists(TEST_LOG_FILE_PATH))
        self.mock_supabase.table.assert_called_once()
        self.mock_supabase.table.return_value.insert.assert_called_once()

    def test_02_successful_command_logging(self):
        with mock.patch(
            "katana.decorators.trace_command.getpass.getuser", return_value="test_user"
        ):
            result = mock_successful_command(
                "arg1_val", "arg2_val", keyword_param="kw_val"
            )

        logs = self.read_log_entries()
        self.assertEqual(len(logs), 1)
        log_entry = logs[0]

        self.assertEqual(log_entry["user"], "test_user")
        self.assertTrue(is_iso_timestamp(log_entry["command_start_time_utc"]))
        self.assertEqual(log_entry["command_name"], "mock_successful_command")
        self.assertEqual(log_entry["arguments"]["args"], ["arg1_val", "arg2_val"])
        self.assertTrue(log_entry["success"])
        self.assertEqual(log_entry["result_type"], type(result).__name__)

        # Verify Supabase call
        self.mock_supabase.table.assert_called_with("command_logs")
        self.mock_supabase.table().insert.assert_called_once()

    def test_03_failing_command_logging(self):
        with self.assertRaises(ValueError), mock.patch(
            "katana.decorators.trace_command.getpass.getuser", return_value="test_user"
        ):
            mock_failing_command("fail")

        logs = self.read_log_entries()
        self.assertEqual(len(logs), 1)
        log_entry = logs[0]

        self.assertFalse(log_entry["success"])
        self.assertEqual(log_entry["error"]["type"], "ValueError")

        # Verify Supabase call
        self.mock_supabase.table.assert_called_with("command_logs")
        self.mock_supabase.table().insert.assert_called_once()

    def test_04_supabase_disabled(self):
        with mock.patch(
            "katana.logging.telemetry_logger.supabase", None
        ), mock.patch(
            "katana.decorators.trace_command.getpass.getuser", return_value="test_user"
        ):
            mock_successful_command("no", "supabase")

        self.assertTrue(os.path.exists(TEST_LOG_FILE_PATH))
        self.mock_supabase.table.assert_not_called()

    def test_05_serializable_helper(self):
        unserializable_data = {
            "datetime": datetime.now(),
            "bytes": b"test",
            "set": {1, 2, 3},
        }
        serialized_data = make_serializable(unserializable_data)
        self.assertIn("datetime", serialized_data)
        self.assertIsInstance(serialized_data["datetime"], str)
        self.assertEqual(serialized_data["bytes"], "b'test'")
        self.assertEqual(serialized_data["set"], "{1, 2, 3}")

    def test_06_write_to_local_log_exception(self):
        with mock.patch(
            "builtins.open", mock.mock_open()
        ) as mock_file, mock.patch("builtins.print") as mock_print:
            mock_file.side_effect = IOError("Disk full")
            write_to_local_log({"test": "data"})
            mock_print.assert_any_call("Error writing to telemetry log: Disk full")

    def test_07_write_to_supabase_exception(self):
        self.mock_supabase.table.return_value.insert.side_effect = Exception(
            "Connection error"
        )
        with mock.patch("builtins.print") as mock_print:
            write_to_supabase({"test": "data"})
            mock_print.assert_any_call(
                "Failed to write to Supabase: Connection error"
            )

    def test_08_init_supabase_exception(self):
        with mock.patch.dict(os.environ, {"SUPABASE_URL": "invalid_url", "SUPABASE_KEY": "key"}), \
             mock.patch("builtins.print") as mock_print:
            # Reload the module to trigger the client creation
            import importlib
            import katana.logging.telemetry_logger
            importlib.reload(katana.logging.telemetry_logger)
            # The error message comes from within the supabase-py library
            mock_print.assert_any_call("Error initializing Supabase client: Invalid URL")

    @mock.patch("katana.logging.telemetry_logger.supabase")
    def test_09_supabase_response_error(self, mock_supabase_client):
        # Create a mock response object with an error attribute
        mock_response = mock.Mock()
        mock_response.data = []
        mock_response.error = "Supabase API error"

        # Configure the mock Supabase client to return the mock response
        mock_supabase_client.table.return_value.insert.return_value.execute.return_value = mock_response

        with mock.patch("builtins.print") as mock_print:
            write_to_supabase({"test": "data"})
            mock_print.assert_any_call("Error writing to Supabase: Supabase API error")


if __name__ == "__main__":
    unittest.main()
