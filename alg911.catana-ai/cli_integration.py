"""
Handles communication from the backend to the Katana CLI agent.
This module provides functions to invoke the CLI agent as a subprocess
and exchange command/response data by adding tasks and polling for their results.
"""

import subprocess
import json
import logging
from logging.handlers import RotatingFileHandler # Import for log rotation
import os
import sys # For sys.executable
import time
import re # For parsing task ID

# Define paths
_KATANA_AGENT_DIR = os.path.dirname(__file__) # Assumes this script is in alg911.catana-ai
LOG_DIR = os.path.join(_KATANA_AGENT_DIR, "logs")
BACKEND_LOG_FILE = os.path.join(LOG_DIR, "backend.log")
KATANA_AGENT_SCRIPT_PATH = os.path.join(_KATANA_AGENT_DIR, "katana_agent.py")
COMMANDS_FILE_PATH = os.path.join(_KATANA_AGENT_DIR, "katana.commands.json")

DEFAULT_POLL_TIMEOUT = 30  # seconds
DEFAULT_POLL_INTERVAL = 0.5  # seconds

# --- Centralized Logger Setup ---
def setup_backend_logger(logger_name, level=logging.INFO):
    """Sets up a logger that writes to backend.log with rotation."""
    logger_instance = logging.getLogger(logger_name)
    logger_instance.setLevel(level)

    # Prevent adding handlers multiple times if function is called repeatedly
    if not logger_instance.handlers:
        os.makedirs(LOG_DIR, exist_ok=True) # Ensure log directory exists

        # Rotating File Handler for backend.log
        file_handler = RotatingFileHandler(
            BACKEND_LOG_FILE,
            maxBytes=5*1024*1024,  # 5 MB
            backupCount=3,
            encoding='utf-8'
        )
        formatter = logging.Formatter('[%(asctime)s] [%(levelname)s] [%(name)s] [%(module)s.%(funcName)s:%(lineno)d] %(message)s',
                                      datefmt='%Y-%m-%dT%H:%M:%S%z')
        file_handler.setFormatter(formatter)
        logger_instance.addHandler(file_handler)

        # Optional: Add a StreamHandler for console output during development/debugging
        # console_handler = logging.StreamHandler(sys.stdout)
        # console_handler.setFormatter(formatter)
        # logger_instance.addHandler(console_handler)

    return logger_instance

# Configure logger for this module using the centralized setup
logger = setup_backend_logger(__name__, logging.DEBUG)

def _load_json_file(file_path: str, default_value=None):
    """
    Helper function to load a JSON file.
    Returns default_value if file not found or on JSON decode error.
    """
    if not os.path.exists(file_path):
        logger.warning(f"JSON file not found: {file_path}")
        return default_value
    try:
        with open(file_path, "r") as f:
            content = f.read()
            if not content.strip():
                logger.warning(f"JSON file is empty: {file_path}")
                return default_value
            return json.loads(content)
    except json.JSONDecodeError:
        logger.exception(f"Error decoding JSON from {file_path}")
        return default_value
    except Exception:
        logger.exception(f"Unexpected error loading JSON from {file_path}")
        return default_value

def send_command_to_cli(command_action: str, parameters: dict) -> dict:
    """
    Sends a command to the Katana CLI agent by adding it as a task
    via a subprocess call to `katana_agent.py addtask ...`.
    It then polls `katana.commands.json` for the task's completion and result.

    Args:
        command_action (str): The action name for the task (e.g., "status_katana").
        parameters (dict): A dictionary of parameters for the task.

    Returns:
        dict: A dictionary containing the response.
              Success: {"status": "success", "task_status": "completed" or "failed",
                        "result": task_result, "task_id": internal_task_id}
              Error:   {"status": "error", "message": "Error message details"}
    """
    logger.info(f"Sending command '{command_action}' with params {parameters} to Katana CLI via addtask.")

    # 1. Construct 'addtask' command arguments
    param_args = [f"{k}={v}" for k, v in parameters.items()]
    cli_command_args = ["addtask", command_action] + param_args

    full_subprocess_command = [sys.executable, KATANA_AGENT_SCRIPT_PATH] + cli_command_args

    logger.debug(f"Executing subprocess: {full_subprocess_command}")

    internal_task_id = None
    try:
        # 2. Execute katana_agent.py as a subprocess
        # The agent will run in non-interactive mode, execute addtask,
        # process tasks (including the one just added), and then exit.
        process = subprocess.run(
            full_subprocess_command,
            capture_output=True,
            text=True,
            timeout=15 # Timeout for the CLI agent to add the task and potentially process it.
                       # This is not the polling timeout for task completion.
        )
        logger.debug(f"Katana agent stdout:\n{process.stdout}")
        if process.stderr:
            logger.error(f"Katana agent stderr:\n{process.stderr}")

        if process.returncode != 0:
            return {
                "status": "error",
                "message": f"Katana agent script execution failed with return code {process.returncode}.",
                "stderr": process.stderr,
                "stdout": process.stdout
            }

        # 3. Parse stdout to get the internal_task_id
        # Expecting "CREATED_TASK_ID: <task_id>" from katana_agent.py's addtask command
        match = re.search(r"CREATED_TASK_ID:\s*([a-f0-9]+)", process.stdout)
        if match:
            internal_task_id = match.group(1)
            logger.info(f"Successfully added task. Katana internal_task_id: {internal_task_id}")
        else:
            logger.error(f"Could not parse CREATED_TASK_ID from Katana agent stdout: {process.stdout}")
            return {
                "status": "error",
                "message": "Could not determine task ID from Katana agent output.",
                "stdout": process.stdout
            }

    except subprocess.TimeoutExpired:
        logger.error(f"Subprocess execution for 'addtask' timed out.")
        return {"status": "error", "message": "Subprocess execution for 'addtask' timed out."}
    except Exception as e:
        logger.exception("An unexpected error occurred during subprocess execution.")
        return {"status": "error", "message": f"Subprocess execution error: {e}"}

    # 4. Poll for Task Completion
    logger.info(f"Polling for completion of task_id: {internal_task_id} in {COMMANDS_FILE_PATH}")
    start_time = time.time()
    while time.time() - start_time < DEFAULT_POLL_TIMEOUT:
        tasks = _load_json_file(COMMANDS_FILE_PATH, [])
        if not isinstance(tasks, list):
             logger.error(f"Commands file {COMMANDS_FILE_PATH} is not a list or is malformed. Polling failed.")
             return {"status": "error", "message": f"Commands file {COMMANDS_FILE_PATH} is malformed."}

        found_task = None
        for task in tasks:
            if isinstance(task, dict) and task.get("command_id") == internal_task_id:
                found_task = task
                break

        if found_task:
            task_status = found_task.get("status")
            logger.debug(f"Polling task {internal_task_id}: current status '{task_status}'.")
            if task_status == "completed":
                logger.info(f"Task {internal_task_id} completed successfully.")
                return {
                    "status": "success",
                    "task_status": "completed",
                    "result": found_task.get("result"),
                    "task_id": internal_task_id
                }
            elif task_status == "failed":
                logger.warning(f"Task {internal_task_id} failed.")
                return {
                    "status": "success", # The operation of polling was successful, but task failed
                    "task_status": "failed",
                    "result": found_task.get("result"), # Should contain error details
                    "task_id": internal_task_id
                }
            # If "pending" or "processing", continue polling
        else:
            # Task might not appear immediately if file system latency or very quick polling
            logger.debug(f"Task {internal_task_id} not yet found in commands file. Will retry.")

        time.sleep(DEFAULT_POLL_INTERVAL)

    logger.error(f"Timeout reached while polling for task {internal_task_id} completion.")
    return {"status": "error", "message": f"Timeout polling for task {internal_task_id} completion."}


if __name__ == '__main__':
    logger.info("Testing cli_integration.py module...")

    # Ensure katana_agent.py is executable:
    # In a real scenario, you might want to add `os.chmod(KATANA_AGENT_SCRIPT_PATH, 0o755)`
    # if it's not guaranteed to be executable. For now, assume it is.

    # Test 1: Send a 'status_katana' command (which is an action for a task)
    logger.info("\n--- Test 1: status_katana ---")
    response = send_command_to_cli(command_action="status_katana", parameters={})
    logger.info(f"Response from send_command_to_cli: {json.dumps(response, indent=2)}")

    # Test 2: Send an 'echo' command (as a task)
    logger.info("\n--- Test 2: echo task ---")
    response_echo = send_command_to_cli(
        command_action="echo",
        parameters={"text_to_echo": "Hello from cli_integration test"}
    )
    logger.info(f"Response from send_command_to_cli (echo): {json.dumps(response_echo, indent=2)}")

    # Test 3: Example of a command that might fail if not set up (e.g., a dummy one)
    # logger.info("\n--- Test 3: Fictional failing command ---")
    # response_fail = send_command_to_cli(command_action="non_existent_action_for_task", parameters={})
    # logger.info(f"Response from send_command_to_cli (fail_test): {json.dumps(response_fail, indent=2)}")

    # Test 4: Add a task that uses a specific parameter
    logger.info("\n--- Test 4: Add task with specific parameters ---")
    response_add_specific = send_command_to_cli(
        command_action="process_telegram_message",
        parameters={"chat_id": "123", "text": "/echo_tg Integration Test"}
    )
    logger.info(f"Response from send_command_to_cli (process_telegram_message): {json.dumps(response_add_specific, indent=2)}")

```
