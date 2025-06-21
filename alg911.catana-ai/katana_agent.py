import json
import os
import datetime
import logging # New import
import requests # For sending messages to Telegram via n8n webhook
import sys # For sys.argv and sys.exit
# import time # Not used
import uuid # For generating command IDs if needed
# import traceback # Not used

# --- File Paths ---
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
COMMANDS_FILE = os.path.join(SCRIPT_DIR, "katana.commands.json")
MEMORY_FILE = os.path.join(SCRIPT_DIR, "katana_memory.json")
HISTORY_FILE = os.path.join(SCRIPT_DIR, "katana.history.json")
EVENTS_LOG_FILE = os.path.join(SCRIPT_DIR, "katana_events.log")
SYNC_STATUS_FILE = os.path.join(SCRIPT_DIR, "sync_status.json")
# AGENT_LOG_PREFIX = "[KatanaAgent_MCP_v1]" # Removed as per requirements

# --- Configuration ---
N8N_TELEGRAM_SEND_WEBHOOK_URL = "YOUR_N8N_WEBHOOK_URL_FOR_SENDING_MESSAGES_HERE"
DEFAULT_REQUEST_TIMEOUT = 10 # seconds

# --- Logging Setup ---
# Note: Logger is configured globally, KatanaCLI will use this instance.
katana_logger = logging.getLogger("katana_logger")
katana_logger.setLevel(logging.DEBUG) # Set logger to lowest level, handlers will filter

# Console Handler
console_handler = logging.StreamHandler()
console_handler.setLevel(logging.INFO)
console_formatter = logging.Formatter('[%(asctime)s] [%(levelname)s] [KatanaAgent] %(message)s', datefmt='%Y-%m-%d %H:%M:%S')
console_handler.setFormatter(console_formatter)
katana_logger.addHandler(console_handler)

# File Handler
# Ensure log directory exists
log_dir = os.path.dirname(EVENTS_LOG_FILE)
if log_dir and not os.path.exists(log_dir):
    os.makedirs(log_dir, exist_ok=True)

file_handler = logging.FileHandler(EVENTS_LOG_FILE)
file_handler.setLevel(logging.DEBUG)
file_formatter = logging.Formatter('[%(asctime)s] [%(levelname)s] [%(name)s] [%(module)s.%(funcName)s:%(lineno)d] %(message)s', datefmt='%Y-%m-%dT%H:%M:%S%z')
file_handler.setFormatter(file_formatter)
katana_logger.addHandler(file_handler)

# --- KatanaCLI Class ---
class KatanaCLI:
    def __init__(self):
        self.logger = katana_logger # Use the globally configured logger
        self.agent_memory_state = {} # Instance variable for memory state
        # File paths remain global constants, accessible directly

        # Command dispatcher
        self.commands = {
            "echo": self._execute_echo_command,
            "memdump": self._execute_memdump_command,
            "exit": self._execute_exit_command,
            "addtask": self._execute_addtask_command,
            "process_telegram_message": self._execute_process_telegram_message,
            "start_katana": self._execute_start_katana_command,
            "stop_katana": self._execute_stop_katana_command,
            "status_katana": self._execute_status_katana_command,
            # Future commands can be added here
        }
        # Warn if Telegram webhook URL is not set
        if N8N_TELEGRAM_SEND_WEBHOOK_URL == "YOUR_N8N_WEBHOOK_URL_FOR_SENDING_MESSAGES_HERE":
            self.logger.warning("N8N_TELEGRAM_SEND_WEBHOOK_URL is not configured. Telegram message sending will not work.")

    # --- JSON File I/O Utilities (now methods) ---
    def load_json_file(self, file_path, default_value, log_prefix="JSONLoad"):
        if not os.path.exists(file_path):
            self.logger.info(f"{log_prefix}: File not found: {file_path}. Returning default.")
            return default_value
        try:
            with open(file_path, "r") as f:
                content = f.read()
                if not content.strip():
                    self.logger.info(f"{log_prefix}: File is empty: {file_path}. Returning default.")
                    return default_value
                data = json.loads(content)
            return data
        except json.JSONDecodeError:
            self.logger.error(f"{log_prefix}: Error decoding JSON from {file_path}. Returning default.")
            return default_value
        except Exception as e:
            self.logger.error(f"{log_prefix}: Unexpected error loading {file_path}: {e}. Returning default.")
            return default_value

    def save_json_file(self, file_path, data, log_prefix="JSONSave", indent=2):
        try:
            dir_name = os.path.dirname(file_path)
            if dir_name and not os.path.exists(dir_name):
                os.makedirs(dir_name, exist_ok=True)
            with open(file_path, "w") as f:
                json.dump(data, f, indent=indent)
            self.logger.info(f"{log_prefix}: Successfully saved JSON to {file_path}.")
            return True
        except Exception as e:
            self.logger.error(f"{log_prefix}: Error saving JSON to {file_path}: {e}")
            return False

    # --- Katana Data File Specific Functions (now methods) ---
    def load_memory(self):
        loaded_data = self.load_json_file(MEMORY_FILE, {}, "MemoryLoad")
        self.agent_memory_state = loaded_data if isinstance(loaded_data, dict) else {}
        if not isinstance(loaded_data, dict):
             self.logger.warning(f"MemoryLoad: Memory file {MEMORY_FILE} content was not a dictionary. Resetting memory state.")
        return self.agent_memory_state

    def save_memory(self):
        return self.save_json_file(MEMORY_FILE, self.agent_memory_state, "MemorySave")

    def load_commands(self): return self.load_json_file(COMMANDS_FILE, [], "CommandsLoad")
    def save_commands(self, commands_list): return self.save_json_file(COMMANDS_FILE, commands_list, "CommandsSave")

    def load_history(self): return self.load_json_file(HISTORY_FILE, [], "HistoryLoad")
    def save_history(self, history_list): return self.save_json_file(HISTORY_FILE, history_list, "HistorySave")

    # --- File Initialization (now a method) ---
    def initialize_katana_files(self):
        self.logger.info("Initializing/Verifying Katana data files for MCP_v1...")
        files_to_initialize_or_verify = {
            COMMANDS_FILE: ([], list, "InitCommands"),
            HISTORY_FILE: ([], list, "InitHistory"),
            MEMORY_FILE: ({}, dict, "InitMemory"),
            SYNC_STATUS_FILE: ({"auto_sync_enabled": False, "last_successful_sync_timestamp": None, "auto_sync_interval_hours": 24}, dict, "InitSyncStatus")
        }

        for file_path, (default_content, expected_type, log_prefix) in files_to_initialize_or_verify.items():
            if not os.path.exists(file_path):
                self.save_json_file(file_path, default_content, log_prefix)
            else:
                loaded_content = self.load_json_file(file_path, None, f"InitCheck{log_prefix[4:]}")
                if loaded_content is None or not isinstance(loaded_content, expected_type):
                    self.logger.warning(f"{log_prefix}: {file_path} is not a {expected_type.__name__} or is corrupted/unreadable. Re-initializing.")
                    self.save_json_file(file_path, default_content, log_prefix)
                elif file_path == SYNC_STATUS_FILE:
                     if not all(k in loaded_content for k in default_content.keys()):
                        self.logger.warning(f"{log_prefix}: {SYNC_STATUS_FILE} is missing essential keys. Re-initializing.")
                        self.save_json_file(SYNC_STATUS_FILE, default_content, log_prefix)
                     else:
                        self.logger.debug(f"{log_prefix}: {file_path} exists and appears valid.")
                else:
                    self.logger.debug(f"{log_prefix}: {file_path} exists and appears valid.")
        self.load_memory() # Load memory state after checks

        # Initialize Katana service status if not already set
        if 'katana_service_status' not in self.agent_memory_state:
            self.logger.info("Initializing Katana service status to 'stopped'.")
            self.agent_memory_state['katana_service_status'] = "stopped"
            self.save_memory() # Persist this initial state

        self.logger.info("Katana data file initialization/verification complete.")

    # --- Task Management Methods ---
    def add_task(self, action: str, parameters: dict, origin: str = "internal") -> str:
        """
        Adds a new task to the command queue (katana.commands.json).
        """
        command_id = uuid.uuid4().hex
        task = {
            "command_id": command_id,
            "action": action,
            "parameters": parameters,
            "status": "pending", # pending, processing, completed, failed
            "created_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
            "processed_at": None,
            "result": None,
            "origin": origin # e.g., "cli", "webhook", "internal"
        }

        tasks = self.load_commands()
        if not isinstance(tasks, list):
            self.logger.warning(f"Commands file {COMMANDS_FILE} was not a list. Initializing with new task.")
            tasks = []
        tasks.append(task)
        self.save_commands(tasks)
        self.logger.info(f"Added new task {command_id} for action '{action}' with origin '{origin}'.")
        return command_id

    def get_oldest_pending_task(self) -> dict | None:
        """
        Retrieves the oldest task with 'pending' status.
        """
        tasks = self.load_commands()
        if not isinstance(tasks, list):
            self.logger.error(f"Commands file {COMMANDS_FILE} is not a list. Cannot retrieve tasks.")
            return None

        for task in tasks:
            if isinstance(task, dict) and task.get("status") == "pending":
                # Optionally sort by created_at if multiple pending tasks and order matters strictly
                # For now, taking the first one found.
                return task
        return None

    def update_task(self, task_id: str, updates: dict) -> bool:
        """
        Updates a task in the command queue by its command_id.
        """
        tasks = self.load_commands()
        if not isinstance(tasks, list):
            self.logger.error(f"Commands file {COMMANDS_FILE} is not a list. Cannot update task.")
            return False

        task_found = False
        for i, task in enumerate(tasks):
            if isinstance(task, dict) and task.get("command_id") == task_id:
                task.update(updates)
                tasks[i] = task # Update the task in the list
                task_found = True
                break

        if task_found:
            self.save_commands(tasks)
            self.logger.info(f"Task {task_id} updated with: {updates}")
            return True
        else:
            self.logger.warning(f"Task {task_id} not found for update.")
            return False

    # --- CLI History and Parsing ---
    def add_to_history(self, command_string):
        history = self.load_history()
        if not isinstance(history, list): # Ensure history is a list
            self.logger.warning("History file was not a list. Re-initializing history.")
            history = []
        history_entry = {
            "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
            "command_string": command_string
        }
        history.append(history_entry)
        self.save_history(history)

    def parse_command(self, raw_input_string):
        parts = raw_input_string.strip().split(maxsplit=1)
        command = parts[0] if parts else ""
        args = parts[1].split() if len(parts) > 1 else []
        return command, args

    # --- Telegram Integration Methods (Placeholders & Initial Logic) ---
    def send_telegram_message(self, chat_id: str, message: str):
        """
        Sends a message to Telegram via the configured N8N webhook URL.
        """
        if N8N_TELEGRAM_SEND_WEBHOOK_URL == "YOUR_N8N_WEBHOOK_URL_FOR_SENDING_MESSAGES_HERE":
            self.logger.error(f"N8N_TELEGRAM_SEND_WEBHOOK_URL is not configured. Cannot send message to chat_id {chat_id}.")
            # To avoid breaking the calling function's expectation of (bool, str) for other command handlers,
            # this method itself doesn't return. The calling function handles responses.
            return

        payload = {"chat_id": chat_id, "text": message}
        try:
            self.logger.debug(f"Attempting to send Telegram message to {chat_id}: {message[:50]}...") # Log snippet
            response = requests.post(N8N_TELEGRAM_SEND_WEBHOOK_URL, json=payload, timeout=DEFAULT_REQUEST_TIMEOUT)

            # Check if the request was successful
            if response.status_code >= 200 and response.status_code < 300:
                self.logger.info(f"Successfully sent message to Telegram chat_id {chat_id}. Response: {response.text}")
            else:
                self.logger.warning(
                    f"Failed to send message to Telegram chat_id {chat_id}. "
                    f"Status Code: {response.status_code}. Response: {response.text}"
                )
        except requests.exceptions.Timeout:
            self.logger.error(
                f"Timeout error when trying to send message to Telegram chat_id {chat_id}."
            )
        except requests.exceptions.RequestException as e:
            self.logger.error(
                f"Error sending message to Telegram chat_id {chat_id}: {e}"
            )
        # This method itself does not return success/failure of sending for now,
        # as _execute_process_telegram_message returns status of command processing, not message delivery.
        # Delivery status is logged.

    def _process_pending_tasks(self, iterations: int = 1):
        """
        Processes a specified number of pending tasks from the queue.
        """
        self.logger.debug(f"Checking for pending tasks to process for {iterations} iteration(s).")
        for _ in range(iterations):
            pending_task = self.get_oldest_pending_task()
            if pending_task:
                task_id = pending_task["command_id"]
                action = pending_task["action"]
                parameters = pending_task.get("parameters", {})

                self.logger.info(f"Processing task {task_id}: {action} with params {parameters}")
                self.update_task(task_id, {
                    "status": "processing",
                    "processed_at": datetime.datetime.now(datetime.timezone.utc).isoformat()
                })

                success, result_msg = self._dispatch_command_execution(action, parameters, source="task")

                final_status = "completed" if success else "failed"
                self.update_task(task_id, {"status": final_status, "result": result_msg})
                self.logger.info(f"Task {task_id} ({action}) finished with status: {final_status}. Result: {result_msg}")
            else:
                self.logger.debug("No pending tasks found in this iteration.")
                break # No more tasks to process in this wave

    def _execute_process_telegram_message(self, params: dict, source: str) -> tuple[bool, str | None]:
        """
        Handles tasks originating from Telegram messages.
        `params` is the original JSON payload from the Telegram webhook.
        """
        if source != "task":
            return False, "process_telegram_message can only be called as a task."

        user_id = params.get("user_id", "unknown_user")
        chat_id = params.get("chat_id", "unknown_chat")
        text = params.get("text", "").strip()
        original_command_id = params.get("original_command_id", "unknown_original_cmd") # From webhook

        self.logger.info(f"Processing Telegram message task: user_id={user_id}, chat_id={chat_id}, text='{text}', original_cmd_id='{original_command_id}'")

        if not chat_id or chat_id == "unknown_chat":
            return False, "Cannot process Telegram message without a valid chat_id."

        if text.startswith("/status"):
            all_tasks = self.load_commands()
            pending_tasks_count = 0
            if isinstance(all_tasks, list):
                pending_tasks_count = sum(1 for task in all_tasks if isinstance(task, dict) and task.get("status") == "pending")

            status_message = f"Katana Agent is running.\nPending tasks: {pending_tasks_count}"
            self.send_telegram_message(chat_id, status_message)
            return True, f"Status request processed. Response placeholder logged for chat_id {chat_id}."

        elif text.startswith("/echo_tg "):
            echo_response = text[len("/echo_tg "):].strip()
            if not echo_response:
                echo_response = "You said /echo_tg but provided nothing to echo!"
            self.send_telegram_message(chat_id, echo_response)
            return True, f"Echo request processed. Response placeholder logged for chat_id {chat_id}."

        else:
            unknown_cmd_message = "Sorry, I didn't understand that command. Try /status or /echo_tg <message>."
            self.send_telegram_message(chat_id, unknown_cmd_message)
            self.logger.info(f"Unknown Telegram command from chat_id {chat_id}: '{text}'")
            return True, "Unknown Telegram command processed."

    # --- System Status Command Execution Methods ---
    def _execute_start_katana_command(self, params, source="cli") -> tuple[bool, str]:
        """Handles the start_katana CLI command."""
        # Params are ignored for this command
        self.logger.info("Executing start_katana command.")
        self.agent_memory_state['katana_service_status'] = "running"
        self.agent_memory_state['katana_service_last_start_time'] = datetime.datetime.now(datetime.timezone.utc).isoformat()
        self.save_memory()
        message = "Katana service started successfully."
        if source == "cli":
            print(message)
        return True, message

    def _execute_stop_katana_command(self, params, source="cli") -> tuple[bool, str]:
        """Handles the stop_katana CLI command."""
        # Params are ignored for this command
        self.logger.info("Executing stop_katana command.")
        self.agent_memory_state['katana_service_status'] = "stopped"
        self.agent_memory_state['katana_service_last_stop_time'] = datetime.datetime.now(datetime.timezone.utc).isoformat()
        self.save_memory()
        message = "Katana service stopped successfully."
        if source == "cli":
            print(message)
        return True, message

    def _execute_status_katana_command(self, params, source="cli") -> tuple[bool, str]:
        """Handles the status_katana CLI command."""
        # Params are ignored for this command
        self.logger.info("Executing status_katana command.")
        self.load_memory() # Ensure we have the latest status from file

        status = self.agent_memory_state.get('katana_service_status', "unknown")
        last_start = self.agent_memory_state.get('katana_service_last_start_time', "N/A")
        last_stop = self.agent_memory_state.get('katana_service_last_stop_time', "N/A")

        message = (
            f"Katana Service Status: {status}\n"
            f"Last Start Time: {last_start}\n"
            f"Last Stop Time: {last_stop}"
        )
        if source == "cli":
            print(message)
        return True, message

    # --- General Command Execution Methods ---
    def _execute_echo_command(self, params, source="cli"):
        """
        Handles the 'echo' command (CLI or task).
        Returns: (success: bool, message: str | None)
        """
        self.logger.debug(f"Executing echo command with params: {params} from source: {source}")
        message = None
        if source == "cli": # params is a list of strings
            message = " ".join(params)
            print(message)
        elif source == "task": # params is a dict
            message = params.get("text_to_echo", "No text_to_echo parameter provided in task.")
            # For tasks, we don't print to console here, it's returned as result.
        else:
            return False, "Unknown source for echo command."
        return True, message

    def _execute_memdump_command(self, params, source="cli"):
        """
        Handles the 'memdump' command.
        Returns: (success: bool, message: str | None)
        """
        # Params are ignored for memdump for now
        self.logger.debug(f"Executing memdump command from source: {source}")
        mem_state_json = json.dumps(self.agent_memory_state, indent=2)
        if source == "cli":
            print(mem_state_json)
        return True, mem_state_json

    def _execute_exit_command(self, params, source="cli"):
        """
        Handles the 'exit' command (CLI only).
        Returns: (success: bool, message: str | None) - Success False signals shell to stop.
        """
        # Params are ignored
        if source == "cli":
            self.logger.info("Exit command received via CLI. Terminating shell.")
            return False, "Exiting KatanaCLI." # False for success to signal exit
        else:
            self.logger.warning("Exit command called as a task, which is not supported. Ignoring.")
            return False, "Exit command cannot be called as a task."


    def _execute_addtask_command(self, args: list, source: str = "cli"):
        """
        CLI command to add a new task.
        Format: addtask <action_name> <param_key=param_value ...>
        Example: addtask log_event level=info message="hello from task"
        Returns: (success: bool, message: str | None)
        """
        if source != "cli":
            return False, "addtask command can only be run from CLI."

        if not args or len(args) < 1:
            usage = "Usage: addtask <action_name> [param_key=param_value ...]"
            print(usage)
            return False, usage

        action_name = args[0]
        parameters = {}
        for item in args[1:]:
            if "=" in item:
                key, value = item.split("=", 1)
                parameters[key] = value
            else:
                # Handle case where a parameter might not have a value or is malformed
                self.logger.warning(f"Malformed parameter '{item}' in addtask command. Ignoring.")

        try:
            task_id = self.add_task(action=action_name, parameters=parameters, origin="cli_addtask")
            # Make the printed output easily parsable for internal_task_id
            cli_output_msg = f"CREATED_TASK_ID: {task_id}"
            # The log message can be more verbose
            log_msg = f"Task {task_id} for action '{action_name}' added via CLI."
            self.logger.info(log_msg)
            # Print only the parsable part to stdout for subprocess communication
            print(cli_output_msg)
            return True, cli_output_msg # Return the parsable message as well
        except Exception as e:
            err_msg = f"Failed to add task: {e}"
            self.logger.error(err_msg)
            print(err_msg)
            return False, err_msg

    def _dispatch_command_execution(self, command_name: str, params, source: str = "cli") -> tuple[bool, str | None]:
        """
        Dispatches command execution to the appropriate handler.
        Manages parameter adaptation based on source (CLI vs Task).
        Returns: (success_status: bool, result_message: str | None)
        """
        self.logger.info(f"Attempting to dispatch command: '{command_name}' with params: {params} from source: {source}")

        command_handler = self.commands.get(command_name)

        if command_handler:
            try:
                # For CLI, params is usually a list of strings.
                # For tasks, params is a dictionary.
                # Handlers are expected to manage this based on the 'source' argument.
                success, result_message = command_handler(params, source=source)
                return success, result_message
            except Exception as e:
                self.logger.error(f"Exception during execution of command '{command_name}': {e}", exc_info=True)
                return False, f"Error executing command '{command_name}': {str(e)}"
        else:
            self.logger.warning(f"Unknown command: {command_name}")
            if source == "cli":
                print(f"Unknown command: {command_name}")
            return False, f"Unknown command: {command_name}"

    def start_shell(self):
        self.logger.info("KatanaCLI interactive shell started.")

        running = True
        while running:
            # 1. Process one pending task before showing prompt in interactive mode
            self._process_pending_tasks(iterations=1)

            # 2. CLI Interaction
            try:
                raw_input_string = input("katana> ")
                if not raw_input_string.strip():
                    continue

                self.add_to_history(raw_input_string)
                command_name, cli_args = self.parse_command(raw_input_string)

                # Pass CLI args as a list
                success, _ = self._dispatch_command_execution(command_name, cli_args, source="cli")

                # Specific check for 'exit' command to terminate the shell
                if command_name == "exit" and not success: # Exit command's handler returns False for success
                    running = False # Break the loop

            except KeyboardInterrupt: # Handle Ctrl+C
                print("\nExiting KatanaCLI (Ctrl+C)...")
                self.logger.info("KatanaCLI shell terminated by user (KeyboardInterrupt).")
                running = False
            except EOFError: # Handle Ctrl+D
                print("\nExiting KatanaCLI (Ctrl+D)...")
                self.logger.info("KatanaCLI shell terminated by user (KeyboardInterrupt).")
                running = False # Break the loop
            except EOFError: # Handle Ctrl+D
                print("\nExiting KatanaCLI (Ctrl+D)...")
                self.logger.info("KatanaCLI shell terminated by user (EOFError).")
                running = False # Break the loop
        self.logger.info("KatanaCLI shell shut down.")


if __name__ == '__main__':
    cli = KatanaCLI()
    cli.initialize_katana_files() # Initialize files first

    if len(sys.argv) > 1:
        # Non-interactive mode: execute command from args, process tasks, then exit.
        cli.logger.info(f"Katana Agent CLI starting in non-interactive mode. Args: {sys.argv[1:]}")

        # Reconstruct the command string from sys.argv for parsing
        # Example: if sys.argv is ['katana_agent.py', 'addtask', 'action_name', 'p1=v1']
        # command_input_str becomes "addtask action_name p1=v1"
        command_input_str = " ".join(sys.argv[1:])
        cli.logger.info(f"Executing command from args: '{command_input_str}'")

        # Use existing parse_command for consistency
        command_name, args = cli.parse_command(command_input_str)

        if command_name:
            # Add to history even for non-interactive commands for audit.
            cli.add_to_history(f"[ARG_CMD] {command_input_str}")
            # Dispatch the command. Source 'cli' is appropriate as it's a direct command.
            # The print(result_message) below handles the output from _execute_addtask_command
            success, result_message_from_dispatch = cli._dispatch_command_execution(command_name, args, source="cli")

            # If the command was not 'addtask', its direct result might be printed by the handler (if source=='cli')
            # or we can print it here. For 'addtask', the specific "CREATED_TASK_ID: ..." is already printed.
            # The result_message_from_dispatch from addtask is "CREATED_TASK_ID: ...", which is already printed by the handler.
            # For other commands, their specific CLI print logic inside handlers (if source=='cli') or here:
            if command_name != "addtask" and result_message_from_dispatch and source=="cli":
                 print(result_message_from_dispatch)

            if not success and command_name == "exit":
                cli.logger.info("Non-interactive 'exit' command processed. Shutting down.")
                sys.exit(0) # Graceful exit if the command was 'exit'

            # Process tasks a couple of times to handle tasks potentially added by the command
            cli.logger.info("Processing tasks (up to 2 iterations) after command execution...")
            cli._process_pending_tasks(iterations=2)
        else:
            cli.logger.warning("No valid command could be parsed from command-line arguments.")

        cli.logger.info("Katana Agent CLI non-interactive mode finished.")
        sys.exit(0)
    else:
        # Interactive mode
        cli.logger.info("Katana Agent CLI starting in interactive mode...")
        cli.start_shell() # Enters the interactive loop
        cli.logger.info("Katana Agent CLI has shut down.")
