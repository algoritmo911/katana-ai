import pytest
import logging
import os
import re
import json # Added
import datetime # Added
from pathlib import Path
from katana.logger import get_logger, setup_logging, DEFAULT_LOGGER_NAME, DEFAULT_LOG_FILE_NAME, MAX_BYTES, BACKUP_COUNT

# Define a test log file name
TEST_LOG_FILE = Path("test_katana_events.log")

# Regex for ISO 8601 timestamp: YYYY-MM-DDTHH:MM:SS.sssZ
TIMESTAMP_REGEX = re.compile(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d{3}Z")

# Expected top-level keys in every JSON log entry (excluding exc_info for general checks)
EXPECTED_JSON_LOG_KEYS = sorted([
    "timestamp", "level", "message", "module", "funcName", "lineno",
    "user_id", "chat_id", "message_id"
])

def _parse_log_line(line):
    """Helper to parse a single JSON log line."""
    try:
        return json.loads(line)
    except json.JSONDecodeError as e:
        pytest.fail(f"Failed to parse log line as JSON: '{line}'. Error: {e}")

def _check_json_log_structure_and_common_fields(
    log_json,
    expected_level,
    expected_message_contains,
    expected_module_contains,
    expected_user_id="N/A",
    expected_chat_id="N/A",
    expected_message_id="N/A"
):
    """
    Helper to check the exact structure and common fields of a parsed JSON log.
    """
    # Check for the exact set of expected keys
    # Allow 'exc_info' as an optional key for error logs, handle it separately in its test
    actual_keys = sorted([k for k in log_json.keys() if k != 'exc_info'])
    assert actual_keys == EXPECTED_JSON_LOG_KEYS, \
        f"JSON log keys mismatch. Expected: {EXPECTED_JSON_LOG_KEYS}, Got: {actual_keys}"

    assert TIMESTAMP_REGEX.match(log_json['timestamp']), \
        f"Timestamp '{log_json['timestamp']}' does not match ISO 8601 format."
    assert log_json['level'] == expected_level
    assert expected_message_contains in log_json['message'], \
        f"Message '{log_json['message']}' does not contain '{expected_message_contains}'"
    assert expected_module_contains in log_json['module'], \
        f"Module '{log_json['module']}' does not contain '{expected_module_contains}'"
    assert isinstance(log_json['funcName'], str) and log_json['funcName']
    assert isinstance(log_json['lineno'], int) and log_json['lineno'] > 0

    assert log_json['user_id'] == expected_user_id
    assert log_json['chat_id'] == expected_chat_id
    assert log_json['message_id'] == expected_message_id

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
    logger.info(unique_message) # This will use default context fields "N/A"

    assert TEST_LOG_FILE.exists(), "Log file should be created at the specified test path."

    # Read the first line of the log file (assuming only one log for this test)
    content = TEST_LOG_FILE.read_text().strip()
    assert content, "Log file is empty."

    log_lines = content.splitlines()
    assert len(log_lines) == 1, "Expected a single log line."
    log_json = _parse_log_line(log_lines[0])

    _check_json_log_structure_and_common_fields(
        log_json,
        expected_level="INFO",
        expected_message_contains=unique_message,
        expected_module_contains=Path(__file__).stem # module is this test file's name
    )

def test_console_output(capsys):
    """Test console output using capsys fixture for colored text logs."""
    setup_logging(log_level=logging.WARNING)
    logger = get_logger(DEFAULT_LOGGER_NAME + ".console_color_test") # Child logger
    warning_message = "Testing console warning output for color."
    logger.warning(warning_message)

    captured = capsys.readouterr()
    captured_err = captured.err.strip()

    assert captured_err, "stderr output for console is empty."
    # Check for ANSI escape codes (basic check for coloring)
    assert "\x1b[" in captured_err, "No ANSI escape codes found in console output, expected colored logs."
    assert warning_message in captured_err, "Warning message not found in console output."
    assert "WARNING" in captured_err, "Log level 'WARNING' not found in console output."
    # Check for some other parts of the format string
    assert Path(__file__).stem in captured_err, "Module name not found in console output."
    assert "console_color_test" in captured_err, "Logger name segment 'console_color_test' not found."

    # Ensure it's NOT JSON
    with pytest.raises(json.JSONDecodeError):
        json.loads(captured_err.splitlines()[0])


def test_log_format_and_exc_info_file(capsys):
    """Test the JSON log format in FILE, including exc_info. Console will be text."""
    setup_logging(log_level=logging.ERROR, log_file_path=str(TEST_LOG_FILE)) # Ensure ERROR level is processed

    # Get a child logger to check formatting via propagation
    logger_name_segment = "format_test_logger_segment"
    logger = get_logger(DEFAULT_LOGGER_NAME + "." + logger_name_segment)
    error_message = "Testing log format with a real error." # Changed message slightly

    try:
        # Simulate a situation where an exception occurs
        _ = 1 / 0
    except ZeroDivisionError:
        # Log the error from within an exception handler context
        logger.error(error_message, exc_info=True)

    # Console output will be colored text
    captured_console = capsys.readouterr()
    console_output = captured_console.err.strip()
    assert error_message in console_output, "Error message not in console output."
    assert "ERROR" in console_output, "Error level not in console output."
    assert "\x1b[" in console_output, "No ANSI escape codes in console error output."

    # File output should be JSON and contain exc_info
    assert TEST_LOG_FILE.exists(), "Log file should be created for exc_info test."
    file_content = TEST_LOG_FILE.read_text().strip()
    assert file_content, "Log file for exc_info test is empty."

    log_lines_file = file_content.splitlines()
    assert len(log_lines_file) == 1, "Expected one log line in the file for exc_info test."
    log_json_file = _parse_log_line(log_lines_file[0])

    # Check common structure first
    _check_json_log_structure_and_common_fields(
        log_json_file,
        expected_level="ERROR",
        expected_message_contains=error_message,
        expected_module_contains=Path(__file__).stem
    )

    assert 'exc_info' in log_json_file, "exc_info field missing in JSON log."
    assert isinstance(log_json_file['exc_info'], str), "exc_info should be a string."
    assert "ZeroDivisionError" in log_json_file['exc_info'], "exc_info should contain ZeroDivisionError details."
    assert "Traceback (most recent call last):" in log_json_file['exc_info'], "Traceback information missing from exc_info."


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

def test_custom_context_fields(capsys):
    """Test that custom context fields (user_id, chat_id, message_id) are logged correctly."""
    setup_logging(log_level=logging.INFO, log_file_path=str(TEST_LOG_FILE))
    logger = get_logger(DEFAULT_LOGGER_NAME + ".context_test")

    # Test 1: All custom fields provided
    msg1 = "Log with full custom context."
    extra1 = {"user_id": "test_user", "chat_id": "test_chat", "message_id": "test_msg_1"}
    logger.info(msg1, extra=extra1)

    # Test 2: Partial custom fields provided
    msg2 = "Log with partial custom context."
    extra2 = {"user_id": "another_user"}
    logger.info(msg2, extra=extra2)

    # Test 3: No custom fields provided (should use defaults "N/A")
    msg3 = "Log with no custom context."
    logger.info(msg3)

    # Check console output (stderr) - it will be colored text, not JSON
    captured_err = capsys.readouterr().err.strip()
    log_lines_err = captured_err.splitlines()
    assert len(log_lines_err) == 3, "Expected 3 log lines in stderr for context test."

    # Basic check for message content in colored logs
    assert msg1 in log_lines_err[0]
    assert msg2 in log_lines_err[1]
    assert msg3 in log_lines_err[2]
    # Custom context fields (user_id, etc.) are not in the default console format for coloredlogs

    # Check file output (JSON)
    assert TEST_LOG_FILE.exists(), "Log file should be created for context test."
    content_file = TEST_LOG_FILE.read_text().strip()
    log_lines_file = content_file.splitlines()
    assert len(log_lines_file) == 3, "Expected 3 log lines in file for context test."

    # Log 1: Full context
    log_json1 = _parse_log_line(log_lines_file[0])
    _check_json_log_structure_and_common_fields(
        log_json1,
        expected_level="INFO",
        expected_message_contains=msg1,
        expected_module_contains=Path(__file__).stem,
        expected_user_id=extra1['user_id'],
        expected_chat_id=extra1['chat_id'],
        expected_message_id=extra1['message_id']
    )

    # Log 2: Partial context
    log_json2 = _parse_log_line(log_lines_file[1])
    _check_json_log_structure_and_common_fields(
        log_json2,
        expected_level="INFO",
        expected_message_contains=msg2,
        expected_module_contains=Path(__file__).stem,
        expected_user_id=extra2['user_id'],
        expected_chat_id="N/A", # Default
        expected_message_id="N/A"  # Default
    )

    # Log 3: No context (all defaults)
    log_json3 = _parse_log_line(log_lines_file[2])
    _check_json_log_structure_and_common_fields(
        log_json3,
        expected_level="INFO",
        expected_message_contains=msg3,
        expected_module_contains=Path(__file__).stem,
        expected_user_id="N/A",
        expected_chat_id="N/A",
        expected_message_id="N/A"
    )


# It's good practice to also test if logging is disabled for levels below the set level.
def test_log_level_filtering(capsys):
    """Test that messages below the set log level are not emitted to console or file."""
    setup_logging(log_level=logging.INFO, log_file_path=str(TEST_LOG_FILE))
    logger = get_logger(DEFAULT_LOGGER_NAME + ".level_filter_test")

    debug_msg = "This debug message should not appear."
    info_msg = "This info message should appear."

    logger.debug(debug_msg)
    logger.info(info_msg)

    # Check console output (stderr) - should be text, not JSON
    captured_console = capsys.readouterr().err.strip()
    assert debug_msg not in captured_console, "Debug message found in console output when level is INFO."
    assert info_msg in captured_console, "Info message not found in console output when level is INFO."
    console_lines = captured_console.splitlines()
    assert len(console_lines) == 1, "Expected only one log line (INFO) in console output."
    assert "INFO" in console_lines[0] # Check level in text
    with pytest.raises(json.JSONDecodeError): # Ensure console is not JSON
        json.loads(console_lines[0]) # Directly use json.loads for the expected failure


    # Check file output - should be JSON
    assert TEST_LOG_FILE.exists(), "Log file should be created for level filtering test."
    content_file = TEST_LOG_FILE.read_text().strip()
    assert debug_msg not in content_file, "Debug message found in file output when level is INFO."
    assert info_msg in content_file, "Info message not found in file output when level is INFO."

    log_lines_file = content_file.splitlines()
    assert len(log_lines_file) == 1, "Expected only one log line (INFO) in file output."

    log_json_file = _parse_log_line(log_lines_file[0])
    _check_json_log_structure_and_common_fields(
        log_json_file,
        expected_level="INFO",
        expected_message_contains=info_msg,
        expected_module_contains=Path(__file__).stem
    )
    assert log_json_file['message'] == info_msg # Also check exact message match

    # Ensure logger level is set correctly on the target logger
    target_logger = logging.getLogger(DEFAULT_LOGGER_NAME)
    assert target_logger.getEffectiveLevel() == logging.INFO

    # Test with a child logger which should inherit the level
    child_logger = get_logger(DEFAULT_LOGGER_NAME + ".child_level_filter_test")
    assert child_logger.getEffectiveLevel() == logging.INFO

    child_debug_msg = "Child debug message, should not appear."
    child_logger.debug(child_debug_msg) # This should not produce output

    captured_err_after_child = capsys.readouterr().err.strip()
    assert child_debug_msg not in captured_err_after_child

    content_file_after_child = TEST_LOG_FILE.read_text().strip()
    assert child_debug_msg not in content_file_after_child
    # Ensure no new lines were added for the child's debug message
    assert len(content_file_after_child.splitlines()) == 1

# Remove pytest.main() call if present, tests should be run by pytest runner
# pytest.main() # For running directly if needed, though typically run via `pytest` command
