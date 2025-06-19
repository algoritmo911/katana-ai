import json
import os
import time # Added for potential future use in run loop or by commands
from pathlib import Path # For robust path handling if needed within class
from datetime import datetime # For timestamps

# Simple logging function for KatanaCore, distinct from Katana Agent's log_event
def log_message_core(level, message):
    """Basic logging for KatanaCore operations."""
    timestamp = datetime.utcnow().isoformat() # Use UTC for logs
    print(f"[{timestamp}] [KatanaCore:{level.upper()}] {message}")

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

        log_message_core("info", f"KatanaCore initialized. Operational directory: {self.core_dir}")
        # log_message_core("info", f"Commands loaded: {list(self.commands.keys())}") # Can be verbose

    def _ensure_files_exist(self):
        """Ensures all core data files exist, creating them with defaults if not."""
        default_files_content = {
            self.commands_file_path: {}, # Default empty JSON object
            self.status_file_path: {"last_sync": None, "last_command": None, "status": "uninitialized"},
            self.memory_file_path: {}    # Default empty JSON object
        }
        for file_path, default_content in default_files_content.items():
            if not file_path.exists():
                log_message_core("warning", f"File {file_path} not found. Creating with default content.")
                self._save_json(file_path, default_content)


    def load_commands(self):
        """Loads commands from the commands.json file."""
        try:
            # _ensure_files_exist should have created it if missing
            with open(self.commands_file_path, 'r', encoding='utf-8') as f:
                self.commands = json.load(f)
            log_message_core("info", f"Commands loaded successfully from {self.commands_file_path}.")
        except json.JSONDecodeError as e:
            log_message_core("error", f"Error decoding JSON from {self.commands_file_path}: {e}. Using empty command set.")
            self.commands = {}
        except FileNotFoundError: # Should be handled by _ensure_files_exist, but as fallback:
            log_message_core("error", f"Commands file {self.commands_file_path} not found during load. Initializing empty.")
            self.commands = {}
            self._save_json(self.commands_file_path, self.commands) # Try to create it
        except Exception as e:
            log_message_core("error", f"Failed to load commands from {self.commands_file_path}: {e}. Using empty command set.")
            self.commands = {}

    def _save_json(self, file_path: Path, data: dict):
        """Helper to save dictionary data to a JSON file."""
        try:
            file_path.parent.mkdir(parents=True, exist_ok=True)
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            return True
        except Exception as e:
            log_message_core("error", f"Error saving data to {file_path}: {e}")
            return False

    def save_status(self, new_status_data=None):
        """Saves the current agent status to the status file."""
        if new_status_data and isinstance(new_status_data, dict):
            self.status.update(new_status_data)

        self.status["last_saved_timestamp_utc"] = datetime.utcnow().isoformat()

        if self._save_json(self.status_file_path, self.status):
            log_message_core("info", f"Status saved to {self.status_file_path}")
        else:
            log_message_core("error", f"Failed to save status to {self.status_file_path}")

    def load_status(self):
        """Loads agent status from the status file."""
        try:
            # _ensure_files_exist should have created it if missing
            with open(self.status_file_path, 'r', encoding='utf-8') as f:
                self.status = json.load(f)
            log_message_core("info", f"Status loaded from {self.status_file_path}")
        except json.JSONDecodeError as e:
            log_message_core("error", f"Error decoding JSON from {self.status_file_path}: {e}. Using default status.")
            self.status = {"last_sync": None, "last_command": None, "status":"error_loading"}
        except FileNotFoundError: # Should be handled by _ensure_files_exist
            log_message_core("error", f"Status file {self.status_file_path} not found during load. Initializing default.")
            self.status = {"last_sync": None, "last_command": None, "status":"error_missing"}
            self._save_json(self.status_file_path, self.status) # Try to create it
        except Exception as e:
            log_message_core("error", f"Failed to load status from {self.status_file_path}: {e}. Using default status.")
            self.status = {"last_sync": None, "last_command": None, "status":"error_unknown"}


    def load_memory(self):
        """Loads memory from the memory.json file."""
        try:
            # _ensure_files_exist should have created it if missing
            with open(self.memory_file_path, 'r', encoding='utf-8') as f:
                self.memory = json.load(f)
            log_message_core("info", f"Memory loaded from {self.memory_file_path}")
        except json.JSONDecodeError as e:
            log_message_core("error", f"Error decoding JSON from {self.memory_file_path}: {e}. Initializing empty memory.")
            self.memory = {}
        except FileNotFoundError: # Should be handled by _ensure_files_exist
            log_message_core("error", f"Memory file {self.memory_file_path} not found during load. Initializing empty.")
            self.memory = {}
            self._save_json(self.memory_file_path, self.memory) # Try to create it
        except Exception as e:
            log_message_core("error", f"Failed to load memory from {self.memory_file_path}: {e}. Initializing empty memory.")
            self.memory = {}

    def save_memory(self):
        """Saves the current memory to the memory.json file."""
        if self._save_json(self.memory_file_path, self.memory):
            log_message_core("info", f"Memory saved to {self.memory_file_path}")
        else:
            log_message_core("error", f"Failed to save memory to {self.memory_file_path}")


    def run(self):
        """Main run loop for the Katana agent's CLI."""
        log_message_core("info", "⚔️ KatanaCore activated. Type 'exit' or 'quit' to stop. Waiting for command...")

        while True:
            try:
                cmd_input = input("katana>> ").strip()
                if not cmd_input:
                    continue

                cmd_key = cmd_input.lower()

                if cmd_key in ['exit', 'quit']:
                    log_message_core("info", "Exit command received. Shutting down KatanaCore.")
                    self.save_status({"last_command": "exit", "status": "terminated_by_user"})
                    self.save_memory()
                    break

                if cmd_key in self.commands:
                    command_to_execute = self.commands[cmd_key]
                    log_message_core("info", f"Executing command '{cmd_key}': {command_to_execute}")

                    self.save_status({"last_command": cmd_key, "status": f"executing_{cmd_key}"})

                    # For security, os.system can be risky. subprocess.run is safer.
                    # Using os.system as per initial plan for simplicity.
                    exit_code = os.system(command_to_execute)

                    if exit_code == 0:
                        log_message_core("info", f"Command '{cmd_key}' executed successfully.")
                        self.save_status({"last_command_result": "success", "status": "idle_after_command"})
                    else:
                        log_message_core("error", f"Command '{cmd_key}' failed with exit code: {exit_code}.")
                        self.save_status({"last_command_result": "failed", "status": "idle_after_failed_command", "exit_code":exit_code})

                elif cmd_key.startswith("remember "):
                    parts = cmd_input.split(" ", 2)
                    if len(parts) == 3:
                        mem_key, mem_value = parts[1], parts[2]
                        self.memory[mem_key] = mem_value
                        self.save_memory()
                        log_message_core("info", f"Memorized: {{mem_key}} = {{mem_value}}") # Escaped for script
                    else:
                        log_message_core("warning", "Usage: remember <key> <value>")

                elif cmd_key.startswith("recall "):
                    parts = cmd_input.split(" ", 1)
                    if len(parts) == 2:
                        mem_key = parts[1]
                        recalled_value = self.memory.get(mem_key, "Not found in memory.")
                        print(f"Recalled {{mem_key}}: {{recalled_value}}")
                        log_message_core("info", f"Recalled: {{mem_key}}")
                    else:
                        log_message_core("warning", "Usage: recall <key>")

                elif cmd_key == "status":
                    print(f"Current Status: {json.dumps(self.status, indent=2)}")
                    log_message_core("info", "Displayed current status.")

                else:
                    log_message_core("warning", f"Unknown command: '{cmd_input}'")
                    print(f"❌ Unknown command. Available: {list(self.commands.keys())} or 'remember/recall <key> <value>', 'status', 'exit'.")

            except KeyboardInterrupt:
                log_message_core("info", "\nKeyboardInterrupt received. Shutting down KatanaCore gracefully...")
                self.save_status({"last_command": "KeyboardInterrupt", "status": "terminated_by_interrupt"})
                self.save_memory()
                break
            except Exception as e:
                log_message_core("critical", f"An unexpected error occurred in the main loop: {e}")
                import traceback # Import locally for this specific error case
                log_message_core("critical", traceback.format_exc())
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
    log_message_core("info", "KatanaCore class defined. To run, instantiate and call .run()")
    log_message_core("info", "Example: kc = KatanaCore('path/to/katana_core_data_dir'); kc.run()")
