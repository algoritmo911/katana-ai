import unittest
from unittest.mock import patch, MagicMock, call
import json
import os
import shutil
import time
import logging
import threading # For managing the background thread if needed

# Assuming mock_backend_api.py is in the same directory or accessible via PYTHONPATH
try:
    from mock_backend_api import app, socketio, tail_log_file_thread, client_log_levels as backend_client_filters
except ImportError:
    import sys
    sys.path.append(os.path.dirname(os.path.abspath(__file__)))
    from mock_backend_api import app, socketio, tail_log_file_thread, client_log_levels as backend_client_filters

# Define a directory for temporary test files
TEST_WS_LOGS_DIR_NAME = "temp_test_websocket_logs_dir"
TEST_WS_LOGS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), TEST_WS_LOGS_DIR_NAME)
TEST_LOG_FILE = os.path.join(TEST_WS_LOGS_DIR, "test_events.log")

# Suppress werkzeug and other noisy loggers for cleaner test output
logging.getLogger('werkzeug').setLevel(logging.WARNING)
logging.getLogger('engineio.server').setLevel(logging.WARNING)
logging.getLogger('socketio.server').setLevel(logging.WARNING)


class TestWebSocketLogStreaming(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        if os.path.exists(TEST_WS_LOGS_DIR):
            shutil.rmtree(TEST_WS_LOGS_DIR)
        os.makedirs(TEST_WS_LOGS_DIR, exist_ok=True)

        # Create an empty test log file initially
        with open(TEST_LOG_FILE, 'w') as f:
            f.write("")

    @classmethod
    def tearDownClass(cls):
        if os.path.exists(TEST_WS_LOGS_DIR):
            shutil.rmtree(TEST_WS_LOGS_DIR)
            pass

    def setUp(self):
        app.config['TESTING'] = True
        self.flask_test_client = app.test_client() # Not strictly needed for SocketIO client if not testing HTTP routes

        # Patch the log file path used by the backend and the polling interval
        self.log_path_patcher = patch('mock_backend_api.KATANA_EVENTS_LOG_PATH', TEST_LOG_FILE)
        self.poll_interval_patcher = patch('mock_backend_api.LOG_POLL_INTERVAL', 0.01) # Fast polling

        self.mock_log_path = self.log_path_patcher.start()
        self.mock_poll_interval = self.poll_interval_patcher.start()

        # Clear the log file before each test
        with open(TEST_LOG_FILE, 'w') as f:
            f.write("")

        # Clear client filters store before each test
        backend_client_filters.clear()

        # Start the background log tailing thread for each test
        # This is tricky because the original script starts it in if __name__ == "__main__"
        # We need to ensure it's running in the test context managed by socketio
        # SocketIO's test_client doesn't automatically run background tasks started with threading.Thread
        # in the main app module. We have to manage it carefully.
        # For `async_mode='threading'`, socketio.start_background_task is a wrapper around threading.Thread

        self.stop_thread_event = threading.Event() # To signal thread to stop

        # Patch the original tail_log_file_thread to check our stop_event
        # This is complex. A simpler way for tests might be to not run the original thread,
        # but to directly call the log parsing and emit logic.
        # However, the requirement is to test *with* the thread running.

        # Let's try starting it via socketio.start_background_task IF it's not already running due to import.
        # The check `if os.environ.get("WERKZEUG_RUN_MAIN")` in mock_backend_api.py
        # is designed to prevent the thread from starting when Flask reloader is active.
        # In a test context, WERKZEUG_RUN_MAIN is usually not set.
        # So the thread in mock_backend_api.py might not start on its own.

        # We will run the original tail_log_file_thread by starting it here.
        # It's a daemon, so it should stop when the main test thread exits.
        # For more control, one might inject a stop condition into it.
        self.log_tail_thread = threading.Thread(target=tail_log_file_thread, daemon=True)
        self.log_tail_thread.start()
        time.sleep(0.05) # Give thread a moment to start and open file

        self.socketio_test_client = socketio.test_client(app, flask_test_client=self.flask_test_client)
        self.assertTrue(self.socketio_test_client.is_connected())


    def tearDown(self):
        if self.socketio_test_client.is_connected():
            self.socketio_test_client.disconnect()

        # Stop patchers
        self.log_path_patcher.stop()
        self.poll_interval_patcher.stop()

        # The daemon thread should exit automatically. If not, manual joining or a stop event is needed.
        # For now, relying on daemon=True.

    def append_to_test_log(self, text_lines: list[str]):
        with open(TEST_LOG_FILE, 'a', encoding='utf-8') as f:
            for line in text_lines:
                f.write(line + '\n')
        # Give the tailing thread a chance to pick up changes
        time.sleep(self.mock_poll_interval * 5) # Wait a bit longer than poll interval

    def _clear_received(self, client=None):
        if client is None:
            client = self.socketio_test_client
        client.get_received() # Clears the list

    def test_connect_receives_initial_logs_default_info(self):
        initial_logs_content = [
            "[2023-01-01T12:00:00Z] [DEBUG] [logger1] [module.func:10] Debug message",
            "[2023-01-01T12:00:01Z] [INFO] [logger1] [module.func:11] Info message",
            "[2023-01-01T12:00:02Z] [WARNING] [logger1] [module.func:12] Warning message",
        ]
        self.append_to_test_log(initial_logs_content)

        # Client connects in setUp
        received = self.socketio_test_client.get_received()

        initial_event_found = False
        for event in received:
            if event['name'] == 'initial_logs':
                initial_event_found = True
                self.assertIsInstance(event['args'][0]['logs'], list)
                # Default level is INFO, so DEBUG lines should be filtered out
                self.assertEqual(len(event['args'][0]['logs']), 2)
                self.assertIn(initial_logs_content[1], event['args'][0]['logs']) # INFO
                self.assertIn(initial_logs_content[2], event['args'][0]['logs']) # WARNING
                self.assertNotIn(initial_logs_content[0], event['args'][0]['logs']) # DEBUG
                break
        self.assertTrue(initial_event_found, "Did not receive 'initial_logs' event on connect.")

    def test_set_filter_level_receives_filtered_initial_logs(self):
        self._clear_received() # Clear connect messages

        initial_logs_content = [
            "[2023-01-01T12:00:00Z] [DEBUG] [logger1] [module.func:10] Debug message for filter test",
            "[2023-01-01T12:00:01Z] [INFO] [logger1] [module.func:11] Info message for filter test",
            "[2023-01-01T12:00:02Z] [ERROR] [logger1] [module.func:12] Error message for filter test",
        ]
        self.append_to_test_log(initial_logs_content)

        # Set filter to ERROR
        self.socketio_test_client.emit('set_filter_level', {'level': 'ERROR'})
        time.sleep(0.1) # Allow server to process and send back
        received = self.socketio_test_client.get_received()

        # Expect 'filter_status' and then 'initial_logs'
        filter_status_event = None
        initial_logs_event = None
        for event in received:
            if event['name'] == 'filter_status':
                filter_status_event = event
            elif event['name'] == 'initial_logs':
                initial_logs_event = event

        self.assertIsNotNone(filter_status_event)
        self.assertEqual(filter_status_event['args'][0]['level'], 'ERROR')

        self.assertIsNotNone(initial_logs_event, "Did not receive 'initial_logs' after setting filter to ERROR.")
        self.assertEqual(len(initial_logs_event['args'][0]['logs']), 1)
        self.assertIn(initial_logs_content[2], initial_logs_event['args'][0]['logs']) # ERROR

        self._clear_received()
        # Set filter to DEBUG
        self.socketio_test_client.emit('set_filter_level', {'level': 'DEBUG'})
        time.sleep(0.1)
        received = self.socketio_test_client.get_received()

        initial_logs_event_debug = None
        for event in received:
            if event['name'] == 'initial_logs': # filter_status also sent, we care about initial_logs
                initial_logs_event_debug = event

        self.assertIsNotNone(initial_logs_event_debug, "Did not receive 'initial_logs' after setting filter to DEBUG.")
        self.assertEqual(len(initial_logs_event_debug['args'][0]['logs']), 3) # DEBUG, INFO, ERROR


    @patch('time.sleep', MagicMock()) # Mock actual sleep to control timing for this specific test more finely
    def test_new_log_lines_broadcast_filtered(self):
        self._clear_received() # From connect

        # Client A (default INFO)
        client_A_sid = self.socketio_test_client.sid

        # Client B connects and sets filter to DEBUG
        client_B = socketio.test_client(app, flask_test_client=self.flask_test_client)
        self.assertTrue(client_B.is_connected())
        self._clear_received(client_B)
        client_B.emit('set_filter_level', {'level': 'DEBUG'})
        time.sleep(0.1) # Process set_filter_level
        self._clear_received(client_B) # Clear initial logs for B

        # Append lines
        log_line_info = "[2023-01-01T12:01:00Z] [INFO] [main] [app.run:50] New INFO line"
        log_line_debug = "[2023-01-01T12:01:01Z] [DEBUG] [main] [app.run:51] New DEBUG line"
        self.append_to_test_log([log_line_info, log_line_debug])

        # Check Client A (INFO level)
        received_A = self.socketio_test_client.get_received()
        new_logs_A_found = False
        for event in received_A:
            if event['name'] == 'new_log_lines':
                self.assertEqual(len(event['args'][0]['logs']), 1)
                self.assertIn(log_line_info, event['args'][0]['logs'])
                new_logs_A_found = True
                break
        self.assertTrue(new_logs_A_found, "Client A (INFO) did not receive the new INFO line.")

        # Check Client B (DEBUG level)
        received_B = client_B.get_received()
        client_B_logs = []
        for event in received_B:
            if event['name'] == 'new_log_lines':
                client_B_logs.extend(event['args'][0]['logs'])

        self.assertIn(log_line_info, client_B_logs, "Client B (DEBUG) did not receive INFO line.")
        self.assertIn(log_line_debug, client_B_logs, "Client B (DEBUG) did not receive DEBUG line.")
        self.assertEqual(len(client_B_logs), 2, "Client B (DEBUG) did not receive both lines.")

        client_B.disconnect()


    def test_disconnect_cleans_up_filter(self):
        client_sid = self.socketio_test_client.sid
        self.assertIn(client_sid, backend_client_filters) # Should be set on connect

        self.socketio_test_client.disconnect()
        time.sleep(0.05) # Allow disconnect handler to run

        # This check might be flaky if disconnect handler is slow or runs in different context
        # For `async_mode='threading'`, it should be relatively quick.
        self.assertNotIn(client_sid, backend_client_filters)


if __name__ == '__main__':
    unittest.main(verbosity=2)

```
