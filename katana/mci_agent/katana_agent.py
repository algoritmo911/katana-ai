# katana_agent.py
import json, time, os
import importlib.util
from pathlib import Path
from datetime import datetime # Still needed for move_to_processed and status updates
import uuid
import traceback
import shutil
import logging
from katana.logging_config import setup_logging, get_logger

# Initialize logger for this module
logger = get_logger(__name__)

# Path Constants (Refactor Z)
BASE_DIR = Path(__file__).resolve().parent
COMMANDS_DIR = BASE_DIR / "commands"
# LOGS_DIR and LOG_ARCHIVE_DIR removed, handled by central logging
STATUS_DIR = BASE_DIR / "status"
MODULES_DIR = BASE_DIR / "modules"
PROCESSED_COMMANDS_DIR = BASE_DIR / "processed"

COMMAND_FILE = COMMANDS_DIR / "katana.commands.json" # Not used by MCI agent, but defined for consistency perhaps
# LOG_FILE removed, handled by central logging
STATUS_FILE = STATUS_DIR / "agent_status.json"

# --- Default Structures for File Recovery ---
DEFAULT_COMMANDS = []  # An empty list for commands.json (the old single file)
DEFAULT_STATUS = {     # Default status content
    "status": "idle_restored_from_internal_default",
    "timestamp": None,
    "notes": "This status file was generated from an internal default structure."
}

# Old log_event and rotate_logs_if_needed functions are removed. Using centralized logging.

# --- Phase 2: Combat Cycle Functions ---

def ensure_command_id(command):
    if not isinstance(command, dict):
        return
    if "id" not in command or not command["id"]:
        command_uuid = str(uuid.uuid4())
        command["id"] = command_uuid

def execute_module(command):
    module_name = command.get("module")
    kwargs_from_command = command.get("args", {})
    if not isinstance(kwargs_from_command, dict):
        logger.warning(f"'args' for module {module_name} (command_id: {command.get('id')}) is not a dictionary. Using empty kwargs. Found: {kwargs_from_command}")
        kwargs_from_command = {}

    kwargs_from_command['command_id'] = command.get('id')
    kwargs_from_command['command_type'] = command.get('type')

    logger.info(f"Executing module '{module_name}' for command_id: {command.get('id')} with effective args: {kwargs_from_command}")

    module_file_path = MODULES_DIR / f"{module_name}.py"

    try:
        if not module_file_path.exists():
            err_msg = f"Module file not found: {module_file_path}"
            logger.error(f"{err_msg} for command_id: {command.get('id')}")
            return {"status": "error", "message": err_msg}

        spec_name = module_file_path.stem
        spec = importlib.util.spec_from_file_location(spec_name, module_file_path)

        if spec is None:
            err_msg = f"Could not create module spec for {module_file_path}"
            logger.error(f"{err_msg} (command_id: {command.get('id')})")
            return {"status": "error", "message": err_msg}

        mod = importlib.util.module_from_spec(spec)
        if mod is None:
            err_msg = f"Could not create module from spec for {module_file_path}"
            logger.error(f"{err_msg} (command_id: {command.get('id')})")
            return {"status": "error", "message": err_msg}

        spec.loader.exec_module(mod)

        if hasattr(mod, "run") and callable(mod.run):
            module_result = mod.run(**kwargs_from_command)
            logger.info(f"Module '{module_name}' (command_id: {command.get('id')}) finished. Raw result: {module_result}")

            if isinstance(module_result, dict) and module_result.get("status") == "error":
                logger.error(f"Module '{module_name}' (command_id: {command.get('id')}) reported error: {module_result.get('message', 'No specific error message.')}")
                return module_result
            elif module_result is False:
                return {"status": "error", "message": "Module returned False, indicating failure."}
            return {"status": "success", "result": module_result}
        else:
            err_msg = f"Module '{module_name}' does not have a callable 'run' function."
            logger.error(f"{err_msg} (command_id: {command.get('id')})")
            return {"status": "error", "message": err_msg}

    except Exception as e:
        error_details = traceback.format_exc()
        err_msg = f"{type(e).__name__}: {e}"
        logger.critical(f"Executing module '{module_name}' (command_id: {command.get('id')}): {err_msg}\nTraceback:\n{error_details}")
        return {"status": "error", "message": err_msg, "traceback": error_details}

# --- MCI Helper Functions ---
def load_commands():
    all_commands_with_paths = []
    if not COMMANDS_DIR.exists():
        # logger.info(f"Commands directory {COMMANDS_DIR} does not exist. No commands loaded.") # Can be noisy
        return all_commands_with_paths

    for json_file_path in COMMANDS_DIR.rglob("*.json"):
        try:
            with open(json_file_path, "r", encoding='utf-8') as f:
                command_data = json.load(f)
            if not isinstance(command_data, dict):
                logger.warning(f"Content of {json_file_path} is not a JSON object. Skipping.")
                continue
            all_commands_with_paths.append((json_file_path, command_data))
        except json.JSONDecodeError as e:
            logger.error(f"Malformed JSON in file {json_file_path}: {e}. Skipping.")
        except Exception as e_read:
            logger.error(f"Error reading command file {json_file_path}: {e_read}. Skipping.")

    if all_commands_with_paths:
        logger.info(f"Loaded {len(all_commands_with_paths)} command(s) from individual files.")
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

        with open(archive_file_full_path, "w", encoding='utf-8') as af:
            json.dump(processed_command_data, af, indent=2)

        original_command_file_path.unlink()

        logger.info(f"Command {original_command_file_path.name} (id: {processed_command_data.get('id')}) processed and moved to {archive_file_full_path}")
        return True
    except Exception as e:
        logger.critical(f"Could not move/archive command file {original_command_file_path}. Error: {e}. Command data: {processed_command_data}")
        logger.critical(f"Traceback for archival failure: {traceback.format_exc()}")
        return False

# --- MCI Main Function ---
def main(loop=False, delay=5):
    # Setup logging as the first step in main
    setup_logging(log_level=logging.INFO) # Or logging.DEBUG, etc.

    # LOGS_DIR and LOG_ARCHIVE_DIR are not created by agent anymore.
    dirs_to_create = [COMMANDS_DIR, STATUS_DIR, MODULES_DIR, PROCESSED_COMMANDS_DIR]
    for d in dirs_to_create:
        try:
            os.makedirs(d, exist_ok=True)
        except Exception as e:
            logger.critical(f"Could not create directory {d}: {e}") # Changed from print

    # --- File Recovery using Internal Defaults (Refactor Z: Log & Test) ---
    # restore_commands = False # This variable was unused.
    if not COMMANDS_DIR.exists() or not any(COMMANDS_DIR.iterdir()): # Check if commands dir is empty or missing for MCI
        # In MCI, COMMAND_FILE is not the single source. We check if COMMANDS_DIR is empty.
        # If COMMANDS_DIR is empty, there's nothing to restore in terms of a single file.
        # The agent will just report "No command files found".
        # However, if the *directory* COMMANDS_DIR is missing, it's created by makedirs above.
        # This section is more about STATUS_FILE now.
        pass # No single COMMAND_FILE to restore in MCI from a default list.

    restore_status = False
    if not STATUS_FILE.exists():
        logger.info(f"{STATUS_FILE} is missing. Attempting restore from internal default.")
        restore_status = True
    else:
        try:
            with open(STATUS_FILE, 'r') as f:
                json.load(f)
        except json.JSONDecodeError:
            logger.warning(f"{STATUS_FILE} is corrupted (invalid JSON). Attempting restore from internal default.")
            restore_status = True
        except Exception as e:
            logger.warning(f"Error checking {STATUS_FILE}: {e}. Attempting restore as precaution.")
            restore_status = True

    if restore_status:
        try:
            status_to_write = DEFAULT_STATUS.copy()
            status_to_write["timestamp"] = datetime.utcnow().isoformat()

            with open(STATUS_FILE, 'w') as f:
                json.dump(status_to_write, f, indent=2)
            logger.info(f"Successfully restored {STATUS_FILE} using internal default and updated timestamp.")
        except Exception as e_copy_status:
            logger.critical(f"Failed to restore {STATUS_FILE} using internal default. Error: {e_copy_status}")
    # --- End File Recovery using Internal Defaults ---

    logger.info("Katana agent started (MCI Enabled).")
    run_once = not loop

    while True:
        try:
            commands_to_process_with_paths = load_commands()

            if not commands_to_process_with_paths:
                if run_once:
                    logger.info("No command files found to process.")
            else:
                logger.info(f"Found {len(commands_to_process_with_paths)} command file(s) to process.")

            for command_file_path, command_data in commands_to_process_with_paths:
                if not isinstance(command_data, dict):
                    logger.warning(f"Skipping invalid command data (not a dict) from file {command_file_path}")
                    try:
                        malformed_dir = PROCESSED_COMMANDS_DIR / "malformed"
                        os.makedirs(malformed_dir, exist_ok=True)
                        timestamp_mal = datetime.utcnow().strftime("%Y%m%d_%H%M%S_%f")
                        malformed_file_path = malformed_dir / f"{command_file_path.name}_{timestamp_mal}.malformed"
                        shutil.move(str(command_file_path), str(malformed_file_path))
                        logger.info(f"Moved malformed command file {command_file_path} to {malformed_file_path}")
                    except Exception as e_move_malformed:
                        logger.error(f"Failed to move malformed command file {command_file_path}: {e_move_malformed}")
                    continue

                ensure_command_id(command_data)
                command_id_log = command_data.get('id', 'N/A_after_ensure')
                logger.info(f"Processing command_id: {command_id_log}, type: {command_data.get('type', 'N/A')} from file: {command_file_path.name}")

                success = False
                command_type = command_data.get("type")
                execution_summary_override = None

                if command_type == "trigger_module":
                    module_response = execute_module(command_data)
                    success = isinstance(module_response, dict) and module_response.get("status") == "success"
                    if success:
                        # Capture success message from module if available
                        execution_summary_override = module_response.get("message") # If module returns a message field in its result
                        if not execution_summary_override and isinstance(module_response.get("result"), dict):
                             execution_summary_override = module_response.get("result", {}).get("message") # common pattern for modules
                        if not execution_summary_override and isinstance(module_response.get("result"), str):
                             execution_summary_override = module_response.get("result") # if module just returns a string message
                    else: # Module failed
                        execution_summary_override = module_response.get("message", "Module execution failed.")
                elif command_type == "log_event": # This command type now logs using the central logger
                    logger.info(command_data.get("message", f"No message for log_event command from {command_id_log}"))
                    success = True
                elif command_type == "status_check":
                    try:
                        with open(STATUS_FILE, "w") as f:
                            json.dump({"status": "active", "timestamp": datetime.utcnow().isoformat(), "last_command_id": command_id_log}, f, indent=2)
                        logger.info(f"Status checked via command_id: {command_id_log}. Agent active.")
                        success = True
                        execution_summary_override = "Status checked and agent_status.json updated." # Specific summary
                    except Exception as e_status:
                        logger.error(f"Error updating status file for command_id {command_id_log}: {e_status}")
                        success = False
                        execution_summary_override = f"Failed to update status file: {e_status}"
                else:
                    logger.warning(f"Unknown or unhandled command type: '{command_type}' for command_id: {command_id_log}")
                    success = False
                    execution_summary_override = f"Unknown command type: {command_type}"

                command_data["executed_at"] = datetime.utcnow().isoformat()
                command_data["status"] = "done" if success else "failed"

                if execution_summary_override:
                     command_data["execution_summary"] = execution_summary_override
                elif "execution_summary" not in command_data:
                    command_data["execution_summary"] = "Successfully processed." if success else "Processing failed or type unhandled."

                move_to_processed(command_file_path, command_data)

        except Exception as e_loop:
            error_details_loop = traceback.format_exc()
            logger.critical(f"CRITICAL_ERROR in main agent loop: {e_loop}\nTraceback:\n{error_details_loop}")
            if loop:
                time.sleep(delay)

        if run_once:
            logger.info("Agent single run complete (MCI).")
            break

        if not commands_to_process_with_paths and loop:
             logger.info(f"No command files found. Waiting for {delay} seconds...")
        elif loop:
             logger.info(f"End of MCI cycle. Waiting for {delay} seconds...")

        time.sleep(delay)

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Katana Agent - Combat Cycle")
    parser.add_argument("--loop", action='store_true', help='Run agent in a continuous loop.')
    parser.add_argument("--delay", type=int, default=5, help='Delay in seconds for loop mode.')
    args = parser.parse_args()

    main(loop=args.loop, delay=args.delay)
