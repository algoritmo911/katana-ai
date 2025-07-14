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

        bot_logger = logging.getLogger("KatanaBotAI")
        for handler in bot_logger.handlers[:]:
            handler.close()
            bot_logger.removeHandler(handler)

    def tearDown(self):
        if BOT_LOG_FILE.exists():
            BOT_LOG_FILE.unlink(missing_ok=True)

    def test_bot_log_levels_and_structured_fields(self):
        logger = setup_katana_logger("KatanaBotAI", str(BOT_LOG_FILE), level=logging.DEBUG)
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
        logger = setup_katana_logger("KatanaBotAI", str(BOT_LOG_FILE), level=logging.DEBUG)
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
        logger = setup_katana_logger("KatanaBotAI", str(BOT_LOG_FILE), level=logging.DEBUG)

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
        logger = setup_katana_logger("KatanaBotAI", str(BOT_LOG_FILE), level=logging.DEBUG)

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
