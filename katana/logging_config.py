import logging
import logging.handlers
from pythonjsonlogger import jsonlogger
import datetime

# Define the default logger name
DEFAULT_LOGGER_NAME = 'katana_logger'
DEFAULT_LOG_FILE_NAME = 'katana_events.log' # Will now store JSON
MAX_BYTES = 1 * 1024 * 1024  # 1MB
BACKUP_COUNT = 5

# --- Custom Log Record Factory ---
# This allows us to add custom fields to the log record if they are not already present.
_old_factory = logging.getLogRecordFactory()

def _katana_record_factory(*args, **kwargs):
    record = _old_factory(*args, **kwargs)
    record.user_id = getattr(record, 'user_id', "N/A")
    record.chat_id = getattr(record, 'chat_id', "N/A")
    record.message_id = getattr(record, 'message_id', "N/A")
    # Ensure standard 'timestamp' from 'asctime'
    # JsonFormatter can also do this with rename_fields, but this makes it explicit.
    # record.timestamp = datetime.datetime.fromtimestamp(record.created).isoformat()
    return record

# logging.setLogRecordFactory(_katana_record_factory) # Set this globally before any loggers are configured.
# Alternative: Use a filter on the handlers if global factory modification is undesirable.

class ContextFilter(logging.Filter):
    """
    A filter to ensure custom context fields (user_id, chat_id, message_id)
    are present on the LogRecord, defaulting to "N/A" if not provided via `extra`.
    """
    def filter(self, record):
        if not hasattr(record, 'user_id'):
            record.user_id = "N/A"
        if not hasattr(record, 'chat_id'):
            record.chat_id = "N/A"
        if not hasattr(record, 'message_id'):
            record.message_id = "N/A"

        # For debugging the specific child logger issue:
        # if record.name and DEFAULT_LOGGER_NAME + ".child_module" in record.name:
        #     print(f"Filter - Child record '{record.name}': user_id={record.user_id}, chat_id={record.chat_id}, message_id={record.message_id} (msg: {record.getMessage()})")
        return True

def setup_logging(log_level=logging.INFO, log_file_path=None):
    """
    Configures the logging for the Katana application using JSON format.

    Args:
        log_level (int, optional): The logging level to set for the logger.
                                   Defaults to logging.INFO.
        log_file_path (str, optional): Path to the log file.
                                       Defaults to DEFAULT_LOG_FILE_NAME.
    """
    logger = logging.getLogger(DEFAULT_LOGGER_NAME)
    logger.setLevel(log_level)

    # Remove existing handlers to prevent duplication if called multiple times
    if logger.hasHandlers():
        for handler in list(logger.handlers): # Iterate over a copy
            logger.removeHandler(handler)
            handler.close() # Close handler before removing

    # Define the JSON formatter
    # We want: timestamp, levelname, message, module, funcName, lineno, user_id, chat_id, message_id
    # 'asctime' will be used for timestamp by default by JsonFormatter if not specified in format string.
    # We can rename 'asctime' to 'timestamp' for clarity.
    # The custom fields user_id, chat_id, message_id will be picked up from the log record
    # if they are passed in `extra` or added by a filter/factory.

    # Option 1: Using a format string with JsonFormatter
    # format_str = '%(timestamp)s %(levelname)s %(message)s %(module)s %(funcName)s %(lineno)d %(user_id)s %(chat_id)s %(message_id)s'
    # formatter = jsonlogger.JsonFormatter(format_str)

    # Configure JsonFormatter
    # We want specific fields at the top level of the JSON.
    # python-json-logger includes many standard fields by default.
    # Custom fields (user_id, chat_id, message_id) are added via the filter
    # and will be picked up if they are attributes on the LogRecord.

    # The `format` parameter can be used to specify the keys.
    # If a field in the format string is not found on the record, it's omitted from JSON.
    # Standard LogRecord attributes: https://docs.python.org/3/library/logging.html#logrecord-attributes
    # We'll ensure 'timestamp' and 'level' are correctly named.
    supported_keys = [
        'timestamp', 'level', 'message', 'module', 'funcName', 'lineno',
        'user_id', 'chat_id', 'message_id',
        'exc_info', 'stack_info', # For errors
        'pathname', 'filename', 'created', 'thread', 'threadName', 'process', 'processName', 'levelname', 'asctime' # Other potentially useful fields
    ]

    class CustomJsonFormatter(jsonlogger.JsonFormatter):
        def add_fields(self, log_record, record, message_dict):
            # Call super first to ensure standard fields are populated by python-json-logger
            super(CustomJsonFormatter, self).add_fields(log_record, record, message_dict)

            # Create ISO 8601 timestamp with milliseconds and Z for UTC
            # Uses timezone-aware datetime object as utcfromtimestamp is deprecated.
            now = datetime.datetime.fromtimestamp(record.created, datetime.timezone.utc)
            log_record['timestamp'] = now.strftime('%Y-%m-%dT%H:%M:%S.%f')[:-3] + 'Z'

            # Ensure 'level' field is from 'levelname'
            log_record['level'] = record.levelname # record.levelname should always be present

            # Remove original fields that were renamed or reformatted to avoid duplication
            if 'asctime' in log_record: del log_record['asctime'] # if super() added it from fmt
            if 'levelname' in log_record: del log_record['levelname'] # if super() added it from fmt

            # Custom fields are ensured by ContextFilter to be attributes on 'record'
            log_record['user_id'] = record.user_id
            log_record['chat_id'] = record.chat_id
            log_record['message_id'] = record.message_id

            # For debugging the specific child logger issue:
            # if record.name and DEFAULT_LOGGER_NAME + ".child_module" in record.name:
            #    print(f"Formatter - Child record '{record.name}': user_id={log_record['user_id']}, chat_id={log_record['chat_id']}, message_id={log_record['message_id']} (msg: {record.getMessage()})")


    # The format string tells the JsonFormatter which LogRecord attributes to consider.
    # We will manage renaming (e.g. levelname to level) and timestamp formatting in add_fields.
    # Include fields that python-json-logger might not pick by default or that we want to ensure are processed.
    # Standard fields like 'message', 'module', 'funcName', 'lineno' are generally auto-picked.
    # Redundant fields (like levelname, asctime) will be handled in add_fields.
    # exc_info is handled by python-json-logger automatically if record.exc_info is set.
    # Do not include %(exc_info)s in the format string directly, as it might conflict.
    formatter = CustomJsonFormatter(
        '%(message)s %(module)s %(funcName)s %(lineno)s %(user_id)s %(chat_id)s %(message_id)s %(levelname)s %(asctime)s',
        json_ensure_ascii=False
    )
    # No rename_fields here, handle it all in add_fields for clarity.

    # Create a single ContextFilter instance
    context_filter = ContextFilter()

    # Create console handler
    console_handler = logging.StreamHandler() # Outputs to stderr by default
    console_handler.setFormatter(formatter)
    console_handler.addFilter(context_filter) # Add filter to handler
    logger.addHandler(console_handler)

    # Determine log file path
    actual_log_file_path = log_file_path if log_file_path else DEFAULT_LOG_FILE_NAME

    # Create file handler with rotation
    file_handler = logging.handlers.RotatingFileHandler(
        actual_log_file_path, maxBytes=MAX_BYTES, backupCount=BACKUP_COUNT, encoding='utf-8'
    )
    file_handler.setFormatter(formatter)
    file_handler.addFilter(context_filter) # Add filter to handler
    logger.addHandler(file_handler)

    # Remove filter from logger if it was there, to avoid double filtering if code was partially run before
    # Though the initial clear of handlers should make this unnecessary.
    # However, if a filter was on the logger AND handlers, it might run twice.
    # For simplicity, filters are now only on handlers.
    for f in list(logger.filters): # Iterate over a copy
        if isinstance(f, ContextFilter): # Or check by specific instance if worried about other ContextFilters
            logger.removeFilter(f)


def get_logger(name=None):
    """
    Returns a logger instance.

    Args:
        name (str, optional): The name of the logger.
                              Defaults to the DEFAULT_LOGGER_NAME.

    Returns:
        logging.Logger: The logger instance.
    """
    if name:
        return logging.getLogger(name)
    return logging.getLogger(DEFAULT_LOGGER_NAME)

if __name__ == '__main__':
    # Example usage:
    setup_logging(log_level=logging.DEBUG, log_file_path="katana_events_test.log") # Use a different file for testing

    logger = get_logger() # This gets 'katana_logger'

    print(f"--- Logging examples to console and katana_events_test.log (if run directly) ---")

    # Basic log messages
    logger.debug("This is a debug message.")
    logger.info("This is an info message.")
    logger.warning("This is a warning message.")

    # Log message with extra context
    logger.info(
        "User action performed.",
        extra={"user_id": "user123", "chat_id": "chat789", "message_id": "msg001"}
    )

    # Log message with partial extra context
    logger.info(
        "System event occurred.",
        extra={"user_id": "system_user"}
    )

    # Log message with no extra context (should get defaults from ContextFilter)
    logger.info("General system status.")

    # Child logger - will propagate to katana_logger and use its handlers/formatters
    child_logger_name = DEFAULT_LOGGER_NAME + ".child_module"
    child_logger = get_logger(child_logger_name) # or logging.getLogger(child_logger_name)
    child_logger.info(
        "Message from child logger.",
        extra={"user_id": "user_child", "chat_id": "chat_child"}
    )

    # Error logging with exc_info
    try:
        x = 1 / 0
    except ZeroDivisionError:
        logger.error("Error dividing by zero!", exc_info=True, extra={"user_id": "error_user"})

    print(f"--- End of logging examples ---")
    print(f"Log output can be found in katana_events_test.log and console.")
    # To clean up, you might want to delete katana_events_test.log after checking
    # import os
    # if os.path.exists("katana_events_test.log"):
    #     # Before deleting, ensure handlers are closed if necessary, though setup_logging handles this for subsequent calls.
    #     # For a simple script like this, direct deletion is usually fine after script finishes.
    #     # os.remove("katana_events_test.log")
    #     pass
