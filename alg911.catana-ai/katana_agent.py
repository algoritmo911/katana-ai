import json
import os
import datetime
# import time # Not used
import uuid # For generating command IDs if needed
# import traceback # Not used
import katana_key_manager as key_manager # Added for key management integration

# --- File Paths ---
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
COMMANDS_FILE = os.path.join(SCRIPT_DIR, "katana.commands.json")
MEMORY_FILE = os.path.join(SCRIPT_DIR, "katana_memory.json")
HISTORY_FILE = os.path.join(SCRIPT_DIR, "katana.history.json")
KEYS_FILE = os.path.join(SCRIPT_DIR, "katana_keys.json") # Added for key management
EVENTS_LOG_FILE = os.path.join(SCRIPT_DIR, "katana_events.log")
SYNC_STATUS_FILE = os.path.join(SCRIPT_DIR, "sync_status.json")
AGENT_LOG_PREFIX = "[KatanaAgent_MCP_v1]"

# --- Default Memory Structure ---
DEFAULT_MEMORY_STRUCTURE = {
    "core_profile": {
        "agent_name": "Katana",
        "agent_version": "0.1.0",
        "status": "nominal"
    },
    "conversation_history": [],
    "knowledge_base": {},
    "user_preferences": {},
    "transient_memory": {}
}

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
    global DEFAULT_MEMORY_STRUCTURE
    loaded_data = load_json_file(MEMORY_FILE, DEFAULT_MEMORY_STRUCTURE, "MemoryLoad")

    if not isinstance(loaded_data, dict) or not loaded_data: # If not a dict or empty
        log_event(f"Memory file {MEMORY_FILE} content was not a valid dictionary or was empty. Initializing with default structure.", "warning")
        agent_memory_state = DEFAULT_MEMORY_STRUCTURE.copy() # Use a copy
    else:
        agent_memory_state = loaded_data
        # Ensure all top-level keys from default structure are present
        updated = False
        for key, default_value in DEFAULT_MEMORY_STRUCTURE.items():
            if key not in agent_memory_state:
                agent_memory_state[key] = default_value
                updated = True
        if updated:
            log_event(f"Memory file {MEMORY_FILE} was missing some default keys. They have been added.", "info")
            save_memory() # Save immediately if we had to add keys

    # Ensure agent_memory_state is always what we expect, even if file load somehow bypassed initial checks.
    # This is a fallback, primary handling is above.
    if not isinstance(agent_memory_state, dict) or not all(k in agent_memory_state for k in DEFAULT_MEMORY_STRUCTURE.keys()):
        log_event(f"Post-load check: Memory state is still not as expected. Resetting to default. Current state: {agent_memory_state}", "warning")
        agent_memory_state = DEFAULT_MEMORY_STRUCTURE.copy()
        save_memory() # Attempt to fix the file

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

    global DEFAULT_MEMORY_STRUCTURE
    files_to_initialize_or_verify = {
        COMMANDS_FILE: ([], list, "InitCommands"),
        HISTORY_FILE: ([], list, "InitHistory"),
        MEMORY_FILE: (DEFAULT_MEMORY_STRUCTURE.copy(), dict, "InitMemory"),
        SYNC_STATUS_FILE: ({"auto_sync_enabled": False, "last_successful_sync_timestamp": None, "auto_sync_interval_hours": 24}, dict, "InitSyncStatus"),
        KEYS_FILE: ({}, dict, "InitKeys") # Added for key management
    }

    for file_path, (default_content, expected_type, log_prefix) in files_to_initialize_or_verify.items():
        if not os.path.exists(file_path):
            save_json_file(file_path, default_content, log_prefix)
            log_event(f"{file_path} initialized.", "info")
        else:
            loaded_content = load_json_file(file_path, None, f"InitCheck{log_prefix[4:]}")
            if loaded_content is None or not isinstance(loaded_content, expected_type):
                log_event(f"{file_path} is not a {expected_type.__name__} or is corrupted/unreadable. Re-initializing.", "warning")
                save_json_file(file_path, default_content, log_prefix)
            elif file_path == MEMORY_FILE: # Specific check for MEMORY_FILE keys
                if not all(k in loaded_content for k in DEFAULT_MEMORY_STRUCTURE.keys()):
                    log_event(f"{MEMORY_FILE} is missing essential keys. Re-initializing with default structure.", "warning")
                    save_json_file(file_path, DEFAULT_MEMORY_STRUCTURE.copy(), log_prefix)
                # Ensure sub-keys of core_profile are also dicts if they exist (simple check)
                elif "core_profile" in loaded_content and not isinstance(loaded_content["core_profile"], dict):
                    log_event(f"{MEMORY_FILE} 'core_profile' is not a dictionary. Re-initializing memory.", "warning")
                    save_json_file(file_path, DEFAULT_MEMORY_STRUCTURE.copy(), log_prefix)
                else:
                    log_event(f"{file_path} exists and appears valid.", "debug")
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

    # Explicitly load memory to test the new loading logic and ensure agent_memory_state is populated
    current_memory = load_memory()
    log_event("katana_agent.py self-test: Current memory state after load: " + json.dumps(current_memory), "debug")

    # Example: Test re-initialization of a corrupted/old format memory file
    # log_event("katana_agent.py self-test: Simulating corrupted memory file...", "info")
    # with open(MEMORY_FILE, 'w') as f: f.write("{\"name\": \"Old Katana\"}") # Simulate old or minimal format
    # initialize_katana_files() # Should detect and fix/align
    # current_memory_after_fix = load_memory()
    # log_event("katana_agent.py self-test: Memory state after fix attempt: " + json.dumps(current_memory_after_fix), "debug")

    # --- Test Key Manager Integration ---
    log_event("katana_agent.py self-test: Testing Key Manager integration...", "info")

    # Ensure keys file is clean for this test part, as key_manager self-test might have written to it
    # For a real scenario, katana_keys.json wouldn't be cleared like this.
    # This is just to ensure this specific agent self-test is predictable.
    # key_manager._save_keys_data({}) # Accessing private method for test setup - not ideal but for self-contained test.
    # A better way would be a dedicated clear function in key_manager or rely on initialize_katana_files if it's first run.
    # For now, we'll assume initialize_katana_files created it empty if it wasn't there.

    service_name = "TestServiceExternal"
    key_name_agent = "agent_api_key"
    key_value_agent = "dummy_agent_key_value_456"

    log_event(f"katana_agent.py self-test: Setting a dummy key '{key_name_agent}' for service '{service_name}'...", "info")
    key_manager.set_key(service_name, key_name_agent, key_value_agent)

    log_event(f"katana_agent.py self-test: Retrieving key '{key_name_agent}' for service '{service_name}'...", "info")
    retrieved_key = key_manager.get_key(service_name, key_name_agent)

    if retrieved_key:
        log_event(f"katana_agent.py self-test: Retrieved key value: {retrieved_key}", "debug") # DEBUG for test
        log_event("katana_agent.py self-test: WARNING - Key value logged for demonstration purposes ONLY. Do NOT log real keys!", "warning")
    else:
        log_event(f"katana_agent.py self-test: Failed to retrieve key '{key_name_agent}' for '{service_name}'.", "error")

    log_event(f"katana_agent.py self-test: Deleting key '{key_name_agent}' for service '{service_name}'...", "info")
    key_manager.delete_key(service_name, key_name_agent)
    retrieved_key_after_delete = key_manager.get_key(service_name, key_name_agent)
    if retrieved_key_after_delete is None:
        log_event(f"katana_agent.py self-test: Key '{key_name_agent}' successfully deleted (or was not there).", "info")
    else:
        log_event(f"katana_agent.py self-test: Key '{key_name_agent}' still present after attempted delete.", "error")


    log_event("katana_agent.py self-test: Key Manager integration test complete.", "info")
    # --- End Test Key Manager Integration ---

    # To verify, after running this, one would check katana_events.log and the content of the .json files.
    # Example: Create a dummy corrupted command file to test re-initialization
    # with open(COMMANDS_FILE, 'w') as f: f.write("corrupted")
    # initialize_katana_files() # Should detect and fix
    # print(load_commands())
