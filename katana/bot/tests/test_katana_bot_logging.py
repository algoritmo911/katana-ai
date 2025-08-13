import unittest
import json
from unittest.mock import MagicMock

# We only need the types and functions that our code-under-test uses.
from katana.utils.telemetry_provider import log_event, log_unstructured_message
from opentelemetry._logs import SeverityNumber, Logger
from opentelemetry.sdk._logs import LogRecord

class TestMirrorProtocolTelemetry(unittest.TestCase):
    """
    Tests the telemetry provider against the "Mirror Protocol".
    It does NOT use a real OTel pipeline. Instead, it verifies that
    the data prepared by our code matches the reference contract by
    inspecting a mock logger object.
    """

    def test_log_event_produces_correct_structure(self):
        """
        Verify that log_event generates a LogRecord whose body, when parsed as JSON,
        matches the structure of our reference Observability Contract.
        """
        # 1. ARRANGE
        # Create a mock logger instance that we can inspect directly.
        mock_logger = MagicMock(spec=Logger)
        mock_logger.resource = {} # The function needs the 'resource' attribute.

        test_body = {
            "message": "A test event occurred.",
            "user_id": "user-test-789",
            "duration_ms": 42,
            "success": False,
            "attributes": {
                "login_method": "sso",
                "client_ip": "127.0.0.1"
            }
        }

        # 2. ACT
        log_event(mock_logger, "test.event", test_body, SeverityNumber.WARN)

        # 3. ASSERT
        # Assert that the logger's emit method was called exactly once.
        mock_logger.emit.assert_called_once()

        # Get the LogRecord object that was passed to emit.
        call_args, _ = mock_logger.emit.call_args
        emitted_record = call_args[0]

        self.assertIsInstance(emitted_record, LogRecord)

        # The body of the record is our JSON string.
        emitted_json_body = emitted_record.body
        self.assertIsInstance(emitted_json_body, str)

        # Parse the JSON and verify its structure.
        generated_data = json.loads(emitted_json_body)

        # Check top-level keys
        self.assertIn("event_name", generated_data)
        self.assertEqual(generated_data["event_name"], "test.event")
        self.assertIn("trace_id", generated_data)
        self.assertIn("span_id", generated_data)
        self.assertIn("timestamp", generated_data)
        self.assertIn("severity", generated_data)
        self.assertEqual(generated_data["severity"], "WARN")
        self.assertIn("body", generated_data)

        # Check that the body we passed is correctly nested
        self.assertDictEqual(generated_data['body'], test_body)


    def test_unstructured_log_adapter_produces_correct_structure(self):
        """
        Verify that the legacy adapter also produces a correctly structured log.
        """
        # 1. ARRANGE
        mock_logger = MagicMock(spec=Logger)
        mock_logger.resource = {}

        # 2. ACT
        log_unstructured_message(mock_logger, "A legacy message.", SeverityNumber.DEBUG)

        # 3. ASSERT
        mock_logger.emit.assert_called_once()
        emitted_record = mock_logger.emit.call_args[0][0]
        self.assertIsInstance(emitted_record, LogRecord)

        generated_data = json.loads(emitted_record.body)

        # Check key fields for the adapter
        self.assertEqual(generated_data['event_name'], "legacy.unstructured.message")
        self.assertEqual(generated_data['severity'], "DEBUG")
        self.assertEqual(generated_data['body']['message'], "A legacy message.")
        self.assertTrue(generated_data['body']['attributes']['legacy_log'])

if __name__ == '__main__':
    unittest.main()
