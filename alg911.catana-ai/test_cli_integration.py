import unittest
from unittest.mock import patch, MagicMock, call
import subprocess
import json
import os
import shutil
import time
import sys

# Assuming cli_integration.py is in the same directory or accessible via PYTHONPATH
try:
    from cli_integration import send_command_to_cli
except ImportError:
    # Fallback for different execution context
    sys.path.append(os.path.dirname(os.path.abspath(__file__)))
    from cli_integration import send_command_to_cli

# Define a directory for temporary test files
TEST_INTEGRATION_DIR_NAME = "temp_test_cli_integration_dir"
TEST_INTEGRATION_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), TEST_INTEGRATION_DIR_NAME)
DUMMY_COMMANDS_FILE = os.path.join(TEST_INTEGRATION_DIR, "dummy_katana.commands.json")
DUMMY_AGENT_SCRIPT = os.path.join(TEST_INTEGRATION_DIR, "dummy_katana_agent.py") # Only if needed

class TestCliIntegration(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        if os.path.exists(TEST_INTEGRATION_DIR):
            shutil.rmtree(TEST_INTEGRATION_DIR)
        os.makedirs(TEST_INTEGRATION_DIR, exist_ok=True)

        # Create a dummy agent script if we were to actually execute it (not typical for these tests)
        # with open(DUMMY_AGENT_SCRIPT, 'w') as f:
        #     f.write("#!/usr/bin/env python\nprint('DUMMY_AGENT_OUTPUT')")
        # os.chmod(DUMMY_AGENT_SCRIPT, 0o755)

    @classmethod
    def tearDownClass(cls):
        if os.path.exists(TEST_INTEGRATION_DIR):
            shutil.rmtree(TEST_INTEGRATION_DIR)

    def setUp(self):
        # Ensure the dummy commands file is clean before each test if it's being written to.
        if os.path.exists(DUMMY_COMMANDS_FILE):
            os.remove(DUMMY_COMMANDS_FILE)

        # Patch constants within cli_integration module for the duration of the test
        self.katana_agent_script_path_patcher = patch('cli_integration.KATANA_AGENT_SCRIPT_PATH', DUMMY_AGENT_SCRIPT)
        self.commands_file_path_patcher = patch('cli_integration.COMMANDS_FILE_PATH', DUMMY_COMMANDS_FILE)

        self.mock_katana_agent_script_path = self.katana_agent_script_path_patcher.start()
        self.mock_commands_file_path = self.commands_file_path_patcher.start()

    def tearDown(self):
        self.katana_agent_script_path_patcher.stop()
        self.commands_file_path_patcher.stop()
        if os.path.exists(DUMMY_COMMANDS_FILE):
            os.remove(DUMMY_COMMANDS_FILE)


    @patch('cli_integration.subprocess.run')
    @patch('cli_integration._load_json_file')
    @patch('cli_integration.time.sleep') # Mock time.sleep to speed up polling
    def test_send_command_success(self, mock_sleep, mock_load_json, mock_subprocess_run):
        mock_subprocess_run.return_value = MagicMock(
            stdout="Some output\nCREATED_TASK_ID: test_task_123\nMore output",
            stderr="",
            returncode=0
        )

        # Simulate polling: pending -> processing -> completed
        mock_load_json.side_effect = [
            [{"command_id": "test_task_123", "status": "pending"}],  # 1st poll
            [{"command_id": "test_task_123", "status": "processing"}], # 2nd poll
            [{"command_id": "test_task_123", "status": "completed", "result": "Task done!"}], # 3rd poll
        ]

        action = "do_something"
        params = {"arg1": "val1"}
        response = send_command_to_cli(action, params)

        expected_cli_args = [sys.executable, DUMMY_AGENT_SCRIPT, "addtask", action, "arg1=val1"]
        mock_subprocess_run.assert_called_once_with(
            expected_cli_args,
            capture_output=True,
            text=True,
            timeout=15
        )
        self.assertEqual(mock_load_json.call_count, 3)
        self.assertEqual(response, {
            "status": "success",
            "task_status": "completed",
            "result": "Task done!",
            "task_id": "test_task_123"
        })

    @patch('cli_integration.subprocess.run')
    @patch('cli_integration._load_json_file')
    @patch('cli_integration.time.sleep')
    def test_send_command_task_fails(self, mock_sleep, mock_load_json, mock_subprocess_run):
        mock_subprocess_run.return_value = MagicMock(stdout="CREATED_TASK_ID: fail_task_456", stderr="", returncode=0)

        mock_load_json.side_effect = [
            [{"command_id": "fail_task_456", "status": "pending"}],
            [{"command_id": "fail_task_456", "status": "failed", "result": "It broke."}],
        ]

        response = send_command_to_cli("do_fail", {})
        self.assertEqual(response, {
            "status": "success", # API call itself was a success
            "task_status": "failed",
            "result": "It broke.",
            "task_id": "fail_task_456"
        })

    @patch('cli_integration.subprocess.run')
    def test_send_command_subprocess_error(self, mock_subprocess_run):
        mock_subprocess_run.return_value = MagicMock(
            stdout="Something went wrong before ID",
            stderr="Big error from script",
            returncode=1
        )
        response = send_command_to_cli("any_action", {})
        self.assertEqual(response, {
            "status": "error",
            "message": "Katana agent script execution failed with return code 1.",
            "stderr": "Big error from script",
            "stdout": "Something went wrong before ID"
        })

    @patch('cli_integration.subprocess.run')
    def test_send_command_task_id_parse_error(self, mock_subprocess_run):
        mock_subprocess_run.return_value = MagicMock(stdout="No task ID here", stderr="", returncode=0)
        response = send_command_to_cli("parse_fail_action", {})
        self.assertEqual(response, {
            "status": "error",
            "message": "Could not determine task ID from Katana agent output.",
            "stdout": "No task ID here"
        })

    @patch('cli_integration.subprocess.run')
    @patch('cli_integration._load_json_file')
    @patch('cli_integration.time.sleep')
    @patch('cli_integration.DEFAULT_POLL_TIMEOUT', 0.1) # Short timeout for testing
    def test_send_command_polling_timeout(self, mock_sleep, mock_load_json, mock_subprocess_run):
        mock_subprocess_run.return_value = MagicMock(stdout="CREATED_TASK_ID: timeout_task_789", stderr="", returncode=0)

        # Simulate task always being pending
        mock_load_json.return_value = [{"command_id": "timeout_task_789", "status": "pending"}]

        response = send_command_to_cli("timeout_action", {})
        self.assertEqual(response, {
            "status": "error",
            "message": "Timeout polling for task timeout_task_789 completion."
        })

    @patch('cli_integration.subprocess.run')
    @patch('cli_integration._load_json_file')
    @patch('cli_integration.time.sleep')
    def test_send_command_commands_file_not_found_during_poll(self, mock_sleep, mock_load_json, mock_subprocess_run):
        mock_subprocess_run.return_value = MagicMock(stdout="CREATED_TASK_ID: file_disappears_task", stderr="", returncode=0)

        # Simulate file found initially, then not found (or malformed)
        mock_load_json.side_effect = [
            [{"command_id": "file_disappears_task", "status": "pending"}], # Found once
            None, # Simulates _load_json_file returning default due to error like file not found
        ]

        response = send_command_to_cli("file_disappears_action", {})
        # Depending on how _load_json_file signals error (None vs specific error dict)
        # and how send_command_to_cli handles it. Current _load_json_file returns default value (None for list).
        # The send_command_to_cli checks `if not isinstance(tasks, list):`
        # Let's refine this: if _load_json_file returns None when default_value is [], then tasks becomes None
        # The check `if not isinstance(tasks, list)` would then be true.

        # If _load_json_file returns the default value (which is an empty list `[]` in send_command_to_cli)
        # when the file is not found or malformed after the first successful read,
        # the task "file_disappears_task" would seem to have vanished from the list.
        # This would lead to the "Task ... not yet found" debug log and eventually a timeout.
        # Let's adjust the mock to simulate a malformed file returning a non-list.
        mock_load_json.side_effect = [
            [{"command_id": "file_disappears_task", "status": "pending"}],
            {"error": "malformed json"}, # Simulate _load_json_file returning a dict due to error
        ]

        response = send_command_to_cli("file_disappears_action", {})
        self.assertEqual(response, {
            "status": "error",
            "message": f"Commands file {DUMMY_COMMANDS_FILE} is malformed."
        })


    @patch('cli_integration.subprocess.run')
    def test_parameter_formatting_for_addtask(self, mock_subprocess_run):
        mock_subprocess_run.return_value = MagicMock(stdout="CREATED_TASK_ID: format_task_000", returncode=0)
        # _load_json_file will be called, needs a valid return for one poll at least
        with patch('cli_integration._load_json_file', return_value=[{"command_id": "format_task_000", "status": "completed", "result": "done"}]):
            with patch('cli_integration.time.sleep'): # Don't actually sleep
                # Test case 1: Empty parameters
                send_command_to_cli("action_no_params", {})
                expected_args1 = [sys.executable, DUMMY_AGENT_SCRIPT, "addtask", "action_no_params"]

                # Test case 2: Simple parameters
                send_command_to_cli("action_simple_params", {"key1": "val1", "key2": 123})
                expected_args2_options = [ # Order of dict items might vary
                    [sys.executable, DUMMY_AGENT_SCRIPT, "addtask", "action_simple_params", "key1=val1", "key2=123"],
                    [sys.executable, DUMMY_AGENT_SCRIPT, "addtask", "action_simple_params", "key2=123", "key1=val1"],
                ]

                # Test case 3: Parameters with spaces (ensure they are one arg like "key=value with spaces")
                send_command_to_cli("action_space_params", {"msg": "Hello world", "path": "/tmp/my file"})
                expected_args3_options = [
                    [sys.executable, DUMMY_AGENT_SCRIPT, "addtask", "action_space_params", "msg=Hello world", "path=/tmp/my file"],
                    [sys.executable, DUMMY_AGENT_SCRIPT, "addtask", "action_space_params", "path=/tmp/my file", "msg=Hello world"],
                ]

                # Check calls - this gets tricky due to dict ordering.
                # We check the last call for the most complex case.
                # For others, we can check parts of the call.
                call_list = mock_subprocess_run.call_args_list

                # Check call 1 (action_no_params)
                self.assertEqual(call_list[0][0][0], expected_args1)

                # Check call 2 (action_simple_params) - flexible for dict order
                found_call2 = False
                for expected_args2 in expected_args2_options:
                    if call_list[1][0][0] == expected_args2:
                        found_call2 = True
                        break
                self.assertTrue(found_call2, f"Call for action_simple_params not found or args mismatched: {call_list[1][0][0]}")

                # Check call 3 (action_space_params)
                found_call3 = False
                for expected_args3 in expected_args3_options:
                    if call_list[2][0][0] == expected_args3:
                        found_call3 = True
                        break
                self.assertTrue(found_call3, f"Call for action_space_params not found or args mismatched: {call_list[2][0][0]}")


if __name__ == '__main__':
    unittest.main(verbosity=2)
```
