import unittest
import logging
import os
from unittest.mock import patch, mock_open
from logging_config import setup_logging, LOG_DIR, LOG_FILE


class TestLoggingConfig(unittest.TestCase):

    def setUp(self):
        # Ensure a clean state for LOG_DIR and LOG_FILE if they exist
        if os.path.exists(LOG_FILE):
            os.remove(LOG_FILE)
        if os.path.exists(LOG_DIR) and not os.listdir(LOG_DIR):  # Only remove if empty
            os.rmdir(LOG_DIR)
        elif (
            os.path.exists(LOG_DIR) and os.listdir(LOG_DIR) and os.path.exists(LOG_FILE)
        ):  # If log file was the only thing
            pass  # Handled by LOG_FILE removal

    def tearDown(self):
        # Clean up created log file and directory
        if os.path.exists(LOG_FILE):
            os.remove(LOG_FILE)
        if os.path.exists(LOG_DIR) and not os.listdir(LOG_DIR):
            os.rmdir(LOG_DIR)

    @patch("os.makedirs")
    @patch("logging.FileHandler")
    @patch("logging.StreamHandler")
    def test_setup_logging_basic_configuration(
        self, mock_stream_handler, mock_file_handler, mock_makedirs
    ):
        """Test that setup_logging configures handlers and formatters correctly."""
        # Prevent actual file/dir creation for this specific test part if only testing logger object
        mock_makedirs.return_value = None

        # Configure the mock handler instances to have an integer level attribute
        # This ensures that when logger.info() is called within setup_logging,
        # the comparison record.levelno >= hdlr.level works.
        mock_file_handler_instance = mock_file_handler.return_value
        mock_file_handler_instance.level = logging.DEBUG
        # Make setFormatter actually set the formatter on the mock instance
        mock_file_handler_instance.setFormatter.side_effect = lambda f: setattr(
            mock_file_handler_instance, "formatter", f
        )

        mock_stream_handler_instance = mock_stream_handler.return_value
        mock_stream_handler_instance.level = logging.DEBUG
        # Make setFormatter actually set the formatter on the mock instance
        mock_stream_handler_instance.setFormatter.side_effect = lambda f: setattr(
            mock_stream_handler_instance, "formatter", f
        )

        logger = setup_logging(logging.DEBUG)

        self.assertEqual(logger.name, "katana")
        self.assertEqual(logger.level, logging.DEBUG)
        self.assertEqual(len(logger.handlers), 2)  # File and Stream handler

        # Check if FileHandler was called correctly
        mock_file_handler.assert_called_once_with(LOG_FILE)
        # Check if StreamHandler was called (it's called by default with no args)
        mock_stream_handler.assert_called_once()

        # Check formatter (indirectly, by checking a handler's formatter)
        # This assumes both handlers get the same formatter instance
        if logger.handlers:
            formatter = logger.handlers[0].formatter
            self.assertIsInstance(formatter, logging.Formatter)
            self.assertEqual(
                formatter._fmt, "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
            )

        # Check if os.makedirs was called if LOG_DIR didn't exist
        # For this, we'd need to simulate LOG_DIR not existing.
        # The patch on os.makedirs already handles this by preventing actual creation.
        # We can check if it was called if we assume it doesn't exist.
        # This part is a bit tricky as setup_logging itself checks os.path.exists
        # A more direct test for os.makedirs is below.

    def test_log_directory_and_file_creation(self):
        """Test that log directory and file are created."""
        self.assertFalse(os.path.exists(LOG_DIR))  # Should not exist initially

        setup_logging(logging.INFO)  # This call will create the dir and file

        self.assertTrue(os.path.exists(LOG_DIR))
        self.assertTrue(os.path.exists(LOG_FILE))

    @patch("logging.getLogger")
    def test_setup_logging_clears_existing_handlers(self, mock_get_logger):
        """Test that existing handlers are cleared before adding new ones."""
        mock_logger = mock_get_logger.return_value
        mock_logger.hasHandlers.return_value = True  # Simulate existing handlers

        setup_logging()

        mock_logger.handlers.clear.assert_called_once()


if __name__ == "__main__":
    unittest.main()
