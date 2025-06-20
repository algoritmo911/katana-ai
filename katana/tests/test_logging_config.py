import pytest
import logging
import os
import re
from pathlib import Path
from katana.logging_config import get_logger, setup_logging, DEFAULT_LOGGER_NAME, DEFAULT_LOG_FILE_NAME, MAX_BYTES, BACKUP_COUNT

# Define a test log file name
TEST_LOG_FILE = Path("test_katana_events.log")

# Fixture to ensure cleanup of the test log file if it's created
@pytest.fixture(autouse=True)
def cleanup_test_log_file():
    # This will run before each test, not strictly necessary for setup,
    # but ensures a clean state if a previous test failed mid-way.
    if TEST_LOG_FILE.exists():
        TEST_LOG_FILE.unlink()
    yield # This is where the test runs
    # This will run after each test
    if TEST_LOG_FILE.exists():
        TEST_LOG_FILE.unlink()

def test_logger_setup_and_basic_log():
    """Test logger initialization and basic message logging."""
    # Using default log file for this test, but ensuring it's cleaned up if created
    # by specific call to setup_logging with default name.
    # For this test, we mainly care about the logger object itself.
    if Path(DEFAULT_LOG_FILE_NAME).exists(): # cleanup default if it exists from other non-test runs
        Path(DEFAULT_LOG_FILE_NAME).unlink()

    setup_logging(log_level=logging.DEBUG)
    logger = get_logger("test_logger_basic") # Get a specific logger

    assert logger is not None, "Logger should be initialized."
    assert logger.name == "test_logger_basic", "Logger name should be set."

    # Test that this specific logger doesn't have handlers directly from this setup
    # It will propagate to the DEFAULT_LOGGER_NAME which has handlers.
    # assert not logger.hasHandlers(), "Specific test_logger_basic should not have handlers itself"

    # Get the main configured logger to check its handlers
    main_katana_logger = logging.getLogger(DEFAULT_LOGGER_NAME)
    assert main_katana_logger.hasHandlers(), f"{DEFAULT_LOGGER_NAME} should have handlers."
    assert len(main_katana_logger.handlers) >= 1, f"{DEFAULT_LOGGER_NAME} should have at least one handler."

    # Test logging a message
    try:
        logger.info("This is a test info message from test_logger_basic.")
    except Exception as e:
        pytest.fail(f"Logging a message failed: {e}")

    # Clean up default log file if this test created it
    if Path(DEFAULT_LOG_FILE_NAME).exists():
        # Close handlers for default log file before unlinking
        for handler in list(main_katana_logger.handlers):
            if isinstance(handler, logging.FileHandler) and Path(handler.baseFilename).name == DEFAULT_LOG_FILE_NAME:
                handler.close()
        Path(DEFAULT_LOG_FILE_NAME).unlink()


def test_log_file_creation_and_content():
    """Test log file creation and content."""
    unique_message = f"Unique test message for file content: {Path(__file__).name}"

    # Explicitly use TEST_LOG_FILE for this test
    setup_logging(log_level=logging.INFO, log_file_path=str(TEST_LOG_FILE))

    # Get the main logger, as setup_logging configures DEFAULT_LOGGER_NAME
    logger = get_logger(DEFAULT_LOGGER_NAME)
    logger.info(unique_message)

    assert TEST_LOG_FILE.exists(), "Log file should be created at the specified test path."

    content = TEST_LOG_FILE.read_text()
    assert unique_message in content, "Unique message should be in the log file."
    assert "INFO" in content, "Log level 'INFO' should be in the log file."
    # %(module)s will be the name of the test file module itself
    assert Path(__file__).stem in content, f"Module name '{Path(__file__).stem}' should be in the log file."

def test_console_output(capsys):
    """Test console output using capsys fixture."""
    # setup_logging is called, configuring DEFAULT_LOGGER_NAME
    # We get a child of it to test propagation for console.
    setup_logging(log_level=logging.WARNING)

    logger = get_logger(DEFAULT_LOGGER_NAME + ".console_test") # Child logger
    warning_message = "Testing console warning output."
    logger.warning(warning_message)

    captured = capsys.readouterr()

    # StreamHandler by default writes to stderr. For WARNING level and above.
    # INFO and DEBUG would go to stdout if StreamHandler was configured for sys.stdout
    # but default StreamHandler() with no args is sys.stderr.
    # Our current setup_logging adds a StreamHandler that goes to console (stderr for WARNING)
    assert warning_message in captured.err, "Warning message should be in stderr."
    assert "WARNING" in captured.err, "Log level 'WARNING' should be in stderr."
    # %(module)s will be the name of the test file module itself
    assert Path(__file__).stem in captured.err, "Module name should be in stderr."

def test_log_format(capsys):
    """Test the log format."""
    setup_logging(log_level=logging.ERROR) # Ensure ERROR level is processed

    # Get a child logger to check formatting via propagation
    logger_name_segment = "format_test_logger_segment"
    logger = get_logger(DEFAULT_LOGGER_NAME + "." + logger_name_segment)
    error_message = "Testing log format with an error message."

    logger.error(error_message)
    captured = capsys.readouterr()

    # Example format: '%(levelname)s %(asctime)s - %(module)s - %(message)s'
    # Date format: '%Y-%m-%d %H:%M:%S'
    log_output = captured.err

    assert "ERROR" in log_output, "Log level 'ERROR' should be present."
    assert error_message in log_output, "The error message should be present."
    # %(module)s will be the name of the test file module itself
    assert Path(__file__).stem in log_output, f"The module name part '{Path(__file__).stem}' should be present."

    # Regex to check for "LEVEL YYYY-MM-DD HH:MM:SS - module - message"
    # The module name captured will be the name of this test file's module.
    expected_pattern = re.compile(
        r"ERROR \d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2} - " +
        re.escape(Path(__file__).stem) + # Expecting the current test module name
        r" - " + re.escape(error_message)
    )
    assert expected_pattern.search(log_output), f"Log output '{log_output}' does not match expected format pattern."


def test_log_rotation_config():
    """Test that log rotation is configured with correct maxBytes and backupCount."""
    # Setup with a test file to avoid affecting the default log
    setup_logging(log_level=logging.INFO, log_file_path=str(TEST_LOG_FILE))

    logger_to_check = logging.getLogger(DEFAULT_LOGGER_NAME)

    file_handler = None
    for handler in logger_to_check.handlers:
        if isinstance(handler, logging.handlers.RotatingFileHandler):
            file_handler = handler
            break

    assert file_handler is not None, "RotatingFileHandler should be present on the logger."
    assert file_handler.maxBytes == MAX_BYTES, f"maxBytes should be {MAX_BYTES}."
    assert file_handler.backupCount == BACKUP_COUNT, f"backupCount should be {BACKUP_COUNT}."

def test_get_logger_default_name():
    """Test that get_logger() returns the default logger if no name is provided."""
    logger = get_logger()
    assert logger.name == DEFAULT_LOGGER_NAME, f"Default logger name should be {DEFAULT_LOGGER_NAME}."

def test_get_logger_custom_name():
    """Test that get_logger() returns a logger with the custom name provided."""
    custom_name = "my_custom_logger"
    logger = get_logger(custom_name)
    assert logger.name == custom_name, f"Custom logger name should be {custom_name}."

def test_multiple_setup_calls():
    """Test that calling setup_logging multiple times doesn't add duplicate handlers."""
    # Initial setup
    setup_logging(log_level=logging.INFO, log_file_path=str(TEST_LOG_FILE))
    logger = logging.getLogger(DEFAULT_LOGGER_NAME)
    initial_handler_count = len(logger.handlers)
    assert initial_handler_count > 0, "Logger should have handlers after first setup."

    # Call setup_logging again
    setup_logging(log_level=logging.DEBUG, log_file_path=str(TEST_LOG_FILE))
    second_handler_count = len(logger.handlers)

    assert second_handler_count == initial_handler_count, \
        "Calling setup_logging multiple times should not increase handler count."

    # Check that handlers are of the correct types (e.g., StreamHandler and RotatingFileHandler)
    has_stream_handler = any(isinstance(h, logging.StreamHandler) for h in logger.handlers)
    has_file_handler = any(isinstance(h, logging.handlers.RotatingFileHandler) for h in logger.handlers)
    assert has_stream_handler, "Logger should have a StreamHandler."
    assert has_file_handler, "Logger should have a RotatingFileHandler."
    assert len(logger.handlers) == 2, "Logger should have exactly two handlers (Stream and RotatingFile) after setup."

    # Log a message to ensure it's only logged once per handler type
    # This is implicitly tested by handler count, but an explicit check could be done
    # by examining file content / console output if there were doubts.
    # For now, handler count check is primary for this aspect.

    # Ensure the log level was updated by the second call
    assert logger.level == logging.DEBUG, "Logger level should be updated by the second setup_logging call."

# It's good practice to also test if logging is disabled for levels below the set level.
def test_log_level_filtering(capsys):
    """Test that messages below the set log level are not emitted."""
    setup_logging(log_level=logging.INFO, log_file_path=str(TEST_LOG_FILE))
    logger = get_logger(DEFAULT_LOGGER_NAME + ".level_test")

    logger.debug("This debug message should not appear.")
    logger.info("This info message should appear.")

    # Check console output
    captured_console = capsys.readouterr()
    assert "This debug message should not appear." not in captured_console.err
    assert "This debug message should not appear." not in captured_console.out
    assert "This info message should appear." in captured_console.err # INFO goes to stderr by default with StreamHandler

    # Check file output
    assert TEST_LOG_FILE.exists(), "Log file should be created."
    if TEST_LOG_FILE.exists():
        content = TEST_LOG_FILE.read_text()
        assert "This debug message should not appear." not in content
        assert "This info message should appear." in content

    # Ensure logger level is set correctly on the target logger
    target_logger = logging.getLogger(DEFAULT_LOGGER_NAME)
    assert target_logger.getEffectiveLevel() == logging.INFO

    # Test with a child logger which should inherit the level
    child_logger = get_logger(DEFAULT_LOGGER_NAME + ".child_level_test")
    assert child_logger.getEffectiveLevel() == logging.INFO
    child_logger.debug("Child debug message, should not appear.")

    captured_console_child = capsys.readouterr()
    assert "Child debug message, should not appear." not in captured_console_child.err
    assert "Child debug message, should not appear." not in captured_console_child.out

    if TEST_LOG_FILE.exists():
        content_after_child_log = TEST_LOG_FILE.read_text()
        assert "Child debug message, should not appear." not in content_after_child_log

pytest.main() # For running directly if needed, though typically run via `pytest` command
