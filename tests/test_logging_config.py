import unittest
import os
import logging
import shutil

from logging_config import setup_logging, LOG_DIR, LOG_FILE


class TestLoggingConfig(unittest.TestCase):
    """
    Unit tests for the logging configuration.
    """

    def setUp(self):
        """
        Clean up the log directory before each test.
        """
        if os.path.exists(LOG_DIR):
            shutil.rmtree(LOG_DIR)

    def tearDown(self):
        """
        Clean up the log directory after each test.
        """
        if os.path.exists(LOG_DIR):
            shutil.rmtree(LOG_DIR, ignore_errors=True)

    def test_setup_logging_creates_directory_and_file(self):
        """
        Test that setup_logging creates the log directory and file.
        """
        self.assertFalse(os.path.exists(LOG_DIR))
        setup_logging()
        self.assertTrue(os.path.exists(LOG_DIR))
        self.assertTrue(os.path.exists(LOG_FILE))

    def test_log_message_is_written_to_file(self):
        """Test that a logged message is written to the file."""
        setup_logging()
        logger = logging.getLogger("katana") # Get the correct logger
        test_message = "A unique test message."
        logger.warning(test_message)

        # Shutdown logging to ensure buffer is flushed to file
        logging.shutdown()
        # Re-initialize for subsequent tests if any, though setUp handles cleaning
        # setup_logging()

        with open(LOG_FILE, 'r') as f:
            log_content = f.read()
        self.assertIn(test_message, log_content)

    def test_setup_logging_uses_correct_default_level(self):
        """Test the default logging level is INFO."""
        setup_logging()
        app_logger = logging.getLogger("katana") # Get the correct logger
        self.assertEqual(app_logger.level, logging.INFO)

    def test_setup_logging_sets_custom_level(self):
        """Test setting a custom logging level."""
        setup_logging(log_level=logging.DEBUG) # Use correct kwarg
        app_logger = logging.getLogger("katana") # Get the correct logger
        self.assertEqual(app_logger.level, logging.DEBUG)

    def test_setup_logging_is_idempotent(self):
        """Test that calling setup_logging multiple times does not add duplicate handlers."""
        logger = logging.getLogger("katana")
        setup_logging()
        initial_handler_count = len(logger.handlers)
        setup_logging()
        final_handler_count = len(logger.handlers)
        self.assertEqual(initial_handler_count, final_handler_count)


if __name__ == "__main__":
    unittest.main()
