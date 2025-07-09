import unittest
from unittest.mock import patch, MagicMock, ANY
import uuid
from datetime import datetime, timezone
import os
import json # Added import

# Assuming katana is in PYTHONPATH or discoverable
from katana.utils.telemetry import trace_command
# SupabaseMemoryClient will be mocked, so we don't need its real implementation here,
# but we need to know its path for mocking.
# from katana.utils.supabase_client import SupabaseMemoryClient
from katana.logger import setup_logging

# Setup logging for tests to see output if necessary
# setup_logging(log_level="DEBUG")

class TestTraceCommandDecorator(unittest.TestCase):

    def _assert_common_trace_fields(self, trace_data, func_name, user_id="N/A", context_id="N/A"):
        self.assertIn("trace_id", trace_data)
        try:
            uuid.UUID(trace_data["trace_id"])
        except ValueError:
            self.fail("trace_id is not a valid UUID")

        self.assertEqual(trace_data["name"], func_name)
        self.assertEqual(trace_data["user_id"], user_id)
        self.assertEqual(trace_data["context_id"], context_id)
        self.assertIn("time_start", trace_data)
        self.assertIn("time_end", trace_data)
        self.assertIn("duration", trace_data)
        self.assertIsInstance(trace_data["duration"], float)
        self.assertTrue(trace_data["duration"] >= 0)
        self.assertIn("args", trace_data)
        self.assertIn("kwargs", trace_data)
        self.assertIn("return_value", trace_data)
        self.assertIn("exception", trace_data)

    # Patch the global supabase_client_instance used by the decorator
    @patch('katana.utils.telemetry.supabase_client_instance')
    def test_decorated_function_success_no_ids(self, mock_supabase_client):
        """Test basic successful execution with no user_id/context_id in kwargs."""
        mock_supabase_client.client = "mock_client_ready" # Simulate configured client
        mock_save_trace = MagicMock(return_value=True)
        mock_supabase_client.save_trace = mock_save_trace

        @trace_command
        def sample_func(a, b):
            return a + b

        result = sample_func(1, 2)
        self.assertEqual(result, 3)

        mock_save_trace.assert_called_once()
        trace_data = mock_save_trace.call_args[0][0]

        self._assert_common_trace_fields(trace_data, "sample_func")
        self.assertEqual(trace_data["args"], [1, 2])
        self.assertEqual(trace_data["kwargs"], {}) # No user_id/context_id passed to sample_func
        self.assertEqual(trace_data["return_value"], 3)
        self.assertIsNone(trace_data["exception"])

    @patch('katana.utils.telemetry.supabase_client_instance')
    def test_decorated_function_success_with_ids(self, mock_supabase_client):
        """Test successful execution with user_id and context_id in kwargs."""
        mock_supabase_client.client = "mock_client_ready"
        mock_save_trace = MagicMock(return_value=True)
        mock_supabase_client.save_trace = mock_save_trace

        @trace_command
        def sample_func_with_ids(a, user_id=None, context_id=None, **other_kwargs):
            # In a real scenario, user_id and context_id might be used by the function
            # or just be there for the decorator.
            return f"{a}, {other_kwargs.get('extra')}"

        result = sample_func_with_ids(10, user_id="test_user_1", context_id="test_ctx_1", extra="info")
        self.assertEqual(result, "10, info")

        mock_save_trace.assert_called_once()
        trace_data = mock_save_trace.call_args[0][0]

        self._assert_common_trace_fields(trace_data, "sample_func_with_ids", user_id="test_user_1", context_id="test_ctx_1")
        self.assertEqual(trace_data["args"], [10]) # Positional args
        # kwargs in trace_data will include user_id, context_id as they were passed to sample_func_with_ids
        self.assertEqual(trace_data["kwargs"], {"user_id": "test_user_1", "context_id": "test_ctx_1", "extra": "info"})
        self.assertEqual(trace_data["return_value"], "10, info")
        self.assertIsNone(trace_data["exception"])

    @patch('katana.utils.telemetry.supabase_client_instance')
    def test_decorated_function_exception(self, mock_supabase_client):
        """Test execution when the decorated function raises an exception."""
        mock_supabase_client.client = "mock_client_ready"
        mock_save_trace = MagicMock(return_value=True)
        mock_supabase_client.save_trace = mock_save_trace

        error_message = "Test exception"
        @trace_command
        def func_raises_error(user_id="err_user", **kwargs): # Added **kwargs
            raise ValueError(error_message)

        with self.assertRaises(ValueError) as cm:
            # Pass context_id, it will be part of kwargs for the decorator and func_raises_error
            func_raises_error(user_id="exception_user", context_id="exception_ctx")

        self.assertEqual(str(cm.exception), error_message)

        mock_save_trace.assert_called_once()
        trace_data = mock_save_trace.call_args[0][0]

        self._assert_common_trace_fields(trace_data, "func_raises_error", user_id="exception_user", context_id="exception_ctx")
        self.assertEqual(trace_data["args"], [])
        self.assertEqual(trace_data["kwargs"], {"user_id": "exception_user", "context_id": "exception_ctx"})
        self.assertIsNone(trace_data["return_value"])
        self.assertEqual(trace_data["exception"], f"ValueError: {error_message}")

    @patch('katana.utils.telemetry.supabase_client_instance')
    @patch('builtins.print') # Mock print for fallback scenario
    @patch('katana.utils.telemetry.logger') # Mock logger within telemetry.py
    def test_supabase_client_not_configured_fallback(self, mock_telemetry_logger, mock_print, mock_supabase_client):
        """Test fallback to print if Supabase client is not configured."""
        mock_supabase_client.client = None # Simulate not configured
        mock_save_trace = MagicMock(return_value=False) # save_trace would not be called if client is None
        mock_supabase_client.save_trace = mock_save_trace


        @trace_command
        def fallback_func(val, user_id="fallback_user", context_id="fallback_ctx", **fkwargs):
            return f"Fallback: {val}"

        # Call with user_id and context_id in kwargs for the decorator to pick them up
        result = fallback_func("data", user_id="fallback_user", context_id="fallback_ctx")
        self.assertEqual(result, "Fallback: data")

        # save_trace on the instance should not have been called because client is None in the decorator's check
        mock_save_trace.assert_not_called()

        # Check that logger.warning was called in the decorator
        mock_telemetry_logger.warning.assert_called_once_with(
            "Supabase client not configured. Printing trace data instead.",
            extra={'user_id': 'fallback_user', 'chat_id': 'fallback_ctx', 'message_id': ANY}
        )
        # Check that print was called with the trace data
        mock_print.assert_called_once()
        args, _ = mock_print.call_args
        printed_trace_data = json.loads(args[0])

        self._assert_common_trace_fields(printed_trace_data, "fallback_func", user_id="fallback_user", context_id="fallback_ctx")
        self.assertEqual(printed_trace_data["return_value"], "Fallback: data")

    @patch('katana.utils.telemetry.supabase_client_instance')
    def test_non_serializable_args_return(self, mock_supabase_client):
        """Test handling of non-JSON-serializable args and return values."""
        mock_supabase_client.client = "mock_client_ready"
        mock_save_trace = MagicMock()
        mock_supabase_client.save_trace = mock_save_trace

        class NonSerializable:
            def __str__(self):
                return "<NonSerializable object>"

        non_serial_arg = NonSerializable()
        non_serial_return = NonSerializable()

        @trace_command
        def func_with_non_serializable(arg1, user_id="test", context_id="test"):
            return non_serial_return

        func_with_non_serializable(non_serial_arg, user_id="user1", context_id="ctx1")

        mock_save_trace.assert_called_once()
        trace_data = mock_save_trace.call_args[0][0]

        self._assert_common_trace_fields(trace_data, "func_with_non_serializable", user_id="user1", context_id="ctx1")
        self.assertEqual(trace_data["args"], [str(non_serial_arg)])
        self.assertEqual(trace_data["return_value"], str(non_serial_return))
        self.assertIsNone(trace_data["exception"])

    # Example of how Telegram Update and Context objects might be handled
    @patch('katana.utils.telemetry.supabase_client_instance')
    def test_telegram_like_objects_serialization(self, mock_supabase_client):
        mock_supabase_client.client = "mock_client_ready"
        mock_save_trace = MagicMock()
        mock_supabase_client.save_trace = mock_save_trace

        # Mocked Telegram Update object
        class MockUpdate:
            def __init__(self, update_id):
                self.update_id = update_id
            # __module__ and __class__.__name__ are used by the decorator
            __module__ = 'telegram.update'
            class Update: pass # Mock inner class name for __class__.__name__
            __class__ = Update

        # Mocked Telegram CallbackContext object
        class MockCallbackContext:
             # __module__ and __class__.__name__ are used by the decorator
            __module__ = 'telegram.ext.callbackcontext'
            class CallbackContext: pass
            __class__ = CallbackContext


        mock_update = MockUpdate(12345)
        mock_context = MockCallbackContext()

        @trace_command
        def telegram_handler(update_obj, context_obj, user_id="tg_user", context_id="tg_chat"):
            return "processed"

        telegram_handler(mock_update, mock_context, user_id="tele_user", context_id="tele_chat")

        mock_save_trace.assert_called_once()
        trace_data = mock_save_trace.call_args[0][0]

        # mock_context is the second positional argument.
        # The decorator's special handling for kwargs['context'] is for when 'context' is a keyword argument.
        # For positional arguments, it will use str() if not JSON serializable and not a Telegram Update object.
        self.assertEqual(trace_data["args"], [f"<Telegram Update object id:{mock_update.update_id}>", str(mock_context)])
        # Check that 'context' is not in kwargs if it wasn't passed as a kwarg to telegram_handler
        self.assertNotIn("context", trace_data["kwargs"])
        self.assertEqual(trace_data["return_value"], "processed")


if __name__ == '__main__':
    unittest.main()
