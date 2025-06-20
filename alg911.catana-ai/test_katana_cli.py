import unittest
import os
import json
import shutil
from unittest.mock import patch, MagicMock, mock_open
import datetime

# Assuming katana_agent.py is in the same directory or accessible via PYTHONPATH
# Need to adjust if running tests from a different working directory.
try:
    from katana_agent import KatanaCLI, N8N_TELEGRAM_SEND_WEBHOOK_URL
except ImportError:
    # Fallback for different execution context (e.g. if tests are in a subfolder)
    import sys
    sys.path.append(os.path.dirname(os.path.abspath(__file__)))
    from katana_agent import KatanaCLI, N8N_TELEGRAM_SEND_WEBHOOK_URL


# Define temporary file paths for testing
TEST_DIR_NAME = "temp_test_katana_files_dir"
# Absolute path for TEST_DIR to avoid issues with current working directory
TEST_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), TEST_DIR_NAME)


TEST_EVENTS_LOG_FILE = os.path.join(TEST_DIR, "test_katana_events.log")
TEST_COMMANDS_FILE = os.path.join(TEST_DIR, "test_katana.commands.json")
TEST_MEMORY_FILE = os.path.join(TEST_DIR, "test_katana_memory.json")
TEST_HISTORY_FILE = os.path.join(TEST_DIR, "test_katana.history.json")
TEST_SYNC_STATUS_FILE = os.path.join(TEST_DIR, "test_sync_status.json")

# Store original values of path constants from katana_agent
ORIGINAL_AGENT_PATHS = {}

# Test paths to be patched into katana_agent
PATCH_PATHS = {
    "EVENTS_LOG_FILE": TEST_EVENTS_LOG_FILE,
    "COMMANDS_FILE": TEST_COMMANDS_FILE,
    "MEMORY_FILE": TEST_MEMORY_FILE,
    "HISTORY_FILE": TEST_HISTORY_FILE,
    "SYNC_STATUS_FILE": TEST_SYNC_STATUS_FILE,
}

# Fixed datetime for mocking
FIXED_DATETIME_NOW = datetime.datetime(2024, 1, 1, 12, 0, 0, tzinfo=datetime.timezone.utc)
FIXED_DATETIME_ISO = FIXED_DATETIME_NOW.isoformat()

class TestKatanaCLI(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        if os.path.exists(TEST_DIR):
            shutil.rmtree(TEST_DIR)
        os.makedirs(TEST_DIR, exist_ok=True)

        # Store original paths from katana_agent and start patching
        cls.path_patchers = []
        import katana_agent # Ensure module is loaded
        for name, test_path in PATCH_PATHS.items():
            ORIGINAL_AGENT_PATHS[name] = getattr(katana_agent, name)
            patcher = patch(f"katana_agent.{name}", test_path)
            patcher.start()
            cls.path_patchers.append(patcher)

        # Patch N8N_TELEGRAM_SEND_WEBHOOK_URL to a test URL
        cls.n8n_url_patcher = patch("katana_agent.N8N_TELEGRAM_SEND_WEBHOOK_URL", "http://fake-n8n-url.com/webhook")
        cls.n8n_url_patcher.start()


    @classmethod
    def tearDownClass(cls):
        for patcher in cls.path_patchers:
            patcher.stop()

        cls.n8n_url_patcher.stop()

        # Restore original paths in katana_agent module (optional, as tests usually run in isolated process)
        # import katana_agent
        # for name, original_path in ORIGINAL_AGENT_PATHS.items():
        #     setattr(katana_agent, name, original_path)

        if os.path.exists(TEST_DIR):
            shutil.rmtree(TEST_DIR)

    def setUp(self):
        # Clean up (remove) temp files before each test to ensure isolation
        for path in PATCH_PATHS.values():
            if os.path.exists(path):
                os.remove(path)

        self.cli = KatanaCLI()
        # Suppress logger output to console during tests
        self.cli.logger.setLevel(logging.CRITICAL + 1)
        # Initialize files (this will use the patched paths)
        self.cli.initialize_katana_files()


    def tearDown(self):
        # Any specific cleanup after each test if needed
        pass

    def _read_json_file(self, path):
        if not os.path.exists(path):
            return None
        with open(path, 'r') as f:
            return json.load(f)

    def test_01_initialize_katana_files(self):
        self.assertTrue(os.path.exists(TEST_COMMANDS_FILE))
        self.assertTrue(os.path.exists(TEST_MEMORY_FILE))
        self.assertTrue(os.path.exists(TEST_HISTORY_FILE))
        self.assertTrue(os.path.exists(TEST_SYNC_STATUS_FILE))

        memory_data = self._read_json_file(TEST_MEMORY_FILE)
        self.assertIsNotNone(memory_data)
        self.assertEqual(memory_data.get('katana_service_status'), "stopped")

    def test_02_add_to_history(self):
        self.cli.add_to_history("test command 1")
        self.cli.add_to_history("test command 2")
        history_data = self._read_json_file(TEST_HISTORY_FILE)
        self.assertIsNotNone(history_data)
        self.assertEqual(len(history_data), 2)
        self.assertEqual(history_data[0]['command_string'], "test command 1")

    @patch('katana_agent.datetime.datetime')
    def test_03_add_task(self, mock_dt):
        mock_dt.now.return_value = FIXED_DATETIME_NOW

        task_id = self.cli.add_task("test_action", {"param1": "value1"}, origin="test_origin")
        self.assertIsNotNone(task_id)

        commands_data = self._read_json_file(TEST_COMMANDS_FILE)
        self.assertIsNotNone(commands_data)
        self.assertEqual(len(commands_data), 1)
        task = commands_data[0]
        self.assertEqual(task['command_id'], task_id)
        self.assertEqual(task['action'], "test_action")
        self.assertEqual(task['parameters']['param1'], "value1")
        self.assertEqual(task['status'], "pending")
        self.assertEqual(task['created_at'], FIXED_DATETIME_ISO)
        self.assertEqual(task['origin'], "test_origin")

    def test_04_get_oldest_pending_task(self):
        self.cli.add_task("action1", {"p":1}) # task1
        task_id2 = self.cli.add_task("action2", {"p":2}) # task2, should be returned if first is processed

        # Mark first task as completed to test retrieval of next pending
        tasks = self._read_json_file(TEST_COMMANDS_FILE)
        tasks[0]['status'] = "completed"
        with open(TEST_COMMANDS_FILE, 'w') as f: json.dump(tasks, f)

        pending_task = self.cli.get_oldest_pending_task()
        self.assertIsNotNone(pending_task)
        self.assertEqual(pending_task['command_id'], task_id2)
        self.assertEqual(pending_task['status'], "pending")

        # Test when no pending tasks
        tasks[1]['status'] = "completed" # Mark second task also completed
        with open(TEST_COMMANDS_FILE, 'w') as f: json.dump(tasks, f)
        self.assertIsNone(self.cli.get_oldest_pending_task())

    def test_05_update_task(self):
        task_id = self.cli.add_task("action_to_update", {})
        updated = self.cli.update_task(task_id, {"status": "completed", "result": "success!"})
        self.assertTrue(updated)

        tasks = self._read_json_file(TEST_COMMANDS_FILE)
        self.assertEqual(tasks[0]['status'], "completed")
        self.assertEqual(tasks[0]['result'], "success!")

        self.assertFalse(self.cli.update_task("non_existent_id", {"status":"failed"}))

    @patch.object(KatanaCLI, 'send_telegram_message', MagicMock())
    def test_06_process_telegram_message_status(self):
        # Prepare a task similar to how n8n_webhook_handler would create it
        telegram_payload = {
            "user_id": "test_user",
            "chat_id": "test_chat",
            "text": "/status",
            "original_command_id": "original_id_from_tg"
        }
        # Manually add it as a task
        task_id = self.cli.add_task(action="process_telegram_message", parameters=telegram_payload, origin="telegram_webhook")

        # Simulate shell loop processing
        pending_task = self.cli.get_oldest_pending_task()
        self.assertIsNotNone(pending_task)
        self.assertEqual(pending_task['command_id'], task_id)

        self.cli.update_task(task_id, {"status": "processing", "processed_at": FIXED_DATETIME_ISO})
        success, result_msg = self.cli._dispatch_command_execution(
            pending_task['action'],
            pending_task['parameters'],
            source="task"
        )
        self.assertTrue(success)
        self.assertIn("Status request processed", result_msg)

        self.cli.update_task(task_id, {"status": "completed", "result": result_msg})

        # Check if send_telegram_message was called correctly
        self.cli.send_telegram_message.assert_called_once()
        args, kwargs = self.cli.send_telegram_message.call_args
        self.assertEqual(args[0], "test_chat") # chat_id
        self.assertIn("Katana Agent is running.", args[1]) # message content
        self.assertIn("Pending tasks: 0", args[1]) # Initially 0 other pending tasks (task itself was pending)


    @patch('katana_agent.datetime.datetime')
    def test_07_start_stop_status_katana(self, mock_dt_status):
        mock_dt_status.now.return_value = FIXED_DATETIME_NOW

        # Test start_katana
        success, msg = self.cli._dispatch_command_execution("start_katana", [], source="cli")
        self.assertTrue(success)
        self.assertIn("Katana service started successfully", msg)
        self.assertEqual(self.cli.agent_memory_state['katana_service_status'], "running")
        self.assertEqual(self.cli.agent_memory_state['katana_service_last_start_time'], FIXED_DATETIME_ISO)

        # Test status_katana (running)
        success, msg = self.cli._dispatch_command_execution("status_katana", [], source="cli")
        self.assertTrue(success)
        self.assertIn("Katana Service Status: running", msg)
        self.assertIn(f"Last Start Time: {FIXED_DATETIME_ISO}", msg)

        # Test stop_katana
        # Advance time slightly for stop
        mock_dt_status.now.return_value = FIXED_DATETIME_NOW + datetime.timedelta(hours=1)
        fixed_stop_iso = (FIXED_DATETIME_NOW + datetime.timedelta(hours=1)).isoformat()

        success, msg = self.cli._dispatch_command_execution("stop_katana", [], source="cli")
        self.assertTrue(success)
        self.assertIn("Katana service stopped successfully", msg)
        self.assertEqual(self.cli.agent_memory_state['katana_service_status'], "stopped")
        self.assertEqual(self.cli.agent_memory_state['katana_service_last_stop_time'], fixed_stop_iso)

        # Test status_katana (stopped)
        success, msg = self.cli._dispatch_command_execution("status_katana", [], source="cli")
        self.assertTrue(success)
        self.assertIn("Katana Service Status: stopped", msg)
        self.assertIn(f"Last Start Time: {FIXED_DATETIME_ISO}", msg) # Start time should persist
        self.assertIn(f"Last Stop Time: {fixed_stop_iso}", msg)

    def test_08_addtask_cli_command(self):
        success, msg = self.cli._dispatch_command_execution("addtask", ["my_cli_action", "p1=v1", "p2=v2_val"], source="cli")
        self.assertTrue(success)
        self.assertIn("Task", msg)
        self.assertIn("added", msg)

        tasks = self._read_json_file(TEST_COMMANDS_FILE)
        self.assertIsNotNone(tasks)
        self.assertEqual(len(tasks), 1)
        task = tasks[0]
        self.assertEqual(task['action'], "my_cli_action")
        self.assertEqual(task['parameters']['p1'], "v1")
        self.assertEqual(task['parameters']['p2'], "v2_val")
        self.assertEqual(task['origin'], "cli_addtask")
        self.assertEqual(task['status'], "pending")

    def test_09_echo_command_cli(self):
        # Using _dispatch_command_execution to simulate CLI call
        # Need to patch print for this test to capture output
        with patch('builtins.print') as mocked_print:
            success, result_msg = self.cli._dispatch_command_execution("echo", ["hello", "world"], source="cli")
            self.assertTrue(success)
            self.assertEqual(result_msg, "hello world")
            mocked_print.assert_called_once_with("hello world")

    def test_10_memdump_command_cli(self):
        self.cli.agent_memory_state = {"test_key": "test_value"} # Setup some memory
        expected_dump = json.dumps({"test_key": "test_value", "katana_service_status": "stopped"}, indent=2) # status init by setup

        with patch('builtins.print') as mocked_print:
            success, result_msg = self.cli._dispatch_command_execution("memdump", [], source="cli")
            self.assertTrue(success)
            # Result message for memdump is the json string
            self.assertEqual(result_msg, expected_dump)
            mocked_print.assert_called_once_with(expected_dump)

    def test_11_exit_command_cli(self):
        success, result_msg = self.cli._dispatch_command_execution("exit", [], source="cli")
        self.assertFalse(success) # Exit command returns False for success to signal shell stop
        self.assertEqual(result_msg, "Exiting KatanaCLI.")


# This is needed to run tests if the file is executed directly
if __name__ == "__main__":
    # Important: We need to adjust sys.path if katana_agent is not directly importable
    # This is usually handled by test runners like `python -m unittest discover` from project root

    # If katana_agent is one level up
    # sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

    # Re-import katana_agent's logger for setting level if needed for debugging tests
    from katana_agent import katana_logger as agent_logger # if needed to configure
    # agent_logger.setLevel(logging.DEBUG) # Example for debugging test issues

    unittest.main(verbosity=2)

# To suppress logging from the agent itself during tests, it was done in setUp.
# If specific tests need to check log output, they might need to configure a
# specific handler or check the content of TEST_EVENTS_LOG_FILE.
# For example, to check for the N8N URL warning:
#   In setUp: self.cli.logger.removeHandler(self.cli.logger.handlers[0]) # remove console handler
#   or set level higher. The current `self.cli.logger.setLevel(logging.CRITICAL + 1)` in setUp works.

```
