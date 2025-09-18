import json
import os
import datetime
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
AGENT_LOG_PREFIX = "[KatanaAgent_MCP_v1]"

# --- Global State ---
agent_memory_state = {} # In-memory representation of katana_memory.json

# --- Logging ---
def log_event(event_message, level="info"):
    timestamp = datetime.datetime.now(datetime.timezone.utc).isoformat()
    log_entry_line = f"[{timestamp}] {level.upper()}: {AGENT_LOG_PREFIX} {event_message}\n"
    try:
        log_dir = os.path.dirname(EVENTS_LOG_FILE)
        if log_dir and not os.path.exists(log_dir): # Ensure directory exists for the log file
            os.makedirs(log_dir, exist_ok=True)
        with open(EVENTS_LOG_FILE, "a") as f:
            f.write(log_entry_line)
    except Exception as e:
        print(f"CRITICAL_LOG_FAILURE: {log_entry_line} (Error: {e})") # Fallback to stdout

# --- JSON File I/O Utilities ---
def load_json_file(file_path, default_value, log_prefix="JSONLoad"):
    # Reduced verbosity for normal loads, will log if issue found.
    # log_event(f"Attempting to load JSON from {file_path}", "debug")
    if not os.path.exists(file_path):
        log_event(f"[{log_prefix}] File not found: {file_path}. Returning default.", "info")
        return default_value
    try:
        with open(file_path, "r") as f:
            content = f.read()
            if not content.strip(): # File is empty
                log_event(f"[{log_prefix}] File is empty: {file_path}. Returning default.", "info")
                return default_value
            data = json.loads(content)
        # log_event(f"[{log_prefix}] Loaded successfully from {file_path}.", "debug")
        return data
    except json.JSONDecodeError:
        log_event(f"[{log_prefix}] Error decoding JSON from {file_path}. Returning default.", "error")
        return default_value
    except Exception as e: # Catch any other read errors
        log_event(f"[{log_prefix}] Unexpected error loading {file_path}: {e}. Returning default.", "error")
        return default_value

def save_json_file(file_path, data, log_prefix="JSONSave", indent=2):
    # log_event(f"Attempting to save JSON to {file_path}", "debug")
    try:
        dir_name = os.path.dirname(file_path)
        if dir_name and not os.path.exists(dir_name): # Create directory if it doesn't exist
            os.makedirs(dir_name, exist_ok=True)
        with open(file_path, "w") as f:
            json.dump(data, f, indent=indent)
        log_event(f"[{log_prefix}] Successfully saved JSON to {file_path}.", "info")
        return True
    except Exception as e:
        log_event(f"[{log_prefix}] Error saving JSON to {file_path}: {e}", "error")
        return False

# --- Katana Data File Specific Functions ---
def load_memory():
    global agent_memory_state
    loaded_data = load_json_file(MEMORY_FILE, {}, "MemoryLoad")
    # Ensure agent_memory_state is always a dict, even if file was corrupted and load_json_file returned None then {}
    agent_memory_state = loaded_data if isinstance(loaded_data, dict) else {}
    if not isinstance(loaded_data, dict):
         log_event(f"Memory file {MEMORY_FILE} content was not a dictionary. Resetting memory state.", "warning")
    return agent_memory_state

def save_memory():
    global agent_memory_state
    return save_json_file(MEMORY_FILE, agent_memory_state, "MemorySave")

def load_commands(): return load_json_file(COMMANDS_FILE, [], "CommandsLoad")
def save_commands(commands_list): return save_json_file(COMMANDS_FILE, commands_list, "CommandsSave")

def load_history(): return load_json_file(HISTORY_FILE, [], "HistoryLoad")
def save_history(history_list): return save_json_file(HISTORY_FILE, history_list, "HistorySave")


# --- File Initialization (for MCP_v1) ---
def initialize_katana_files():
    log_event("Initializing/Verifying Katana data files for MCP_v1...", "info")

    files_to_initialize_or_verify = {
        COMMANDS_FILE: ([], list, "InitCommands"),
        HISTORY_FILE: ([], list, "InitHistory"),
        MEMORY_FILE: ({}, dict, "InitMemory"),
        SYNC_STATUS_FILE: ({"auto_sync_enabled": False, "last_successful_sync_timestamp": None, "auto_sync_interval_hours": 24}, dict, "InitSyncStatus")
    }

    for file_path, (default_content, expected_type, log_prefix) in files_to_initialize_or_verify.items():
        if not os.path.exists(file_path):
            save_json_file(file_path, default_content, log_prefix)
            log_event(f"{file_path} initialized.", "info")
        else:
            loaded_content = load_json_file(file_path, None, f"InitCheck{log_prefix[4:]}") # Use None to distinguish file error vs empty
            if loaded_content is None or not isinstance(loaded_content, expected_type): # Check type or if load failed critically
                log_event(f"{file_path} is not a {expected_type.__name__} or is corrupted/unreadable. Re-initializing.", "warning")
                save_json_file(file_path, default_content, log_prefix)
            elif file_path == SYNC_STATUS_FILE: # Specific check for SYNC_STATUS_FILE keys
                 if not all(k in loaded_content for k in default_content.keys()):
                    log_event(f"{SYNC_STATUS_FILE} is missing essential keys. Re-initializing.", "warning")
                    save_json_file(SYNC_STATUS_FILE, default_content, log_prefix)
                 else:
                    log_event(f"{file_path} exists and appears valid.", "debug")
            else:
                log_event(f"{file_path} exists and appears valid.", "debug")

    # Ensure global memory state is loaded after checks
    global agent_memory_state
    agent_memory_state = load_memory()
    log_event("Katana data file initialization/verification complete.", "info")

if __name__ == '__main__':
    log_event("katana_agent.py self-test: Initializing files...", "info")
    initialize_katana_files()
    log_event("katana_agent.py self-test: File initialization complete.", "info")
    log_event("katana_agent.py self-test: Current memory state: " + json.dumps(agent_memory_state), "debug")
    # To verify, after running this, one would check katana_events.log and the content of the .json files.
    # Example: Create a dummy corrupted file to test re-initialization
    # with open(COMMANDS_FILE, 'w') as f: f.write("corrupted")
    # initialize_katana_files() # Should detect and fix
    # print(load_commands())
