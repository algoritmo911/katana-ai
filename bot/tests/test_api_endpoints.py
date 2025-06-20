import unittest
import json
import os # For setting environment variables
from datetime import datetime, timezone # For timestamp validation

# Attempt to import from the bot package.
# This assumes katana_bot.py is structured to allow importing flask_app, etc.
# If katana_bot.py executes significant logic upon import (like starting the bot),
# it might need restructuring, or tests might need to mock parts of it.
# For now, assume direct import works.
from bot.katana_bot import flask_app, bot_logs, log_lock, log_local_bot_event

class TestAPIEndpoints(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        # This method is called once before any tests in the class run
        # Set the dummy token before flask_app is further configured or used by test_client
        os.environ['KATANA_TELEGRAM_TOKEN'] = '123:dummy_token_for_testing'

        # Ensure Flask app is in testing mode
        flask_app.testing = True


    def setUp(self):
        # This method is called before each test method
        self.client = flask_app.test_client()

        # Clear logs before each test to ensure test isolation
        with log_lock:
            bot_logs.clear()

    def tearDown(self):
        # This method is called after each test method
        # Can be used for cleanup if needed, e.g. clearing environment variables
        pass

    def test_get_status_success(self):
        # Make a GET request to /api/status
        response = self.client.get('/api/status')

        # Assert that the HTTP status code is 200 OK
        self.assertEqual(response.status_code, 200)

        # Assert that the response content type is application/json
        self.assertEqual(response.content_type, 'application/json')

        # Parse the JSON response
        try:
            data = json.loads(response.data)
        except json.JSONDecodeError:
            self.fail("Response is not valid JSON")

        # Assert that the JSON response contains the expected keys
        expected_keys = ['status', 'uptime', 'ping', 'bot_status', 'timestamp']
        for key in expected_keys:
            self.assertIn(key, data, f"Key '{key}' missing from /api/status response")

        # Assert specific values
        self.assertEqual(data['status'], 'Online')
        self.assertIsInstance(data['uptime'], str) # Check if uptime is a string
        self.assertTrue(len(data['uptime']) > 0) # Check if uptime string is not empty
        self.assertIsInstance(data['timestamp'], str) # Check if timestamp is a string
        # A more robust timestamp check could parse it and verify it's a recent ISO date
        try:
            # datetime.fromisoformat is available in Python 3.7+
            # For Python <3.11, 'Z' (Zulu time) needs to be replaced with +00:00 for fromisoformat
            datetime.fromisoformat(data['timestamp'].replace('Z', '+00:00'))
        except ValueError:
            self.fail("Timestamp is not a valid ISO 8601 string")

    def test_get_logs_empty(self):
        # Ensure logs are empty (setUp already does this, but good for clarity)
        with log_lock: # Accessing bot_logs directly, so use lock
            self.assertEqual(len(bot_logs), 0, "bot_logs should be empty at the start of this test")

        # Make a GET request to /api/logs
        response = self.client.get('/api/logs')

        # Assert that the HTTP status code is 200 OK
        self.assertEqual(response.status_code, 200)

        # Assert that the response content type is application/json
        self.assertEqual(response.content_type, 'application/json')

        # Parse the JSON response
        try:
            data = json.loads(response.data)
        except json.JSONDecodeError:
            self.fail("Response is not valid JSON for /api/logs (empty)")

        # Assert that the response is an empty list
        self.assertEqual(data, [], "Expected an empty list for /api/logs when no logs are present")

    def test_get_logs_with_data(self):
        # Add some sample logs using the imported log_local_bot_event function
        sample_logs_data = [
            {"message": "Test log 1: INFO message", "level": "INFO", "module": "test_module_A"},
            {"message": "Test log 2: ERROR message", "level": "ERROR", "module": "test_module_B"},
            {"message": "Test log 3: DEBUG message", "level": "DEBUG", "module": "test_module_A"},
        ]

        for log_data in sample_logs_data:
            log_local_bot_event(log_data["message"], level=log_data["level"], module=log_data["module"])

        # Verify that logs were added (optional sanity check)
        with log_lock: # Accessing bot_logs directly
             self.assertEqual(len(bot_logs), len(sample_logs_data), "Logs were not added correctly by log_local_bot_event")

        # Make a GET request to /api/logs
        response = self.client.get('/api/logs')

        # Assert that the HTTP status code is 200 OK
        self.assertEqual(response.status_code, 200)

        # Assert that the response content type is application/json
        self.assertEqual(response.content_type, 'application/json')

        # Parse the JSON response
        try:
            returned_logs = json.loads(response.data)
        except json.JSONDecodeError:
            self.fail("Response is not valid JSON for /api/logs (with data)")

        # Assert that the correct number of logs is returned
        self.assertEqual(len(returned_logs), len(sample_logs_data))

        # Assert that each returned log has the expected keys and content (check the first and last for brevity)
        expected_keys = ['timestamp', 'level', 'module', 'message']
        for i in [0, len(sample_logs_data) - 1]: # Check first and last log
            for key in expected_keys:
                self.assertIn(key, returned_logs[i], f"Key '{key}' missing from log entry {i}")

            self.assertEqual(returned_logs[i]['message'], sample_logs_data[i]['message'])
            self.assertEqual(returned_logs[i]['level'], sample_logs_data[i]['level'].upper()) # log_local_bot_event stores level as UPPERCASE
            self.assertEqual(returned_logs[i]['module'], sample_logs_data[i]['module'])
            self.assertIsInstance(returned_logs[i]['timestamp'], str) # Check timestamp is a string

    # Test methods will be added here in subsequent steps

if __name__ == '__main__':
    unittest.main()
