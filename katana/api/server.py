import logging
import re
import json # Added
import uuid # Added
from pathlib import Path
from typing import List, Dict, Optional

from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel
import uvicorn

from katana.logger import (
    setup_logging as setup_katana_logging,
    get_logger as get_katana_logger,
    DEFAULT_LOGGER_NAME,
    DEFAULT_LOG_FILE_NAME
)

# Initialize FastAPI app
app = FastAPI()

# Use the default log file name from the logging_config module
LOG_FILE_PATH = Path(DEFAULT_LOG_FILE_NAME)

# Regex to parse log lines, made slightly more flexible for module names and messages
# Example: INFO 2023-10-27 10:00:00,123 - my.module - This is a message
LOG_LINE_REGEX = re.compile(
    r"^(DEBUG|INFO|WARNING|ERROR|CRITICAL)\s+"  # Level
    r"(\d{4}-\d{2}-\d{2}\s\d{2}:\d{2}:\d{2}(?:,\d{3})?)\s+-\s+"  # Timestamp (optional millis)
    r"([\w.-]+)\s+-\s+"  # Module name (allow dots and hyphens)
    r"(.*)$"  # Message
)

# Ensure Katana's main logging is set up when the server starts.
# This primarily ensures that if the API server is the first thing to run,
# katana_events.log is properly configured for other parts of a larger app
# or for the API server's own katana_logger usage if it were to use get_katana_logger().
# For the API server's own internal logs (uvicorn, fastapi), they have their own logging.
setup_katana_logging() # Ensures the main katana logger is configured
# Use katana's logger for API server specific messages, namespaced under the main logger
api_server_logger = get_katana_logger(DEFAULT_LOGGER_NAME + ".api")


# Pydantic model for the request body of /api/logs/level
class LogLevelRequest(BaseModel):
    level: str

@app.get("/api/logs/status", response_model=Dict[str, str])
async def get_log_status():
    """
    Returns the current logging status for the Katana application.
    """
    # Get the logger configured by setup_katana_logging
    katana_logger = logging.getLogger(DEFAULT_LOGGER_NAME)
    current_level_name = logging.getLevelName(katana_logger.getEffectiveLevel())
    return {
        "level": current_level_name,
        "log_file": str(LOG_FILE_PATH.resolve())
    }

@app.get("/api/logs", response_model=List[Dict[str, str]])
async def get_logs(
    page: int = Query(1, ge=1, description="Page number, 1-indexed"),
    limit: int = Query(100, ge=1, le=1000, description="Number of log entries per page"),
    level: Optional[str] = Query(None, description="Filter by log level (e.g., INFO, ERROR)"),
    search: Optional[str] = Query(None, description="Search term to filter log messages (case-insensitive)")
):
    """
    Reads and returns paginated log entries from the Katana application log file.
    Log entries are returned newest first by default after parsing all lines.
    """
    request_id = str(uuid.uuid4())
    api_context = {'user_id': 'api_user', 'chat_id': 'api_session', 'message_id': request_id}

    if not LOG_FILE_PATH.exists():
        api_server_logger.error(f"Log file not found: {LOG_FILE_PATH}", extra=api_context)
        raise HTTPException(status_code=404, detail=f"Log file not found: {LOG_FILE_PATH}")

    try:
        with open(LOG_FILE_PATH, "r", encoding="utf-8") as f:
            lines = f.readlines()
    except Exception as e:
        api_server_logger.error(f"Could not read log file {LOG_FILE_PATH}: {e}", exc_info=True, extra=api_context)
        raise HTTPException(status_code=500, detail=f"Could not read log file: {str(e)}")

    all_parsed_logs: List[Dict[str, str]] = []
    # Note: The LOG_LINE_REGEX is for parsing the old string format.
    # Now that logs are JSON, this parsing logic will need to change if this endpoint reads its own output.
    # For now, assuming it reads katana_events.log which is now JSON.
    # The parsing logic below will fail for JSON lines.
    # This endpoint needs to be updated to parse JSON log lines.
    # For this step, I'm only updating the logger calls *made by this server*.
    # The logic of *reading and parsing* the log file by this endpoint is a separate concern.
    # However, the logger.debug call below for unparsable lines should be updated.

    for line_number, line_content in enumerate(lines, start=1):
        line_content = line_content.strip()
        if not line_content: # Skip empty lines
            continue
        try:
            # Attempt to parse as JSON first
            log_entry = json.loads(line_content)
            # Ensure it has the fields we expect for display, even if it's a generic JSON log
            all_parsed_logs.append({
                "timestamp": log_entry.get("timestamp", "N/A"),
                "level": log_entry.get("level", log_entry.get("levelname", "N/A")), # Handle old levelname too
                "module": log_entry.get("module", "N/A"),
                "message": log_entry.get("message", str(log_entry)), # Fallback to string of whole log
                # Potentially add user_id, chat_id, message_id if they should be displayed
            })
        except json.JSONDecodeError:
            # Fallback to regex for old format or non-JSON lines, if any might still exist
            match = LOG_LINE_REGEX.match(line_content)
            if match:
                log_level_old, timestamp_old, module_old, message_old = match.groups()
                all_parsed_logs.append({
                    "timestamp": timestamp_old,
                    "level": log_level_old,
                    "module": module_old,
                    "message": message_old.strip()
                })
            elif line_content: # If it's not JSON and not matching old regex, log a debug message.
                # Use a more specific message_id for these parsing issues.
                parse_fail_ctx = {**api_context, 'message_id': f'{request_id}_parse_fail_line_{line_number}'}
                api_server_logger.debug(
                    f"Could not parse log line {line_number} as JSON or old format from {LOG_FILE_PATH}: '{line_content[:100]}...'",
                    extra=parse_fail_ctx
                )

    # Reverse logs to have newest first - apply after parsing and before filtering
    all_parsed_logs.reverse()

    # Apply filters
    filtered_logs = all_parsed_logs

    if level:
        normalized_level = level.upper()
        # We don't need to check if normalized_level is in logging._nameToLevel here for filtering,
        # as an exact string match is what's needed. Client should send valid levels.
        # If it's an invalid level string, it simply won't match anything.
        filtered_logs = [log for log in filtered_logs if log["level"] == normalized_level]
        api_server_logger.debug(f"Applied level filter: {normalized_level}, found {len(filtered_logs)} entries.")


    if search:
        normalized_search = search.lower()
        filtered_logs = [
            log for log in filtered_logs if normalized_search in log["message"].lower()
        ]
        api_server_logger.debug(f"Applied search filter: '{normalized_search}', found {len(filtered_logs)} entries after search.")

    # Apply pagination to the filtered list
    start_index = (page - 1) * limit
    end_index = start_index + limit
    paginated_logs = filtered_logs[start_index:end_index]

    api_server_logger.info(
        f"Serving {len(paginated_logs)} log entries. Page: {page}, Limit: {limit}, "
        f"Level Filter: {level or 'None'}, Search Filter: {search or 'None'}. "
        f"Total matched before pagination: {len(filtered_logs)}.",
        extra=api_context # Use the same request_id for this summary log
    )
    return paginated_logs

@app.post("/api/logs/level", response_model=Dict[str, str])
async def set_log_level(request: LogLevelRequest):
    """
    Sets the logging level for the Katana application.
    """
    requested_level_str = request.level.upper()
    request_id = str(uuid.uuid4())
    api_context = {'user_id': 'api_user', 'chat_id': 'api_set_level', 'message_id': request_id}


    # Validate if the provided level string is a valid log level name
    if requested_level_str not in logging._nameToLevel:
        api_server_logger.warning(f"Invalid log level requested: {request.level}", extra=api_context)
        raise HTTPException(
            status_code=400,
            detail=f"Invalid log level '{request.level}'. Valid levels are: {list(logging._nameToLevel.keys())}"
        )

    numeric_level = logging.getLevelName(requested_level_str)

    try:
        current_log_file_path = LOG_FILE_PATH
        if 'log_file_path' in setup_katana_logging.__code__.co_varnames:
             setup_katana_logging(log_level=numeric_level, log_file_path=str(current_log_file_path))
        else:
             setup_katana_logging(log_level=numeric_level)

        api_server_logger.info(f"Application log level set to {requested_level_str} by API request.", extra=api_context)
        return {"message": f"Log level set to {requested_level_str}"}
    except Exception as e:
        api_server_logger.error(f"Failed to set log level to {requested_level_str}: {e}", exc_info=True, extra=api_context)
        raise HTTPException(status_code=500, detail=f"Failed to set log level: {str(e)}")


if __name__ == "__main__":
    # The setup_katana_logging() call at global scope ensures the file handler for katana_events.log
    # is attached early. FastAPI/Uvicorn have their own logging for HTTP requests etc.
    # The api_server_logger is already an instance of the configured katana_logger.

    main_run_context = {'user_id': 'api_system', 'chat_id': 'api_startup', 'message_id': 'server_main_start'}
    api_server_logger.info(f"Katana API server starting. Log file expected at: {LOG_FILE_PATH.resolve()}", extra=main_run_context)
    api_server_logger.info("Access API documentation at http://localhost:8000/docs or http://localhost:8000/redoc", extra=main_run_context)

    # Uvicorn's log_level controls its own access logs, not Katana application logs.
    uvicorn.run(app, host="0.0.0.0", port=8000, log_level="info")

# Prerequisites for running this server:
# pip install fastapi uvicorn[standard]
# Ensure katana_events.log exists and has some content to view logs.
# Run with: python katana/api/server.py
