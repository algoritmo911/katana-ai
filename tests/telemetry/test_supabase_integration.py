import unittest
from unittest.mock import patch, MagicMock
import os
import logging

# Modules to test
from src.telemetry.supabase_config import get_supabase_credentials
from src.telemetry.supabase_client import SupabaseTelemetryClient, SupabaseHandler

# Store original environment variables
original_environ = None

def setUpModule():
    global original_environ
    original_environ = os.environ.copy()

def tearDownModule():
    global original_environ
    if original_environ:
        os.environ.clear()
        os.environ.update(original_environ)

class TestSupabaseConfig(unittest.TestCase):

    def setUp(self):
        # Ensure a clean environment for each test
        self.patcher = patch.dict(os.environ, {}, clear=True)
        self.patcher.start()

    def tearDown(self):
        self.patcher.stop()

    def test_get_supabase_credentials_success(self):
        os.environ["SUPABASE_URL"] = "http://test.supabase.co"
        os.environ["SUPABASE_KEY"] = "test_key"
        url, key = get_supabase_credentials()
        self.assertEqual(url, "http://test.supabase.co")
        self.assertEqual(key, "test_key")

    def test_get_supabase_credentials_missing_url(self):
        os.environ["SUPABASE_KEY"] = "test_key"
        with self.assertRaisesRegex(ValueError, "SUPABASE_URL environment variable not set."):
            get_supabase_credentials()

    def test_get_supabase_credentials_missing_key(self):
        os.environ["SUPABASE_URL"] = "http://test.supabase.co"
        with self.assertRaisesRegex(ValueError, "SUPABASE_KEY environment variable not set."):
            get_supabase_credentials()

    def test_get_supabase_credentials_missing_both(self):
        with self.assertRaisesRegex(ValueError, "SUPABASE_URL environment variable not set."):
            get_supabase_credentials()


class TestSupabaseTelemetryClient(unittest.TestCase):

    def setUp(self):
        self.patcher = patch.dict(os.environ, {}, clear=True)
        self.patcher.start()

    def tearDown(self):
        self.patcher.stop()

    @patch('src.telemetry.supabase_client.create_client')
    def test_client_initialization_success(self, mock_create_client):
        os.environ["SUPABASE_URL"] = "http://test.supabase.co"
        os.environ["SUPABASE_KEY"] = "test_key"

        mock_supabase_instance = MagicMock()
        mock_create_client.return_value = mock_supabase_instance

        client = SupabaseTelemetryClient()
        self.assertIsNotNone(client.get_client())
        mock_create_client.assert_called_once_with("http://test.supabase.co", "test_key", unittest.mock.ANY)

    def test_client_initialization_no_creds(self):
        # This should raise ValueError because get_supabase_credentials will fail
        with self.assertRaises(ValueError):
            SupabaseTelemetryClient()

    @patch('src.telemetry.supabase_client.create_client')
    def test_client_initialization_with_direct_creds(self, mock_create_client):
        mock_supabase_instance = MagicMock()
        mock_create_client.return_value = mock_supabase_instance
        client = SupabaseTelemetryClient(url="direct_url", key="direct_key")
        self.assertIsNotNone(client.get_client())
        mock_create_client.assert_called_once_with("direct_url", "direct_key", unittest.mock.ANY)


    @patch('src.telemetry.supabase_client.create_client')
    def test_send_data_success(self, mock_create_client):
        os.environ["SUPABASE_URL"] = "http://test.supabase.co"
        os.environ["SUPABASE_KEY"] = "test_key"

        mock_api_response = MagicMock()
        mock_api_response.data = [{"id": 1, "name": "Test Data"}] # Example successful response
        mock_api_response.error = None

        mock_table_ops = MagicMock()
        mock_table_ops.insert.return_value.execute.return_value = mock_api_response

        mock_supabase_instance = MagicMock()
        mock_supabase_instance.table.return_value = mock_table_ops
        mock_create_client.return_value = mock_supabase_instance

        client = SupabaseTelemetryClient()
        test_data = {"name": "Test Data"}
        success, response = client.send_data("test_table", test_data)

        self.assertTrue(success)
        self.assertEqual(response, mock_api_response.data)
        mock_supabase_instance.table.assert_called_once_with("test_table")
        mock_table_ops.insert.assert_called_once_with(test_data)

    @patch('src.telemetry.supabase_client.create_client')
    def test_send_data_api_error(self, mock_create_client):
        os.environ["SUPABASE_URL"] = "http://test.supabase.co"
        os.environ["SUPABASE_KEY"] = "test_key"

        mock_api_error = MagicMock()
        mock_api_error.message = "Supabase error"

        mock_api_response = MagicMock()
        mock_api_response.data = None
        mock_api_response.error = mock_api_error

        mock_table_ops = MagicMock()
        mock_table_ops.insert.return_value.execute.return_value = mock_api_response

        mock_supabase_instance = MagicMock()
        mock_supabase_instance.table.return_value = mock_table_ops
        mock_create_client.return_value = mock_supabase_instance

        client = SupabaseTelemetryClient()
        success, response = client.send_data("test_table", {"name": "Test Data"})

        self.assertFalse(success)
        self.assertEqual(response, mock_api_error)

    def test_send_data_client_not_initialized(self):
        # Intentionally don't set env vars, so client init fails
        with self.assertRaises(ValueError): # Client init fails
            client = SupabaseTelemetryClient()
            # If client init didn't raise, this would be the test:
            # success, response = client.send_data("test_table", {"name": "Test Data"})
            # self.assertFalse(success)
            # self.assertEqual(response, "Client not initialized")

    @patch('src.telemetry.supabase_client.create_client')
    def test_send_data_exception_in_supabase_call(self, mock_create_client):
        os.environ["SUPABASE_URL"] = "http://test.supabase.co"
        os.environ["SUPABASE_KEY"] = "test_key"

        mock_table_ops = MagicMock()
        mock_table_ops.insert.return_value.execute.side_effect = Exception("Network Error")

        mock_supabase_instance = MagicMock()
        mock_supabase_instance.table.return_value = mock_table_ops
        mock_create_client.return_value = mock_supabase_instance

        client = SupabaseTelemetryClient()
        success, response = client.send_data("test_table", {"name": "Test Data"})
        self.assertFalse(success)
        self.assertEqual(response, "Network Error")


class TestSupabaseHandler(unittest.TestCase):

    def setUp(self):
        self.patcher = patch.dict(os.environ, {}, clear=True)
        self.patcher.start()
        # Mock SupabaseTelemetryClient to avoid actual client creation unless specified
        self.mock_telemetry_client_patcher = patch('src.telemetry.supabase_client.SupabaseTelemetryClient')
        self.MockSupabaseTelemetryClient = self.mock_telemetry_client_patcher.start()

    def tearDown(self):
        self.patcher.stop()
        self.mock_telemetry_client_patcher.stop()

    def test_handler_initialization_with_client_instance(self):
        mock_client_instance = MagicMock(spec=SupabaseTelemetryClient)
        mock_client_instance.get_client.return_value = True # Simulate active client

        handler = SupabaseHandler(supabase_client=mock_client_instance, table_name="custom_logs")
        self.assertEqual(handler.supabase_client, mock_client_instance)
        self.assertEqual(handler.table_name, "custom_logs")
        self.MockSupabaseTelemetryClient.assert_not_called() # Should not create new client

    def test_handler_initialization_creates_client(self):
        # This time, the handler will try to create its own client
        mock_internal_client = MagicMock(spec=SupabaseTelemetryClient)
        mock_internal_client.get_client.return_value = True # Simulate active internal client
        self.MockSupabaseTelemetryClient.return_value = mock_internal_client

        handler = SupabaseHandler(table_name="logs_table")
        self.MockSupabaseTelemetryClient.assert_called_once() # It should attempt to create one
        self.assertEqual(handler.supabase_client, mock_internal_client)
        self.assertEqual(handler.table_name, "logs_table")

    def test_handler_initialization_fails_gracefully(self):
        self.MockSupabaseTelemetryClient.side_effect = ValueError("No creds")

        # Supress warnings/errors from logger during this specific test
        with patch('src.telemetry.supabase_client.logger') as mock_logger:
            handler = SupabaseHandler()
            self.assertIsNone(handler.supabase_client)
            mock_logger.warning.assert_called_with(
                "SupabaseHandler: SupabaseTelemetryClient could not be initialized. Logs will not be sent to Supabase."
            )

    def test_emit_sends_data(self):
        mock_client_instance = MagicMock(spec=SupabaseTelemetryClient)
        mock_client_instance.get_client.return_value = True # Active client
        mock_client_instance.send_data.return_value = (True, {"id": 1}) # Simulate successful send

        handler = SupabaseHandler(supabase_client=mock_client_instance, table_name="test_log_table")

        # Create a LogRecord
        record = logging.LogRecord(
            name='test.logger',
            level=logging.INFO,
            pathname='test_file.py',
            lineno=10,
            msg='Test log message with %s',
            args=('args',),
            exc_info=None,
            func='test_function'
        )
        # Set other attributes that might be accessed if not already on LogRecord by default
        record.module = 'test_module'
        record.filename = os.path.basename(record.pathname)
        record.process = 1234
        record.thread = 5678
        record.threadName = "MainThread"

        handler.emit(record)

        mock_client_instance.send_data.assert_called_once()
        args, kwargs = mock_client_instance.send_data.call_args
        self.assertEqual(args[0], "test_log_table") # Table name
        log_entry = args[1] # The data dict

        self.assertEqual(log_entry['level_name'], 'INFO')
        self.assertEqual(log_entry['logger_name'], 'test.logger')
        self.assertEqual(log_entry['raw_message'], 'Test log message with args') # getMessage()
        self.assertEqual(log_entry['message'], 'Test log message with args') # format(record) by default
        self.assertEqual(log_entry['filename'], 'test_file.py')
        self.assertEqual(log_entry['line_number'], 10)
        self.assertEqual(log_entry['function_name'], 'test_function')

    def test_emit_does_not_send_if_client_unavailable(self):
        mock_client_instance = MagicMock(spec=SupabaseTelemetryClient)
        mock_client_instance.get_client.return_value = None # Client not active

        handler = SupabaseHandler(supabase_client=mock_client_instance)
        record = logging.LogRecord(name='test', level=logging.INFO, pathname='', lineno=0, msg='test', args=(), exc_info=None)

        handler.emit(record)
        mock_client_instance.send_data.assert_not_called()

    def test_emit_handles_send_data_failure(self):
        mock_client_instance = MagicMock(spec=SupabaseTelemetryClient)
        mock_client_instance.get_client.return_value = True
        mock_client_instance.send_data.return_value = (False, "Error sending")

        handler = SupabaseHandler(supabase_client=mock_client_instance)
        # Suppress print/logging from handler during error
        with patch('builtins.print'), patch.object(handler, 'handleError') as mock_handle_error:
            record = logging.LogRecord(name='test', level=logging.ERROR, pathname='', lineno=0, msg='test error', args=(), exc_info=None)
            handler.emit(record)
            mock_client_instance.send_data.assert_called_once()
            # Default handleError does nothing, but we can check it was called if we expect specific error handling
            # For now, just ensuring it doesn't crash and send_data was attempted.
            # mock_handle_error.assert_called_once_with(record) # This would be called if send_data itself raised an exception

    def test_emit_handles_exception_during_send(self):
        mock_client_instance = MagicMock(spec=SupabaseTelemetryClient)
        mock_client_instance.get_client.return_value = True
        mock_client_instance.send_data.side_effect = Exception("Big boom")

        handler = SupabaseHandler(supabase_client=mock_client_instance)
        with patch.object(handler, 'handleError') as mock_handle_error:
            record = logging.LogRecord(name='test', level=logging.CRITICAL, pathname='', lineno=0, msg='critical error', args=(), exc_info=None)
            handler.emit(record)
            mock_client_instance.send_data.assert_called_once()
            mock_handle_error.assert_called_once_with(record)


if __name__ == '__main__':
    unittest.main(verbosity=2)
