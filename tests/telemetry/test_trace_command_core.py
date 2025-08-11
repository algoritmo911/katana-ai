import os
import unittest
from unittest.mock import patch, MagicMock, ANY
import time
import logging

# Adjust imports based on your project structure
from katana.telemetry.trace_command import trace_command, get_supabase_memory_client
from katana.memory.core import MemoryCore

# Suppress logging during tests unless specifically needed
logging.disable(logging.CRITICAL)

class TestTraceCommandSupabaseIntegration(unittest.TestCase):

    def setUp(self):
        # Reset the global client instance before each test to ensure isolation
        # This is important because get_supabase_memory_client uses a global singleton
        patcher = patch('katana.telemetry.trace_command.supabase_memory_client_instance', None)
        self.addCleanup(patcher.stop)
        patcher.start()

    @patch.object(MemoryCore, 'add_dialogue')
    @patch.dict(os.environ, {"SUPABASE_URL": "http://test.supabase.co", "SUPABASE_KEY": "test_key"})
    def test_trace_command_success_with_supabase(self, mock_add_dialogue):
        # Ensure MemoryCore is mocked for get_supabase_memory_client()
        # The get_supabase_memory_client will instantiate a MemoryCore,
        # which will have its add_dialogue method mocked by the decorator.

        @trace_command(use_supabase=True, tags=["test_success"], user_id_arg_name="user")
        def sample_command_success(user: str, data: str):
            time.sleep(0.01) # Simulate work
            return {"status": "ok", "processed_data": data.upper()}

        result = sample_command_success(user="user_alpha", data="input_data")

        self.assertEqual(result, {"status": "ok", "processed_data": "INPUT_DATA"})
        mock_add_dialogue.assert_called_once()
        call_args = mock_add_dialogue.call_args[1]

        self.assertEqual(call_args['user_id'], "user_alpha")
        self.assertEqual(call_args['command_name'], "sample_command_success")
        self.assertIn("'user': 'user_alpha'", str(call_args['input_data'])) # Check if user_id is in input_data
        self.assertIn("'data': 'input_data'", str(call_args['input_data']))
        self.assertEqual(call_args['output_data'], {"status": "ok", "processed_data": "INPUT_DATA"})
        self.assertAlmostEqual(call_args['duration'], 0.01, delta=0.005)
        self.assertEqual(call_args['success'], True)
        self.assertEqual(call_args['tags'], ["test_success"])

    @patch.object(MemoryCore, 'add_dialogue')
    @patch.dict(os.environ, {"SUPABASE_URL": "http://test.supabase.co", "SUPABASE_KEY": "test_key"})
    def test_trace_command_failure_with_supabase(self, mock_add_dialogue):

        @trace_command(use_supabase=True, tags=["test_failure"])
        def sample_command_failure(user_id: str):
            time.sleep(0.01) # Simulate work
            raise ValueError("Simulated error")

        with self.assertRaises(ValueError):
            sample_command_failure(user_id="user_beta")

        mock_add_dialogue.assert_called_once()
        call_args = mock_add_dialogue.call_args[1]

        self.assertEqual(call_args['user_id'], "user_beta")
        self.assertEqual(call_args['command_name'], "sample_command_failure")
        self.assertIn("'user_id': 'user_beta'", str(call_args['input_data']))
        self.assertEqual(call_args['output_data'], {"error": "Simulated error"})
        self.assertAlmostEqual(call_args['duration'], 0.01, delta=0.005)
        self.assertEqual(call_args['success'], False)
        self.assertEqual(call_args['tags'], ["test_failure"])

    @patch.object(MemoryCore, 'add_dialogue')
    @patch.dict(os.environ, {"SUPABASE_URL": "http://test.supabase.co", "SUPABASE_KEY": "test_key"})
    def test_trace_command_supabase_disabled(self, mock_add_dialogue):

        @trace_command(use_supabase=False) # Supabase explicitly disabled
        def sample_command_no_supabase(data: str):
            return f"processed: {data}"

        sample_command_no_supabase(data="my_data")
        mock_add_dialogue.assert_not_called()

    @patch.object(MemoryCore, 'add_dialogue')
    @patch.dict(os.environ, {"SUPABASE_URL": "http://test.supabase.co", "SUPABASE_KEY": "test_key"})
    def test_trace_command_user_id_from_args(self, mock_add_dialogue):

        @trace_command(use_supabase=True, user_id_arg_name="uid")
        def command_user_in_args(pos_arg1, uid, pos_arg2): # uid is a positional arg
            return "done"

        command_user_in_args("val1", "user_gamma", "val2")

        mock_add_dialogue.assert_called_once()
        call_args = mock_add_dialogue.call_args[1]
        self.assertEqual(call_args['user_id'], "user_gamma")
        self.assertIn("'args': ('val1', 'user_gamma', 'val2')", str(call_args['input_data']))

    @patch.object(MemoryCore, 'add_dialogue')
    @patch.dict(os.environ, {"SUPABASE_URL": "http://test.supabase.co", "SUPABASE_KEY": "test_key"})
    def test_trace_command_unknown_user(self, mock_add_dialogue):

        @trace_command(use_supabase=True) # Default user_id_arg_name is "user_id"
        def command_no_user_arg(some_data: str):
            return f"data: {some_data}"

        command_no_user_arg(some_data="test_val")

        mock_add_dialogue.assert_called_once()
        call_args = mock_add_dialogue.call_args[1]
        self.assertEqual(call_args['user_id'], "unknown_user")
        self.assertIn("'some_data': 'test_val'", str(call_args['input_data']))

    @patch('katana.memory.core.create_client') # Mock create_client at source
    @patch.dict(os.environ, {"SUPABASE_URL": "", "SUPABASE_KEY": ""}) # No URL/KEY
    def test_trace_command_supabase_client_not_initialized(self, mock_create_client):
        # This test is a bit tricky because MemoryCore logs a warning.
        # We want to ensure add_dialogue is NOT called if the client isn't functional.

        # Prevent MemoryCore from being created with a real client
        mock_supabase_sdk = MagicMock()
        mock_create_client.return_value = mock_supabase_sdk

        # Make the client inside MemoryCore None, as if init failed
        with patch('katana.telemetry.trace_command.MemoryCore') as mock_smc:
            instance = mock_smc.return_value
            instance.client = None # Simulate failed initialization
            instance.add_dialogue = MagicMock() # Add a mock add_dialogue to this instance

            # Need to reset the global singleton to use this mocked instance
            with patch('katana.telemetry.trace_command.supabase_memory_client_instance', instance):
                @trace_command(use_supabase=True)
                def sample_command_bad_init(data: str):
                    return f"processed: {data}"

                sample_command_bad_init(data="my_data")
                instance.add_dialogue.assert_not_called() # The key assertion

if __name__ == '__main__':
    unittest.main(argv=['first-arg-is-ignored'], exit=False)
