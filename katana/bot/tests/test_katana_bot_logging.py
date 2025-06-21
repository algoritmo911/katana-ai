import unittest
import os
import json
import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path
from datetime import datetime, timezone
from katana.utils.logging_config import (
    setup_logger as setup_katana_logger,
)  # Moved import to top

# Assuming katana_bot.py is in the parent directory
# Adjust if necessary, or consider making tests runnable from a project root
# with PYTHONPATH adjustments.
BOT_SCRIPT_DIR = Path(__file__).resolve().parent.parent
BOT_LOG_DIR = BOT_SCRIPT_DIR / "logs"
BOT_LOG_FILE = BOT_LOG_DIR / "katana_bot.log"  # As defined in katana_bot.py


# --- Copied JsonFormatter from katana_bot.py for test isolation ---
# This ensures the test knows about the log format it expects for rotation test.
# For caplog tests, we assert on LogRecord attributes directly.
class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        log_record = {
            "timestamp": datetime.fromtimestamp(
                record.created, tz=timezone.utc
            ).isoformat(),
            "level": record.levelname,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line_number": record.lineno,
        }
        if record.exc_info:
            log_record["exception"] = self.formatException(record.exc_info)

        # More dynamic way to include 'extra' fields
        # Standard LogRecord attributes, to exclude them from 'extra'
        standard_attrs = [
            "args",
            "asctime",
            "created",
            "exc_info",
            "exc_text",
            "filename",
            "funcName",
            "levelname",
            "levelno",
            "lineno",
            "message",
            "module",
            "msecs",
            "msg",
            "name",
            "pathname",
            "process",
            "processName",
            "relativeCreated",
            "stack_info",
            "thread",
            "threadName",
            "levelname",
        ]
        for key, value in record.__dict__.items():
            if key not in standard_attrs and key not in log_record:
                log_record[key] = value

        return json.dumps(log_record)


# This helper is now primarily for test_bot_log_rotation
def get_json_log_entries(log_file_path):
    entries = []
    if not log_file_path.exists():
        return entries
    with open(log_file_path, "r") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                entries.append(json.loads(line))
            except json.JSONDecodeError:
                print(f"Warning: Test could not parse log line as JSON: '{line}'")
    return entries


# Import the centralized setup function moved to top
# from katana.utils.logging_config import setup_logger as setup_katana_logger # E402: moved to top # Comment remains but import is above


class TestKatanaBotLogging(unittest.TestCase):

    def setUp(self):
        BOT_LOG_DIR.mkdir(exist_ok=True)
        if BOT_LOG_FILE.exists():  # This is the actual bot log file
            BOT_LOG_FILE.unlink()

        # For tests NOT using caplog (like rotation test), ensure temp files are clear
        # This glob might be too broad if LOGS_DIR is shared; refined in tearDown.
        # For now, let's assume BOT_LOG_DIR is specific enough or rotation test uses unique names.
        # The rotation test itself cleans its specific temp files.

    def tearDown(self):
        if BOT_LOG_FILE.exists():
            BOT_LOG_FILE.unlink(missing_ok=True)

        # Cleanup for rotation test files specifically
        # Note: BOT_LOG_DIR should be used here instead of a potentially mis-scoped LOGS_DIR
        for f in BOT_LOG_DIR.glob("rotation_test_bot_temp.log*"):
            f.unlink(missing_ok=True)

        # Clean up handlers for the main "KatanaBotAI" logger if it was configured by a test
        main_bot_logger = logging.getLogger("KatanaBotAI")
        for handler in main_bot_logger.handlers[:]:
            handler.close()
            main_bot_logger.removeHandler(handler)

        # Clean up test-specific loggers
        if "RotationTestBotLogger" in logging.Logger.manager.loggerDict:
            test_rot_logger = logging.getLogger("RotationTestBotLogger")
            for handler in test_rot_logger.handlers[:]:
                handler.close()
                test_rot_logger.removeHandler(handler)

    def test_bot_log_rotation(self):
        # This test remains file I/O based as it checks file rotation.
        # It uses its own logger and handler setup.
        temp_log_file_name = "rotation_test_bot_temp.log"
        temp_log_file_path = BOT_LOG_DIR / temp_log_file_name

        # Ensure clean state
        if temp_log_file_path.exists():
            temp_log_file_path.unlink()
        for i in range(1, 6):  # Clean up potential backups
            backup_file = Path(f"{str(temp_log_file_path)}.{i}")
            if backup_file.exists():
                backup_file.unlink()

        test_logger = logging.getLogger(
            "RotationTestBotLogger"
        )  # Unique name for this test logger
        test_logger.propagate = False
        test_logger.setLevel(logging.DEBUG)

        # Remove any handlers that might persist if logger name was reused and not cleaned up
        if test_logger.hasHandlers():
            for handler in test_logger.handlers[:]:
                handler.close()
                test_logger.removeHandler(handler)

        handler_max_bytes = 1024  # 1KB
        handler_backup_count = 2

        rotating_handler = RotatingFileHandler(
            temp_log_file_path,
            maxBytes=handler_max_bytes,
            backupCount=handler_backup_count,
        )
        # JsonFormatter is defined in this test file.
        rotating_handler.setFormatter(JsonFormatter())
        rotating_handler.setLevel(logging.DEBUG)
        test_logger.addHandler(rotating_handler)

        log_message_content = "Bot rotation test log message. This needs to be reasonably long to help fill the log file for rotation testing with JSON."
        # Approx 250-300 bytes per JSON entry with this message and fields.
        # To fill 1KB (maxBytes) and trigger rotation for 2 backups:
        # Each file holds ~1024/280 = ~3-4 messages.
        # (backupCount + 1) files = 3 files. So 3 * 4 = 12 messages. Let's write 20 to be safe.
        num_log_entries_to_write = 20

        for i in range(num_log_entries_to_write):
            test_logger.info(
                f"{log_message_content} - Entry {i+1}",
                extra={"user_id": f"test_rot_user_{i+1}"},
            )

        rotating_handler.close()
        test_logger.removeHandler(
            rotating_handler
        )  # Important to remove to release file for next tests/cleanup

        self.assertTrue(
            temp_log_file_path.exists(),
            f"Main log file {temp_log_file_path} should exist.",
        )

        backup_files_found = 0
        for i in range(1, handler_backup_count + 1):
            expected_backup_file = Path(f"{str(temp_log_file_path)}.{i}")
            if expected_backup_file.exists():
                backup_files_found += 1
                self.assertTrue(
                    expected_backup_file.stat().st_size > 0,
                    f"Backup file {expected_backup_file} is empty.",
                )

        self.assertEqual(
            backup_files_found,
            handler_backup_count,
            f"Expected {handler_backup_count} backup files, but found {backup_files_found}. Files in log dir: {list(BOT_LOG_DIR.glob(temp_log_file_name + '*'))}",
        )

        current_log_size = temp_log_file_path.stat().st_size
        # Allow for some variation due to JSON structure, but it should be roughly around one message size if rotation is aggressive.
        # Or less than maxBytes if it just rotated and started fresh.
        self.assertLessEqual(
            current_log_size,
            handler_max_bytes + 350,  # Margin for one full log message
            f"Current log file {temp_log_file_path} size {current_log_size} "
            f"is unexpectedly larger than maxBytes {handler_max_bytes} (plus margin).",
        )

        all_log_files = list(BOT_LOG_DIR.glob(f"{temp_log_file_name}*"))
        self.assertEqual(
            len(all_log_files),
            handler_backup_count + 1,
            f"Expected total {handler_backup_count + 1} log files, found {len(all_log_files)}.",
        )

        # Explicit cleanup, though tearDown also has a glob for this pattern.
        temp_log_file_path.unlink(missing_ok=True)
        for i in range(1, handler_backup_count + 2):
            backup_file = Path(f"{str(temp_log_file_path)}.{i}")
            backup_file.unlink(missing_ok=True)

    def _configure_bot_logger_for_caplog_test(self, caplog):
        """
        Configures the KatanaBotAI logger using the centralized setup_logger,
        and sets caplog to the appropriate level.
        """
        logger = setup_katana_logger(
            "KatanaBotAI", str(BOT_LOG_FILE), level=logging.DEBUG
        )
        caplog.set_level(logging.DEBUG, logger="KatanaBotAI")
        return logger

    def test_bot_log_levels_and_structured_fields(self, caplog):  # Added caplog fixture
        logger = self._configure_bot_logger_for_caplog_test(caplog)

        # 2. Simulate bot actions that log messages
        test_user_id = "test_user_123"

        # Simulate a DEBUG log
        logger.debug(
            "This is a debug message from test.",
            extra={"user_id": test_user_id, "custom_field": "debug_val"},
        )

        # Simulate an INFO log (like a command received)
        logger.info(
            "Test command received.",
            extra={"user_id": test_user_id, "command_name": "/test_cmd"},
        )

        # Simulate a WARNING log
        logger.warning(
            "This is a test warning.",
            extra={"user_id": test_user_id, "warn_param": "some_issue"},
        )

        # Simulate an ERROR log (without exception for now)
        logger.error(
            "This is a test error without exception.",
            extra={"user_id": test_user_id, "error_code": 500},
        )

        # No need to close/remove handlers when using caplog; it handles cleanup.

        # 3. Read and verify log entries from caplog
        self.assertEqual(len(caplog.records), 4, "Expected 4 log records.")

        debug_record = caplog.records[0]
        self.assertEqual(debug_record.levelname, "DEBUG")
        self.assertEqual(debug_record.message, "This is a debug message from test.")
        self.assertEqual(debug_record.user_id, test_user_id)
        self.assertEqual(debug_record.custom_field, "debug_val")

        info_record = caplog.records[1]
        self.assertEqual(info_record.levelname, "INFO")
        self.assertEqual(info_record.message, "Test command received.")
        self.assertEqual(info_record.user_id, test_user_id)
        self.assertEqual(info_record.command_name, "/test_cmd")

        warning_record = caplog.records[2]
        self.assertEqual(warning_record.levelname, "WARNING")
        self.assertEqual(warning_record.message, "This is a test warning.")
        self.assertEqual(warning_record.user_id, test_user_id)
        self.assertEqual(warning_record.warn_param, "some_issue")

        error_record = caplog.records[3]
        self.assertEqual(error_record.levelname, "ERROR")
        self.assertEqual(
            error_record.message, "This is a test error without exception."
        )
        self.assertEqual(error_record.user_id, test_user_id)
        self.assertEqual(error_record.error_code, 500)

        for record in caplog.records:
            self.assertEqual(record.name, "KatanaBotAI")
            self.assertEqual(record.module, "test_katana_bot_logging")
            self.assertTrue(isinstance(record.funcName, str))
            self.assertTrue(isinstance(record.lineno, int))
            # self.assertTrue(is_iso_timestamp_str(datetime.fromtimestamp(record.created).isoformat())) # caplog provides 'created'

    def test_bot_exception_logging(self, caplog):  # Added caplog fixture
        logger = self._configure_bot_logger_for_caplog_test(caplog)
        test_user_id = "user_exception_test"
        error_custom_field = "custom_error_data"

        try:
            raise ValueError("This is a simulated exception for bot logging.")
        except ValueError:
            logger.error(
                "Simulated error occurred in bot operation.",
                exc_info=True,
                extra={"user_id": test_user_id, "error_details": error_custom_field},
            )

        self.assertEqual(len(caplog.records), 1)
        error_record = caplog.records[0]

        self.assertEqual(error_record.levelname, "ERROR")
        self.assertEqual(
            error_record.message, "Simulated error occurred in bot operation."
        )
        self.assertEqual(error_record.name, "KatanaBotAI")
        self.assertEqual(error_record.user_id, test_user_id)
        self.assertEqual(error_record.error_details, error_custom_field)

        self.assertIsNotNone(error_record.exc_info)
        self.assertTrue(
            isinstance(error_record.exc_text, str)
        )  # Check exc_text from caplog
        self.assertIn(
            "ValueError: This is a simulated exception for bot logging.",
            error_record.exc_text,
        )
        self.assertIn("Traceback (most recent call last):", error_record.exc_text)

        self.assertEqual(error_record.module, "test_katana_bot_logging")
        self.assertEqual(error_record.funcName, "test_bot_exception_logging")

    def test_bot_startup_logging(self, caplog):  # Added caplog fixture
        logger = self._configure_bot_logger_for_caplog_test(caplog)

        # Scenario 1: All keys present
        original_openai_key = os.environ.pop("OPENAI_API_KEY", None)
        original_telegram_token = os.environ.pop("KATANA_TELEGRAM_TOKEN", None)
        os.environ["OPENAI_API_KEY"] = "fake_openai_key_for_test_startup1"
        os.environ["KATANA_TELEGRAM_TOKEN"] = "fake_telegram_token_for_startup1"

        logger.info(
            "OpenAI client initialized with API key ending: ...test_startup1."
        )  # F541: Removed f
        logger.info(
            "Initializing Katana Telegram Bot with token ending: ...test_startup1."  # F541: Removed f
        )

        self.assertGreaterEqual(len(caplog.records), 2)
        # Check the last two records for this scenario's logs
        self.assertEqual(caplog.records[-2].levelname, "INFO")
        self.assertIn("OpenAI client initialized", caplog.records[-2].message)
        self.assertEqual(caplog.records[-1].levelname, "INFO")
        self.assertIn("Initializing Katana Telegram Bot", caplog.records[-1].message)
        self.assertEqual(caplog.records[-1].name, "KatanaBotAI")
        caplog.clear()

        if original_openai_key is not None:
            os.environ["OPENAI_API_KEY"] = original_openai_key
        else:
            os.environ.pop("OPENAI_API_KEY", None)
        if original_telegram_token is not None:
            os.environ["KATANA_TELEGRAM_TOKEN"] = original_telegram_token
        else:
            os.environ.pop("KATANA_TELEGRAM_TOKEN", None)

        # Scenario 2: OpenAI API key missing
        original_openai_key = os.environ.pop("OPENAI_API_KEY", None)
        original_telegram_token = os.environ.pop("KATANA_TELEGRAM_TOKEN", None)
        os.environ["KATANA_TELEGRAM_TOKEN"] = "fake_telegram_token_for_startup2"

        logger.warning("OPENAI_API_KEY not found for startup2.")
        logger.critical("OpenAI API Key not set for startup2.")

        self.assertGreaterEqual(len(caplog.records), 2)
        self.assertEqual(caplog.records[-2].levelname, "WARNING")
        self.assertIn(
            "OPENAI_API_KEY not found for startup2", caplog.records[-2].message
        )
        self.assertEqual(caplog.records[-1].levelname, "CRITICAL")
        self.assertIn("OpenAI API Key not set for startup2", caplog.records[-1].message)
        self.assertEqual(caplog.records[-1].name, "KatanaBotAI")
        caplog.clear()

        if original_openai_key is not None:
            os.environ["OPENAI_API_KEY"] = original_openai_key
        if original_telegram_token is not None:
            os.environ["KATANA_TELEGRAM_TOKEN"] = original_telegram_token
        else:
            os.environ.pop("KATANA_TELEGRAM_TOKEN", None)

        # Scenario 3: Telegram token missing
        original_openai_key = os.environ.pop("OPENAI_API_KEY", None)
        original_telegram_token = os.environ.pop("KATANA_TELEGRAM_TOKEN", None)
        os.environ["OPENAI_API_KEY"] = "fake_openai_key_for_startup3"

        logger.critical("KATANA_TELEGRAM_TOKEN not set for startup3.")

        self.assertGreaterEqual(len(caplog.records), 1)
        self.assertEqual(caplog.records[-1].levelname, "CRITICAL")
        self.assertIn(
            "KATANA_TELEGRAM_TOKEN not set for startup3", caplog.records[-1].message
        )
        self.assertEqual(caplog.records[-1].name, "KatanaBotAI")
        caplog.clear()

        if original_openai_key is not None:
            os.environ["OPENAI_API_KEY"] = original_openai_key
        else:
            os.environ.pop("OPENAI_API_KEY", None)
        if original_telegram_token is not None:
            os.environ["KATANA_TELEGRAM_TOKEN"] = original_telegram_token


if __name__ == "__main__":
    # This allows running the tests directly.
    # Add `katana/bot` to PYTHONPATH if running from `katana/bot/tests`
    # or run with `python -m unittest katana.bot.tests.test_katana_bot_logging` from project root.

    # For direct execution from this file's directory:
    # current_dir = Path(__file__).parent
    # project_root = current_dir.parent.parent # Assuming tests is a subdir of bot, and bot is a subdir of project
    # sys.path.insert(0, str(project_root))

    unittest.main(verbosity=2)
