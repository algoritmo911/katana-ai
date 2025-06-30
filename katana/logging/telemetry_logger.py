import json
import os
import logging
import logging.handlers
from datetime import datetime, timezone

# Configuration
LOG_FILE_PATH = "logs/command_telemetry.log"
MAX_LOG_SIZE_BYTES = 5 * 1024 * 1024  # 5 MB
BACKUP_COUNT = 5
TELEMETRY_LOGGER_NAME = "CommandTelemetryLogger"

class JsonFormatter(logging.Formatter):
    """
    Formats log records as JSON objects.
    """
    def format(self, record):
        # record.msg is expected to be a dictionary
        if isinstance(record.msg, dict):
            log_obj = record.msg
        else:
            # Fallback if record.msg is not a dict (should not happen with current usage)
            log_obj = {"message": record.getMessage()}

        # Add standard logging attributes if desired, e.g., logger name, level
        # log_obj['logger_name'] = record.name
        # log_obj['level'] = record.levelname
        return json.dumps(log_obj)

def ensure_log_directory_exists():
    """Ensures that the directory for the log file exists."""
    log_dir = os.path.dirname(LOG_FILE_PATH)
    if not os.path.exists(log_dir):
        try:
            os.makedirs(log_dir)
        except OSError as e:
            # Handle potential race condition if directory is created by another process
            if not os.path.isdir(log_dir):
                raise # Reraise if it's not a directory or other error

def _setup_logger():
    """Sets up and returns the telemetry logger instance."""
    ensure_log_directory_exists()

    logger = logging.getLogger(TELEMETRY_LOGGER_NAME)
    logger.setLevel(logging.INFO) # Set the desired logging level

    # Prevent multiple handlers if this function is somehow called more than once
    # or if other loggers (e.g. root logger) are configured to propagate.
    if logger.hasHandlers():
        logger.handlers.clear()

    handler = logging.handlers.RotatingFileHandler(
        LOG_FILE_PATH,
        maxBytes=MAX_LOG_SIZE_BYTES,
        backupCount=BACKUP_COUNT,
        encoding='utf-8' # Good practice to specify encoding
    )
    handler.setFormatter(JsonFormatter())
    logger.addHandler(handler)

    # Do not propagate to parent loggers (like the root logger)
    # to avoid duplicate logging if the root logger is also configured,
    # and to ensure only our JSON format is used for this specific logger.
    logger.propagate = False

    return logger

# Initialize the logger instance when the module is loaded
telemetry_logger = _setup_logger()

# Helper to make arguments JSON serializable
def _make_serializable(data):
    if isinstance(data, (list, tuple)):
        return [_make_serializable(item) for item in data]
    elif isinstance(data, dict):
        return {k: _make_serializable(v) for k, v in data.items()}
    elif isinstance(data, (int, float, str, bool)) or data is None:
        return data
    else:
        try:
            # Try to json encode it directly, if it fails, convert to string
            json.dumps(data) # This is just a check, not for actual serialization here
            return data
        except (TypeError, OverflowError):
            return str(data)


def log_command_telemetry(command_name: str, args: tuple, kwargs: dict, success: bool, result: any = None, error: Exception = None, execution_time: float = None):
    """
    Logs telemetry data for a command execution using the configured logger.

    Args:
        command_name (str): The name of the command.
        args (tuple): Positional arguments passed to the command.
        kwargs (dict): Keyword arguments passed to the command.
        success (bool): Whether the command executed successfully.
        result (any, optional): The result of the command execution if successful. Defaults to None.
        error (Exception, optional): The exception raised if the command failed. Defaults to None.
        execution_time (float, optional): The time taken for the command to execute in seconds. Defaults to None.
    """
    log_entry = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "command_name": command_name,
        "arguments": {
            "args": _make_serializable(list(args)), # Convert tuple to list for JSON
            "kwargs": _make_serializable(kwargs)
        },
        "success": success,
        "execution_time_seconds": execution_time
    }

    if success:
        log_entry["result_type"] = type(result).__name__
    else:
        log_entry["error"] = {
            "type": type(error).__name__,
            "message": str(error)
        } if error else None

    try:
        telemetry_logger.info(log_entry)
    except Exception as e:
        # Fallback logging in case of issues with the logger itself
        # (e.g., file permission issues not caught by RotatingFileHandler setup)
        # This should be rare.
        fallback_log_message = f"Error using telemetry_logger: {e}. Original log entry: {json.dumps(log_entry)}"
        print(fallback_log_message)
        # Optionally, try to write to a different fallback log or stderr
        try:
            with open("logs/telemetry_fallback.log", "a") as fb_log:
                fb_log.write(datetime.now(timezone.utc).isoformat() + " " + fallback_log_message + "\n")
        except Exception:
            pass # Avoid further exceptions during fallback

if __name__ == '__main__':
    # Example usage (for testing the logger directly)
    print(f"Logging to: {os.path.abspath(LOG_FILE_PATH)}")
    print(f"Logger configured: {telemetry_logger.name} with handlers: {telemetry_logger.handlers}")

    # Test with various command scenarios
    log_command_telemetry("test_command_1", (1, "arg2_val"), {"kwarg1": True, "kwarg2": "another"}, True, result="Test success", execution_time=0.123)

    try:
        raise ValueError("Something went wrong during execution")
    except ValueError as e:
        log_command_telemetry("error_command_example", ("param_x",), {"attempt": 1}, False, error=e, execution_time=0.05)

    log_command_telemetry("another_command_run", ("data_item", [1,2,3]), {}, True, result={"key": "value_pair", "nested": {"a":1}}, execution_time=0.002)

    # Example of a command with non-serializable data (should be handled by _make_serializable)
    class NonSerializableObject:
        def __str__(self):
            return "<NonSerializableObject instance>"
    log_command_telemetry("serializable_test_cmd", (NonSerializableObject(),), {}, True, result="OK", execution_time=0.01)


    print("Example logs written. Check the log file and potential rotated files if volume is high.")
    print("To test rotation, you might need to run this script multiple times or log more data.")
    # Forcing rotation for a quick test:
    # current_max_bytes = telemetry_logger.handlers[0].maxBytes
    # telemetry_logger.handlers[0].maxBytes = 100 # Temporarily set very small size
    # for i in range(20):
    #     log_command_telemetry(f"rotation_test_cmd_{i}", (i,), {}, True, result=f"item {i}", execution_time=0.001)
    # telemetry_logger.handlers[0].maxBytes = current_max_bytes # Reset
    # print("Rotation test logs (if any) written.")
