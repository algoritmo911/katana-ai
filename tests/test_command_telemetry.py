import unittest
import os
import json
import time
import shutil
from katana.decorators.trace_command import trace_command
from katana.logging.telemetry_logger import LOG_FILE_PATH, ensure_log_directory_exists

# Define a directory for logs specific to these tests
TEST_LOGS_DIR = "test_logs_temp"
TEST_LOG_FILE_PATH = os.path.join(TEST_LOGS_DIR, "command_telemetry.log")

# Mocked commands for testing purposes
@trace_command
def mock_successful_command(param1, param2, keyword_param=None):
    """A mock command that succeeds."""
    time.sleep(0.01) # Simulate some work
    return {"status": "success", "data": f"{param1}-{param2}-{keyword_param}"}

@trace_command
def mock_failing_command(param1):
    """A mock command that fails."""
    time.sleep(0.01) # Simulate some work
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
        print(f"MockTraderCLI ({self.instance_name}): Reset successful. User arg: {user_arg}")
        return {"instance": self.instance_name, "status": self.status, "user_arg": user_arg}

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

        # Ensure the test log directory exists
        if os.path.exists(TEST_LOGS_DIR):
            shutil.rmtree(TEST_LOGS_DIR)
        ensure_log_directory_exists() # This will now use TEST_LOG_FILE_PATH

    @classmethod
    def tearDownClass(cls):
        # Clean up the test log directory
        if os.path.exists(TEST_LOGS_DIR):
            shutil.rmtree(TEST_LOGS_DIR)

        # Restore original log file path if necessary (though tests run in separate process usually)
        import katana.logging.telemetry_logger
        katana.logging.telemetry_logger.LOG_FILE_PATH = "logs/command_telemetry.log"


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
        mock_successful_command("test", "log_creation")
        self.assertTrue(os.path.exists(TEST_LOG_FILE_PATH), "Log file should be created after command execution.")

    def test_02_successful_command_logging(self):
        result = mock_successful_command("arg1_val", "arg2_val", keyword_param="kw_val")
        self.assertEqual(result["status"], "success")

        logs = self.read_log_entries()
        self.assertEqual(len(logs), 1)
        log_entry = logs[0]

        self.assertEqual(log_entry["command_name"], "mock_successful_command")
        self.assertEqual(log_entry["arguments"]["args"], ["arg1_val", "arg2_val"]) # Expect list
        self.assertEqual(log_entry["arguments"]["kwargs"], {"keyword_param": "kw_val"})
        self.assertTrue(log_entry["success"])
        self.assertIn("execution_time_seconds", log_entry)
        self.assertTrue(log_entry["execution_time_seconds"] > 0)
        self.assertEqual(log_entry["result_type"], type(result).__name__) # Expecting 'dict'

    def test_03_failing_command_logging(self):
        with self.assertRaises(ValueError) as context:
            mock_failing_command("fail")

        self.assertEqual(str(context.exception), "Mock command failed as requested")

        logs = self.read_log_entries()
        self.assertEqual(len(logs), 1)
        log_entry = logs[0]

        self.assertEqual(log_entry["command_name"], "mock_failing_command")
        self.assertEqual(log_entry["arguments"]["args"], ["fail"]) # Expect list
        self.assertEqual(log_entry["arguments"]["kwargs"], {})
        self.assertFalse(log_entry["success"])
        self.assertIn("execution_time_seconds", log_entry)
        self.assertTrue(log_entry["execution_time_seconds"] > 0)
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
        self.assertEqual(log_entry["arguments"]["args"], []) # No positional args were passed
        self.assertEqual(log_entry["arguments"]["kwargs"], {"user_arg": "test_reset"}) # user_arg is a kwarg
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
        self.assertEqual(log_entry["arguments"]["args"], []) # No positional args were passed
        self.assertEqual(log_entry["arguments"]["kwargs"], {"user_arg": "fail_reset"})  # user_arg is a kwarg
        self.assertFalse(log_entry["success"])
        self.assertIsNotNone(log_entry["error"])
        self.assertEqual(log_entry["error"]["type"], "RuntimeError")
        self.assertEqual(log_entry["error"]["message"], "Reset failed due to an internal error")


    def test_06_trader_get_status_command_simulated(self):
        trader_sim = MockTraderCLI("SimStatusTrader")
        trader_sim.status = "running_ok" # Set a status
        result = trader_sim.get_status()

        self.assertEqual(result["current_status"], "running_ok")

        logs = self.read_log_entries()
        self.assertEqual(len(logs), 1)
        log_entry = logs[0]

        self.assertEqual(log_entry["command_name"], "MockTraderCLI.get_status")
        self.assertEqual(log_entry["arguments"]["args"], []) # Expect empty list
        self.assertEqual(log_entry["arguments"]["kwargs"], {})
        self.assertTrue(log_entry["success"])
        self.assertEqual(log_entry["result_type"], "dict")

    def test_07_multiple_logs_append(self):
        mock_successful_command("cmd1", "call1")
        try:
            mock_failing_command("fail")
        except ValueError:
            pass # Expected
        mock_successful_command("cmd3", "call3", keyword_param="final_one")

        logs = self.read_log_entries()
        self.assertEqual(len(logs), 3)
        self.assertEqual(logs[0]["command_name"], "mock_successful_command")
        self.assertEqual(logs[0]["arguments"]["args"], ["cmd1", "call1"]) # Expect list
        self.assertEqual(logs[1]["command_name"], "mock_failing_command")
        self.assertFalse(logs[1]["success"])
        self.assertEqual(logs[2]["command_name"], "mock_successful_command")
        self.assertEqual(logs[2]["arguments"]["kwargs"], {"keyword_param": "final_one"})


if __name__ == "__main__":
    unittest.main()
