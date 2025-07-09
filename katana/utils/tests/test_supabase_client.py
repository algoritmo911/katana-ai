import unittest
from unittest.mock import patch, MagicMock
import os
import json

# Ensure imports for SupabaseMemoryClient and logger setup are correct
# Assuming katana is in PYTHONPATH or discoverable
from katana.utils.supabase_client import SupabaseMemoryClient
from katana.logger import setup_logging, get_logger

# Setup logging for tests to see output if necessary, but usually keep it minimal
# setup_logging(log_level="DEBUG") # Or "CRITICAL" to suppress most logs during tests

class TestSupabaseMemoryClient(unittest.TestCase):

    def setUp(self):
        # Basic setup for logging to be available if any tested component uses it directly
        # but we'll mostly mock loggers used within the client.
        self.test_logger = get_logger(__name__) # Logger for test output, not for mocking client's logger

    @patch.dict(os.environ, {}, clear=True) # Start with a clean environment
    @patch('katana.utils.supabase_client.logger') # Mock the logger used by SupabaseMemoryClient
    def test_init_no_env_vars(self, mock_logger):
        """Test client initialization when SUPABASE_URL and SUPABASE_KEY are not set."""
        client = SupabaseMemoryClient()
        self.assertIsNone(client.client)
        self.assertIsNone(client.supabase_url)
        self.assertIsNone(client.supabase_key)

        # Check that warnings were logged
        self.assertIn("SUPABASE_URL environment variable not set", mock_logger.warning.call_args_list[0][0][0])
        self.assertIn("SUPABASE_KEY environment variable not set", mock_logger.warning.call_args_list[1][0][0])
        mock_logger.info.assert_any_call("SupabaseMemoryClient is not configured due to missing URL/key.", extra=unittest.mock.ANY)

    @patch.dict(os.environ, {"SUPABASE_URL": "http://test-url.com", "SUPABASE_KEY": "test-key"})
    @patch('katana.utils.supabase_client.logger')
    def test_init_with_env_vars(self, mock_logger):
        """Test client initialization with SUPABASE_URL and SUPABASE_KEY set."""
        client = SupabaseMemoryClient()
        self.assertEqual(client.supabase_url, "http://test-url.com")
        self.assertEqual(client.supabase_key, "test-key")
        # In our current mock, self.client becomes a string "mock_supabase_client_initialized"
        self.assertEqual(client.client, "mock_supabase_client_initialized")
        mock_logger.info.assert_any_call("SupabaseMemoryClient initialized (conceptually). Actual Supabase client setup would be here.", extra=unittest.mock.ANY)

    @patch.dict(os.environ, {}, clear=True) # No env vars, so client.client will be None
    @patch('katana.utils.supabase_client.logger')
    def test_save_trace_no_client(self, mock_logger):
        """Test save_trace when the client is not initialized."""
        client = SupabaseMemoryClient() # client.client will be None
        trace_data = {"trace_id": "123", "message": "test"}
        result = client.save_trace(trace_data)

        self.assertFalse(result)
        # Check if this specific warning was among the calls
        mock_logger.warning.assert_any_call(
            "Supabase client not initialized. Cannot save trace.",
            extra={'user_id': 'system_trace', 'chat_id': 'trace_saving', 'message_id': '123'}
        )
        # Optionally, verify the number of warning calls if it's important
        # self.assertEqual(mock_logger.warning.call_count, 3) # If 2 from init + 1 from save_trace

    @patch.dict(os.environ, {"SUPABASE_URL": "http://test-url.com", "SUPABASE_KEY": "test-key"})
    @patch('katana.utils.supabase_client.logger')
    def test_save_trace_with_client_success(self, mock_logger):
        """Test save_trace when the client is initialized (mocked success)."""
        client = SupabaseMemoryClient() # client.client will be "mock_supabase_client_initialized"
        trace_data = {
            "trace_id": "trace-001",
            "name": "test_command",
            "user_id": "user-test",
            "context_id": "session-test",
            "data": "sample"
        }
        result = client.save_trace(trace_data)

        self.assertTrue(result)
        # Check that the info log contains the trace data (as it's simulated save)
        logged_message = mock_logger.info.call_args[0][0]
        self.assertIn("Simulating save_trace to Supabase table 'command_traces'", logged_message)
        self.assertIn(json.dumps(trace_data), logged_message)

        expected_log_extra = {
            'user_id': 'user-test',
            'chat_id': 'session-test',
            'message_id': 'trace-001'
        }
        mock_logger.info.assert_called_with(unittest.mock.ANY, extra=expected_log_extra)

    @patch.dict(os.environ, {"SUPABASE_URL": "http://test-url.com", "SUPABASE_KEY": "test-key"})
    @patch('katana.utils.supabase_client.logger')
    @patch('json.dumps') # To simulate an error during json.dumps within save_trace
    def test_save_trace_unexpected_error(self, mock_json_dumps, mock_logger):
        """Test save_trace when an unexpected error occurs (e.g., during logging itself)."""
        client = SupabaseMemoryClient()
        mock_json_dumps.side_effect = Exception("JSON dump error")

        trace_data = {"trace_id": "err-trace", "user_id": "err_user", "context_id": "err_ctx"}
        result = client.save_trace(trace_data)

        self.assertFalse(result)
        mock_logger.error.assert_called_once_with(
            "An unexpected error occurred in save_trace: JSON dump error",
            extra={'user_id': 'err_user', 'chat_id': 'err_ctx', 'message_id': 'err-trace'}
        )

if __name__ == '__main__':
    unittest.main()
