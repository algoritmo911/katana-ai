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

    def _ensure_files_exist(self):
        """Ensures all core data files exist, creating them with defaults if not."""
        base_context = {'user_id': 'system_core', 'chat_id': 'katana_core_setup'}
        default_files_content = {
            self.commands_file_path: {},
            self.status_file_path: {"last_sync": None, "last_command": None, "status": "uninitialized"},
            self.memory_file_path: {}
        }
        for file_path, default_content in default_files_content.items():
            if not file_path.exists():
                file_specific_context = {**base_context, 'message_id': f'ensure_file_{file_path.name}'}
                logger.warning(
                    f"File {file_path} not found. Creating with default content.",
                    extra=file_specific_context
                )
                # Pass system context for internal operations like saving a default file
                self._save_json(file_path, default_content, user_id="system_internal", context_id="ensure_files")

    def load_commands(self):
        """Loads commands from the commands.json file."""
        log_ctx = {'user_id': 'system_core', 'chat_id': 'katana_core_load', 'message_id': 'load_commands'}
        try:
            with open(self.commands_file_path, 'r', encoding='utf-8') as f:
                self.commands = json.load(f)
            logger.info(f"Commands loaded successfully from {self.commands_file_path}.", extra=log_ctx)
        except json.JSONDecodeError as e:
            logger.error(f"Error decoding JSON from {self.commands_file_path}: {e}. Using empty command set.", extra={**log_ctx, 'message_id': 'load_commands_decode_error'})
            self.commands = {}
        except FileNotFoundError:
            logger.error(f"Commands file {self.commands_file_path} not found during load. Initializing empty.", extra={**log_ctx, 'message_id': 'load_commands_notfound_error'})
            self.commands = {}
            self._save_json(self.commands_file_path, self.commands, user_id="system_internal", context_id="load_commands_fallback_save")
        except Exception as e:
            logger.error(f"Failed to load commands from {self.commands_file_path}: {e}. Using empty command set.", extra={**log_ctx, 'message_id': 'load_commands_exception'})
            self.commands = {}

    @trace_command
    def _save_json(self, file_path: Path, data: dict, user_id: str = "system_core", context_id: str = "save_json_internal"):
        """
        Helper to save dictionary data to a JSON file.
        user_id and context_id are passed to @trace_command via kwargs.
        """
        # user_id and context_id are now implicitly passed to trace_command through **kwargs
        log_ctx = {'user_id': user_id, 'chat_id': context_id, 'message_id': f'save_json_{file_path.name}'}
        try:
            file_path.parent.mkdir(parents=True, exist_ok=True)
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            # Success logging can be done by the caller or here if needed
            # logger.debug(f"Data saved to {file_path} by {user_id}/{context_id}", extra=log_ctx)
            return True
        except Exception as e:
            logger.error(f"Error saving data to {file_path}: {e}", extra=log_ctx)
            return False

    def save_status(self, new_status_data=None, user_id: str = "system_core", context_id: str = "update_status"):
        """Saves the current agent status to the status file."""
        log_ctx = {'user_id': user_id, 'chat_id': context_id, 'message_id': 'save_status'}
        if new_status_data and isinstance(new_status_data, dict):
            self.status.update(new_status_data)

        self.status["last_saved_timestamp_utc"] = datetime.utcnow().isoformat()

        if self._save_json(self.status_file_path, self.status, user_id=user_id, context_id=context_id):
            logger.info(f"Status saved to {self.status_file_path}", extra=log_ctx)
        else:
            logger.error(f"Failed to save status to {self.status_file_path}", extra={**log_ctx, 'message_id': 'save_status_fail'})

    def load_status(self):
        """Loads agent status from the status file."""
        log_ctx = {'user_id': 'system_core', 'chat_id': 'katana_core_status', 'message_id': 'load_status'}
        try:
            with open(self.status_file_path, 'r', encoding='utf-8') as f:
                self.status = json.load(f)
            logger.info(f"Status loaded from {self.status_file_path}", extra=log_ctx)
        except json.JSONDecodeError as e:
            logger.error(f"Error decoding JSON from {self.status_file_path}: {e}. Using default status.", extra={**log_ctx, 'message_id': 'load_status_decode_error'})
            self.status = {"last_sync": None, "last_command": None, "status":"error_loading"}
        except FileNotFoundError:
            logger.error(f"Status file {self.status_file_path} not found during load. Initializing default.", extra={**log_ctx, 'message_id': 'load_status_notfound_error'})
            self.status = {"last_sync": None, "last_command": None, "status":"error_missing"}
            self._save_json(self.status_file_path, self.status, user_id="system_internal", context_id="load_status_fallback_save")
        except Exception as e:
            logger.error(f"Failed to load status from {self.status_file_path}: {e}. Using default status.", extra={**log_ctx, 'message_id': 'load_status_exception'})
            self.status = {"last_sync": None, "last_command": None, "status":"error_unknown"}

    def load_memory(self):
        """Loads memory from the memory.json file."""
        log_ctx = {'user_id': 'system_core', 'chat_id': 'katana_core_memory', 'message_id': 'load_memory'}
        try:
            with open(self.memory_file_path, 'r', encoding='utf-8') as f:
                self.memory = json.load(f)
            logger.info(f"Memory loaded from {self.memory_file_path}", extra=log_ctx)
        except json.JSONDecodeError as e:
            logger.error(f"Error decoding JSON from {self.memory_file_path}: {e}. Initializing empty memory.", extra={**log_ctx, 'message_id': 'load_memory_decode_error'})
            self.memory = {}
        except FileNotFoundError:
            logger.error(f"Memory file {self.memory_file_path} not found during load. Initializing empty.", extra={**log_ctx, 'message_id': 'load_memory_notfound_error'})
            self.memory = {}
            self._save_json(self.memory_file_path, self.memory, user_id="system_internal", context_id="load_memory_fallback_save")
        except Exception as e:
            logger.error(f"Failed to load memory from {self.memory_file_path}: {e}. Initializing empty memory.", extra={**log_ctx, 'message_id': 'load_memory_exception'})
            self.memory = {}

    def save_memory(self, user_id: str = "system_core", context_id: str = "update_memory"):
        """Saves the current memory to the memory.json file."""
        log_ctx = {'user_id': user_id, 'chat_id': context_id, 'message_id': 'save_memory'}
        if self._save_json(self.memory_file_path, self.memory, user_id=user_id, context_id=context_id):
            logger.info(f"Memory saved to {self.memory_file_path}", extra=log_ctx)
        else:
            logger.error(f"Failed to save memory to {self.memory_file_path}", extra={**log_ctx, 'message_id': 'save_memory_fail'})

    @trace_command
    def _execute_system_command(self, command_key: str, command_to_execute: str, user_id: str, context_id: str):
        """Executes a system command and returns its exit code."""
        # user_id and context_id are passed to @trace_command via kwargs
        logger.info(f"Executing system command '{command_key}': {command_to_execute}", extra={'user_id': user_id, 'chat_id': context_id, 'message_id': f'exec_sys_cmd_{command_key}'})
        self.save_status({"last_command": command_key, "status": f"executing_{command_key}"}, user_id=user_id, context_id=context_id)
        exit_code = os.system(command_to_execute)
        return exit_code

    @trace_command
    def _handle_remember_command(self, mem_key: str, mem_value: str, user_id: str, context_id: str):
        """Handles the 'remember' command."""
        self.memory[mem_key] = mem_value
        self.save_memory(user_id=user_id, context_id=context_id)
        logger.info(f"Memorized: {mem_key} = {mem_value}", extra={'user_id': user_id, 'chat_id': context_id, 'message_id': f'remember_cmd_{mem_key}'})
        return f"Memorized: {mem_key} = {mem_value}"

    @trace_command
    def _handle_recall_command(self, mem_key: str, user_id: str, context_id: str):
        """Handles the 'recall' command."""
        recalled_value = self.memory.get(mem_key, "Not found in memory.")
        print(f"Recalled {mem_key}: {recalled_value}") # CLI output
        logger.info(f"Recalled: {mem_key}", extra={'user_id': user_id, 'chat_id': context_id, 'message_id': f'recall_cmd_{mem_key}'})
        return recalled_value

    @trace_command
    def _handle_status_command(self, user_id: str, context_id: str):
        """Handles the 'status' command."""
        status_str = json.dumps(self.status, indent=2)
        print(f"Current Status: {status_str}") # CLI output
        logger.info("Displayed current status.", extra={'user_id': user_id, 'chat_id': context_id, 'message_id': 'status_cmd'})
        return self.status # Return the status dict for tracing

    def run(self):
        """Main run loop for the Katana agent's CLI."""
        cli_user_id = 'cli_user'
        cli_context_id = 'cli_session'

        logger.info(
            "⚔️ KatanaCore activated. Type 'exit' or 'quit' to stop. Waiting for command...",
            extra={'user_id': cli_user_id, 'chat_id': cli_context_id, 'message_id': 'run_start'}
        )

        while True:
            try:
                cmd_input = input("katana>> ").strip()
                current_cmd_log_message_id = f'cmd_input_{datetime.utcnow().isoformat()}'
                cmd_context_for_logging = {'user_id': cli_user_id, 'chat_id': cli_context_id, 'message_id': current_cmd_log_message_id}

                if not cmd_input:
                    continue

                cmd_key_full = cmd_input # For logging raw input if needed
                cmd_parts = cmd_input.lower().split(" ", 1)
                cmd_action = cmd_parts[0]

                if cmd_action in ['exit', 'quit']:
                    logger.info("Exit command received. Shutting down KatanaCore.", extra=cmd_context_for_logging)
                    self.save_status({"last_command": cmd_action, "status": "terminated_by_user"}, user_id=cli_user_id, context_id=cli_context_id)
                    self.save_memory(user_id=cli_user_id, context_id=cli_context_id)
                    break

                if cmd_action in self.commands:
                    command_to_execute = self.commands[cmd_action]
                    exit_code = self._execute_system_command(
                        command_key=cmd_action,
                        command_to_execute=command_to_execute,
                        user_id=cli_user_id,
                        context_id=cli_context_id
                    )
                    if exit_code == 0:
                        logger.info(f"Command '{cmd_action}' executed successfully.", extra=cmd_context_for_logging)
                        self.save_status({"last_command_result": "success", "status": "idle_after_command"}, user_id=cli_user_id, context_id=cli_context_id)
                    else:
                        logger.error(f"Command '{cmd_action}' failed with exit code: {exit_code}.", extra=cmd_context_for_logging)
                        self.save_status({"last_command_result": "failed", "status": "idle_after_failed_command", "exit_code":exit_code}, user_id=cli_user_id, context_id=cli_context_id)

                elif cmd_action == "remember":
                    parts = cmd_input.split(" ", 2) # Use original cmd_input for parsing
                    if len(parts) == 3:
                        mem_key, mem_value = parts[1], parts[2]
                        self._handle_remember_command(mem_key, mem_value, user_id=cli_user_id, context_id=cli_context_id)
                    else:
                        logger.warning("Usage: remember <key> <value>", extra=cmd_context_for_logging)
                        print("Usage: remember <key> <value>")


                elif cmd_action == "recall":
                    parts = cmd_input.split(" ", 1) # Use original cmd_input for parsing
                    if len(parts) == 2:
                        mem_key = parts[1]
                        self._handle_recall_command(mem_key, user_id=cli_user_id, context_id=cli_context_id)
                    else:
                        logger.warning("Usage: recall <key>", extra=cmd_context_for_logging)
                        print("Usage: recall <key>")

                elif cmd_action == "status":
                    self._handle_status_command(user_id=cli_user_id, context_id=cli_context_id)

                else:
                    logger.warning(f"Unknown command: '{cmd_input}'", extra=cmd_context_for_logging)
                    print(f"❌ Unknown command. Available: {list(self.commands.keys())} or 'remember/recall <key> <value>', 'status', 'exit'.")

            except KeyboardInterrupt:
                shutdown_context = {'user_id': cli_user_id, 'chat_id': cli_context_id, 'message_id': 'keyboard_interrupt'}
                logger.info("\nKeyboardInterrupt received. Shutting down KatanaCore gracefully...", extra=shutdown_context)
                self.save_status({"last_command": "KeyboardInterrupt", "status": "terminated_by_interrupt"}, user_id=cli_user_id, context_id=cli_context_id)
                self.save_memory(user_id=cli_user_id, context_id=cli_context_id)
                break
            except Exception as e:
                error_context = {'user_id': cli_user_id, 'chat_id': cli_context_id, 'message_id': f'main_loop_exception_{datetime.utcnow().isoformat()}'}
                logger.critical(f"An unexpected error occurred in the main loop: {e}", extra=error_context)
                import traceback
                logger.critical(traceback.format_exc(), extra=error_context)
                time.sleep(1)

if __name__ == '__main__':
    # Example: Initialize KatanaCore pointing to its own directory structure
    core_directory = Path(__file__).resolve().parent
    # For testing, ensure katana.logger.setup_logging() is called if you want to see formatted logs
    # from katana.logger import setup_logging
    # import logging as py_logging
    # setup_logging(log_level=py_logging.DEBUG) # Example setup for direct execution

    # kc = KatanaCore(core_dir_path_str=str(core_directory))
    # kc.run()

    dev_context = {'user_id': 'developer', 'chat_id': 'direct_run', 'message_id': 'katana_core_main_info'}
    logger.info("KatanaCore class defined. To run, instantiate and call .run()", extra=dev_context)
    logger.info("Example: kc = KatanaCore('path/to/katana_core_data_dir'); kc.run()", extra={**dev_context, 'message_id': 'katana_core_main_example'})
