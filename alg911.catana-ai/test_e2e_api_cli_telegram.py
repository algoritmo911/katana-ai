import unittest
from unittest.mock import patch, MagicMock
import json
import os
import shutil
import time
import sys
import logging

# Ensure alg911.catana-ai is in path if running tests from a different root
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '.')))

from mock_backend_api import app # For the test client
# We need to patch paths *before* cli_integration or katana_agent are heavily used or imported elsewhere
# if their global constants are defined at import time.

# Define a directory for all temporary E2E test files
TEST_E2E_DIR_NAME = "temp_test_e2e_katana_files_dir"
TEST_E2E_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), TEST_E2E_DIR_NAME)

# Temporary file paths for this E2E test suite
TEMP_COMMANDS_FILE = os.path.join(TEST_E2E_DIR, "e2e_katana.commands.json")
TEMP_MEMORY_FILE = os.path.join(TEST_E2E_DIR, "e2e_katana_memory.json")
TEMP_HISTORY_FILE = os.path.join(TEST_E2E_DIR, "e2e_katana.history.json")
TEMP_EVENTS_LOG_FILE = os.path.join(TEST_E2E_DIR, "e2e_katana_events.log")
TEMP_SYNC_STATUS_FILE = os.path.join(TEST_E2E_DIR, "e2e_sync_status.json")

# Path to the actual katana_agent.py script
# This assumes the test file is in alg911.catana-ai/
ACTUAL_KATANA_AGENT_SCRIPT_PATH = os.path.join(os.path.dirname(__file__), "katana_agent.py")
# This will be patched into cli_integration.KATANA_AGENT_SCRIPT_PATH

# Suppress non-critical logs for cleaner test output
logging.getLogger('werkzeug').setLevel(logging.WARNING)
logging.getLogger('cli_integration').setLevel(logging.INFO) # Allow INFO for cli_integration
# Katana agent's logger (katana_logger) might be configured internally;
# its file output will go to TEMP_EVENTS_LOG_FILE.

class TestE2EApiCliTelegram(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        if os.path.exists(TEST_E2E_DIR):
            shutil.rmtree(TEST_E2E_DIR)
        os.makedirs(TEST_E2E_DIR, exist_ok=True)

        # Patch file paths in cli_integration module
        cls.cli_integration_commands_patcher = patch('cli_integration.COMMANDS_FILE_PATH', TEMP_COMMANDS_FILE)
        cls.cli_integration_agent_path_patcher = patch('cli_integration.KATANA_AGENT_SCRIPT_PATH', ACTUAL_KATANA_AGENT_SCRIPT_PATH)

        # Patch file paths in katana_agent module
        cls.agent_commands_patcher = patch('katana_agent.COMMANDS_FILE', TEMP_COMMANDS_FILE)
        cls.agent_memory_patcher = patch('katana_agent.MEMORY_FILE', TEMP_MEMORY_FILE)
        cls.agent_history_patcher = patch('katana_agent.HISTORY_FILE', TEMP_HISTORY_FILE)
        cls.agent_events_patcher = patch('katana_agent.EVENTS_LOG_FILE', TEMP_EVENTS_LOG_FILE)
        cls.agent_sync_patcher = patch('katana_agent.SYNC_STATUS_FILE', TEMP_SYNC_STATUS_FILE)

        # Start patchers
        cls.cli_integration_commands_patcher.start()
        cls.cli_integration_agent_path_patcher.start()
        cls.agent_commands_patcher.start()
        cls.agent_memory_patcher.start()
        cls.agent_history_patcher.start()
        cls.agent_events_patcher.start()
        cls.agent_sync_patcher.start()

        # Patch the N8N URL to a test one for requests.post mocking
        cls.n8n_url_patcher = patch('katana_agent.N8N_TELEGRAM_SEND_WEBHOOK_URL', "http://mocked-n8n-telegram-url.com/test")
        cls.mock_n8n_url = cls.n8n_url_patcher.start()


    @classmethod
    def tearDownClass(cls):
        cls.cli_integration_commands_patcher.stop()
        cls.cli_integration_agent_path_patcher.stop()
        cls.agent_commands_patcher.stop()
        cls.agent_memory_patcher.stop()
        cls.agent_history_patcher.stop()
        cls.agent_events_patcher.stop()
        cls.agent_sync_patcher.stop()
        cls.n8n_url_patcher.stop()

        if os.path.exists(TEST_E2E_DIR):
            shutil.rmtree(TEST_E2E_DIR)
            pass


    def setUp(self):
        app.config['TESTING'] = True
        self.client = app.test_client()

        # Clean up (remove) temp files before each test to ensure isolation and clear state
        for path in [TEMP_COMMANDS_FILE, TEMP_MEMORY_FILE, TEMP_HISTORY_FILE, TEMP_EVENTS_LOG_FILE, TEMP_SYNC_STATUS_FILE]:
            if os.path.exists(path):
                os.remove(path)

        # Initialize katana_agent's files (it will use patched paths)
        # This is done implicitly when katana_agent.py runs for the first time.
        # To ensure a clean state, we can pre-create empty files or initialize memory.
        with open(TEMP_COMMANDS_FILE, 'w') as f: json.dump([], f)
        with open(TEMP_MEMORY_FILE, 'w') as f: json.dump({"katana_service_status": "stopped"}, f) # Default state
        with open(TEMP_HISTORY_FILE, 'w') as f: json.dump([], f)
        with open(TEMP_EVENTS_LOG_FILE, 'w') as f: f.write("") # Clear log
        with open(TEMP_SYNC_STATUS_FILE, 'w') as f: json.dump({},f)


    def tearDown(self):
        pass # Cleanup is mostly handled by setUp and tearDownClass

    def _read_json_file(self, path):
        if not os.path.exists(path): return None
        with open(path, 'r') as f: return json.load(f)

    @patch('requests.post') # Mocks requests.post globally, will catch calls from send_telegram_message
    def test_e2e_telegram_status_command(self, mock_requests_post):
        mock_requests_post.return_value = MagicMock(status_code=200, text="Mocked n8n response")

        payload = {
            "action": "process_telegram_message",
            "parameters": {"chat_id": "test_chat_123", "text": "/status", "user_id": "test_user"}
        }
        response = self.client.post('/api/command', json=payload)

        self.assertEqual(response.status_code, 200)
        json_response = json.loads(response.data)
        self.assertEqual(json_response.get("status"), "success")
        self.assertEqual(json_response.get("task_status"), "completed")
        self.assertIn("Status request processed", json_response.get("result", ""))

        mock_requests_post.assert_called_once()
        args, kwargs = mock_requests_post.call_args
        self.assertEqual(args[0], "http://mocked-n8n-telegram-url.com/test")
        self.assertEqual(kwargs['json']['chat_id'], "test_chat_123")
        self.assertIn("Katana Agent is running.", kwargs['json']['text'])
        self.assertIn("Pending tasks:", kwargs['json']['text'])
        self.assertIn("Katana Service Status: stopped", kwargs['json']['text']) # Default initial status

    @patch('requests.post')
    def test_e2e_telegram_echo_command(self, mock_requests_post):
        mock_requests_post.return_value = MagicMock(status_code=200, text="Mocked n8n response")

        payload = {
            "action": "process_telegram_message",
            "parameters": {"chat_id": "test_chat_456", "text": "/echo_tg Hello Katana E2E", "user_id": "test_user"}
        }
        response = self.client.post('/api/command', json=payload)

        self.assertEqual(response.status_code, 200)
        json_response = json.loads(response.data)
        self.assertEqual(json_response.get("status"), "success")
        self.assertEqual(json_response.get("task_status"), "completed")
        self.assertIn("Echo request processed", json_response.get("result", ""))

        mock_requests_post.assert_called_once_with(
            "http://mocked-n8n-telegram-url.com/test",
            json={"chat_id": "test_chat_456", "text": "Hello Katana E2E"},
            timeout=unittest.mock.ANY # from cli_integration.DEFAULT_REQUEST_TIMEOUT
        )

    @patch('requests.post')
    def test_e2e_telegram_start_katana_command(self, mock_requests_post):
        mock_requests_post.return_value = MagicMock(status_code=200, text="Mocked n8n response")

        payload = {
            "action": "process_telegram_message",
            "parameters": {"chat_id": "test_chat_789", "text": "/start_katana", "user_id": "test_user"}
        }
        response = self.client.post('/api/command', json=payload)

        self.assertEqual(response.status_code, 200)
        json_response = json.loads(response.data)
        self.assertEqual(json_response.get("status"), "success")
        self.assertEqual(json_response.get("task_status"), "completed")
        self.assertIn("Processed /start_katana", json_response.get("result", ""))

        mock_requests_post.assert_called_once_with(
            "http://mocked-n8n-telegram-url.com/test",
            json={"chat_id": "test_chat_789", "text": "Katana service started successfully."},
            timeout=unittest.mock.ANY
        )

        memory_data = self._read_json_file(TEMP_MEMORY_FILE)
        self.assertEqual(memory_data.get("katana_service_status"), "running")
        self.assertIsNotNone(memory_data.get("katana_service_last_start_time"))

    @patch('requests.post')
    def test_e2e_telegram_stop_katana_command(self, mock_requests_post):
        mock_requests_post.return_value = MagicMock(status_code=200, text="Mocked n8n response")

        # Ensure service is "running" first by calling start_katana via API
        start_payload = {
            "action": "process_telegram_message",
            "parameters": {"chat_id": "test_chat_setup", "text": "/start_katana", "user_id": "test_user_setup"}
        }
        self.client.post('/api/command', json=start_payload) # API call to start
        mock_requests_post.reset_mock() # Reset mock for the main test assertion

        stop_payload = {
            "action": "process_telegram_message",
            "parameters": {"chat_id": "test_chat_101", "text": "/stop_katana", "user_id": "test_user"}
        }
        response = self.client.post('/api/command', json=stop_payload)

        self.assertEqual(response.status_code, 200)
        json_response = json.loads(response.data)
        self.assertEqual(json_response.get("status"), "success")
        self.assertEqual(json_response.get("task_status"), "completed")
        self.assertIn("Processed /stop_katana", json_response.get("result", ""))

        mock_requests_post.assert_called_once_with(
            "http://mocked-n8n-telegram-url.com/test",
            json={"chat_id": "test_chat_101", "text": "Katana service stopped successfully."},
            timeout=unittest.mock.ANY
        )

        memory_data = self._read_json_file(TEMP_MEMORY_FILE)
        self.assertEqual(memory_data.get("katana_service_status"), "stopped")
        self.assertIsNotNone(memory_data.get("katana_service_last_stop_time"))

    @patch('requests.post')
    def test_e2e_telegram_unknown_command(self, mock_requests_post):
        mock_requests_post.return_value = MagicMock(status_code=200, text="Mocked n8n response")

        payload = {
            "action": "process_telegram_message",
            "parameters": {"chat_id": "err_chat_001", "text": "/unknown_tg_cmd_test", "user_id": "test_user"}
        }
        response = self.client.post('/api/command', json=payload)

        self.assertEqual(response.status_code, 200) # API call is success
        json_response = json.loads(response.data)
        self.assertEqual(json_response.get("status"), "success") # cli_integration reports success
        self.assertEqual(json_response.get("task_status"), "completed") # Task itself "completed" by handling unknown cmd
        self.assertIn("Unknown Telegram command processed", json_response.get("result", ""))

        mock_requests_post.assert_called_once()
        args, kwargs = mock_requests_post.call_args
        self.assertEqual(kwargs['json']['chat_id'], "err_chat_001")
        self.assertIn("Sorry, I didn't understand that command", kwargs['json']['text'])

    @patch('cli_integration.subprocess.run') # Patch subprocess.run used by cli_integration
    def test_e2e_cli_agent_script_error(self, mock_subprocess_run):
        mock_subprocess_run.return_value = MagicMock(
            stdout="",
            stderr="Major Python error in katana_agent.py",
            returncode=1 # Non-zero return code indicates error
        )

        payload = {"action": "any_action", "parameters": {}} # Any valid API call
        response = self.client.post('/api/command', json=payload)

        self.assertEqual(response.status_code, 500) # API should report internal error
        json_response = json.loads(response.data)
        self.assertEqual(json_response.get("status"), "error")
        self.assertIn("Katana agent script execution failed", json_response.get("message", ""))
        self.assertIn("Major Python error in katana_agent.py", json_response.get("stderr", ""))

    @patch('cli_integration.subprocess.run')
    @patch('cli_integration._load_json_file') # To control polling outcome
    @patch('cli_integration.DEFAULT_POLL_TIMEOUT', 0.1) # Shorten timeout for test
    @patch('time.sleep') # Mock time.sleep in cli_integration
    def test_e2e_cli_integration_polling_timeout(self, mock_time_sleep, mock_load_json, mock_subprocess_run):
        # Simulate subprocess.run successfully adding task and returning ID
        mock_subprocess_run.return_value = MagicMock(
            stdout="CREATED_TASK_ID: timeout_task_id_123",
            stderr="",
            returncode=0
        )
        # Simulate task always being pending during polling in _load_json_file
        mock_load_json.return_value = [{"command_id": "timeout_task_id_123", "status": "pending"}]

        payload = {"action": "some_action", "parameters": {}}
        response = self.client.post('/api/command', json=payload)

        self.assertEqual(response.status_code, 500) # API reports internal error due to timeout
        json_response = json.loads(response.data)
        self.assertEqual(json_response.get("status"), "error")
        self.assertIn("Timeout polling for task timeout_task_id_123 completion", json_response.get("message", ""))

        # Ensure _load_json_file was called multiple times during polling
        self.assertTrue(mock_load_json.call_count > 1)


    @patch('cli_integration.subprocess.run')
    @patch('cli_integration._load_json_file')
    @patch('time.sleep') # Mock time.sleep in cli_integration
    def test_e2e_task_execution_failure_reported(self, mock_time_sleep, mock_load_json, mock_subprocess_run):
        # Simulate subprocess.run successfully adding task and returning ID
        mock_subprocess_run.return_value = MagicMock(
            stdout="CREATED_TASK_ID: agent_failed_task_456",
            stderr="",
            returncode=0
        )
        # Simulate task being found as "failed" by the agent during polling
        mock_load_json.side_effect = [
            [{"command_id": "agent_failed_task_456", "status": "pending"}], # First poll
            [{"command_id": "agent_failed_task_456", "status": "failed", "result": "Agent error: Division by zero"}] # Second poll
        ]

        payload = {"action": "action_that_fails_in_agent", "parameters": {}}
        response = self.client.post('/api/command', json=payload)

        self.assertEqual(response.status_code, 200) # API call itself is successful
        json_response = json.loads(response.data)
        self.assertEqual(json_response.get("status"), "success") # cli_integration successfully got a final task status
        self.assertEqual(json_response.get("task_status"), "failed")
        self.assertEqual(json_response.get("result"), "Agent error: Division by zero")
        self.assertEqual(json_response.get("task_id"), "agent_failed_task_456")


if __name__ == '__main__':
    # Ensure the logger for cli_integration is also suppressed or set to WARNING if too noisy
    # logging.getLogger('cli_integration').setLevel(logging.WARNING)
    unittest.main(verbosity=2)
```
