import unittest
import json
from unittest.mock import patch, MagicMock
import logging

# Assuming mock_backend_api.py is in the same directory or accessible via PYTHONPATH
try:
    from mock_backend_api import app
except ImportError:
    # Fallback for different execution context
    import sys
    import os
    sys.path.append(os.path.dirname(os.path.abspath(__file__)))
    from mock_backend_api import app

class TestMockBackendAPI(unittest.TestCase):

    def setUp(self):
        """Set up test client and configure app for testing."""
        app.config['TESTING'] = True
        self.client = app.test_client()

        # Suppress non-critical logs during tests for cleaner output
        # Get the logger used by mock_backend_api (which is likely the root logger or one named __main__ if run directly)
        # For simplicity, we can try to get the app's logger if it's configured,
        # or just disable werkzeug's default request logging if too noisy.
        # logging.getLogger('werkzeug').setLevel(logging.WARNING) # Example to quiet werkzeug
        # For this test, we'll assume the default basicConfig in mock_backend_api is sufficient
        # and we are interested in the application's specific logs.

    def tearDown(self):
        """Clean up after each test."""
        pass # Nothing specific to clean up for these tests

    @patch('mock_backend_api.send_command_to_cli')
    def test_api_command_success_task_completed(self, mock_send_command):
        mock_response = {"status": "success", "task_status": "completed", "result": "Task done", "task_id": "t123"}
        mock_send_command.return_value = mock_response

        payload = {"action": "test_action", "parameters": {"p1": "v1"}}
        response = self.client.post('/api/command', data=json.dumps(payload), content_type='application/json')

        self.assertEqual(response.status_code, 200)
        self.assertEqual(json.loads(response.data), mock_response)
        mock_send_command.assert_called_once_with("test_action", {"p1": "v1"})

    @patch('mock_backend_api.send_command_to_cli')
    def test_api_command_success_task_failed(self, mock_send_command):
        mock_response = {"status": "success", "task_status": "failed", "result": "Task execution error", "task_id": "t124"}
        mock_send_command.return_value = mock_response

        payload = {"action": "failed_action", "parameters": {}}
        response = self.client.post('/api/command', data=json.dumps(payload), content_type='application/json')

        self.assertEqual(response.status_code, 200) # API call itself is successful
        self.assertEqual(json.loads(response.data), mock_response)
        mock_send_command.assert_called_once_with("failed_action", {})

    @patch('mock_backend_api.send_command_to_cli')
    def test_api_command_cli_integration_error(self, mock_send_command):
        mock_response = {"status": "error", "message": "CLI subprocess failed"}
        mock_send_command.return_value = mock_response

        payload = {"action": "error_action"} # Parameters optional, defaults to {}
        response = self.client.post('/api/command', data=json.dumps(payload), content_type='application/json')

        self.assertEqual(response.status_code, 500)
        self.assertEqual(json.loads(response.data), mock_response)
        mock_send_command.assert_called_once_with("error_action", {})

    def test_api_command_bad_request_no_json(self):
        response = self.client.post('/api/command', data="this is not json", content_type='text/plain')

        self.assertEqual(response.status_code, 400)
        json_response = json.loads(response.data)
        self.assertEqual(json_response['status'], "error")
        self.assertIn("payload must be JSON", json_response['message'])

    def test_api_command_bad_request_missing_action(self):
        payload = {"parameters": {"p1": "v1"}} # Missing 'action'
        response = self.client.post('/api/command', data=json.dumps(payload), content_type='application/json')

        self.assertEqual(response.status_code, 400)
        json_response = json.loads(response.data)
        self.assertEqual(json_response['status'], "error")
        self.assertIn("'action' field is required", json_response['message'])

    def test_api_command_bad_request_invalid_action_type(self):
        payload = {"action": 123, "parameters": {}} # Action is not a string
        response = self.client.post('/api/command', data=json.dumps(payload), content_type='application/json')

        self.assertEqual(response.status_code, 400)
        json_response = json.loads(response.data)
        self.assertEqual(json_response['status'], "error")
        self.assertIn("'action' field must be a string", json_response['message'])


    def test_api_command_bad_request_invalid_parameters_type(self):
        payload = {"action": "test_action", "parameters": "not_a_dict"}
        response = self.client.post('/api/command', data=json.dumps(payload), content_type='application/json')

        self.assertEqual(response.status_code, 400)
        json_response = json.loads(response.data)
        self.assertEqual(json_response['status'], "error")
        self.assertIn("'parameters' field must be a dictionary", json_response['message'])

    @patch('mock_backend_api.send_command_to_cli')
    def test_api_command_parameters_optional(self, mock_send_command):
        # Test that if 'parameters' is not provided in payload, it defaults to {}
        mock_response = {"status": "success", "task_status": "completed", "result": "Default params task done", "task_id": "t125"}
        mock_send_command.return_value = mock_response

        payload = {"action": "action_with_default_params"} # No 'parameters' field
        response = self.client.post('/api/command', data=json.dumps(payload), content_type='application/json')

        self.assertEqual(response.status_code, 200)
        self.assertEqual(json.loads(response.data), mock_response)
        # Assert that send_command_to_cli was called with an empty dict for parameters
        mock_send_command.assert_called_once_with("action_with_default_params", {})


if __name__ == '__main__':
    unittest.main(verbosity=2)
```
