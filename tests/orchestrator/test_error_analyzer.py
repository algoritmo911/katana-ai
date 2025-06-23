import unittest
from src.orchestrator.error_analyzer import classify_error, ErrorCriticality

class TestErrorAnalyzer(unittest.TestCase):

    def test_classify_timeout_error(self):
        details = "Operation timed out after 60 seconds"
        classification = classify_error(details)
        self.assertEqual(classification['type'], "TimeoutError")
        self.assertEqual(classification['criticality'], ErrorCriticality.MEDIUM.value)
        self.assertEqual(classification['original_details'], details)
        self.assertIn("exceeded the allocated time", classification['description'])

    def test_classify_api_error_limit(self):
        details = "API error: Rate limit exceeded for endpoint /v1/data."
        classification = classify_error(details)
        self.assertEqual(classification['type'], "APIError")
        self.assertEqual(classification['criticality'], ErrorCriticality.HIGH.value)
        self.assertIn("external API", classification['description'])

    def test_classify_api_error_service_unavailable(self):
        details = "Service unavailable. Please try again later. (503 error)"
        classification = classify_error(details)
        self.assertEqual(classification['type'], "APIError") # "service unavailable" is a keyword
        self.assertEqual(classification['criticality'], ErrorCriticality.HIGH.value)

    def test_classify_connection_error(self):
        details = "Failed to establish a new connection: [Errno 111] Connection refused"
        classification = classify_error(details)
        self.assertEqual(classification['type'], "ConnectionError")
        self.assertEqual(classification['criticality'], ErrorCriticality.HIGH.value)
        self.assertIn("network connection problem", classification['description'])

    def test_classify_type_error(self):
        details = "TypeError: unsupported operand type(s) for +: 'int' and 'str'"
        classification = classify_error(details)
        self.assertEqual(classification['type'], "TypeError")
        self.assertEqual(classification['criticality'], ErrorCriticality.MEDIUM.value)
        self.assertIn("inappropriate type", classification['description'])

    def test_classify_value_error(self):
        details = "ValueError: math domain error"
        classification = classify_error(details)
        self.assertEqual(classification['type'], "ValueError")
        self.assertEqual(classification['criticality'], ErrorCriticality.MEDIUM.value)
        self.assertIn("inappropriate value", classification['description'])

    def test_classify_file_not_found_error(self):
        details = "FileNotFoundError: [Errno 2] No such file or directory: 'important_data.csv'"
        classification = classify_error(details)
        self.assertEqual(classification['type'], "FileNotFoundError")
        self.assertEqual(classification['criticality'], ErrorCriticality.LOW.value)

    def test_classify_permission_error(self):
        details = "PermissionError: [Errno 13] Permission denied: '/etc/config.json'"
        classification = classify_error(details)
        self.assertEqual(classification['type'], "PermissionError")
        self.assertEqual(classification['criticality'], ErrorCriticality.MEDIUM.value)

    def test_classify_authentication_error(self):
        details = "401 Unauthorized: Invalid API token provided."
        classification = classify_error(details)
        self.assertEqual(classification['type'], "AuthenticationError")
        self.assertEqual(classification['criticality'], ErrorCriticality.HIGH.value)

    def test_classify_configuration_error(self):
        details = "Configuration error: 'API_ENDPOINT' not set in environment."
        classification = classify_error(details)
        self.assertEqual(classification['type'], "ConfigurationError")
        self.assertEqual(classification['criticality'], ErrorCriticality.HIGH.value)

    def test_classify_unknown_error(self):
        details = "A very peculiar and specific cosmic ray interference error."
        classification = classify_error(details)
        self.assertEqual(classification['type'], "UnknownError")
        self.assertEqual(classification['criticality'], ErrorCriticality.LOW.value)
        self.assertIn("unrecognized or uncategorized", classification['description'])

    def test_classify_empty_string_error(self):
        details = ""
        classification = classify_error(details)
        self.assertEqual(classification['type'], "UnknownError") # Should default
        self.assertEqual(classification['criticality'], ErrorCriticality.LOW.value)

    def test_classify_non_string_error(self):
        class CustomError:
            def __str__(self):
                return "Custom error object representing a failure."
        details = CustomError()
        classification = classify_error(details)
        # The classify_error function converts non-string to string.
        # It won't match specific keywords unless they are in the string representation.
        self.assertEqual(classification['type'], "UnknownError")
        self.assertEqual(classification['criticality'], ErrorCriticality.LOW.value)
        self.assertEqual(classification['original_details'], str(details))

    def test_case_insensitivity(self):
        details = "typeerror: CANNOT CONCATENATE STR AND INT"
        classification = classify_error(details)
        self.assertEqual(classification['type'], "TypeError")
        self.assertEqual(classification['criticality'], ErrorCriticality.MEDIUM.value)

if __name__ == '__main__':
    unittest.main()
