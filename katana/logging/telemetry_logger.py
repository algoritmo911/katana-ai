import json
import os
from datetime import datetime, timezone
from supabase import create_client, Client

# Supabase configuration
SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")
SUPABASE_TABLE = "command_logs"

# Local log file path
LOG_FILE_PATH = "logs/command_telemetry.log"

# Initialize Supabase client
supabase: Client = None
if SUPABASE_URL and SUPABASE_KEY:
    try:
        supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
    except Exception as e:
        print(f"Error initializing Supabase client: {e}")
        supabase = None


def ensure_log_directory_exists():
    """Ensures that the directory for the log file exists."""
    log_dir = os.path.dirname(LOG_FILE_PATH)
    if not os.path.exists(log_dir):
        os.makedirs(log_dir)


def make_serializable(data):
    """Helper to make arguments JSON serializable."""
    if isinstance(data, (list, tuple)):
        return [make_serializable(item) for item in data]
    elif isinstance(data, dict):
        return {k: make_serializable(v) for k, v in data.items()}
    elif isinstance(data, (int, float, str, bool)) or data is None:
        return data
    else:
        try:
            json.dumps(data)
            return data
        except (TypeError, OverflowError):
            return str(data)


def write_to_supabase(log_entry: dict):
    """Writes a log entry to Supabase."""
    if not supabase:
        return

    try:
        response = supabase.table(SUPABASE_TABLE).insert(log_entry).execute()
        # In v2, a failed insert returns a response with an empty `data` list and an `error` object
        if not response.data and hasattr(response, "error") and response.error:
            print(f"Error writing to Supabase: {response.error}")
    except Exception as e:
        print(f"Failed to write to Supabase: {e}")


def write_to_local_log(log_entry: dict):
    """Writes a log entry to a local file."""
    try:
        with open(LOG_FILE_PATH, "a") as f:
            f.write(json.dumps(log_entry) + "\n")
    except Exception as e:
        print(f"Error writing to telemetry log: {e}")
        print(f"Original log entry: {log_entry}")


def log_command_telemetry(
    command_name: str,
    args: tuple,
    kwargs: dict,
    success: bool,
    result: any = None,
    error: Exception = None,
    execution_time: float = None,
    user: str = "unknown",
    start_time_iso: str = None,
):
    """
    Logs telemetry data for a command execution to local file and Supabase.
    """
    ensure_log_directory_exists()

    log_entry = {
        "log_event_timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "command_start_time_utc": start_time_iso if start_time_iso else "N/A",
        "user": user,
        "command_name": command_name,
        "arguments": {
            "args": make_serializable(list(args)),
            "kwargs": make_serializable(kwargs),
        },
        "success": success,
        "execution_time_seconds": execution_time,
    }

    if success:
        log_entry["result_type"] = type(result).__name__
    else:
        log_entry["error"] = (
            {"type": type(error).__name__, "message": str(error)} if error else None
        )

    # Write to local log file
    write_to_local_log(log_entry)

    # Write to Supabase
    write_to_supabase(log_entry)


if __name__ == "__main__":
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
        start_time_iso=current_time_iso,
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
            start_time_iso=error_time_iso,
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
        start_time_iso=another_cmd_time_iso,
    )
    print("Example logs written.")
