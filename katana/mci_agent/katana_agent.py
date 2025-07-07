# katana_agent.py
import json
import time
import os
import logging

# Removed: from logging.handlers import RotatingFileHandler - now handled by setup_logger
import importlib.util
from pathlib import Path
from katana.utils.logging_config import (
    setup_logger,
)  # Import the new setup function
from datetime import (
    datetime,
)  # Removed timezone import as it's unused directly
import uuid
import traceback
import shutil

# Path Constants (Refactor Z)
BASE_DIR = Path(__file__).resolve().parent
COMMANDS_DIR = BASE_DIR / "commands"
LOGS_DIR = BASE_DIR / "logs"  # Base directory for logs
LOG_ARCHIVE_DIR = LOGS_DIR / "archive"
STATUS_DIR = BASE_DIR / "status"
MODULES_DIR = BASE_DIR / "modules"
PROCESSED_COMMANDS_DIR = BASE_DIR / "processed"

# Determine if running in development mode
IS_DEV_MODE = os.environ.get("ENV_MODE", "").lower() == "dev"

# Log file will be command_telemetry.log as per new requirements
LOG_FILE_NAME = "command_telemetry.log"
LOG_FILE = LOGS_DIR / LOG_FILE_NAME # Path object for the log file

COMMAND_FILE = (
    COMMANDS_DIR / "katana.commands.json"
)  # Not used by MCI agent, but defined for consistency perhaps
STATUS_FILE = STATUS_DIR / "agent_status.json"


# --- Initialize Logger using centralized configuration ---
# The actual logger object is now configured and retrieved via setup_logger.
# We still define a global 'logger' variable for the rest of the script to use.
# The setup_logger call will be made in main() or at script start if preferred.
# For now, just getting the logger by name. It will be configured in main().
logger = logging.getLogger("KatanaMCIAgent") # Default logger instance


# --- Default Structures for File Recovery ---
DEFAULT_COMMANDS = []  # An empty list for commands.json (the old single file)
DEFAULT_STATUS = {  # Default status content
    "status": "idle_restored_from_internal_default",
    "timestamp": None,
    "notes": "This status file was generated from an internal default structure.",
}

# --- Phase 2: Combat Cycle Functions ---


def ensure_command_id(command):
    if not isinstance(command, dict):
        return
    if "id" not in command or not command["id"]:
        command_uuid = str(uuid.uuid4())
        command["id"] = command_uuid


def execute_module(command):
    module_name = command.get("module")
    command_id = command.get("id")  # Get command_id for logging
    kwargs_from_command = command.get("args", {})
    if not isinstance(kwargs_from_command, dict):
        logger.warning(
            f"Args for module {module_name} is not a dictionary. Using empty kwargs.",
            extra={
                "command_id": command_id,
                "found_args": kwargs_from_command,
            },
        )
        kwargs_from_command = {}

    kwargs_from_command["command_id"] = command_id
    kwargs_from_command["command_type"] = command.get("type")

    logger.debug(
        f"Preparing to execute module '{module_name}'. Effective args: {kwargs_from_command}",
        extra={"command_id": command_id},
    )
    logger.info(f"Executing module '{module_name}'", extra={"command_id": command_id})

    module_file_path = MODULES_DIR / f"{module_name}.py"

    try:
        if not module_file_path.exists():
            err_msg = f"Module file not found: {module_file_path}"
            logger.error(err_msg, extra={"command_id": command_id})
            return {"status": "error", "message": err_msg}

        spec_name = module_file_path.stem
        spec = importlib.util.spec_from_file_location(spec_name, module_file_path)

        if spec is None:
            err_msg = f"Could not create module spec for {module_file_path}"
            logger.error(err_msg, extra={"command_id": command_id})
            return {"status": "error", "message": err_msg}

        mod = importlib.util.module_from_spec(spec)
        if mod is None:
            err_msg = f"Could not create module from spec for {module_file_path}"
            logger.error(err_msg, extra={"command_id": command_id})
            return {"status": "error", "message": err_msg}

        spec.loader.exec_module(mod)

        if hasattr(mod, "run") and callable(mod.run):
            module_result = mod.run(**kwargs_from_command)
            logger.info(
                f"Module '{module_name}' finished.",
                extra={"command_id": command_id, "raw_result": module_result},
            )

            if (
                isinstance(module_result, dict)
                and module_result.get("status") == "error"
            ):
                logger.error(
                    f"Module '{module_name}' reported error.",
                    extra={
                        "command_id": command_id,
                        "error_message": module_result.get(
                            "message", "No specific error message."
                        ),
                    },
                )
                return module_result
            elif module_result is False:  # Consider this an error state
                logger.error(
                    f"Module '{module_name}' returned False, indicating failure.",
                    extra={"command_id": command_id},
                )
                return {
                    "status": "error",
                    "message": "Module returned False, indicating failure.",
                }
            return {"status": "success", "result": module_result}
        else:
            err_msg = f"Module '{module_name}' does not have a callable 'run' function."
            logger.error(err_msg, extra={"command_id": command_id})
            return {"status": "error", "message": err_msg}

    except Exception as e:
        error_details = traceback.format_exc()
        err_msg = f"{type(e).__name__}: {e}"
        logger.error(
            f"Error executing module '{module_name}': {err_msg}",
            extra={"command_id": command_id, "traceback": error_details},
        )  # Changed to ERROR
        return {
            "status": "error",
            "message": err_msg,
            "traceback": error_details,
        }


# --- MCI Helper Functions ---
def load_commands():
    logger.debug("Entering load_commands function.")
    all_commands_with_paths = []
    if not COMMANDS_DIR.exists():
        logger.debug(
            f"Commands directory {COMMANDS_DIR} does not exist. No commands loaded."
        )
        return all_commands_with_paths

    json_files_found = list(COMMANDS_DIR.rglob("*.json"))
    logger.debug(
        f"Found {len(json_files_found)} potential JSON files in {COMMANDS_DIR}."
    )

    for json_file_path in json_files_found:
        logger.debug(f"Attempting to load command from: {json_file_path}")
        try:
            with open(json_file_path, "r", encoding="utf-8") as f:
                command_data = json.load(f)
            if not isinstance(command_data, dict):
                logger.warning(
                    f"Content of {json_file_path} is not a JSON object. Skipping.",
                    extra={"file_path": str(json_file_path)},
                )
                continue
            all_commands_with_paths.append((json_file_path, command_data))
            logger.debug(
                f"Successfully loaded command from {json_file_path}.",
                extra={"file_path": str(json_file_path)},
            )
        except json.JSONDecodeError as e:
            logger.warning(
                f"Malformed JSON in file {json_file_path}: {e}. Skipping.",
                extra={"file_path": str(json_file_path)},
            )  # Changed to WARNING
        except Exception as e_read:
            logger.warning(
                f"Error reading command file {json_file_path}: {e_read}. Skipping.",
                extra={"file_path": str(json_file_path)},
            )  # Changed to WARNING

    if all_commands_with_paths:
        logger.info(
            f"Loaded {len(all_commands_with_paths)} command(s) from individual files."
        )
    else:
        logger.debug("No command files loaded.")
    logger.debug("Exiting load_commands function.")
    return all_commands_with_paths


def move_to_processed(original_command_file_path, processed_command_data):
    try:
        relative_path = original_command_file_path.relative_to(COMMANDS_DIR)
        timestamp_str = datetime.utcnow().strftime("%Y%m%d_%H%M%S_%f")
        archive_file_name_base = original_command_file_path.stem
        archive_file_name = f"{archive_file_name_base}_{timestamp_str}{original_command_file_path.suffix}"
        dest_dir = PROCESSED_COMMANDS_DIR / relative_path.parent
        os.makedirs(dest_dir, exist_ok=True)
        archive_file_full_path = dest_dir / archive_file_name
        command_id = processed_command_data.get("id")

        with open(archive_file_full_path, "w", encoding="utf-8") as af:
            json.dump(processed_command_data, af, indent=2)

        original_command_file_path.unlink()

        logger.info(
            f"Command {original_command_file_path.name} processed and moved to {archive_file_full_path}",
            extra={"command_id": command_id},
        )
        return True
    except Exception as e:
        command_id = processed_command_data.get("id", "UnknownID_on_archive_error")
        logger.error(
            f"Could not move/archive command file {original_command_file_path}. Error: {e}.",
            extra={
                "command_id": command_id,
                "command_data": processed_command_data,
                "traceback": traceback.format_exc(),
            },
        )  # Changed to ERROR
        return False


# --- MCI Main Function ---
def main(loop=False, delay=5):
    global logger  # Ensure we are modifying the global logger instance
    # Update the setup_logger call to include dev_mode and use the new log file name.
    # LOG_FILE path object now correctly points to "command_telemetry.log" within LOGS_DIR.
    logger = setup_logger(
        logger_name="KatanaMCIAgent",
        log_file_path_str=str(LOG_FILE),
        level=logging.DEBUG,
        dev_mode=IS_DEV_MODE,  # Pass the dev_mode status
    )

    # LOGS_DIR parent directory for LOG_FILE is handled by setup_logger's Path.mkdir().
    # Other specific application directories still need to be ensured.
    dirs_to_create = [
        COMMANDS_DIR,
        LOG_ARCHIVE_DIR,
        STATUS_DIR,
        MODULES_DIR,
        PROCESSED_COMMANDS_DIR,
    ]
    # LOG_ARCHIVE_DIR was used for manual rotation, which is now replaced by RotatingFileHandler's backupCount.
    # We still create it if it's used for other purposes, but it's not for this handler's direct rotation.
    dirs_to_create = [
        COMMANDS_DIR,
        LOG_ARCHIVE_DIR,
        STATUS_DIR,
        MODULES_DIR,
        PROCESSED_COMMANDS_DIR,
    ]
    for d in dirs_to_create:
        try:
            os.makedirs(d, exist_ok=True)
            logger.debug(f"Ensured directory exists: {d}")
        except Exception as e:
            logger.critical(f"Could not create directory {d}: {e}")

    # --- File Recovery using Internal Defaults (Refactor Z: Log & Test) ---
    # restore_commands = False # Unused variable
    if not COMMANDS_DIR.exists() or not any(
        COMMANDS_DIR.iterdir()
    ):  # Check if commands dir is empty or missing for MCI
        # In MCI, COMMAND_FILE is not the single source. We check if COMMANDS_DIR is empty.
        # If COMMANDS_DIR is empty, there's nothing to restore in terms of a single file.
        # The agent will just report "No command files found".
        # However, if the *directory* COMMANDS_DIR is missing, it's created by makedirs above.
        # This section is more about STATUS_FILE now.
        pass  # No single COMMAND_FILE to restore in MCI from a default list.

    restore_status = False
    if not STATUS_FILE.exists():
        logger.info(
            f"{STATUS_FILE} is missing. Attempting restore from internal default."
        )  # Changed from print
        restore_status = True
    else:
        try:
            with open(STATUS_FILE, "r") as f:
                json.load(f)
        except json.JSONDecodeError:
            logger.warning(
                f"{STATUS_FILE} is corrupted (invalid JSON). Attempting restore from internal default."
            )  # Changed from print
            restore_status = True
        except Exception as e:
            logger.warning(
                f"Error checking {STATUS_FILE}: {e}. Attempting restore as precaution."
            )  # Changed from print
            restore_status = True

    if restore_status:
        try:
            status_to_write = DEFAULT_STATUS.copy()
            status_to_write["timestamp"] = datetime.utcnow().isoformat()

            with open(STATUS_FILE, "w") as f:
                json.dump(status_to_write, f, indent=2)
            logger.info(
                f"Successfully restored {STATUS_FILE} using internal default and updated timestamp."
            )  # Changed from print
            logger.info(
                f"Restored {STATUS_FILE} from internal default and updated timestamp."
            )  # Was log_event
        except Exception as e_copy_status:
            logger.critical(
                f"Failed to restore {STATUS_FILE} using internal default. Error: {e_copy_status}"
            )
            # Removed duplicate critical log
    # --- End File Recovery using Internal Defaults ---

    logger.info("Katana agent started (MCI Enabled).")
    run_once = not loop
    logger.debug(f"Agent main loop starting. Run once: {run_once}, Delay: {delay}s")

    while True:
        logger.debug("Start of main agent processing cycle.")
        try:
            commands_to_process_with_paths = load_commands()

            if not commands_to_process_with_paths:
                if run_once:
                    logger.info("No command files found to process for single run.")
                else:  # Continuous loop, no commands is normal
                    logger.debug("No command files found in this cycle.")
            else:
                logger.info(
                    f"Found {len(commands_to_process_with_paths)} command file(s) to process."
                )

            for (
                command_file_path,
                command_data,
            ) in commands_to_process_with_paths:
                logger.debug(
                    f"Preparing to process command from file: {command_file_path}"
                )
                if not isinstance(command_data, dict):
                    logger.warning(
                        f"Skipping invalid command data (not a dict) from file {command_file_path}",
                        extra={"file_path": str(command_file_path)},
                    )
                    try:
                        malformed_dir = PROCESSED_COMMANDS_DIR / "malformed"
                        os.makedirs(malformed_dir, exist_ok=True)
                        timestamp_mal = datetime.utcnow().strftime("%Y%m%d_%H%M%S_%f")
                        malformed_file_path = (
                            malformed_dir
                            / f"{command_file_path.name}_{timestamp_mal}.malformed"
                        )
                        shutil.move(str(command_file_path), str(malformed_file_path))
                        logger.info(
                            f"Moved malformed command file {command_file_path} to {malformed_file_path}",
                            extra={
                                "original_path": str(command_file_path),
                                "new_path": str(malformed_file_path),
                            },
                        )
                    except Exception as e_move_malformed:
                        logger.error(
                            f"Failed to move malformed command file {command_file_path}: {e_move_malformed}",
                            extra={"file_path": str(command_file_path)},
                        )
                    continue

                ensure_command_id(command_data)
                command_id_log = command_data.get("id", "N/A_after_ensure")
                logger.info(
                    f"Processing command, type: {command_data.get('type', 'N/A')}, file: {command_file_path.name}",
                    extra={"command_id": command_id_log},
                )
                logger.debug(
                    f"Full command data for command ID {command_id_log}: {command_data}"
                )

                success = False
                command_type = command_data.get("type")
                execution_summary_override = None

                if command_type == "trigger_module":
                    module_response = execute_module(command_data)
                    success = (
                        isinstance(module_response, dict)
                        and module_response.get("status") == "success"
                    )
                    if success:
                        # Capture success message from module if available
                        execution_summary_override = module_response.get("message")
                        if not execution_summary_override and isinstance(
                            module_response.get("result"), dict
                        ):
                            execution_summary_override = module_response.get(
                                "result", {}
                            ).get("message")
                        if not execution_summary_override and isinstance(
                            module_response.get("result"), str
                        ):
                            execution_summary_override = module_response.get("result")
                    else:  # Module failed
                        execution_summary_override = module_response.get(
                            "message", "Module execution failed."
                        )
                elif (
                    command_type == "log_event"
                ):  # This command type itself is for logging
                    logger.info(
                        command_data.get(
                            "message",
                            "No message for log_event command",  # Removed unnecessary f-string
                        ),
                        extra={"command_id": command_id_log},
                    )
                    success = True
                elif command_type == "status_check":
                    try:
                        with open(STATUS_FILE, "w") as f:
                            json.dump(
                                {
                                    "status": "active",
                                    "timestamp": datetime.utcnow().isoformat(),
                                    "last_command_id": command_id_log,
                                },
                                f,
                                indent=2,
                            )
                        logger.info(
                            f"Status checked. Agent active.",
                            extra={"command_id": command_id_log},
                        )
                        success = True
                        execution_summary_override = (
                            "Status checked and agent_status.json updated."
                        )
                    except Exception as e_status:
                        logger.error(
                            f"Error updating status file: {e_status}",
                            extra={"command_id": command_id_log},
                        )
                        success = False
                        execution_summary_override = (
                            f"Failed to update status file: {e_status}"
                        )
                else:
                    logger.warning(
                        f"Unknown or unhandled command type: '{command_type}'",
                        extra={"command_id": command_id_log},
                    )
                    success = False
                    execution_summary_override = f"Unknown command type: {command_type}"

                command_data["executed_at"] = datetime.utcnow().isoformat()
                command_data["status"] = "done" if success else "failed"

                if execution_summary_override:
                    command_data["execution_summary"] = execution_summary_override
                elif (
                    "execution_summary" not in command_data
                ):  # Ensure execution_summary exists
                    command_data["execution_summary"] = (
                        "Successfully processed."
                        if success
                        else "Processing failed or type unhandled."  # noqa: F541
                    )

                # Log final status before moving
                log_level = logging.INFO if success else logging.ERROR
                logger.log(
                    log_level,
                    f"Command processing finished. Status: {command_data['status']}",
                    extra={
                        "command_id": command_id_log,
                        "summary": command_data["execution_summary"],
                    },
                )

                move_to_processed(command_file_path, command_data)

        except Exception as e_loop:
            # For exceptions in the main loop, command_id might not be directly available
            # or relevant for all log messages.
            logger.critical(
                f"CRITICAL_ERROR in main agent loop: {e_loop}",
                extra={"traceback": traceback.format_exc()},
            )
            if loop:
                logger.debug(
                    f"Main loop exception. Sleeping for {delay} seconds before retry."
                )
                time.sleep(delay)

        if run_once:
            logger.info("Agent single run complete (MCI).")
            logger.debug("Exiting main loop as run_once is True.")
            break

        logger.debug(
            f"End of main agent processing cycle. Sleeping for {delay} seconds."
        )
        time.sleep(delay)

    # --- Sample logs for review ---
    logger.debug(
        "This is a sample debug message for review.",  # No f-string needed
        extra={
            "command_id": "test_review_cmd_001",
            "detail": "some_debug_info",
        },
    )
    logger.info(
        "This is a sample info message for review.",  # No f-string needed
        extra={"command_id": "test_review_cmd_001"},
    )
    logger.warning(
        "This is a sample warning message.",  # No f-string needed
        extra={"command_id": "test_review_cmd_001", "warning_code": "W005"},
    )
    logger.error(
        "This is a sample error message, without exc_info.",  # No f-string needed
        extra={
            "command_id": "test_review_cmd_001",
            "error_source": "manual_test",
        },
    )
    try:
        _ = 1 / 0  # Assign to _ to indicate 'x' is unused
    except ZeroDivisionError:
        logger.error(
            "Sample error with exception after attempted division by zero.",  # No f-string needed
            exc_info=True,
            extra={
                "command_id": "test_review_cmd_001",
                "operation": "division_test",
            },
        )
        logger.critical(
            "Sample critical message following an exception.",  # No f-string needed
            extra={
                "command_id": "test_review_cmd_001",
                "status": "unstable_maybe",
            },
        )
    # --- End of sample logs for review ---

    logger.info(
        "Katana agent stopped."  # No f-string needed
    )  # This will be the last message if run_once is true and sample logs are added before this.


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Katana Agent - Combat Cycle")
    parser.add_argument(
        "--loop", action="store_true", help="Run agent in a continuous loop."
    )
    parser.add_argument(
        "--delay", type=int, default=5, help="Delay in seconds for loop mode."
    )
    args = parser.parse_args()

    main(loop=args.loop, delay=args.delay)
