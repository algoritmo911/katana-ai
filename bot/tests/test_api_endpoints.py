import unittest
import json
import os # For setting environment variables
from datetime import datetime, timezone # For timestamp validation
from pathlib import Path # Add this if not present

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

    def test_post_command_success(self):
        # Ensure the main API command directory exists (it's created by katana_bot.py on import/load)
        # from bot.katana_bot import API_COMMAND_FILE_DIR # Import if not already available
        # self.assertTrue(API_COMMAND_FILE_DIR.exists()) # Optional: check if base dir was created

        valid_command_payload = {
            "type": "test_command",
            "module": "test_module",
            "args": {"param1": "value1", "param2": 123},
            "id": "test-cmd-001"
        }

        response = self.client.post('/api/command',
                                    data=json.dumps(valid_command_payload),
                                    content_type='application/json')

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content_type, 'application/json')

        try:
            data = json.loads(response.data)
        except json.JSONDecodeError:
            self.fail("Response from /api/command (success) is not valid JSON")

        self.assertTrue(data.get('success'), "Response data should indicate success")
        self.assertIn('message', data, "Response data should contain a message")
        self.assertIn('file_path', data, "Response data should contain a file_path")

        # Verify file creation
        file_path_str = data['file_path']
        self.assertIsNotNone(file_path_str, "file_path in response should not be None")

        command_file = Path(file_path_str)
        self.assertTrue(command_file.exists(), f"Command file {command_file} was not created")
        self.assertTrue(command_file.is_file(), f"Command file path {command_file} is not a file")

        # Verify content of the created file (optional but good)
        try:
            with open(command_file, 'r', encoding='utf-8') as f:
                saved_command_data = json.load(f)
            self.assertEqual(saved_command_data, valid_command_payload, "Saved command content does not match payload")
        except Exception as e:
            self.fail(f"Failed to read or parse saved command file {command_file}: {e}")

        # Register cleanup for the created file
        self.addCleanup(os.remove, command_file)
        # If the parent directories (mod_test_module) are created per command and might be empty after,
        # consider self.addCleanup(shutil.rmtree, command_file.parent) but be careful.
        # For now, just removing the file is fine. If mod_test_module might be empty and needs removal:
        # We need to import shutil for rmtree.
        # For simplicity, this example only removes the file.
        # A more robust cleanup might involve removing parent dirs if they become empty.

    def test_post_command_invalid_json_malformed(self):
        malformed_json_string = '{"type": "test", "module": "test_module", "args": {"param1": "value1"}, "id": "test-002"' # Missing closing brace

        response = self.client.post('/api/command',
                                    data=malformed_json_string,
                                    content_type='application/json')

        # The server should identify this as a malformed JSON before our custom validation.
        # Werkzeug (Flask's underlying library) usually returns a 400 Bad Request for malformed JSON.
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.content_type, 'application/json') # Flask's default error handler returns JSON

        try:
            data = json.loads(response.data)
        except json.JSONDecodeError:
            self.fail("Response from /api/command (malformed JSON) is not valid JSON itself")

        # The actual error message for malformed JSON might come from Werkzeug/Flask directly
        # and might not perfectly match our {"success": False, "error": "..."} structure,
        # or our endpoint might not even be reached if Flask handles it earlier.
        # Let's check if there's an "error" key or if the response indicates a bad request.
        # A more specific check depends on how Flask/Werkzeug structures its default error for malformed JSON.
        # For now, checking for a non-empty error or message related to bad JSON is sufficient.

        # If Flask's default 400 error for malformed JSON is HTML, then the content_type check would fail.
        # However, Flask usually tries to return JSON for API-like requests if it can.
        # Let's assume it returns JSON. We expect our custom handler for `request.is_json` might not be hit
        # if the JSON is fundamentally unparseable by Werkzeug.

        # Given our current endpoint logic, `request.get_json()` would fail and Werkzeug/Flask
        # would likely return a generic 400 error. The custom validation for specific fields
        # in `/api/command` won't be reached.
        # The default Flask error for malformed JSON often looks like:
        # { "name": "Bad Request", "description": "Failed to decode JSON object: ..." }
        # So, we'll check for 'description' or 'name' or a general non-success structure if success field is absent.

        if 'success' in data: # If our custom error handler was somehow reached despite malformed JSON
             self.assertFalse(data.get('success'))
             self.assertIn('error', data)
        else: # More likely, Flask's default handler for unparseable JSON
            self.assertTrue(any(key in data for key in ['error', 'description', 'name']),
                            "Response should contain an error, description, or name key for malformed JSON")
            if 'name' in data:
                self.assertIn("Bad Request", data['name'], "Error name should indicate Bad Request")

    def test_post_command_invalid_content_type(self):
        # Send data with a Content-Type other than application/json
        # Even if the data *is* a valid JSON string, the Content-Type header is what matters here.
        payload_string = '{"type": "test", "module": "test_module", "id": "test-003"}'

        response = self.client.post('/api/command',
                                    data=payload_string,
                                    content_type='text/plain') # Incorrect Content-Type

        # The endpoint explicitly checks `request.is_json` and should return 415
        self.assertEqual(response.status_code, 415) # Unsupported Media Type
        self.assertEqual(response.content_type, 'application/json') # Our custom error is JSON

        try:
            data = json.loads(response.data)
        except json.JSONDecodeError:
            self.fail("Response from /api/command (invalid content type) is not valid JSON")

        self.assertFalse(data.get('success'))
        self.assertIn('error', data)
        self.assertIn("Content-Type must be application/json", data['error'],
                      "Error message should indicate incorrect Content-Type")

    def test_post_command_missing_field(self):
        # Payload is valid JSON, but missing the 'module' field
        payload_missing_module = {
            "type": "test_command",
            # "module": "test_module", # 'module' is missing
            "args": {"param1": "value1"},
            "id": "test-cmd-004"
        }

        response = self.client.post('/api/command',
                                    data=json.dumps(payload_missing_module),
                                    content_type='application/json')

        self.assertEqual(response.status_code, 400) # Bad Request due to custom validation
        self.assertEqual(response.content_type, 'application/json')

        try:
            data = json.loads(response.data)
        except json.JSONDecodeError:
            self.fail("Response from /api/command (missing field) is not valid JSON")

        self.assertFalse(data.get('success'))
        self.assertIn('error', data)
        self.assertIn("Missing required field(s): module", data['error'],
                      "Error message should specify the missing field 'module'")

        # Test with another missing field, e.g., 'id'
        payload_missing_id = {
            "type": "another_command",
            "module": "another_module",
            "args": {}
            # "id": "test-cmd-005" # 'id' is missing
        }
        response_missing_id = self.client.post('/api/command',
                                               data=json.dumps(payload_missing_id),
                                               content_type='application/json')

        self.assertEqual(response_missing_id.status_code, 400)
        data_missing_id = json.loads(response_missing_id.data)
        self.assertFalse(data_missing_id.get('success'))
        self.assertIn("Missing required field(s): id", data_missing_id['error'],
                      "Error message should specify the missing field 'id'")

    def test_post_command_incorrect_field_type(self):
        # Payload has all fields, but 'id' is a boolean instead of str/int
        payload_incorrect_type_id = {
            "type": "test_command",
            "module": "test_module",
            "args": {"param1": "value1"},
            "id": True # Incorrect type for 'id'
        }

        response_id = self.client.post('/api/command',
                                       data=json.dumps(payload_incorrect_type_id),
                                       content_type='application/json')

        self.assertEqual(response_id.status_code, 400) # Bad Request due to custom validation
        self.assertEqual(response_id.content_type, 'application/json')

        try:
            data_id = json.loads(response_id.data)
        except json.JSONDecodeError:
            self.fail("Response from /api/command (incorrect field type for id) is not valid JSON")

        self.assertFalse(data_id.get('success'))
        self.assertIn('error', data_id)
        self.assertIn("Field 'id' must be type str or int. Got bool.", data_id['error'],
                      "Error message should specify incorrect type for 'id'")

        # Test with another field, e.g., 'args' as a string instead of dict
        payload_incorrect_type_args = {
            "type": "another_command",
            "module": "another_module",
            "args": "not a dictionary", # Incorrect type for 'args'
            "id": "test-cmd-006"
        }
        response_args = self.client.post('/api/command',
                                         data=json.dumps(payload_incorrect_type_args),
                                         content_type='application/json')

        self.assertEqual(response_args.status_code, 400)
        data_args = json.loads(response_args.data)
        self.assertFalse(data_args.get('success'))
        self.assertIn('error', data_args)
        self.assertIn("Field 'args' must be type dict. Got str.", data_args['error'],
                      "Error message should specify incorrect type for 'args'")

    def test_get_logs_filter_by_level(self):
        # Add logs with various levels
        log_local_bot_event("Info message 1", level="INFO", module="system")
        log_local_bot_event("Error message 1", level="ERROR", module="system")
        log_local_bot_event("Info message 2", level="INFO", module="network")
        log_local_bot_event("Warn message 1", level="WARN", module="system")
        log_local_bot_event("Error message 2", level="ERROR", module="network")

        # Test filtering for ERROR level
        response_error = self.client.get('/api/logs?level=ERROR')
        self.assertEqual(response_error.status_code, 200)
        data_error = json.loads(response_error.data)

        self.assertEqual(len(data_error), 2, "Should return 2 ERROR logs")
        for log_entry in data_error:
            self.assertEqual(log_entry['level'], 'ERROR')

        # Test filtering for INFO level
        response_info = self.client.get('/api/logs?level=INFO')
        self.assertEqual(response_info.status_code, 200)
        data_info = json.loads(response_info.data)

        self.assertEqual(len(data_info), 2, "Should return 2 INFO logs")
        for log_entry in data_info:
            self.assertEqual(log_entry['level'], 'INFO')

        # Test filtering for a level with no logs (e.g., DEBUG, assuming none were added)
        response_debug = self.client.get('/api/logs?level=DEBUG')
        self.assertEqual(response_debug.status_code, 200)
        data_debug = json.loads(response_debug.data)
        self.assertEqual(len(data_debug), 0, "Should return 0 DEBUG logs if none were added with that level")

        # Test filtering with lowercase level query parameter (should still work if API handles it, API does level.upper())
        response_warn_lower = self.client.get('/api/logs?level=warn') # API converts query param to UPPER
        self.assertEqual(response_warn_lower.status_code, 200)
        data_warn_lower = json.loads(response_warn_lower.data)
        self.assertEqual(len(data_warn_lower), 1, "Should return 1 WARN log even with lowercase query")
        if len(data_warn_lower) == 1:
            self.assertEqual(data_warn_lower[0]['level'], 'WARN')

    def test_get_logs_filter_by_module(self):
        # Add logs with various modules, including different cases
        log_local_bot_event("Message from System module", level="INFO", module="System")
        log_local_bot_event("Message from network module", level="WARN", module="network")
        log_local_bot_event("Another System message", level="DEBUG", module="system") # Lowercase 'system'
        log_local_bot_event("Message from API module", level="INFO", module="API_Command")

        # Test filtering for 'system' module (case-insensitive)
        # The API endpoint implements case-insensitive matching for module: log['module'].lower() == filter_module.lower()
        response_system_lower = self.client.get('/api/logs?module=system')
        self.assertEqual(response_system_lower.status_code, 200)
        data_system_lower = json.loads(response_system_lower.data)

        self.assertEqual(len(data_system_lower), 2, "Should return 2 logs for 'system' module (case-insensitive)")
        for log_entry in data_system_lower:
            self.assertEqual(log_entry['module'].lower(), 'system')

        # Test filtering for 'System' module (uppercase query)
        response_system_upper = self.client.get('/api/logs?module=System')
        self.assertEqual(response_system_upper.status_code, 200)
        data_system_upper = json.loads(response_system_upper.data)
        self.assertEqual(len(data_system_upper), 2, "Should return 2 logs for 'System' module (case-insensitive)")
        for log_entry in data_system_upper:
            self.assertEqual(log_entry['module'].lower(), 'system') # Check against normalized form

        # Test filtering for 'network' module
        response_network = self.client.get('/api/logs?module=network')
        self.assertEqual(response_network.status_code, 200)
        data_network = json.loads(response_network.data)
        self.assertEqual(len(data_network), 1, "Should return 1 log for 'network' module")
        if len(data_network) == 1:
            self.assertEqual(data_network[0]['module'].lower(), 'network')

        # Test filtering for a module with no logs
        response_other = self.client.get('/api/logs?module=unknown_module')
        self.assertEqual(response_other.status_code, 200)
        data_other = json.loads(response_other.data)
        self.assertEqual(len(data_other), 0, "Should return 0 logs for 'unknown_module'")

    def test_get_logs_combined_filters(self):
        # Add diverse logs
        log_local_bot_event("System Info 1", level="INFO", module="System")
        log_local_bot_event("System Error 1", level="ERROR", module="System")
        log_local_bot_event("Network Info 1", level="INFO", module="Network")
        log_local_bot_event("System Info 2", level="INFO", module="system") # Lowercase module
        log_local_bot_event("Network Warn 1", level="WARN", module="network")

        # Test filtering for INFO logs in 'system' module (case-insensitive for module)
        response = self.client.get('/api/logs?level=INFO&module=system')
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)

        self.assertEqual(len(data), 2, "Should return 2 INFO logs from 'system' module")
        for log_entry in data:
            self.assertEqual(log_entry['level'], 'INFO')
            self.assertEqual(log_entry['module'].lower(), 'system')

        # Test filtering for ERROR logs in 'System' module (uppercase module query)
        response_err = self.client.get('/api/logs?level=ERROR&module=System')
        self.assertEqual(response_err.status_code, 200)
        data_err = json.loads(response_err.data)
        self.assertEqual(len(data_err), 1, "Should return 1 ERROR log from 'System' module")
        if len(data_err) == 1:
            self.assertEqual(data_err[0]['level'], 'ERROR')
            self.assertEqual(data_err[0]['module'].lower(), 'system')
            self.assertEqual(data_err[0]['message'], 'System Error 1')

        # Test filtering for a combination that should yield no results
        response_none = self.client.get('/api/logs?level=DEBUG&module=network')
        self.assertEqual(response_none.status_code, 200)
        data_none = json.loads(response_none.data)
        self.assertEqual(len(data_none), 0, "Should return 0 logs for DEBUG level in 'network' module")

    # Test methods will be added here in subsequent steps

if __name__ == '__main__':
    unittest.main()
