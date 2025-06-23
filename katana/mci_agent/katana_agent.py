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
    command_id = command.get('id', 'unknown_command_id') # Ensure command_id is available for logging context

    # Define base context for this execution. user_id and chat_id are system-level for MCI.
    # message_id is the command_id.
    exec_context = {'user_id': 'mci_agent', 'chat_id': 'mci_execution', 'message_id': command_id}

    kwargs_from_command = command.get("args", {})
    if not isinstance(kwargs_from_command, dict):
        logger.warning(
            f"'args' for module {module_name} (command_id: {command_id}) is not a dictionary. Using empty kwargs. Found: {kwargs_from_command}",
            extra=exec_context
        )
        kwargs_from_command = {}

    kwargs_from_command['command_id'] = command_id # Already present from ensure_command_id
    kwargs_from_command['command_type'] = command.get('type')

    logger.info(
        f"Executing module '{module_name}' for command_id: {command_id} with effective args: {kwargs_from_command}",
        extra=exec_context
    )

    module_file_path = MODULES_DIR / f"{module_name}.py"

    try:
        if not module_file_path.exists():
            err_msg = f"Module file not found: {module_file_path}"
            logger.error(f"{err_msg} for command_id: {command_id}", extra=exec_context)
            return {"status": "error", "message": err_msg}

        spec_name = module_file_path.stem
        spec = importlib.util.spec_from_file_location(spec_name, module_file_path)

        if spec is None:
            err_msg = f"Could not create module spec for {module_file_path}"
            logger.error(f"{err_msg} (command_id: {command_id})", extra=exec_context)
            return {"status": "error", "message": err_msg}

        mod = importlib.util.module_from_spec(spec)
        if mod is None:
            err_msg = f"Could not create module from spec for {module_file_path}"
            logger.error(f"{err_msg} (command_id: {command_id})", extra=exec_context)
            return {"status": "error", "message": err_msg}

        spec.loader.exec_module(mod)

        if hasattr(mod, "run") and callable(mod.run):
            module_result = mod.run(**kwargs_from_command)
            logger.info(
                f"Module '{module_name}' (command_id: {command_id}) finished. Raw result: {module_result}",
                extra=exec_context
            )

            if isinstance(module_result, dict) and module_result.get("status") == "error":
                logger.error(
                    f"Module '{module_name}' (command_id: {command_id}) reported error: {module_result.get('message', 'No specific error message.')}",
                    extra=exec_context
                )
                return module_result
            elif module_result is False: # Added logging for this case
                logger.error(
                    f"Module '{module_name}' (command_id: {command_id}) returned False, indicating failure.",
                    extra=exec_context
                )
                return {"status": "error", "message": "Module returned False, indicating failure."}
            return {"status": "success", "result": module_result}
        else:
            err_msg = f"Module '{module_name}' does not have a callable 'run' function."
            logger.error(f"{err_msg} (command_id: {command_id})", extra=exec_context)
            return {"status": "error", "message": err_msg}

    except Exception as e:
        err_msg = f"{type(e).__name__}: {e}"
        logger.critical(
            f"Executing module '{module_name}' (command_id: {command_id}): {err_msg}",
            exc_info=True,
            extra=exec_context
        )
        # Return traceback in the response if needed by the caller, otherwise just log it.
        # For now, keeping it in the response as per original logic.
        return {"status": "error", "message": err_msg, "traceback": traceback.format_exc()}

# --- MCI Helper Functions ---
def load_commands():
    all_commands_with_paths = []
    # System context for general loading operations
    sys_load_context = {'user_id': 'mci_agent', 'chat_id': 'mci_load_process', 'message_id': 'load_commands_scan'}

    if not COMMANDS_DIR.exists():
        # logger.info("Commands directory does not exist.", extra=sys_load_context) # Potentially noisy
        return all_commands_with_paths

    for json_file_path in COMMANDS_DIR.rglob("*.json"):
        # Context specific to each file being processed
        file_process_context = {
            'user_id': 'mci_agent',
            'chat_id': 'mci_load_file',
            'message_id': f'load_cmd_file_{json_file_path.name}'
        }
        try:
            with open(json_file_path, "r", encoding='utf-8') as f:
                command_data = json.load(f)
            if not isinstance(command_data, dict):
                logger.warning(f"Content of {json_file_path} is not a JSON object. Skipping.", extra=file_process_context)
                continue
            all_commands_with_paths.append((json_file_path, command_data))
        except json.JSONDecodeError as e:
            logger.error(f"Malformed JSON in file {json_file_path}: {e}. Skipping.", extra=file_process_context)
        except Exception as e_read:
            logger.error(f"Error reading command file {json_file_path}: {e_read}. Skipping.", extra=file_process_context)

    if all_commands_with_paths:
        logger.info(f"Loaded {len(all_commands_with_paths)} command(s) from individual files.", extra=sys_load_context)
    return all_commands_with_paths

def move_to_processed(original_command_file_path, processed_command_data):
    command_id = processed_command_data.get('id', 'unknown_command_id_archive')
    archive_context = {
        'user_id': 'mci_agent',
        'chat_id': 'mci_archive_process',
        'message_id': command_id # Use command_id as message_id for this operation
    }
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

        logger.info(
            f"Command {original_command_file_path.name} (id: {command_id}) processed and moved to {archive_file_full_path}",
            extra=archive_context
        )
        return True
    except Exception as e:
        logger.critical(
            f"Could not move/archive command file {original_command_file_path}. Error: {e}. Command data: {processed_command_data}",
            exc_info=True,
            extra=archive_context
        )
        return False

# --- MCI Main Function ---
def main(loop=False, delay=5):
    # Setup logging as the first step in main
    setup_logging(log_level=logging.INFO) # Or logging.DEBUG, etc.

    # Base context for main MCI agent operations (system-level)
    mci_sys_context = {'user_id': 'mci_agent_system', 'chat_id': 'mci_lifecycle'}

    # LOGS_DIR and LOG_ARCHIVE_DIR are not created by agent anymore.
    dirs_to_create = [COMMANDS_DIR, STATUS_DIR, MODULES_DIR, PROCESSED_COMMANDS_DIR]
    for d_idx, d in enumerate(dirs_to_create):
        try:
            os.makedirs(d, exist_ok=True)
        except Exception as e:
            logger.critical(
                f"Could not create directory {d}: {e}",
                extra={**mci_sys_context, 'message_id': f'main_mkdir_fail_{d_idx}'}
            )

    # --- File Recovery using Internal Defaults (Refactor Z: Log & Test) ---
    restore_status = False
    status_file_check_ctx = {**mci_sys_context, 'message_id': 'main_status_file_check'}
    if not STATUS_FILE.exists():
        logger.info(f"{STATUS_FILE} is missing. Attempting restore from internal default.", extra=status_file_check_ctx)
        restore_status = True
    else:
        try:
            with open(STATUS_FILE, 'r') as f:
                json.load(f)
        except json.JSONDecodeError:
            logger.warning(f"{STATUS_FILE} is corrupted (invalid JSON). Attempting restore from internal default.", extra=status_file_check_ctx)
            restore_status = True
        except Exception as e:
            logger.warning(f"Error checking {STATUS_FILE}: {e}. Attempting restore as precaution.", extra=status_file_check_ctx)
            restore_status = True

    if restore_status:
        restore_ctx = {**mci_sys_context, 'message_id': 'main_status_file_restore'}
        try:
            status_to_write = DEFAULT_STATUS.copy()
            status_to_write["timestamp"] = datetime.utcnow().isoformat()

            with open(STATUS_FILE, 'w') as f:
                json.dump(status_to_write, f, indent=2)
            logger.info(f"Successfully restored {STATUS_FILE} using internal default and updated timestamp.", extra=restore_ctx)
        except Exception as e_copy_status:
            logger.critical(f"Failed to restore {STATUS_FILE} using internal default. Error: {e_copy_status}", extra=restore_ctx)
    # --- End File Recovery using Internal Defaults ---

    logger.info("Katana agent started (MCI Enabled).", extra={**mci_sys_context, 'message_id': 'main_agent_start'})
    run_once = not loop

    loop_iteration = 0
    while True:
        loop_iteration += 1
        current_loop_msg_id = f'main_loop_iter_{loop_iteration}'
        loop_context = {**mci_sys_context, 'message_id': current_loop_msg_id}

        try:
            commands_to_process_with_paths = load_commands() # load_commands has its own logging

            if not commands_to_process_with_paths:
                if run_once:
                    logger.info("No command files found to process.", extra=loop_context)
            else:
                logger.info(f"Found {len(commands_to_process_with_paths)} command file(s) to process.", extra=loop_context)

            for command_file_path, command_data in commands_to_process_with_paths:
                # Per-command file processing context
                cmd_file_id = command_data.get('id', Path(command_file_path).name) # Use pre-existing ID or filename
                per_cmd_process_context = {'user_id': 'mci_agent', 'chat_id': 'mci_command_processing', 'message_id': cmd_file_id}

                if not isinstance(command_data, dict):
                    logger.warning(f"Skipping invalid command data (not a dict) from file {command_file_path}", extra=per_cmd_process_context)
                    try:
                        malformed_dir = PROCESSED_COMMANDS_DIR / "malformed"
                        os.makedirs(malformed_dir, exist_ok=True)
                        timestamp_mal = datetime.utcnow().strftime("%Y%m%d_%H%M%S_%f")
                        malformed_file_path = malformed_dir / f"{command_file_path.name}_{timestamp_mal}.malformed"
                        shutil.move(str(command_file_path), str(malformed_file_path))
                        logger.info(f"Moved malformed command file {command_file_path} to {malformed_file_path}", extra=per_cmd_process_context)
                    except Exception as e_move_malformed:
                        logger.error(f"Failed to move malformed command file {command_file_path}: {e_move_malformed}", extra=per_cmd_process_context)
                    continue

                ensure_command_id(command_data) # Ensures 'id' key exists
                command_id_log = command_data.get('id') # Now guaranteed to exist

                # Update context with the definite command_id
                per_cmd_process_context['message_id'] = command_id_log

                logger.info(f"Processing command_id: {command_id_log}, type: {command_data.get('type', 'N/A')} from file: {command_file_path.name}", extra=per_cmd_process_context)

                success = False
                command_type = command_data.get("type")
                execution_summary_override = None

                if command_type == "trigger_module":
                    # execute_module logs with its own context using command_id as message_id
                    module_response = execute_module(command_data)
                    success = isinstance(module_response, dict) and module_response.get("status") == "success"
                    if success:
                        execution_summary_override = module_response.get("message")
                        if not execution_summary_override and isinstance(module_response.get("result"), dict):
                             execution_summary_override = module_response.get("result", {}).get("message")
                        if not execution_summary_override and isinstance(module_response.get("result"), str):
                             execution_summary_override = module_response.get("result")
                    else:
                        execution_summary_override = module_response.get("message", "Module execution failed.")
                elif command_type == "log_event":
                    logger.info(
                        command_data.get("message", f"No message for log_event command from {command_id_log}"),
                        extra=per_cmd_process_context # Use this command's context
                    )
                    success = True
                elif command_type == "status_check":
                    try:
                        with open(STATUS_FILE, "w") as f:
                            json.dump({"status": "active", "timestamp": datetime.utcnow().isoformat(), "last_command_id": command_id_log}, f, indent=2)
                        logger.info(f"Status checked via command_id: {command_id_log}. Agent active.", extra=per_cmd_process_context)
                        success = True
                        execution_summary_override = "Status checked and agent_status.json updated."
                    except Exception as e_status:
                        logger.error(f"Error updating status file for command_id {command_id_log}: {e_status}", extra=per_cmd_process_context)
                        success = False
                        execution_summary_override = f"Failed to update status file: {e_status}"
                else:
                    logger.warning(f"Unknown or unhandled command type: '{command_type}' for command_id: {command_id_log}", extra=per_cmd_process_context)
                    success = False
                    execution_summary_override = f"Unknown command type: {command_type}"

                command_data["executed_at"] = datetime.utcnow().isoformat()
                command_data["status"] = "done" if success else "failed"

                if execution_summary_override:
                     command_data["execution_summary"] = execution_summary_override
                elif "execution_summary" not in command_data:
                    command_data["execution_summary"] = "Successfully processed." if success else "Processing failed or type unhandled."

                # move_to_processed logs with its own context using command_id
                move_to_processed(command_file_path, command_data)

        except Exception as e_loop:
            logger.critical(
                f"CRITICAL_ERROR in main agent loop: {e_loop}",
                exc_info=True,
                extra={**mci_sys_context, 'message_id': f'main_loop_exception_iter_{loop_iteration}'}
            )
            if loop:
                time.sleep(delay)

        if run_once:
            logger.info("Agent single run complete (MCI).", extra={**mci_sys_context, 'message_id': 'main_agent_single_run_complete'})
            break

        if not commands_to_process_with_paths and loop:
             logger.info(f"No command files found. Waiting for {delay} seconds...", extra=loop_context)
        elif loop:
             logger.info(f"End of MCI cycle. Waiting for {delay} seconds...", extra=loop_context)

        time.sleep(delay)

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Katana Agent - Combat Cycle")
    parser.add_argument("--loop", action='store_true', help='Run agent in a continuous loop.')
    parser.add_argument("--delay", type=int, default=5, help='Delay in seconds for loop mode.')
    args = parser.parse_args()

    main(loop=args.loop, delay=args.delay)
