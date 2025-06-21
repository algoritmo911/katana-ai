import pytest
import os
import logging
from pathlib import Path
from katana.logging_config import setup_logging, get_logger, VOICE_LOG_FILE, DEFAULT_LOGGER_NAME, LOGS_DIR

# Define the expected log path using os.path.join for OS compatibility
EXPECTED_LOG_PATH = Path(LOGS_DIR) / Path(VOICE_LOG_FILE).name # Use Path(VOICE_LOG_FILE).name to get just "voice.log"

@pytest.fixture(scope="function", autouse=True)
def ensure_logs_dir_and_cleanup():
    # Create logs directory if it doesn't exist
    # LOGS_DIR from logging_config is 'logs'
    # EXPECTED_LOG_PATH.parent will resolve to 'logs'
    os.makedirs(EXPECTED_LOG_PATH.parent, exist_ok=True)

    # Pre-test cleanup: Remove log file if it exists to ensure a clean state
    if EXPECTED_LOG_PATH.exists():
        EXPECTED_LOG_PATH.unlink()

    yield # This is where the test runs

    # Post-test cleanup: Optionally remove log file after test
    # if EXPECTED_LOG_PATH.exists():
    #     EXPECTED_LOG_PATH.unlink()

def test_katana_bot_logs_to_voice_log():
    # 1. Configure logging for the bot
    #    Ensure katana_logger.bot logs to VOICE_LOG_FILE (logs/voice.log)
    bot_module_config = {
        f"{DEFAULT_LOGGER_NAME}.bot": {
            "filename": VOICE_LOG_FILE, # VOICE_LOG_FILE should be "logs/voice.log"
            "level": logging.INFO,
        }
    }
    setup_logging(
        log_level=logging.INFO, # Default for katana_logger
        module_file_configs=bot_module_config
    )

    # 2. Get the specific logger for the bot
    #    The name must match exactly what's configured in module_file_configs
    logger = get_logger(f"{DEFAULT_LOGGER_NAME}.bot")

    # 3. Log a test message
    test_message = "This is a test log entry from katana_logger.bot for voice.log"
    logger.info(test_message)

    # Ensure all handlers are flushed, especially file handlers
    # Iterating through all known loggers and their handlers to flush
    # This is important because logging can be asynchronous or buffered.
    for logger_name in list(logging.Logger.manager.loggerDict) + [None]: # Include root logger
        current_logger_obj = logging.getLogger(logger_name)
        if hasattr(current_logger_obj, 'handlers'):
            for handler in current_logger_obj.handlers:
                handler.flush()
    # Additionally, close handlers to ensure file write completion,
    # especially for file handlers before reading the file content.
    # This is aggressive and might affect subsequent tests if not reconfigured,
    # but for a single test function focusing on file output, it helps ensure writes.
    # A better approach for multiple tests would be specific handler management or logging shutdown.
    for logger_name in list(logging.Logger.manager.loggerDict) + [None]:
        current_logger_obj = logging.getLogger(logger_name)
        if hasattr(current_logger_obj, 'handlers'):
            for handler in current_logger_obj.handlers:
                handler.close()


    # 4. Assert that the log file was created
    assert EXPECTED_LOG_PATH.exists(), f"Log file not found at {EXPECTED_LOG_PATH}"

    # 5. Assert that the log file contains the test message
    content = EXPECTED_LOG_PATH.read_text()
    assert test_message in content, f"Test message not found in {EXPECTED_LOG_PATH}. Content:\n{content}"
