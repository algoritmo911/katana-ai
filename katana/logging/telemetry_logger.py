import json
import os
from datetime import datetime, timezone
import uuid # Added for trace_id

LOG_FILE_PATH = "logs/command_telemetry.log"

def ensure_log_directory_exists():
    """Ensures that the directory for the log file exists."""
    log_dir = os.path.dirname(LOG_FILE_PATH)
    if not os.path.exists(log_dir):
        os.makedirs(log_dir)

def log_command_telemetry(
    command_name: str,
    args: tuple,
    kwargs: dict,
    success: bool,
    result: any = None,
    error: Exception = None,
    execution_time: float = None,
    user: any = "unknown", # Can be str or dict
    start_time_iso: str = None,
    trace_id: str = None,
    tags: dict = None
):
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
        user (any, optional): The user executing the command (e.g., system username string, or a dict with user_id/username for bot). Defaults to "unknown".
        start_time_iso (str, optional): The ISO format UTC timestamp of when the command started. Defaults to None.
        trace_id (str, optional): A unique identifier for this command invocation. Defaults to None.
        tags (dict, optional): Arbitrary key-value tags for analytics. Defaults to None.
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
        "trace_id": trace_id if trace_id else str(uuid.uuid4()),
        "log_event_timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "command_start_time_utc": start_time_iso if start_time_iso else "N/A",
        "user": make_serializable(user), # User info could be a dict
        "command_name": command_name,
        "arguments": {
            "args": make_serializable(list(args)),
            "kwargs": make_serializable(kwargs)
        },
        "success": success,
        "execution_time_seconds": execution_time
    }

    if tags is not None:
        log_entry["tags"] = make_serializable(tags)

    if success:
        log_entry["result"] = make_serializable(result)
    else:
        log_entry["error"] = {
            "type": type(error).__name__,
            "message": str(error),
            "details": make_serializable(getattr(error, 'args', None)) # Log error arguments if any
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
    trace_id_1 = str(uuid.uuid4())
    current_time_iso_1 = datetime.now(timezone.utc).isoformat()
    log_command_telemetry(
        command_name="test_command_with_tags",
        args=(1, "arg2"),
        kwargs={"kwarg1": True, "sensitive_data": "should_be_serialized_as_string_if_object"},
        success=True,
        result="Test success",
        execution_time=0.123,
        user={"id": 12345, "username": "test_tg_user"},
        start_time_iso=current_time_iso_1,
        trace_id=trace_id_1,
        tags={"category": "test", "priority": 1}
    )

    trace_id_2 = str(uuid.uuid4())
    try:
        err_arg1 = {"a": 1}
        err_arg2 = "some context"
        raise ValueError("Something went wrong", err_arg1, err_arg2)
    except ValueError as e:
        error_time_iso_2 = datetime.now(timezone.utc).isoformat()
        log_command_telemetry(
            command_name="error_command_detailed",
            args=(),
            kwargs={},
            success=False,
            error=e,
            execution_time=0.05,
            user="cli_user",
            start_time_iso=error_time_iso_2,
            trace_id=trace_id_2,
            tags={"source": "main_test"}
        )

    trace_id_3 = str(uuid.uuid4())
    another_cmd_time_iso_3 = datetime.now(timezone.utc).isoformat()
    log_command_telemetry(
        command_name="another_command_no_tags",
        args=("data",),
        kwargs={},
        success=True,
        result={"key": "value", "nested": {"num": 1, "text": "sample"}},
        execution_time=0.002,
        user="test_user_another",
        start_time_iso=another_cmd_time_iso_3,
        trace_id=trace_id_3
    )
    print("Example logs written.")
