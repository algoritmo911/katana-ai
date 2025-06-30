# src/telemetry/command_telemetry.py
import json
import logging
import os
from datetime import datetime, timezone
from typing import Dict, Any, Optional

# Configure a dedicated logger for telemetry
# This allows telemetry logs to be handled (e.g., written to a specific file)
# independently of the main application's logging configuration if needed.
telemetry_logger = logging.getLogger('CommandTelemetry')
telemetry_logger.setLevel(logging.INFO) # Default level, can be configured

# Ensure the logger doesn't propagate to the root logger if we want separate handling.
# telemetry_logger.propagate = False # Uncomment if specific file handling is added below and no console output is desired from this logger.

DEFAULT_LOG_FILE = 'command_telemetry.log'
_log_file_path: Optional[str] = None
_file_handler: Optional[logging.FileHandler] = None

def configure_telemetry_logging(log_file: str = DEFAULT_LOG_FILE, level: int = logging.INFO, enable_console_logging: bool = True):
    """
    Configures the telemetry logger, optionally writing to a specified file.
    """
    global _log_file_path, _file_handler, telemetry_logger

    _log_file_path = os.path.abspath(log_file)
    telemetry_logger.setLevel(level)

    # Remove existing file handler if any, to prevent duplicate logs on re-configuration
    if _file_handler:
        telemetry_logger.removeHandler(_file_handler)
        _file_handler.close()
        _file_handler = None

    # Create directory if it doesn't exist
    log_dir = os.path.dirname(_log_file_path)
    if log_dir: # Ensure log_dir is not empty (e.g. if log_file is just a filename)
        os.makedirs(log_dir, exist_ok=True)

    # Add a file handler to write logs to the specified file
    # Using a rotating file handler could be an option for production to manage log file sizes.
    # For now, a simple FileHandler is used.
    _file_handler = logging.FileHandler(_log_file_path, mode='a', encoding='utf-8') # 'a' for append
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    _file_handler.setFormatter(formatter)
    telemetry_logger.addHandler(_file_handler)

    if enable_console_logging:
        # If console logging is also desired for telemetry events (e.g., for debugging)
        # and it's not already handled by a root logger configuration.
        # This assumes that if the root logger is configured, it might already output these.
        # For simplicity, we'll add a StreamHandler if no other handlers are present or if explicitly asked.
        if not telemetry_logger.handlers or (len(telemetry_logger.handlers) == 1 and telemetry_logger.handlers[0] == _file_handler) : # only file handler or none
            console_handler = logging.StreamHandler()
            console_handler.setFormatter(formatter) # Use the same format
            telemetry_logger.addHandler(console_handler)
            telemetry_logger.info(f"Telemetry console logging enabled.")


    telemetry_logger.info(f"Command Telemetry configured. Logging to: {_log_file_path}")


def log_command_event(event_type: str, command_id: str, details: Dict[str, Any], success: Optional[bool] = None):
    """
    Logs a command event.

    Args:
        event_type: Type of event (e.g., "command_received", "command_processed", "task_started", "task_completed").
        command_id: A unique identifier for the command or task.
        details: A dictionary containing event-specific information.
        success: Optional boolean indicating success or failure of an operation.
    """
    if not _file_handler and not any(isinstance(h, logging.StreamHandler) for h in telemetry_logger.handlers):
        # Auto-configure with default if not configured, primarily for standalone use or testing.
        # In a full app, configure_telemetry_logging should be called explicitly during setup.
        print("Warning: Telemetry logging not configured. Using default console and file logger.")
        configure_telemetry_logging()


    log_entry = {
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "event_type": event_type,
        "command_id": command_id,
        "details": details
    }
    if success is not None:
        log_entry["success"] = success

    # Log as a JSON string for structured logging.
    telemetry_logger.info(json.dumps(log_entry))


# --- Example Usage ---
if __name__ == '__main__':
    # Configure logging (this would typically be done at application startup)
    # Writing to a local file 'command_telemetry.log' in the current directory
    configure_telemetry_logging(log_file="command_telemetry.log", level=logging.DEBUG, enable_console_logging=True)

    telemetry_logger.info("Command Telemetry test started.") # General info log

    # Simulate receiving a command
    cmd_id_1 = "cmd_20240315_001"
    log_command_event(
        event_type="command_received",
        command_id=cmd_id_1,
        details={"source": "telegram_bot", "user_id": "user123", "raw_command": "/do_something arg1"}
    )

    # Simulate starting a task related to the command
    log_command_event(
        event_type="task_execution_started",
        command_id=cmd_id_1,
        details={"task_name": "process_data", "params": {"input_file": "data.csv"}}
    )

    # Simulate task completion (success)
    log_command_event(
        event_type="task_execution_completed",
        command_id=cmd_id_1,
        details={"task_name": "process_data", "output": "results.json", "duration_ms": 1250},
        success=True
    )

    # Simulate another command that fails
    cmd_id_2 = "cmd_20240315_002"
    log_command_event(
        event_type="command_received",
        command_id=cmd_id_2,
        details={"source": "api_call", "api_key_partial": "sk_...xyz", "request_payload": {"action": "update_db"}}
    )
    log_command_event(
        event_type="database_update_failed",
        command_id=cmd_id_2,
        details={"error_code": 500, "message": "Database connection timeout"},
        success=False
    )

    telemetry_logger.info(f"Command Telemetry test finished. Check '{_log_file_path}'.")

    # Example of how to read and print the log file content (for verification)
    if _log_file_path and os.path.exists(_log_file_path):
        print(f"\n--- Content of '{_log_file_path}' ---")
        try:
            with open(_log_file_path, 'r', encoding='utf-8') as f:
                for line in f:
                    print(line.strip())
        except Exception as e:
            print(f"Error reading log file: {e}")
    else:
        print(f"Log file '{_log_file_path}' not found or not configured for file output.")
