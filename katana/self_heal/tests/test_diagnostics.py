import unittest
import os
from katana.self_heal import diagnostics

class TestDiagnostics(unittest.TestCase):

    def setUp(self):
        # Create a dummy file for hash calculation
        self.test_file = "test_file.txt"
        with open(self.test_file, "w") as f:
            f.write("This is a test file.")

        # Create a dummy log file
        self.log_file = "test.log"
        with open(self.log_file, "w") as f:
            f.write("INFO: Application started.\n")
            f.write("ERROR: A critical error occurred.\n")
            f.write("TRACEBACK: Fake traceback.\n")
            f.write("ERROR: Another error.\n")
            f.write("ERROR: Another error.\n")
            f.write("ERROR: Another error.\n")
            f.write("ERROR: Another error.\n")
            f.write("ERROR: Another error.\n")
            f.write("ERROR: Another error.\n")


    def tearDown(self):
        os.remove(self.test_file)
        os.remove(self.log_file)

    def test_calculate_hash(self):
        # Hash of "This is a test file."
        expected_hash = "f29bc64a9d3732b4b9035125fdb3285f5b6455778edca72414671e0ca3b2e0de"
        actual_hash = diagnostics.calculate_hash(self.test_file)
        self.assertEqual(actual_hash, expected_hash)

    def test_check_module_integrity(self):
        expected_hash = "f29bc64a9d3732b4b9035125fdb3285f5b6455778edca72414671e0ca3b2e0de"
        success, message = diagnostics.check_module_integrity(self.test_file, expected_hash)
        self.assertTrue(success)

        # Test with wrong hash
        success, message = diagnostics.check_module_integrity(self.test_file, "wrong_hash")
        self.assertFalse(success)

    def test_analyze_logs(self):
        """Test that analyze_logs correctly finds all error-related lines."""
        errors_found, message = diagnostics.analyze_logs(self.log_file)

        # The log file contains 8 lines with "error" or "traceback"
        self.assertEqual(len(errors_found), 8)
        self.assertIn("Found 8 error-related lines", message)

        # Check that one of the expected lines is present
        self.assertIn("ERROR: A critical error occurred.", errors_found)

        # Test with a non-existent file
        errors_found, message = diagnostics.analyze_logs("non_existent_file.log")
        self.assertIsNone(errors_found)
        self.assertIn("Log file not found", message)

if __name__ == "__main__":
    unittest.main()
