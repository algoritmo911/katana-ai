import json
import os
import time # Added for potential future use in run loop or by commands
from pathlib import Path # For robust path handling if needed within class
from datetime import datetime # For timestamps
from katana.logger import get_logger # Corrected import
import logging # For consistency, though setup_logging is not called here

# Import the decorator
from katana.utils.telemetry import trace_command

logger = get_logger(__name__)

# log_message_core function removed, using logger directly.

class KatanaCore:
    def __init__(self, core_dir_path_str="."):
        """
        Initializes the KatanaCore.
        core_dir_path_str: Path to the katana_core directory. Assumed to be relative to CWD if not absolute.
                           For this class, it's where commands.json etc. are expected.
        """
        # If core_dir_path_str is ".", it means files are in the current working directory.
        # If harvester.py (for example) is in katana_core/ and runs KatanaCore(),
        # it would pass "katana_core" or rely on CWD.
        # For simplicity, let's assume core_dir_path_str *is* "katana_core" or similar base.
        self.core_dir = Path(core_dir_path_str).resolve() # Resolve to absolute path

        self.commands_file_path = self.core_dir / 'commands.json'
        self.status_file_path = self.core_dir / 'sync_status.json'
        self.memory_file_path = self.core_dir / 'memory.json'

        self.commands = {}
        self.memory = {}
        self.status = {}

        self._ensure_files_exist() # Call helper to create files if they don't exist with defaults

        self.load_commands()
        self.load_memory()
        self.load_status()

        init_context = {'user_id': 'system_core', 'chat_id': 'katana_core_setup', 'message_id': 'core_init'}
        logger.info(f"KatanaCore initialized. Operational directory: {self.core_dir}", extra=init_context)
        # logger.info(f"Commands loaded: {list(self.commands.keys())}", extra=init_context) # Can be verbose

    def _ensure_files_exist(self):
        """Ensures all core data files exist, creating them with defaults if not."""
        base_context = {'user_id': 'system_core', 'chat_id': 'katana_core_setup'}
        default_files_content = {
            self.commands_file_path: {}, # Default empty JSON object
            self.status_file_path: {"last_sync": None, "last_command": None, "status": "uninitialized"},
            self.memory_file_path: {}    # Default empty JSON object
        }
        for file_path, default_content in default_files_content.items():
            if not file_path.exists():
                file_specific_context = {**base_context, 'message_id': f'ensure_file_{file_path.name}'}
                logger.warning(
                    f"File {file_path} not found. Creating with default content.",
                    extra=file_specific_context
                )
                self._save_json(file_path, default_content) # _save_json will have its own logging


    def load_commands(self):
        """Loads commands from the commands.json file."""
        """Loads commands from the commands.json file."""
        log_ctx = {'user_id': 'system_core', 'chat_id': 'katana_core_load', 'message_id': 'load_commands'}
        try:
            # _ensure_files_exist should have created it if missing
            with open(self.commands_file_path, 'r', encoding='utf-8') as f:
                self.commands = json.load(f)
            logger.info(f"Commands loaded successfully from {self.commands_file_path}.", extra=log_ctx)
        except json.JSONDecodeError as e:
            logger.error(f"Error decoding JSON from {self.commands_file_path}: {e}. Using empty command set.", extra={**log_ctx, 'message_id': 'load_commands_decode_error'})
            self.commands = {}
        except FileNotFoundError: # Should be handled by _ensure_files_exist, but as fallback:
            logger.error(f"Commands file {self.commands_file_path} not found during load. Initializing empty.", extra={**log_ctx, 'message_id': 'load_commands_notfound_error'})
            self.commands = {}
            self._save_json(self.commands_file_path, self.commands) # Try to create it
        except Exception as e:
            logger.error(f"Failed to load commands from {self.commands_file_path}: {e}. Using empty command set.", extra={**log_ctx, 'message_id': 'load_commands_exception'})
            self.commands = {}

    @trace_command # Re-applying with the simplified decorator
    def _save_json(self, file_path: Path, data: dict):
        """Helper to save dictionary data to a JSON file."""
        log_ctx = {'user_id': 'system_core', 'chat_id': 'katana_core_save', 'message_id': f'save_json_{file_path.name}'}
        try:
            file_path.parent.mkdir(parents=True, exist_ok=True)
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            return True # Logging success is handled by caller
        except Exception as e:
            logger.error(f"Error saving data to {file_path}: {e}", extra=log_ctx)
            return False

    def save_status(self, new_status_data=None):
        """Saves the current agent status to the status file."""
        log_ctx = {'user_id': 'system_core', 'chat_id': 'katana_core_status', 'message_id': 'save_status'}
        if new_status_data and isinstance(new_status_data, dict):
            self.status.update(new_status_data)

        self.status["last_saved_timestamp_utc"] = datetime.utcnow().isoformat()

        if self._save_json(self.status_file_path, self.status):
            logger.info(f"Status saved to {self.status_file_path}", extra=log_ctx)
        else:
            logger.error(f"Failed to save status to {self.status_file_path}", extra={**log_ctx, 'message_id': 'save_status_fail'}) # Error already logged by _save_json, but this adds specific context

    def load_status(self):
        """Loads agent status from the status file."""
        log_ctx = {'user_id': 'system_core', 'chat_id': 'katana_core_status', 'message_id': 'load_status'}
        try:
            # _ensure_files_exist should have created it if missing
            with open(self.status_file_path, 'r', encoding='utf-8') as f:
                self.status = json.load(f)
            logger.info(f"Status loaded from {self.status_file_path}", extra=log_ctx)
        except json.JSONDecodeError as e:
            logger.error(f"Error decoding JSON from {self.status_file_path}: {e}. Using default status.", extra={**log_ctx, 'message_id': 'load_status_decode_error'})
            self.status = {"last_sync": None, "last_command": None, "status":"error_loading"}
        except FileNotFoundError: # Should be handled by _ensure_files_exist
            logger.error(f"Status file {self.status_file_path} not found during load. Initializing default.", extra={**log_ctx, 'message_id': 'load_status_notfound_error'})
            self.status = {"last_sync": None, "last_command": None, "status":"error_missing"}
            self._save_json(self.status_file_path, self.status) # Try to create it
        except Exception as e:
            logger.error(f"Failed to load status from {self.status_file_path}: {e}. Using default status.", extra={**log_ctx, 'message_id': 'load_status_exception'})
            self.status = {"last_sync": None, "last_command": None, "status":"error_unknown"}


    def load_memory(self):
        """Loads memory from the memory.json file."""
        log_ctx = {'user_id': 'system_core', 'chat_id': 'katana_core_memory', 'message_id': 'load_memory'}
        try:
            # _ensure_files_exist should have created it if missing
            with open(self.memory_file_path, 'r', encoding='utf-8') as f:
                self.memory = json.load(f)
            logger.info(f"Memory loaded from {self.memory_file_path}", extra=log_ctx)
        except json.JSONDecodeError as e:
            logger.error(f"Error decoding JSON from {self.memory_file_path}: {e}. Initializing empty memory.", extra={**log_ctx, 'message_id': 'load_memory_decode_error'})
            self.memory = {}
        except FileNotFoundError: # Should be handled by _ensure_files_exist
            logger.error(f"Memory file {self.memory_file_path} not found during load. Initializing empty.", extra={**log_ctx, 'message_id': 'load_memory_notfound_error'})
            self.memory = {}
            self._save_json(self.memory_file_path, self.memory) # Try to create it
        except Exception as e:
            logger.error(f"Failed to load memory from {self.memory_file_path}: {e}. Initializing empty memory.", extra={**log_ctx, 'message_id': 'load_memory_exception'})
            self.memory = {}

    def save_memory(self):
        """Saves the current memory to the memory.json file."""
        log_ctx = {'user_id': 'system_core', 'chat_id': 'katana_core_memory', 'message_id': 'save_memory'}
        if self._save_json(self.memory_file_path, self.memory):
            logger.info(f"Memory saved to {self.memory_file_path}", extra=log_ctx)
        else:
            logger.error(f"Failed to save memory to {self.memory_file_path}", extra={**log_ctx, 'message_id': 'save_memory_fail'}) # Error already logged by _save_json


    def run(self):
        """Main run loop for the Katana agent's CLI."""
        cli_user_context = {'user_id': 'cli_user', 'chat_id': 'cli_session'}

        logger.info(
            "⚔️ KatanaCore activated. Type 'exit' or 'quit' to stop. Waiting for command...",
            extra={**cli_user_context, 'message_id': 'run_start'}
        )

        while True:
            try:
                cmd_input = input("katana>> ").strip()
                # For CLI, message_id could be a timestamp or a sequential ID for the command input.
                # Using a timestamp-based one for simplicity here.
                current_cmd_message_id = f'cmd_{datetime.utcnow().isoformat()}'
                cmd_context = {**cli_user_context, 'message_id': current_cmd_message_id}

                if not cmd_input:
                    continue

                cmd_key = cmd_input.lower()

                if cmd_key in ['exit', 'quit']:
                    logger.info("Exit command received. Shutting down KatanaCore.", extra=cmd_context)
                    self.save_status({"last_command": "exit", "status": "terminated_by_user"})
                    self.save_memory()
                    break

                if cmd_key in self.commands:
                    command_to_execute = self.commands[cmd_key]
                    logger.info(f"Executing command '{cmd_key}': {command_to_execute}", extra=cmd_context)

                    self.save_status({"last_command": cmd_key, "status": f"executing_{cmd_key}"})

                    exit_code = os.system(command_to_execute)

                    if exit_code == 0:
                        logger.info(f"Command '{cmd_key}' executed successfully.", extra=cmd_context)
                        self.save_status({"last_command_result": "success", "status": "idle_after_command"})
                    else:
                        logger.error(f"Command '{cmd_key}' failed with exit code: {exit_code}.", extra=cmd_context)
                        self.save_status({"last_command_result": "failed", "status": "idle_after_failed_command", "exit_code":exit_code})

                elif cmd_key.startswith("remember "):
                    parts = cmd_input.split(" ", 2)
                    if len(parts) == 3:
                        mem_key, mem_value = parts[1], parts[2]
                        self.memory[mem_key] = mem_value
                        self.save_memory() # This already logs with its own context
                        logger.info(f"Memorized: {mem_key} = {mem_value}", extra=cmd_context) # Corrected f-string
                    else:
                        logger.warning("Usage: remember <key> <value>", extra=cmd_context)

                elif cmd_key.startswith("recall "):
                    parts = cmd_input.split(" ", 1)
                    if len(parts) == 2:
                        mem_key = parts[1]
                        recalled_value = self.memory.get(mem_key, "Not found in memory.")
                        print(f"Recalled {mem_key}: {recalled_value}") # CLI output
                        logger.info(f"Recalled: {mem_key}", extra=cmd_context) # Corrected f-string
                    else:
                        logger.warning("Usage: recall <key>", extra=cmd_context)

                elif cmd_key == "status":
                    print(f"Current Status: {json.dumps(self.status, indent=2)}") # CLI output
                    logger.info("Displayed current status.", extra=cmd_context)

                else:
                    logger.warning(f"Unknown command: '{cmd_input}'", extra=cmd_context)
                    print(f"❌ Unknown command. Available: {list(self.commands.keys())} or 'remember/recall <key> <value>', 'status', 'exit'.")

            except KeyboardInterrupt:
                shutdown_context = {**cli_user_context, 'message_id': 'keyboard_interrupt'}
                logger.info("\nKeyboardInterrupt received. Shutting down KatanaCore gracefully...", extra=shutdown_context)
                self.save_status({"last_command": "KeyboardInterrupt", "status": "terminated_by_interrupt"})
                self.save_memory()
                break
            except Exception as e:
                error_context = {**cli_user_context, 'message_id': f'main_loop_exception_{datetime.utcnow().isoformat()}'}
                logger.critical(f"An unexpected error occurred in the main loop: {e}", extra=error_context)
                import traceback
                logger.critical(traceback.format_exc(), extra=error_context) # format_exc() provides the message
                time.sleep(1)

if __name__ == '__main__':
    # Example: Initialize KatanaCore pointing to its own directory structure
    # If katana.py is inside "katana_core", then KatanaCore(".") means data files are in "katana_core"
    # If running from outside "katana_core", you'd pass "katana_core"

    # Determine path relative to this script file if needed, or assume CWD is katana_core
    # For this example, assume it's run from a directory containing katana_core,
    # or katana_core is in PYTHONPATH and script is elsewhere.
    # Safest for now: assume script is run from parent of katana_core, or CWD is katana_core itself.

    # If this script (katana.py) is in katana_core/:
    core_directory = Path(__file__).resolve().parent
    # If you want to run this example main, ensure katana_core/ exists where python is run
    # or adjust path. For subtask, just writing the file.

    # kc = KatanaCore(core_dir_path_str=str(core_directory))
    # kc.run()

    # Note: If setup_logging() hasn't been called by an entry point,
    # these logs might not appear as configured or use default Python logging.
    # For this refactor, we assume setup_logging IS called by any actual application entry point.
    # These logs are for developers running this file directly, so simple context is fine.
    dev_context = {'user_id': 'developer', 'chat_id': 'direct_run', 'message_id': 'katana_core_main_info'}
    logger.info("KatanaCore class defined. To run, instantiate and call .run()", extra=dev_context)
    logger.info("Example: kc = KatanaCore('path/to/katana_core_data_dir'); kc.run()", extra={**dev_context, 'message_id': 'katana_core_main_example'})
