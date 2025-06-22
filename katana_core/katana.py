import json
import os
import time
import logging # Added for logging
from pathlib import Path
from datetime import datetime
# Assuming katana.utils.logging_config is resolvable.
# If katana_core is a separate package, this might need adjustment or a local config.
# For now, let's assume it can be imported.
try:
    from katana.utils.logging_config import setup_logger
except ImportError:
    # Fallback if running katana_core standalone or if structure prevents direct import
    # This is a simplified fallback, real setup_logger is more complex.
    print("Warning: katana.utils.logging_config not found. Using basic logging for KatanaCore.")
    def setup_logger(logger_name, log_file_path_str, level=logging.DEBUG):
        logger = logging.getLogger(logger_name)
        logger.setLevel(level)
        # Basic console handler as fallback
        if not logger.hasHandlers(): # Avoid adding multiple handlers if called repeatedly
            ch = logging.StreamHandler()
            ch.setLevel(level)
            formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
            ch.setFormatter(formatter)
            logger.addHandler(ch)
        return logger

class KatanaCore:
    def __init__(self, core_dir_path_str="."):
        self.core_dir = Path(core_dir_path_str).resolve()

        # Define log directory and file path for KatanaCore
        self.log_dir = self.core_dir / "logs"
        self.log_file_path = self.log_dir / "katana_core.log"

        # Ensure log directory exists (setup_logger will also do this, but good practice)
        self.log_dir.mkdir(parents=True, exist_ok=True)

        # Initialize logger using setup_logger
        self.logger = setup_logger("KatanaCore", str(self.log_file_path), level=logging.DEBUG)

        self.commands_file_path = self.core_dir / 'commands.json'
        self.status_file_path = self.core_dir / 'sync_status.json'
        self.memory_file_path = self.core_dir / 'memory.json'

        self.commands = {}
        self.memory = {}
        self.status = {}

        self._ensure_files_exist()

        self.load_commands()
        self.load_memory()
        self.load_status()

        self.logger.info(f"KatanaCore initialized. Operational directory: {self.core_dir}", extra={"core_dir": str(self.core_dir)})
        self.logger.debug(f"Commands loaded: {list(self.commands.keys())}", extra={"num_commands": len(self.commands)})

    def _ensure_files_exist(self):
        default_files_content = {
            self.commands_file_path: {},
            self.status_file_path: {"last_sync": None, "last_command": None, "status": "uninitialized"},
            self.memory_file_path: {}
        }
        for file_path, default_content in default_files_content.items():
            if not file_path.exists():
                self.logger.warning(
                    f"File {file_path} not found. Creating with default content.",
                    extra={"file_path": str(file_path)}
                )
                self._save_json(file_path, default_content) # _save_json now uses self.logger

    def load_commands(self):
        try:
            with open(self.commands_file_path, 'r', encoding='utf-8') as f:
                self.commands = json.load(f)
            self.logger.info(f"Commands loaded successfully from {self.commands_file_path}.", extra={"file_path": str(self.commands_file_path)})
        except json.JSONDecodeError as e:
            self.logger.error(
                f"Error decoding JSON from {self.commands_file_path}: {e}. Using empty command set.",
                exc_info=True, extra={"file_path": str(self.commands_file_path), "error": str(e)}
            )
            self.commands = {}
        except FileNotFoundError:
            self.logger.error(
                f"Commands file {self.commands_file_path} not found during load. Initializing empty.",
                exc_info=True, extra={"file_path": str(self.commands_file_path)}
            )
            self.commands = {}
            self._save_json(self.commands_file_path, self.commands)
        except Exception as e:
            self.logger.error(
                f"Failed to load commands from {self.commands_file_path}: {e}. Using empty command set.",
                exc_info=True, extra={"file_path": str(self.commands_file_path), "error": str(e)}
            )
            self.commands = {}

    def _save_json(self, file_path: Path, data: dict):
        try:
            file_path.parent.mkdir(parents=True, exist_ok=True)
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            self.logger.debug(f"Data successfully saved to {file_path}", extra={"file_path": str(file_path)})
            return True
        except Exception as e:
            self.logger.error(f"Error saving data to {file_path}: {e}", exc_info=True, extra={"file_path": str(file_path), "error": str(e)})
            return False

    def save_status(self, new_status_data=None):
        if new_status_data and isinstance(new_status_data, dict):
            self.status.update(new_status_data)
        self.status["last_saved_timestamp_utc"] = datetime.utcnow().isoformat()

        if self._save_json(self.status_file_path, self.status):
            self.logger.info(f"Status saved to {self.status_file_path}", extra={"file_path": str(self.status_file_path)})
        else:
            self.logger.error(f"Failed to save status to {self.status_file_path}", extra={"file_path": str(self.status_file_path)})

    def load_status(self):
        try:
            with open(self.status_file_path, 'r', encoding='utf-8') as f:
                self.status = json.load(f)
            self.logger.info(f"Status loaded from {self.status_file_path}", extra={"file_path": str(self.status_file_path)})
        except json.JSONDecodeError as e:
            self.logger.error(
                f"Error decoding JSON from {self.status_file_path}: {e}. Using default status.",
                exc_info=True, extra={"file_path": str(self.status_file_path), "error": str(e)}
            )
            self.status = {"last_sync": None, "last_command": None, "status":"error_loading"}
        except FileNotFoundError:
            self.logger.error(
                f"Status file {self.status_file_path} not found during load. Initializing default.",
                exc_info=True, extra={"file_path": str(self.status_file_path)}
            )
            self.status = {"last_sync": None, "last_command": None, "status":"error_missing"}
            self._save_json(self.status_file_path, self.status)
        except Exception as e:
            self.logger.error(
                f"Failed to load status from {self.status_file_path}: {e}. Using default status.",
                exc_info=True, extra={"file_path": str(self.status_file_path), "error": str(e)}
            )
            self.status = {"last_sync": None, "last_command": None, "status":"error_unknown"}

    def load_memory(self):
        try:
            with open(self.memory_file_path, 'r', encoding='utf-8') as f:
                self.memory = json.load(f)
            self.logger.info(f"Memory loaded from {self.memory_file_path}", extra={"file_path": str(self.memory_file_path)})
        except json.JSONDecodeError as e:
            self.logger.error(
                f"Error decoding JSON from {self.memory_file_path}: {e}. Initializing empty memory.",
                exc_info=True, extra={"file_path": str(self.memory_file_path), "error": str(e)}
            )
            self.memory = {}
        except FileNotFoundError:
            self.logger.error(
                f"Memory file {self.memory_file_path} not found during load. Initializing empty.",
                exc_info=True, extra={"file_path": str(self.memory_file_path)}
            )
            self.memory = {}
            self._save_json(self.memory_file_path, self.memory)
        except Exception as e:
            self.logger.error(
                f"Failed to load memory from {self.memory_file_path}: {e}. Initializing empty memory.",
                exc_info=True, extra={"file_path": str(self.memory_file_path), "error": str(e)}
            )
            self.memory = {}

    def save_memory(self):
        if self._save_json(self.memory_file_path, self.memory):
            self.logger.info(f"Memory saved to {self.memory_file_path}", extra={"file_path": str(self.memory_file_path)})
        else:
            self.logger.error(f"Failed to save memory to {self.memory_file_path}", extra={"file_path": str(self.memory_file_path)})

    def run(self):
        self.logger.info("⚔️ KatanaCore activated. Type 'exit' or 'quit' to stop. Waiting for command...", extra={"event": "activation"})
        while True:
            try:
                cmd_input = input("katana>> ").strip()
                if not cmd_input:
                    continue
                cmd_key = cmd_input.lower()
                self.logger.debug(f"Received CLI input: '{cmd_input}'", extra={"cli_input": cmd_input})

                if cmd_key in ['exit', 'quit']:
                    self.logger.info("Exit command received. Shutting down KatanaCore.", extra={"command": cmd_key})
                    self.save_status({"last_command": cmd_key, "status": "terminated_by_user"})
                    self.save_memory()
                    break

                if cmd_key in self.commands:
                    command_to_execute = self.commands[cmd_key]
                    self.logger.info(
                        f"Executing command '{cmd_key}': {command_to_execute}",
                        extra={"command_key": cmd_key, "command_action": command_to_execute}
                    )
                    self.save_status({"last_command": cmd_key, "status": f"executing_{cmd_key}"})

                    exit_code = os.system(command_to_execute) # Still using os.system as per original

                    if exit_code == 0:
                        self.logger.info(f"Command '{cmd_key}' executed successfully.", extra={"command_key": cmd_key, "exit_code": exit_code})
                        self.save_status({"last_command_result": "success", "status": "idle_after_command"})
                    else:
                        self.logger.error(
                            f"Command '{cmd_key}' failed with exit code: {exit_code}.",
                            extra={"command_key": cmd_key, "exit_code": exit_code}
                        )
                        self.save_status({"last_command_result": "failed", "status": "idle_after_failed_command", "exit_code":exit_code})

                elif cmd_key.startswith("remember "):
                    parts = cmd_input.split(" ", 2)
                    if len(parts) == 3:
                        mem_key, mem_value = parts[1], parts[2]
                        self.memory[mem_key] = mem_value
                        self.save_memory() # This already logs
                        self.logger.info(f"Memorized: '{mem_key}' = '{mem_value}'", extra={"memory_key": mem_key, "memory_value": mem_value})
                    else:
                        self.logger.warning("Usage: remember <key> <value>", extra={"cli_input": cmd_input})
                        print("Usage: remember <key> <value>")


                elif cmd_key.startswith("recall "):
                    parts = cmd_input.split(" ", 1)
                    if len(parts) == 2:
                        mem_key = parts[1]
                        recalled_value = self.memory.get(mem_key)
                        if recalled_value is not None:
                            print(f"Recalled '{mem_key}': {recalled_value}")
                            self.logger.info(f"Recalled: '{mem_key}'", extra={"memory_key": mem_key, "found": True})
                        else:
                            print(f"Key '{mem_key}' not found in memory.")
                            self.logger.info(f"Recall attempt for key '{mem_key}': Not found.", extra={"memory_key": mem_key, "found": False})
                    else:
                        self.logger.warning("Usage: recall <key>", extra={"cli_input": cmd_input})
                        print("Usage: recall <key>")

                elif cmd_key == "status":
                    status_str = json.dumps(self.status, indent=2)
                    print(f"Current Status:\n{status_str}")
                    self.logger.info("Displayed current status.", extra={"current_status": self.status})

                else:
                    self.logger.warning(f"Unknown command: '{cmd_input}'", extra={"unknown_command": cmd_input})
                    print(f"❌ Unknown command. Available: {list(self.commands.keys())} or 'remember/recall <key> <value>', 'status', 'exit'.")

            except KeyboardInterrupt:
                self.logger.info("KeyboardInterrupt received. Shutting down KatanaCore gracefully...", extra={"event": "KeyboardInterrupt"})
                self.save_status({"last_command": "KeyboardInterrupt", "status": "terminated_by_interrupt"})
                self.save_memory()
                print("\nKatanaCore terminated by user.")
                break
            except Exception as e:
                self.logger.critical(f"An unexpected error occurred in the main loop: {e}", exc_info=True, extra={"error": str(e)})
                # import traceback # No longer needed here, exc_info=True handles it
                # self.logger.critical(traceback.format_exc()) # Redundant with exc_info=True
                time.sleep(1) # Brief pause before potentially retrying or exiting

if __name__ == '__main__':
    # This part is for example usage and won't run during normal import.
    # For KatanaCore to find katana.utils.logging_config, PYTHONPATH might need to be set up
    # if katana_core is not in the same root as katana/ or if they are structured as separate packages.

    # Assuming this script (katana.py) is in katana_core/
    # And katana/ (with utils) is in the parent directory or accessible via PYTHONPATH.
    current_file_dir = Path(__file__).resolve().parent

    # Example of instantiating for direct run:
    # Create a dummy logger for the __main__ block if setup_logger fails or is not the focus here
    main_logger = logging.getLogger("KatanaCoreMain")
    if not main_logger.hasHandlers():
        ch = logging.StreamHandler()
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        ch.setFormatter(formatter)
        main_logger.addHandler(ch)
        main_logger.setLevel(logging.INFO)

    main_logger.info("KatanaCore class defined. To run, instantiate and call .run()")
    main_logger.info(f"Example: kc = KatanaCore(core_dir_path_str='{str(current_file_dir)}'); kc.run()")

    # To actually run it for testing this file directly:
    # Ensure 'katana_core/commands.json', etc. can be created/read in CWD or specified path.
    # kc = KatanaCore(core_dir_path_str=str(current_file_dir)) # Assumes data files are in the same dir as katana.py
    # kc.run()
