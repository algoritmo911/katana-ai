import json
import os
import datetime
import time  # For command processing loop
import uuid  # For generating command IDs if needed (though API does it now)
import threading  # For running self-healing in a separate thread

# import traceback # Not used

import shared_config  # Import the shared configuration
from katana.modules import command_handler, status_logger

# Attempt to import the self-healing orchestrator
try:
    from self_healing.orchestrator import SelfHealingOrchestrator

    SELF_HEALING_ENABLED = True
except ImportError as e:
    SELF_HEALING_ENABLED = False
    # Use shared_config.log_event if available, otherwise print
    startup_log_message = f"Self-Healing module not found or import error: {e}. Continuing without self-healing capabilities."
    if hasattr(shared_config, "log_event"):
        # This log might occur before shared_config.log_event's file handler is fully set up if there's an issue there,
        # but it's better to try.
        shared_config.log_event(startup_log_message, "warning", "KatanaAgentStartup")
    else:
        print(f"STARTUP WARNING: {startup_log_message}")


# --- File Paths (from shared_config) ---
COMMANDS_FILE = shared_config.COMMANDS_FILE_PATH
MEMORY_FILE = shared_config.MEMORY_FILE_PATH
HISTORY_FILE = shared_config.HISTORY_FILE_PATH
# EVENTS_LOG_FILE = shared_config.EVENTS_LOG_FILE_PATH # Logging handled by shared_config.log_event
SYNC_STATUS_FILE = shared_config.SYNC_STATUS_FILE_PATH

# --- Use shared logger ---
log_event = shared_config.log_event
AGENT_LOG_PREFIX = (
    shared_config.AGENT_LOG_PREFIX
)  # Component prefix for logs from this agent

# --- Global State ---
agent_memory_state = {}  # In-memory representation of katana_memory.json
processed_command_ids = set()  # Keep track of processed commands in this session


# --- JSON File I/O Utilities (adapted to use shared logger) ---
def load_json_file(file_path, default_value, log_prefix_override=None):
    # log_event(f"Attempting to load JSON from {file_path}", "debug", AGENT_LOG_PREFIX)
    if not os.path.exists(file_path):
        log_event(
            f"[{log_prefix_override or 'JSONLoad'}] File not found: {file_path}. Returning default.",
            "info",
            AGENT_LOG_PREFIX,
        )
        return default_value
    try:
        with open(file_path, "r") as f:
            content = f.read()
            if not content.strip():  # File is empty
                log_event(
                    f"[{log_prefix_override or 'JSONLoad'}] File is empty: {file_path}. Returning default.",
                    "info",
                    AGENT_LOG_PREFIX,
                )
                return default_value
            data = json.loads(content)
        # log_event(f"[{log_prefix_override or 'JSONLoad'}] Loaded successfully from {file_path}.", "debug", AGENT_LOG_PREFIX)
        return data
    except json.JSONDecodeError:
        log_event(
            f"[{log_prefix_override or 'JSONLoad'}] Error decoding JSON from {file_path}. Returning default.",
            "error",
            AGENT_LOG_PREFIX,
        )
        return default_value
    except Exception as e:  # Catch any other read errors
        log_event(
            f"[{log_prefix_override or 'JSONLoad'}] Unexpected error loading {file_path}: {e}. Returning default.",
            "error",
            AGENT_LOG_PREFIX,
        )
        return default_value


def save_json_file(file_path, data, log_prefix_override=None, indent=2):
    # log_event(f"Attempting to save JSON to {file_path}", "debug", AGENT_LOG_PREFIX)
    try:
        dir_name = os.path.dirname(file_path)
        if dir_name and not os.path.exists(
            dir_name
        ):  # Create directory if it doesn't exist
            os.makedirs(dir_name, exist_ok=True)
        with open(file_path, "w") as f:
            json.dump(data, f, indent=indent)
        log_event(
            f"[{log_prefix_override or 'JSONSave'}] Successfully saved JSON to {file_path}.",
            "info",
            AGENT_LOG_PREFIX,
        )
        return True
    except Exception as e:
        log_event(
            f"[{log_prefix_override or 'JSONSave'}] Error saving JSON to {file_path}: {e}",
            "error",
            AGENT_LOG_PREFIX,
        )
        return False


# --- Katana Data File Specific Functions ---
def load_memory():
    global agent_memory_state
    loaded_data = load_json_file(MEMORY_FILE, {}, "MemoryLoad")
    agent_memory_state = loaded_data if isinstance(loaded_data, dict) else {}
    if not isinstance(loaded_data, dict):
        log_event(
            f"Memory file {MEMORY_FILE} content was not a dictionary. Resetting memory state.",
            "warning",
            AGENT_LOG_PREFIX,
        )
    return agent_memory_state


def save_memory():
    global agent_memory_state
    return save_json_file(MEMORY_FILE, agent_memory_state, "MemorySave")


def load_commands_from_file():
    return load_json_file(COMMANDS_FILE, [], "CommandsLoad")


def save_commands_to_file(commands_list):
    return save_json_file(COMMANDS_FILE, commands_list, "CommandsSave")


def load_history():
    return load_json_file(HISTORY_FILE, [], "HistoryLoad")


def save_history(history_list):
    return save_json_file(HISTORY_FILE, history_list, "HistorySave")


# --- File Initialization (for MCP_v1, adapted) ---
def initialize_katana_files():
    log_event(
        "Initializing/Verifying Katana data files for MCP_v1...",
        "info",
        AGENT_LOG_PREFIX,
    )

    # Paths are now from shared_config
    files_to_initialize_or_verify = {
        COMMANDS_FILE: ([], list, "InitCommands"),
        HISTORY_FILE: ([], list, "InitHistory"),
        MEMORY_FILE: ({}, dict, "InitMemory"),
        SYNC_STATUS_FILE: (
            {
                "auto_sync_enabled": False,
                "last_successful_sync_timestamp": None,
                "auto_sync_interval_hours": 24,
            },
            dict,
            "InitSyncStatus",
        ),
    }

    for file_path, (
        default_content,
        expected_type,
        log_prefix_short,
    ) in files_to_initialize_or_verify.items():
        if not os.path.exists(file_path):
            save_json_file(file_path, default_content, log_prefix_short)
            log_event(f"{file_path} initialized.", "info", AGENT_LOG_PREFIX)
        else:
            # Check if file is empty, if so, re-initialize
            if os.path.getsize(file_path) == 0:
                log_event(
                    f"{file_path} is empty. Re-initializing.",
                    "warning",
                    AGENT_LOG_PREFIX,
                )
                save_json_file(file_path, default_content, log_prefix_short)
            else:
                loaded_content = load_json_file(
                    file_path, None, f"InitCheck{log_prefix_short[4:]}"
                )
                if loaded_content is None or not isinstance(
                    loaded_content, expected_type
                ):
                    log_event(
                        f"{file_path} is not a {expected_type.__name__} or is corrupted/unreadable. Re-initializing.",
                        "warning",
                        AGENT_LOG_PREFIX,
                    )
                    save_json_file(file_path, default_content, log_prefix_short)
                elif (
                    file_path == SYNC_STATUS_FILE
                ):  # Specific check for SYNC_STATUS_FILE keys
                    if not all(k in loaded_content for k in default_content.keys()):
                        log_event(
                            f"{SYNC_STATUS_FILE} is missing essential keys. Re-initializing.",
                            "warning",
                            AGENT_LOG_PREFIX,
                        )
                        save_json_file(
                            SYNC_STATUS_FILE, default_content, log_prefix_short
                        )
                    else:
                        log_event(
                            f"{file_path} exists and appears valid.",
                            "debug",
                            AGENT_LOG_PREFIX,
                        )
                else:
                    log_event(
                        f"{file_path} exists and appears valid.",
                        "debug",
                        AGENT_LOG_PREFIX,
                    )

    global agent_memory_state
    agent_memory_state = load_memory()  # Load memory after ensuring files are okay
    log_event(
        "Katana data file initialization/verification complete.",
        "info",
        AGENT_LOG_PREFIX,
    )


# --- Command Processing ---
def process_pending_commands():
    """
    Loads commands from COMMANDS_FILE, processes new ones.
    For now, "processing" means logging them and adding to history.
    Actual command execution logic would go here.
    """
    log_event("Checking for pending commands...", "debug", AGENT_LOG_PREFIX)
    commands_on_disk = load_commands_from_file()

    if not isinstance(commands_on_disk, list):
        log_event(
            f"Command file {COMMANDS_FILE} does not contain a list. Skipping processing cycle.",
            "error",
            AGENT_LOG_PREFIX,
        )
        return

    new_commands_found = False
    history_modified = False
    current_history = load_history()  # Load history once per cycle

    for command in commands_on_disk:
        command_id = command.get("command_id")
        if not command_id:
            log_event(
                f"Found command without ID: {command}. Skipping.",
                "warning",
                AGENT_LOG_PREFIX,
            )
            continue

        if command_id not in processed_command_ids:
            new_commands_found = True
            log_event(
                f"Processing new command ID: {command_id}, Type: {command.get('command_details', {}).get('command_type', 'N/A')}",
                "info",
                AGENT_LOG_PREFIX,
            )

            # Simulate processing: Update status and add to history
            command["status"] = "processed_by_agent"
            command["timestamp_processed_agent"] = datetime.datetime.now(
                datetime.timezone.utc
            ).isoformat()

            # Add to history (simple list append for now)
            current_history.append(command)
            history_modified = True

            processed_command_ids.add(command_id)  # Mark as processed for this session

            # TODO: Implement actual command execution logic here based on command_details
            # e.g., if command.get('command_details', {}).get('source') == 'trader_api':
            #           handle_trader_command(command)
            result = command_handler.handle(
                command.get("command_details", {}).get("command_type")
            )
            status_logger.log_status(result)

    if new_commands_found:
        # If commands were processed, we might want to update the commands.json file
        # Option 1: Remove processed commands from commands.json (acting as a queue)
        # Option 2: Keep them but update their status (acting as a log, history more detailed)
        # For now, let's choose Option 2 for simplicity and to see status update in file.
        if save_commands_to_file(commands_on_disk):  # Save back with updated statuses
            log_event(
                f"Updated command statuses in {COMMANDS_FILE}.",
                "info",
                AGENT_LOG_PREFIX,
            )
        else:
            log_event(
                f"Failed to update command statuses in {COMMANDS_FILE}.",
                "error",
                AGENT_LOG_PREFIX,
            )

        if history_modified:
            if save_history(current_history):
                log_event(
                    f"Saved {len(current_history)} items to history file.",
                    "info",
                    AGENT_LOG_PREFIX,
                )
            else:
                log_event(
                    f"Failed to save history to {HISTORY_FILE}.",
                    "error",
                    AGENT_LOG_PREFIX,
                )

    else:
        log_event("No new commands to process.", "debug", AGENT_LOG_PREFIX)


def agent_main_loop(loop_interval_seconds=10):
    """Main loop for the agent to periodically check for commands."""
    log_event(
        f"Katana Agent started. Will check for commands every {loop_interval_seconds} seconds.",
        "info",
        AGENT_LOG_PREFIX,
    )
    try:
        while True:
            try:
                process_pending_commands()
                # TODO: Add other periodic tasks here (e.g., sync, memory cleanup)
                time.sleep(loop_interval_seconds)
            except Exception as e:
                status_logger.log_status(f"[ERROR] {e}")
    except KeyboardInterrupt:
        log_event(
            "Katana Agent shutting down due to user interrupt.",
            "info",
            AGENT_LOG_PREFIX,
        )
    except Exception as e:
        log_event(
            f"Katana Agent encountered a critical error: {e}",
            "critical",
            AGENT_LOG_PREFIX,
        )
        # import traceback
        # log_event(traceback.format_exc(), "error", AGENT_LOG_PREFIX) # For detailed debugging
    finally:
        log_event("Katana Agent loop terminated.", "info", AGENT_LOG_PREFIX)


if __name__ == "__main__":
    log_event("katana_agent.py starting...", "info", AGENT_LOG_PREFIX)
    initialize_katana_files()
    log_event(
        "katana_agent.py: File initialization complete.", "info", AGENT_LOG_PREFIX
    )

    # Load current memory state into global
    agent_memory_state = load_memory()
    log_event(
        f"katana_agent.py: Current memory state: {json.dumps(agent_memory_state)}",
        "debug",
        AGENT_LOG_PREFIX,
    )

    if SELF_HEALING_ENABLED:
        log_event(
            "Attempting to start Self-Healing Orchestrator...", "info", AGENT_LOG_PREFIX
        )
        try:
            orchestrator = SelfHealingOrchestrator()
            if orchestrator.is_enabled:
                healing_thread = threading.Thread(
                    target=orchestrator.start, name="SelfHealingThread", daemon=True
                )
                healing_thread.start()
                log_event(
                    "Self-Healing Orchestrator started in a separate thread.",
                    "info",
                    AGENT_LOG_PREFIX,
                )
            else:
                log_event(
                    "Self-Healing Orchestrator is configured but disabled internally. Not starting thread.",
                    "warning",
                    AGENT_LOG_PREFIX,
                )
        except Exception as e:
            log_event(
                f"Failed to initialize or start Self-Healing Orchestrator: {e}",
                "error",
                AGENT_LOG_PREFIX,
            )
    else:
        log_event(
            "Self-Healing module is not available. Skipping orchestrator start.",
            "info",
            AGENT_LOG_PREFIX,
        )

    # Start the main command processing loop
    agent_main_loop(loop_interval_seconds=5)  # Check every 5 seconds for testing
