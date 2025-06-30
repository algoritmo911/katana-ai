import unittest
import os
import json
import time
import shutil
import logging # Added
import glob # Added for checking rotated files

from katana.decorators.trace_command import trace_command
# Import the actual logger and its components for manipulation in tests
from katana.logging.telemetry_logger import telemetry_logger, JsonFormatter, LOG_FILE_PATH as DEFAULT_LOG_FILE_PATH, MAX_LOG_SIZE_BYTES as DEFAULT_MAX_BYTES, BACKUP_COUNT as DEFAULT_BACKUP_COUNT, _setup_logger as setup_telemetry_logger_module

# Define a directory for logs specific to these tests
TEST_LOGS_DIR = "test_logs_temp"
TEST_LOG_FILE_PATH = os.path.join(TEST_LOGS_DIR, "command_telemetry.log")

# Original handler details to restore later
original_handler_config = {}

# Mocked commands for testing purposes
@trace_command
def mock_successful_command(param1, param2, keyword_param=None):
    """A mock command that succeeds."""
    time.sleep(0.001) # Reduced sleep for faster tests
    return {"status": "success", "data": f"{param1}-{param2}-{keyword_param}"}

@trace_command
def mock_failing_command(param1):
    """A mock command that fails."""
    time.sleep(0.001) # Reduced sleep for faster tests
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
        time.sleep(0.001)
        if user_arg == "fail_reset":
            self.status = "reset_failed"
            raise RuntimeError("Reset failed due to an internal error")
        self.status = "reset_complete"
        # print(f"MockTraderCLI ({self.instance_name}): Reset successful. User arg: {user_arg}")
        return {"instance": self.instance_name, "status": self.status, "user_arg": user_arg}

    @trace_command
    def get_status(self):
        """Simulates a get_status command."""
        time.sleep(0.001)
        return {"instance": self.instance_name, "current_status": self.status}

def ensure_test_log_directory_exists():
    """Ensures that the directory for the test log file exists."""
    if not os.path.exists(TEST_LOGS_DIR):
        os.makedirs(TEST_LOGS_DIR)

class TestCommandTelemetry(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        global original_handler_config
        ensure_test_log_directory_exists()

        # Store original handler's settings from the actual logger
        if telemetry_logger.handlers:
            original_handler = telemetry_logger.handlers[0]
            if isinstance(original_handler, logging.handlers.RotatingFileHandler):
                original_handler_config['path'] = original_handler.baseFilename
                original_handler_config['maxBytes'] = original_handler.maxBytes
                original_handler_config['backupCount'] = original_handler.backupCount
                original_handler_config['formatter'] = original_handler.formatter
                original_handler_config['level'] = original_handler.level

        # Remove existing handlers
        for handler in telemetry_logger.handlers[:]:
            telemetry_logger.removeHandler(handler)
            handler.close() # Important to close file handles

        # Create and add a new handler for tests
        test_handler = logging.handlers.RotatingFileHandler(
            TEST_LOG_FILE_PATH,
            maxBytes=DEFAULT_MAX_BYTES, # Use default or specific test values
            backupCount=DEFAULT_BACKUP_COUNT,
            encoding='utf-8'
        )
        test_handler.setFormatter(JsonFormatter())
        test_handler.setLevel(logging.INFO) # Ensure it matches the logger's effective level
        telemetry_logger.addHandler(test_handler)
        telemetry_logger.propagate = False # Ensure no propagation during tests
        telemetry_logger.setLevel(logging.INFO) # Ensure logger level is set

        # Clean up the test log directory before any tests run
        if os.path.exists(TEST_LOGS_DIR):
            shutil.rmtree(TEST_LOGS_DIR)
        ensure_test_log_directory_exists()

    @classmethod
    def tearDownClass(cls):
        global original_handler_config
        # Clean up the test log directory
        if os.path.exists(TEST_LOGS_DIR):
            shutil.rmtree(TEST_LOGS_DIR)

        # Restore original handler if it was stored
        if original_handler_config:
            for handler in telemetry_logger.handlers[:]:
                telemetry_logger.removeHandler(handler)
                handler.close()

            restored_handler = logging.handlers.RotatingFileHandler(
                original_handler_config['path'],
                maxBytes=original_handler_config['maxBytes'],
                backupCount=original_handler_config['backupCount'],
                encoding='utf-8'
            )
            restored_handler.setFormatter(original_handler_config['formatter'])
            restored_handler.setLevel(original_handler_config['level'])
            telemetry_logger.addHandler(restored_handler)

        # Reset the LOG_FILE_PATH in the module if it was changed by other means (fallback)
        # This is less critical now that we manipulate the handler directly.
        import katana.logging.telemetry_logger
        katana.logging.telemetry_logger.LOG_FILE_PATH = DEFAULT_LOG_FILE_PATH
        # Potentially re-run _setup_logger if we had modified its global constants
        # For now, direct handler manipulation is preferred.


    def setUp(self):
        ensure_test_log_directory_exists()
        # Clear the main log file and any backup files before each test
        # This is important for rotation tests to not interfere with each other
        log_files = glob.glob(os.path.join(TEST_LOGS_DIR, "command_telemetry.log*"))
        for f_path in log_files:
            try:
                os.remove(f_path)
            except OSError:
                pass # File might have been rotated and removed by another process/thread


    def tearDown(self):
        pass # Cleanup is mostly handled in setUp or tearDownClass

    def read_log_entries(self, file_path=None):
        if file_path is None:
            file_path = TEST_LOG_FILE_PATH

        entries = []
        if not os.path.exists(file_path):
            return entries

        # Wait briefly for logs to flush, especially important for rotation tests
        # This is a bit of a hack; proper solution involves logger flushing if available
        # or more deterministic rotation triggering.
        time.sleep(0.05)

        with open(file_path, "r", encoding='utf-8') as f:
            for line in f:
                if line.strip(): # Ensure line is not empty
                    try:
                        entries.append(json.loads(line))
                    except json.JSONDecodeError as e:
                        print(f"Warning: Could not decode JSON line in {file_path}: {line.strip()} - Error: {e}")
        return entries

    def get_test_log_handler(self):
        for handler in telemetry_logger.handlers:
            if isinstance(handler, logging.handlers.RotatingFileHandler) and handler.baseFilename == TEST_LOG_FILE_PATH:
                return handler
        self.fail("Test log handler not found on telemetry_logger.")
        return None


    def test_01_log_file_creation(self):
        self.assertFalse(os.path.exists(TEST_LOG_FILE_PATH), "Log file should not exist before command execution.")
        mock_successful_command("test", "log_creation")
        # Need to give a tiny moment for the log to be written due to async nature of logging
        time.sleep(0.01)
        self.assertTrue(os.path.exists(TEST_LOG_FILE_PATH), "Log file should be created after command execution.")

    def test_02_successful_command_logging(self):
        result = mock_successful_command("arg1_val", "arg2_val", keyword_param="kw_val")
        self.assertEqual(result["status"], "success")

        logs = self.read_log_entries()
        self.assertEqual(len(logs), 1)
        log_entry = logs[0]

        self.assertEqual(log_entry["command_name"], "mock_successful_command")
        self.assertEqual(log_entry["arguments"]["args"], ["arg1_val", "arg2_val"])
        self.assertEqual(log_entry["arguments"]["kwargs"], {"keyword_param": "kw_val"})
        self.assertTrue(log_entry["success"])
        self.assertIn("execution_time_seconds", log_entry)
        self.assertTrue(log_entry["execution_time_seconds"] >= 0) # Can be very small
        self.assertEqual(log_entry["result_type"], type(result).__name__)

    def test_03_failing_command_logging(self):
        with self.assertRaises(ValueError) as context:
            mock_failing_command("fail")

        self.assertEqual(str(context.exception), "Mock command failed as requested")

        logs = self.read_log_entries()
        self.assertEqual(len(logs), 1)
        log_entry = logs[0]

        self.assertEqual(log_entry["command_name"], "mock_failing_command")
        self.assertEqual(log_entry["arguments"]["args"], ["fail"])
        self.assertEqual(log_entry["arguments"]["kwargs"], {})
        self.assertFalse(log_entry["success"])
        self.assertIn("execution_time_seconds", log_entry)
        self.assertTrue(log_entry["execution_time_seconds"] >= 0)
        self.assertIn("error", log_entry)
        self.assertEqual(log_entry["error"]["type"], "ValueError")
        self.assertEqual(log_entry["error"]["message"], "Mock command failed as requested")

    def test_04_trader_reset_command_simulated(self):
        trader_sim = MockTraderCLI("SimTrader1")
        result = trader_sim.reset(user_arg="test_reset")

        self.assertEqual(result["status"], "reset_complete")
        self.assertEqual(trader_sim.status, "reset_complete")

        logs = self.read_log_entries()
        self.assertEqual(len(logs), 1)
        log_entry = logs[0]

        self.assertEqual(log_entry["command_name"], "MockTraderCLI.reset")
        self.assertEqual(log_entry["arguments"]["args"], [])
        self.assertEqual(log_entry["arguments"]["kwargs"], {"user_arg": "test_reset"})
        self.assertTrue(log_entry["success"])
        self.assertEqual(log_entry["result_type"], "dict")

    def test_05_trader_reset_command_simulated_failure(self):
        trader_sim = MockTraderCLI("SimTraderFail")
        with self.assertRaises(RuntimeError) as context:
            trader_sim.reset(user_arg="fail_reset")

        self.assertEqual(str(context.exception), "Reset failed due to an internal error")
        self.assertEqual(trader_sim.status, "reset_failed")

        logs = self.read_log_entries()
        self.assertEqual(len(logs), 1)
        log_entry = logs[0]

        self.assertEqual(log_entry["command_name"], "MockTraderCLI.reset")
        self.assertEqual(log_entry["arguments"]["args"], [])
        self.assertEqual(log_entry["arguments"]["kwargs"], {"user_arg": "fail_reset"})
        self.assertFalse(log_entry["success"])
        self.assertIsNotNone(log_entry["error"])
        self.assertEqual(log_entry["error"]["type"], "RuntimeError")
        self.assertEqual(log_entry["error"]["message"], "Reset failed due to an internal error")


    def test_06_trader_get_status_command_simulated(self):
        trader_sim = MockTraderCLI("SimStatusTrader")
        trader_sim.status = "running_ok"
        result = trader_sim.get_status()

        self.assertEqual(result["current_status"], "running_ok")

        logs = self.read_log_entries()
        self.assertEqual(len(logs), 1)
        log_entry = logs[0]

        self.assertEqual(log_entry["command_name"], "MockTraderCLI.get_status")
        self.assertEqual(log_entry["arguments"]["args"], [])
        self.assertEqual(log_entry["arguments"]["kwargs"], {})
        self.assertTrue(log_entry["success"])
        self.assertEqual(log_entry["result_type"], "dict")

    def test_07_multiple_logs_append(self):
        mock_successful_command("cmd1", "call1")
        try:
            mock_failing_command("fail")
        except ValueError:
            pass
        mock_successful_command("cmd3", "call3", keyword_param="final_one")

        logs = self.read_log_entries()
        self.assertEqual(len(logs), 3)
        self.assertEqual(logs[0]["command_name"], "mock_successful_command")
        self.assertEqual(logs[0]["arguments"]["args"], ["cmd1", "call1"])
        self.assertEqual(logs[1]["command_name"], "mock_failing_command")
        self.assertFalse(logs[1]["success"])
        self.assertEqual(logs[2]["command_name"], "mock_successful_command")
        self.assertEqual(logs[2]["arguments"]["kwargs"], {"keyword_param": "final_one"})

    def test_08_log_rotation(self):
        test_handler = self.get_test_log_handler()
        original_max_bytes = test_handler.maxBytes
        original_backup_count = test_handler.backupCount

        # Configure for small logs to force rotation quickly
        test_handler.maxBytes = 300  # Small enough for a few log entries to trigger
        test_handler.backupCount = 2   # Keep command_telemetry.log, .log.1, .log.2

        try:
            # Each log entry is around 150-250 bytes.
            # Log enough messages to trigger rotation multiple times.
            # Aim for at least (backupCount + 1) * maxBytes / avg_log_size_ish
            # (2+1) * 300 bytes = 900 bytes total. If logs are ~200 bytes, need ~5 logs.
            # To be safe and ensure multiple rotations if possible:
            num_logs_to_generate = 15
            for i in range(num_logs_to_generate):
                mock_successful_command(f"rotate_test_{i}", f"data_{i}", keyword_param=f"kw_{i}")
                # Small delay may be needed if logging is very fast and file system ops are slow
                if i % 5 == 0: time.sleep(0.02)


            # Check number of log files
            # Flush logger to ensure all logs are written before checking files
            test_handler.flush()
            # It might take a moment for the rotation to complete and files to appear
            time.sleep(0.1)


            log_files = sorted(glob.glob(os.path.join(TEST_LOGS_DIR, "command_telemetry.log*")))

            # We expect at most backupCount + 1 files
            self.assertTrue(len(log_files) <= test_handler.backupCount + 1,
                            f"Expected at most {test_handler.backupCount + 1} log files, found {len(log_files)}: {log_files}")
            self.assertTrue(len(log_files) > 0, "Expected at least one log file, found none.")

            # Verify that the main log file exists
            self.assertIn(TEST_LOG_FILE_PATH, log_files, "Main log file not found after rotation test.")

            # Verify content if possible (e.g., total number of logs across files)
            total_logged_entries = 0
            all_log_entries_chronological = []

            # Read logs from all files, starting with the oldest backup
            # Rotated files are .log.1, .log.2, etc., where .log.1 is newer than .log.2
            # So, we should read them in reverse order of their number extension for chronological order
            # Or, if we sort them alphabetically, command_telemetry.log.9 comes before command_telemetry.log.10
            # A robust way is to sort by modification time if available, but glob gives strings.
            # For .1, .2, .3, simple string sort works if numbers are single digit.
            # If numbers can be > 9, need custom sort. glob.glob output is not guaranteed to be sorted.

            # Let's sort them by name to ensure .log, .log.1, .log.2 order for reading
            # This means .log is newest, .log.1 is older, .log.N is oldest.
            # To get chronological order, we should read .log.N, then .log.N-1, ..., .log.1, then .log

            processed_files_for_log_count = []
            # Files like command_telemetry.log.1, command_telemetry.log.2 etc.
            backup_files = sorted([f for f in log_files if f != TEST_LOG_FILE_PATH], reverse=True) # .log.2, .log.1

            for log_file in backup_files:
                processed_files_for_log_count.append(log_file)
                entries = self.read_log_entries(file_path=log_file)
                total_logged_entries += len(entries)
                all_log_entries_chronological.extend(entries)

            # Add current log file (newest)
            if TEST_LOG_FILE_PATH in log_files:
                processed_files_for_log_count.append(TEST_LOG_FILE_PATH)
                entries = self.read_log_entries(file_path=TEST_LOG_FILE_PATH)
                total_logged_entries += len(entries)
                all_log_entries_chronological.extend(entries)

            self.assertEqual(total_logged_entries, num_logs_to_generate,
                             f"Expected {num_logs_to_generate} total log entries across all files, but found {total_logged_entries}. Files processed: {processed_files_for_log_count}")

            # Check if the newest log entries are in the main log file (command_telemetry.log)
            # And oldest in the last backup
            if len(log_files) > 1 and total_logged_entries > 0:
                # Last entry generated should be in the main log file
                main_log_entries = self.read_log_entries(file_path=TEST_LOG_FILE_PATH)
                if main_log_entries: # It might be empty if all logs fit into maxBytes and then rotated away
                    last_generated_command_name = f"mock_successful_command" # All use this
                    last_generated_arg1 = f"rotate_test_{num_logs_to_generate - 1}"

                    # The very last log entry should be in the main log file
                    # or one of the recent backups if rotation was very aggressive.
                    # This check is more complex due to exact rotation points.
                    # A simpler check is that the last log entry in all_log_entries_chronological
                    # matches the last generated log.
                    self.assertEqual(all_log_entries_chronological[-1]["arguments"]["args"][0], last_generated_arg1)


        finally:
            # Restore original handler settings
            test_handler.maxBytes = original_max_bytes
            test_handler.backupCount = original_backup_count
            # It's good practice to flush after tests involving file I/O
            test_handler.close() # Close the handler to release file resource
            # Re-add it, or better, restore the original handler setup in tearDownClass
            # For simplicity here, we assume tearDownClass will handle full restoration.
            # Re-adding is tricky because the stream might be closed.
            # The current setUpClass/tearDownClass structure should handle re-creating the test handler
            # for the next test, or restoring the original application handler after all tests.


if __name__ == "__main__":
    unittest.main()
