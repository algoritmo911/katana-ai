import unittest
import logging
import os
import shutil
from unittest.mock import patch, mock_open
from logging_config import setup_logging, LOG_DIR, LOG_FILE


class TestLoggingConfig(unittest.TestCase):

    def setUp(self):
        # Ensure the log directory does not exist before each test
        if os.path.exists(LOG_DIR):
            shutil.rmtree(LOG_DIR)

    def tearDown(self):
        # Clean up after each test
        if os.path.exists(LOG_DIR):
            shutil.rmtree(LOG_DIR)

    @patch("os.makedirs")
    @patch("logging.FileHandler")
    @patch("logging.StreamHandler")
    def test_setup_logging_basic_configuration(
        self, mock_stream_handler, mock_file_handler, mock_makedirs
    ):
        mock_makedirs.return_value = None

        mock_file_handler_instance = mock_file_handler.return_value
        mock_file_handler_instance.level = logging.DEBUG
        mock_file_handler_instance.setFormatter.side_effect = lambda f: setattr(
            mock_file_handler_instance, "formatter", f
        )

        mock_stream_handler_instance = mock_stream_handler.return_value
        mock_stream_handler_instance.level = logging.DEBUG
        mock_stream_handler_instance.setFormatter.side_effect = lambda f: setattr(
            mock_stream_handler_instance, "formatter", f
        )

        logger = setup_logging(logging.DEBUG)

        self.assertEqual(logger.name, "katana")
        self.assertEqual(logger.level, logging.DEBUG)
        self.assertEqual(len(logger.handlers), 2)

        mock_file_handler.assert_called_once_with(LOG_FILE)
        mock_stream_handler.assert_called_once()

        if logger.handlers:
            formatter = logger.handlers[0].formatter
            self.assertIsInstance(formatter, logging.Formatter)
            self.assertEqual(
                formatter._fmt, "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
            )

    def test_log_directory_and_file_creation(self):
        # This test now has a clean slate thanks to setUp
        self.assertFalse(os.path.exists(LOG_DIR))

        setup_logging(logging.INFO)

        self.assertTrue(os.path.exists(LOG_DIR))
        self.assertTrue(os.path.exists(LOG_FILE))

    @patch("logging.getLogger")
    def test_setup_logging_clears_existing_handlers(self, mock_get_logger):
        mock_logger = mock_get_logger.return_value
        mock_logger.hasHandlers.return_value = True

        setup_logging()

        mock_logger.handlers.clear.assert_called_once()


if __name__ == "__main__":
    unittest.main()
