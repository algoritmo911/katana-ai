import json
import os
from datetime import datetime, timezone # Added timezone

LOG_FILE_PATH = "logs/command_telemetry.log"

def ensure_log_directory_exists():
    """Ensures that the directory for the log file exists."""
    log_dir = os.path.dirname(LOG_FILE_PATH)
    if not os.path.exists(log_dir):
        os.makedirs(log_dir)

def log_command_telemetry(command_name: str, args: tuple, kwargs: dict, success: bool, result: any = None, error: Exception = None, execution_time: float = None, user: str = "unknown", start_time_iso: str = None):
    """
    Logs telemetry data for a command execution.

    Args:
        command_name (str): The name of the command.
        args (tuple): Positional arguments passed to the command.
        kwargs (dict): Keyword arguments passed to the command.
        success (bool): Whether the command executed successfully.
        result (any, optional): The result of the command execution if successful. Defaults to None.
        error (Exception, optional): The exception raised if the command failed. Defaults to None.
        execution_time (float, optional): The time taken for the command to execute in seconds. Defaults to None.
        user (str, optional): The username of the user executing the command. Defaults to "unknown".
        start_time_iso (str, optional): The ISO format UTC timestamp of when the command started. Defaults to None.
    """
    ensure_log_directory_exists()

    # Helper to make arguments JSON serializable
    def make_serializable(data):
        if isinstance(data, (list, tuple)):
            return [make_serializable(item) for item in data]
        elif isinstance(data, dict):
            return {k: make_serializable(v) for k, v in data.items()}
        elif isinstance(data, (int, float, str, bool)) or data is None:
            return data
        else:
            try:
                # Try to json encode it directly, if it fails, convert to string
                json.dumps(data)
                return data
            except (TypeError, OverflowError):
                return str(data)

    log_entry = {
        "log_event_timestamp_utc": datetime.now(timezone.utc).isoformat(), # Time the log entry is created
        "command_start_time_utc": start_time_iso if start_time_iso else "N/A", # Actual command start time
        "user": user,
        "command_name": command_name,
        "arguments": {
            "args": make_serializable(list(args)), # Convert tuple to list for JSON, then make serializable
            "kwargs": make_serializable(kwargs)
        },
        "success": success,
        "execution_time_seconds": execution_time
    }

    if success:
        # Avoid logging potentially large or sensitive results by default.
        # Consider adding a configuration for verbosity later if needed.
        log_entry["result_type"] = type(result).__name__
    else:
        log_entry["error"] = {
            "type": type(error).__name__,
            "message": str(error)
        } if error else None

    try:
        with open(LOG_FILE_PATH, "a") as f:
            f.write(json.dumps(log_entry) + "\n")
    except Exception as e:
        # Fallback logging in case of issues with writing to the telemetry log
        print(f"Error writing to telemetry log: {e}")
        print(f"Original log entry: {log_entry}")

if __name__ == '__main__':
    # Example usage (for testing the logger directly)
    ensure_log_directory_exists()
    print(f"Logging to: {os.path.abspath(LOG_FILE_PATH)}")

    # Example usage (for testing the logger directly)
    current_time_iso = datetime.now(timezone.utc).isoformat()
    log_command_telemetry(
        command_name="test_command",
        args=(1, "arg2"),
        kwargs={"kwarg1": True},
        success=True,
        result="Test success",
        execution_time=0.123,
        user="test_user",
        start_time_iso=current_time_iso
    )
    try:
        raise ValueError("Something went wrong")
    except ValueError as e:
        error_time_iso = datetime.now(timezone.utc).isoformat()
        log_command_telemetry(
            command_name="error_command",
            args=(),
            kwargs={},
            success=False,
            error=e,
            execution_time=0.05,
            user="test_user_error",
            start_time_iso=error_time_iso
        )

    another_cmd_time_iso = datetime.now(timezone.utc).isoformat()
    log_command_telemetry(
        command_name="another_command",
        args=("data",),
        kwargs={},
        success=True,
        result={"key": "value"},
        execution_time=0.002,
        user="test_user_another",
        start_time_iso=another_cmd_time_iso
    )
    print("Example logs written.")
