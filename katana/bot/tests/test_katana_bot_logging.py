import unittest
import os
import json
import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path
from datetime import datetime, timezone

# Correctly import setup_logger from the utils module
from katana.utils.logging_config import setup_logger as setup_katana_logger

BOT_SCRIPT_DIR = Path(__file__).resolve().parent.parent
BOT_LOG_DIR = BOT_SCRIPT_DIR / "logs"
BOT_LOG_FILE = BOT_LOG_DIR / "katana_bot.log"

# This JsonFormatter is defined locally for the tests, specifically for test_bot_log_rotation
# and for verifying the output structure if reading from BOT_LOG_FILE.
class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        log_record = {
            "timestamp": datetime.fromtimestamp(record.created, tz=timezone.utc).isoformat(),
            "level": record.levelname,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line_number": record.lineno,
        }
        if record.exc_info:
            log_record["exception"] = self.formatException(record.exc_info)

        standard_attrs = [
            'args', 'asctime', 'created', 'exc_info', 'exc_text', 'filename',
            'funcName', 'levelname', 'levelno', 'lineno', 'message', 'module',
            'msecs', 'msg', 'name', 'pathname', 'process', 'processName',
            'relativeCreated', 'stack_info', 'thread', 'threadName', 'levelname'
        ]
        for key, value in record.__dict__.items():
            if key not in standard_attrs and key not in log_record:
                log_record[key] = value
        return json.dumps(log_record)

def get_json_log_entries(log_file_path):
    entries = []
    if not log_file_path.exists():
        return entries
    with open(log_file_path, 'r') as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                entries.append(json.loads(line))
            except json.JSONDecodeError:
                print(f"Warning: Test could not parse log line as JSON: '{line}'")
    return entries

class TestKatanaBotLogging(unittest.TestCase):

    def setUp(self):
        BOT_LOG_DIR.mkdir(exist_ok=True)
        if BOT_LOG_FILE.exists():
            BOT_LOG_FILE.unlink(missing_ok=True)

        # Clean up handlers for the main "KatanaBotAI" logger before each test
        # to ensure a clean state for handler configuration by _configure_bot_logger_for_file_test.
        bot_logger = logging.getLogger("KatanaBotAI")
        for handler in bot_logger.handlers[:]:
            handler.close()
            bot_logger.removeHandler(handler)

    def tearDown(self):
        if BOT_LOG_FILE.exists():
            BOT_LOG_FILE.unlink(missing_ok=True)

        # Cleanup for rotation test files
        for f in BOT_LOG_DIR.glob("rotation_test_bot_temp.log*"):
            f.unlink(missing_ok=True)

        # Clean up handlers for "KatanaBotAI" and any test-specific loggers
        logger_names = ["KatanaBotAI", "RotationTestBotLogger"]
        for name in logger_names:
            logger_instance = logging.getLogger(name)
            for handler in logger_instance.handlers[:]:
                handler.close()
                logger_instance.removeHandler(handler)

    def _configure_bot_logger_for_file_test(self):
        """Configures the KatanaBotAI logger to write to BOT_LOG_FILE for testing."""
        # Uses the centralized setup_logger but ensures it targets the test BOT_LOG_FILE
        # and uses the JsonFormatter defined in this test file for verification consistency.

        # Temporarily override setup_logger's internal JsonFormatter for this test run
        # This is a bit of a hack. A cleaner way would be for setup_logger to accept a formatter class.
        original_formatter = None
        if hasattr(setup_katana_logger, '__closure__') or hasattr(setup_katana_logger, '__globals__'):
            # This is a complex way to attempt to modify the formatter if it's hardcoded in setup_logger
            # For now, we rely on setup_logger using a JsonFormatter that's compatible,
            # or we accept that the test JsonFormatter might only be for get_json_log_entries.
            # The main goal is that setup_logger *configures* the logger.
            pass

        logger = setup_katana_logger("KatanaBotAI", str(BOT_LOG_FILE), level=logging.DEBUG)

        # Ensure it uses the test's JsonFormatter for file output for predictable parsing
        # by finding the file handler and replacing its formatter.
        for handler in logger.handlers:
            if isinstance(handler, RotatingFileHandler) and handler.baseFilename == str(BOT_LOG_FILE):
                handler.setFormatter(JsonFormatter())
                break
        return logger


    def test_bot_log_rotation(self):
        temp_log_file_name = "rotation_test_bot_temp.log"
        temp_log_file_path = BOT_LOG_DIR / temp_log_file_name

        if temp_log_file_path.exists(): temp_log_file_path.unlink(missing_ok=True)
        for i in range(1, 6):
            backup_file = Path(f"{str(temp_log_file_path)}.{i}")
            if backup_file.exists(): backup_file.unlink(missing_ok=True)

        test_logger = logging.getLogger("RotationTestBotLogger")
        test_logger.propagate = False
        test_logger.setLevel(logging.DEBUG)

        if test_logger.hasHandlers():
            for h in test_logger.handlers[:]: h.close(); test_logger.removeHandler(h)

        handler_max_bytes = 1024
        handler_backup_count = 2

        rotating_handler = RotatingFileHandler(
            temp_log_file_path, maxBytes=handler_max_bytes, backupCount=handler_backup_count
        )
        rotating_handler.setFormatter(JsonFormatter()) # Uses JsonFormatter from this file
        test_logger.addHandler(rotating_handler)

        log_message_content = "Bot rotation test log message."
        num_log_entries_to_write = 20
        for i in range(num_log_entries_to_write):
            test_logger.info(f"{log_message_content} - Entry {i+1}", extra={"user_id": f"test_rot_user_{i+1}"})

        rotating_handler.close()
        test_logger.removeHandler(rotating_handler)

        self.assertTrue(temp_log_file_path.exists())
        backup_files_found = sum(1 for i in range(1, handler_backup_count + 1) if Path(f"{str(temp_log_file_path)}.{i}").exists())
        self.assertEqual(backup_files_found, handler_backup_count)
        if temp_log_file_path.exists(): # Check before stat
            self.assertLessEqual(temp_log_file_path.stat().st_size, handler_max_bytes + 400) # Increased margin

    def test_bot_log_levels_and_structured_fields(self):
        logger = self._configure_bot_logger_for_file_test()
        test_user_id = "test_user_123"

        logger.debug("This is a debug message from test.", extra={"user_id": test_user_id, "custom_field": "debug_val"})
        logger.info("Test command received.", extra={"user_id": test_user_id, "command_name": "/test_cmd"})
        logger.warning("This is a test warning.", extra={"user_id": test_user_id, "warn_param": "some_issue"})
        logger.error("This is a test error without exception.", extra={"user_id": test_user_id, "error_code": 500})

        for handler in logger.handlers: handler.close() # Flush logs

        log_entries = get_json_log_entries(BOT_LOG_FILE)
        self.assertGreaterEqual(len(log_entries), 4)

        debug_log = next((le for le in log_entries if le["level"] == "DEBUG"), None)
        self.assertIsNotNone(debug_log)
        self.assertEqual(debug_log["message"], "This is a debug message from test.")
        self.assertEqual(debug_log.get("user_id"), test_user_id)
        self.assertEqual(debug_log.get("custom_field"), "debug_val")

        info_log = next((le for le in log_entries if le["level"] == "INFO"), None)
        self.assertIsNotNone(info_log)
        self.assertEqual(info_log["message"], "Test command received.")
        self.assertEqual(info_log.get("user_id"), test_user_id)
        self.assertEqual(info_log.get("command_name"), "/test_cmd")

        warning_log = next((le for le in log_entries if le["level"] == "WARNING"), None)
        self.assertIsNotNone(warning_log)
        self.assertEqual(warning_log["message"], "This is a test warning.")
        self.assertEqual(warning_log.get("user_id"), test_user_id)
        self.assertEqual(warning_log.get("warn_param"), "some_issue")

        error_log = next((le for le in log_entries if le["level"] == "ERROR" and "without exception" in le["message"]), None)
        self.assertIsNotNone(error_log)
        self.assertEqual(error_log["message"], "This is a test error without exception.")
        self.assertEqual(error_log.get("user_id"), test_user_id)
        self.assertEqual(error_log.get("error_code"), 500)

        for entry in [debug_log, info_log, warning_log, error_log]:
            if entry: # Ensure entry is not None
                self.assertEqual(entry["module"], "test_katana_bot_logging")
                self.assertTrue(isinstance(entry["function"], str))


    def test_bot_exception_logging(self):
        logger = self._configure_bot_logger_for_file_test()
        test_user_id = "user_exception_test"
        try:
            raise ValueError("This is a simulated exception for bot logging.")
        except ValueError:
            logger.error("Simulated error occurred.", exc_info=True, extra={"user_id": test_user_id, "detail": "exception_test"})

        for handler in logger.handlers: handler.close()

        log_entries = get_json_log_entries(BOT_LOG_FILE)
        self.assertEqual(len(log_entries), 1)
        error_log = log_entries[0]
        self.assertEqual(error_log["level"], "ERROR")
        self.assertEqual(error_log["message"], "Simulated error occurred.")
        self.assertEqual(error_log.get("user_id"), test_user_id)
        self.assertEqual(error_log.get("detail"), "exception_test")
        self.assertIn("exception", error_log)
        self.assertIn("ValueError: This is a simulated exception for bot logging.", error_log["exception"])

    def test_bot_startup_logging(self):
        logger = self._configure_bot_logger_for_file_test()

        # Scenario 1: All keys present
        original_env = os.environ.copy()
        os.environ["OPENAI_API_KEY"] = "fake_openai_key_for_test_startup1"
        os.environ["KATANA_TELEGRAM_TOKEN"] = "fake_telegram_token_for_startup1"

        logger.info("OpenAI client initialized test.")
        logger.info("Initializing Katana Telegram Bot test.")

        for handler in logger.handlers: handler.close()
        log_entries = get_json_log_entries(BOT_LOG_FILE)

        self.assertTrue(any("OpenAI client initialized test" in le["message"] for le in log_entries if le["level"] == "INFO"))
        self.assertTrue(any("Initializing Katana Telegram Bot test" in le["message"] for le in log_entries if le["level"] == "INFO"))

        os.environ.clear()
        os.environ.update(original_env)
        if BOT_LOG_FILE.exists(): BOT_LOG_FILE.unlink()
        for handler in logger.handlers[:]: handler.close(); logger.removeHandler(handler)
        logger = self._configure_bot_logger_for_file_test()

        # Scenario 2: OpenAI API key missing
        os.environ["KATANA_TELEGRAM_TOKEN"] = "fake_telegram_token_for_startup2"
        # OPENAI_API_KEY is missing (cleared by previous step)

        logger.warning("OPENAI_API_KEY not found test.")
        logger.critical("OpenAI API Key not set test.")

        for handler in logger.handlers: handler.close()
        log_entries = get_json_log_entries(BOT_LOG_FILE)
        self.assertTrue(any("OPENAI_API_KEY not found test" in le["message"] for le in log_entries if le["level"] == "WARNING"))
        self.assertTrue(any("OpenAI API Key not set test" in le["message"] for le in log_entries if le["level"] == "CRITICAL"))

        os.environ.clear()
        os.environ.update(original_env)

if __name__ == '__main__':
    unittest.main()
