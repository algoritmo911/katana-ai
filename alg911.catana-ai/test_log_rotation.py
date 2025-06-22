import unittest
import logging
from logging.handlers import RotatingFileHandler
import os
import shutil
import time # For unique logger names if needed, or just use test id

# Define a directory for all temporary E2E test files
TEST_LOG_ROTATION_DIR_NAME = "temp_log_rotation_tests_dir"
TEST_LOG_ROTATION_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), TEST_LOG_ROTATION_DIR_NAME)

class TestLogRotation(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        if os.path.exists(TEST_LOG_ROTATION_DIR):
            shutil.rmtree(TEST_LOG_ROTATION_DIR)
        os.makedirs(TEST_LOG_ROTATION_DIR, exist_ok=True)

    @classmethod
    def tearDownClass(cls):
        if os.path.exists(TEST_LOG_ROTATION_DIR):
            shutil.rmtree(TEST_LOG_ROTATION_DIR)
            pass # Keep the directory for inspection if a test fails by commenting this out

    def setUp(self):
        # Ensure a clean state for each test method by using unique log file names
        # or by cleaning up specific files if names are reused.
        # For this suite, each test method will use its own uniquely named log file.
        pass

    def tearDown(self):
        # General cleanup of logging handlers after each test to avoid interference
        # and ensure file handles are released.
        # This is important if loggers are not uniquely named or if files are reused.
        # However, with unique file names per test, explicit handler removal from specific loggers
        # within each test (as done in _perform_rotation_test) is more targeted.
        logging.shutdown() # Shuts down all logging, good for test end

    def _get_unique_log_path(self, base_name):
        # Creates a unique log file path for each test run to ensure isolation
        # Using test ID for uniqueness. self.id() gives something like 'test_log_rotation.TestLogRotation.test_method_name'
        test_id_suffix = self.id().split('.')[-1] # Get the test method name
        return os.path.join(TEST_LOG_ROTATION_DIR, f"{base_name}_{test_id_suffix}.log")

    def setup_test_rotating_logger(self, log_file_path, max_bytes, backup_count, logger_name_suffix):
        logger_name = f"test_logger.{logger_name_suffix}.{self.id()}" # Ensure unique logger name
        logger = logging.getLogger(logger_name)
        logger.setLevel(logging.DEBUG)

        # Remove any existing handlers from previous runs if names were somehow reused (defensive)
        for handler in list(logger.handlers):
            logger.removeHandler(handler)
            handler.close()

        handler = RotatingFileHandler(
            log_file_path,
            maxBytes=max_bytes,
            backupCount=backup_count,
            encoding='utf-8'
        )
        formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
        handler.setFormatter(formatter)
        logger.addHandler(handler)
        return logger, handler # Return handler for explicit closing

    def _perform_rotation_test(self, log_file_base_name, max_bytes, backup_count, log_message_size, num_messages_to_log):
        temp_log_file = self._get_unique_log_path(log_file_base_name)

        logger, handler = self.setup_test_rotating_logger(
            temp_log_file,
            max_bytes,
            backup_count,
            log_file_base_name # Suffix for logger name
        )

        log_message = 'A' * log_message_size # Approx log_message_size bytes + formatter overhead

        try:
            for i in range(num_messages_to_log):
                logger.info(f"Message {i+1}: {log_message}")

            # Allow time for file operations if async or buffered
            handler.flush()
            # handler.close() # Closing forces flush and release, good before checking files

            # List files in the directory
            log_dir = os.path.dirname(temp_log_file)
            all_files_in_log_dir = os.listdir(log_dir)

            # Filter for files related to this specific test's log base name
            related_log_files = [f for f in all_files_in_log_dir if f.startswith(os.path.basename(temp_log_file))]

            # Assert number of log files
            self.assertTrue(len(related_log_files) <= backup_count + 1,
                            f"Expected at most {backup_count + 1} files, found {len(related_log_files)}: {related_log_files}")

            # Assert current log file size (approximate, due to formatter and potential partial writes)
            # This might be slightly flaky if the exact byte count is critical.
            if os.path.exists(temp_log_file):
                 # After rotation, the main file might be smaller than max_bytes.
                 # The most recently rotated file (.1) should be close to max_bytes.
                 # For simplicity, we check if the current file is not excessively large.
                current_size = os.path.getsize(temp_log_file)
                self.assertTrue(current_size <= max_bytes + (log_message_size + 100), # Add buffer for formatter/timestamps
                                f"Current log file {temp_log_file} size {current_size} exceeded maxBytes {max_bytes} significantly.")

            # Check if at least some rotation occurred if enough data was logged
            if num_messages_to_log * log_message_size > max_bytes * (backup_count / 2): # Heuristic
                 self.assertTrue(len(related_log_files) > 1,
                                 f"Expected rotation to occur, but only found {len(related_log_files)} file(s). Logged enough data for rotation.")

        finally:
            # Clean up handlers for this specific logger
            handler.close()
            logger.removeHandler(handler)
            # Remove logger from logging system's cache
            if logger.name in logging.Logger.manager.loggerDict:
                del logging.Logger.manager.loggerDict[logger.name]


    def test_katana_events_log_rotation(self):
        # Mimicking katana_events.log: 10MB, 5 backups
        # Test params: smaller size for quicker test
        self._perform_rotation_test(
            log_file_base_name="katana_events_test",
            max_bytes=1024,  # 1KB
            backup_count=3,
            log_message_size=200, # Approx 200 bytes per message
            num_messages_to_log=20 # 20 * 200 = 4000 bytes, should cause ~3 rotations (1KB files, 3 backups)
        )

    def test_backend_log_rotation(self):
        # Mimicking backend.log: 5MB, 3 backups
        self._perform_rotation_test(
            log_file_base_name="backend_test",
            max_bytes=800, # 0.8KB
            backup_count=2,
            log_message_size=150,
            num_messages_to_log=15 # 15 * 150 = 2250 bytes, should cause ~2 rotations (0.8KB files, 2 backups)
        )

    def test_cli_log_rotation(self):
        # Mimicking cli.log: 5MB, 3 backups
        self._perform_rotation_test(
            log_file_base_name="cli_activities_test",
            max_bytes=1200, # 1.2KB
            backup_count=3,
            log_message_size=250,
            num_messages_to_log=20 # 20 * 250 = 5000 bytes, should cause ~4 rotations (1.2KB files, 3 backups)
        )

    def test_telegram_log_rotation(self):
        # Mimicking telegram.log: 5MB, 3 backups
        self._perform_rotation_test(
            log_file_base_name="telegram_processing_test",
            max_bytes=1000, # 1KB
            backup_count=2,
            log_message_size=180,
            num_messages_to_log=15 # 15 * 180 = 2700 bytes, should cause ~2 rotations (1KB files, 2 backups)
        )

if __name__ == '__main__':
    unittest.main(verbosity=2)
```
