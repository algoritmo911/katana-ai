import json
import os
import datetime
# import time # Not used
import uuid # For generating command IDs if needed
# import traceback # Not used
import yaml
import platform # For katana-005

# --- File Paths ---
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
COMMANDS_FILE = os.path.join(SCRIPT_DIR, "katana.commands.json")
MEMORY_FILE = os.path.join(SCRIPT_DIR, "katana_memory.json")
HISTORY_FILE = os.path.join(SCRIPT_DIR, "katana.history.json")
EVENTS_LOG_FILE = os.path.join(SCRIPT_DIR, "katana_events.log")
SYNC_STATUS_FILE = os.path.join(SCRIPT_DIR, "sync_status.json")
DIAGNOSTIC_LOG_FILE = os.path.join(SCRIPT_DIR, "diagnostic_log.yaml") # Added for katana-005
AGENT_LOG_PREFIX = "[KatanaAgent_MCP_v1]"

# --- Global State ---
agent_memory_state = {} # In-memory representation of katana_memory.json
OUTDATED_COMMAND_THRESHOLD_HOURS = 24 # For katana-001

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

# --- Katana-001: Scan for outdated commands ---
def scan_for_outdated_commands():
    """
    Scans katana.commands.json for outdated "pending" commands and logs them.
    An outdated command is one that has been in "pending" status for longer than OUTDATED_COMMAND_THRESHOLD_HOURS.
    """
    log_event("Starting scan for outdated commands (katana-001)...", "info")
    commands = load_commands()
    if not isinstance(commands, list):
        log_event(f"Cannot scan outdated commands: {COMMANDS_FILE} does not contain a list.", "error")
        return

    now = datetime.datetime.now(datetime.timezone.utc)
    outdated_count = 0

    for command in commands:
        if isinstance(command, dict):
            command_id = command.get("command_id", "N/A")
            status = command.get("status")
            timestamp_str = command.get("timestamp")

            if status == "pending" and timestamp_str:
                try:
                    # Ensure timestamp is offset-aware for correct comparison
                    command_ts = datetime.datetime.fromisoformat(timestamp_str)
                    if command_ts.tzinfo is None:
                        # If timestamp is naive, assume it's UTC as per our intended standard for new commands
                        command_ts = command_ts.replace(tzinfo=datetime.timezone.utc)

                    age = now - command_ts
                    if age.total_seconds() > OUTDATED_COMMAND_THRESHOLD_HOURS * 3600:
                        outdated_count += 1
                        log_event(f"Outdated command found: ID {command_id}, Status: {status}, Age: {age}. Please review.", "warning")
                        # "Proposing replacement" for now is this log message.
                except ValueError:
                    log_event(f"Invalid timestamp format for command ID {command_id}: '{timestamp_str}'. Cannot determine if outdated.", "error")
            elif not timestamp_str and status == "pending":
                 log_event(f"Command ID {command_id} is 'pending' but has no timestamp. Cannot determine if outdated.", "warning")

    if outdated_count > 0:
        log_event(f"Scan complete. Found {outdated_count} outdated commands.", "info")
    else:
        log_event("Scan complete. No outdated commands found.", "info")

# --- Katana-002: Track sync_status.json ---
def check_sync_status():
    """
    Checks sync_status.json for rclone synchronization status and logs warnings if needed.
    """
    log_event("Starting sync status check (katana-002)...", "info")
    sync_status = load_json_file(SYNC_STATUS_FILE, None, "SyncStatusCheck")

    if sync_status is None:
        log_event(f"Cannot check sync status: {SYNC_STATUS_FILE} is missing or unreadable. This should have been initialized.", "error")
        return

    if not isinstance(sync_status, dict):
        log_event(f"Cannot check sync status: {SYNC_STATUS_FILE} does not contain a valid JSON object.", "error")
        return

    last_sync_str = sync_status.get("last_successful_sync_timestamp")
    auto_sync_enabled = sync_status.get("auto_sync_enabled", False)
    sync_interval_hours = sync_status.get("auto_sync_interval_hours", 24)

    if not auto_sync_enabled:
        log_event("Auto-sync is disabled. Manual sync checks may be required.", "info")
        # No further checks if auto-sync is off.
        # The task "if auto_sync_enabled is false but a sync is expected" is ambiguous.
        # For now, we just note it's off.
        return

    if last_sync_str is None:
        log_event("Sync status: `last_successful_sync_timestamp` is missing. Potential first run or issue.", "warning")
        return

    try:
        last_sync_ts = datetime.datetime.fromisoformat(last_sync_str)
        if last_sync_ts.tzinfo is None: # Ensure tz-aware
            last_sync_ts = last_sync_ts.replace(tzinfo=datetime.timezone.utc)

        now = datetime.datetime.now(datetime.timezone.utc)
        time_since_last_sync = now - last_sync_ts
        sync_interval_seconds = sync_interval_hours * 3600

        if time_since_last_sync.total_seconds() > sync_interval_seconds:
            log_event(f"Synchronization is overdue. Last sync: {last_sync_str} (over {sync_interval_hours} hours ago).", "warning")
        else:
            log_event(f"Synchronization status is OK. Last sync: {last_sync_str}.", "info")

    except ValueError:
        log_event(f"Invalid timestamp format for `last_successful_sync_timestamp`: '{last_sync_str}'.", "error")
    except TypeError: # Handles case where sync_interval_hours might not be a number
        log_event(f"Invalid format for `auto_sync_interval_hours`: '{sync_interval_hours}'. Must be a number.", "error")


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

# --- Agent Command Handlers (based on user feedback) ---
# Note: agent_memory_state is the global dictionary for memory.
# log_event is the existing logging function.

def handle_agent_get_config(command_params=None):
    # command_params is included for consistency, though not used in this version
    log_event("Processing 'get_agent_config' command internally.", "info")
    config_data = {
        "agent_version": "1.0.0-agent", # Distinct from UI backend version
        "status": "online", # Placeholder
        "last_config_retrieval_time_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "hostname": os.uname().nodename if hasattr(os, "uname") else "unknown", # Get actual hostname if possible
        "os_type": os.uname().sysname if hasattr(os, "uname") else "unknown",
        "max_cpu_usage_limit_pct": 75, # Example placeholder
        "max_memory_usage_limit_mb": 2048, # Example placeholder
        "active_tasks_count": 0, # Placeholder, agent needs logic to track this
        "environment_info": { # Renamed from environment_vars for clarity
            "KATANA_ENV_setting": os.environ.get("KATANA_ENV", "not_set"), # Example of reading actual env var
            "API_TOKEN_IS_SET": "True" if os.environ.get("KATANA_API_TOKEN") else "False", # Example
        },
        "monitored_files": { # Example of agent-specific config
            "commands_file": COMMANDS_FILE,
            "memory_file": MEMORY_FILE,
            "events_log_file": EVENTS_LOG_FILE
        }
    }
    # Ensure 'katana_config' key is used as expected by UI (KatanaStatus.js)
    agent_memory_state["katana_config"] = config_data
    save_memory() # Persist the updated memory
    log_event("Agent configuration updated in agent_memory_state['katana_config'] and saved.", "info")
    return config_data

def handle_agent_reload_settings(command_params=None):
    log_event("Processing 'reload_core_settings' command internally.", "info")
    # Placeholder action: re-initialize core files, as discussed.
    try:
        initialize_katana_files() # This re-checks/re-creates files if needed
        log_event("Core settings reload attempted (file initialization re-triggered).", "info")
        agent_memory_state["last_settings_reload_status"] = "success"
        agent_memory_state["last_settings_reload_time_utc"] = datetime.datetime.now(datetime.timezone.utc).isoformat()
        save_memory()
        return {"status": "success", "message": "Core settings reload process initiated (file initialization re-triggered)."}
    except Exception as e:
        log_event(f"Error during settings reload attempt: {str(e)}", "error")
        agent_memory_state["last_settings_reload_status"] = "error"
        agent_memory_state["last_settings_reload_error"] = str(e)
        agent_memory_state["last_settings_reload_time_utc"] = datetime.datetime.now(datetime.timezone.utc).isoformat()
        save_memory()
        return {"status": "error", "message": f"Failed to reload settings: {str(e)}"}

def handle_agent_ping_received(command_params=None):
    log_event("Processing 'ping_received' command internally.", "info")
    agent_memory_state["last_agent_ping_processed_utc"] = datetime.datetime.now(datetime.timezone.utc).isoformat()
    if command_params:
        log_event(f"Ping command parameters: {command_params}", "debug")
    save_memory()
    return {"status": "success", "message": "Ping processed by agent."}

# --- Stub for future command processing loop ---
def process_agent_command(command_object):
    action = command_object.get("action")
    params = command_object.get("parameters")
    command_id = command_object.get("command_id", "unknown_id")

    log_event(f"Agent attempting to process command: {command_id}, Action: {action}", "info")
    result = {"status": "unknown_action", "message": f"Action '{action}' not recognized by agent."}

    if action == "get_agent_config":
        get_config_result = handle_agent_get_config(params)
        result = {"status": "success", "data": get_config_result}
    elif action == "reload_core_settings":
        result = handle_agent_reload_settings(params)
    elif action == "ping_received_from_ui_backend":
        result = handle_agent_ping_received(params)
    else:
        log_event(f"Agent received unknown action: '{action}' for command_id: {command_id}", "warning")

    log_event(f"Agent processing finished for command: {command_id}. Result status: {result.get('status')}", "info")

    # --- Katana-003: Log command to history ---
    try:
        history = load_history()
        if not isinstance(history, list):
            log_event(f"Command history file {HISTORY_FILE} is not a list. Re-initializing for safety.", "warning")
            history = [] # Reset to empty list if corrupted

        history_entry = {
            "command_id": command_id,
            "action": action,
            "parameters": params, # Storing raw params, ensure no sensitive data if this becomes an issue
            "processed_timestamp_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
            "processing_status": result.get("status", "unknown")
        }
        history.append(history_entry)
        save_history(history)
        log_event(f"Command {command_id} logged to history.", "debug")
    except Exception as e:
        log_event(f"Failed to log command {command_id} to history: {e}", "error")

    return result

# --- Katana-003: Analyze command history for patterns ---
def analyze_command_history(max_history_items_to_check=50, pattern_threshold=3, lookback_window_hours=24):
    """
    Analyzes katana.history.json for frequently repeated command patterns (simple check).
    Logs a suggestion if a pattern is detected.
    """
    log_event("Starting command history analysis for patterns (katana-003)...", "info")
    history = load_history()

    if not isinstance(history, list) or not history:
        log_event("Command history is empty or invalid. No patterns to analyze.", "info")
        return

    # Consider only recent history for performance and relevance
    recent_history = []
    now = datetime.datetime.now(datetime.timezone.utc)
    lookback_timedelta = datetime.timedelta(hours=lookback_window_hours)

    # Iterate in reverse to get most recent items first, up to max_history_items_to_check
    for entry in reversed(history):
        if len(recent_history) >= max_history_items_to_check:
            break
        try:
            ts_str = entry.get("processed_timestamp_utc")
            if ts_str:
                entry_ts = datetime.datetime.fromisoformat(ts_str)
                if entry_ts.tzinfo is None:
                    entry_ts = entry_ts.replace(tzinfo=datetime.timezone.utc)
                if (now - entry_ts) <= lookback_timedelta:
                    recent_history.insert(0, entry) # Keep chronological order
        except (ValueError, TypeError):
            log_event(f"Skipping history entry with invalid timestamp: {entry.get('command_id')}", "debug")
            continue

    if len(recent_history) < pattern_threshold: # Need at least `pattern_threshold` items to find a pattern
        log_event(f"Not enough recent history items ({len(recent_history)}) to analyze for patterns (threshold: {pattern_threshold}).", "info")
        return

    # Simple pattern detection: count occurrences of the same "action"
    action_counts = {}
    for entry in recent_history:
        action = entry.get("action")
        if action:
            action_counts[action] = action_counts.get(action, 0) + 1

    for action, count in action_counts.items():
        if count >= pattern_threshold:
            log_event(f"Potential repetitive pattern detected: Action '{action}' executed {count} times recently within the last {lookback_window_hours} hours (out of {len(recent_history)} commands checked). Consider creating a template or automation.", "info")

    log_event("Command history analysis complete.", "info")

# --- Katana-005: Startup Diagnostics ---
def log_diagnostic_entry(check_name, status, message, diagnostic_results_list):
    """Helper to create and append a diagnostic entry."""
    entry = {
        "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "check_name": check_name,
        "status": status, # e.g., "OK", "ERROR", "INFO"
        "message": message
    }
    diagnostic_results_list.append(entry)
    # Also log to main event log for visibility during startup sequence
    log_event(f"Diagnostic [{check_name}]: {status} - {message}", level="debug" if status == "OK" else "info")


def run_startup_diagnostics():
    """
    Runs startup diagnostics and logs them to diagnostic_log.yaml.
    """
    log_event("Running startup diagnostics (katana-005)...", "info")
    diagnostic_results = []

    # 1. Check Python Version
    python_version = platform.python_version()
    log_diagnostic_entry("Python Version", "INFO", f"Running on Python {python_version}", diagnostic_results)

    # 2. Check OS Type
    os_type = platform.system()
    os_release = platform.release()
    log_diagnostic_entry("Operating System", "INFO", f"{os_type} {os_release}", diagnostic_results)

    # 3. Check essential file accessibility
    essential_files = {
        "Commands File": COMMANDS_FILE,
        "Memory File": MEMORY_FILE,
        "History File": HISTORY_FILE,
        "Events Log File": EVENTS_LOG_FILE,
        "Sync Status File": SYNC_STATUS_FILE
        # DIAGNOSTIC_LOG_FILE itself is not checked here as we are about to write to it
    }

    for name, path in essential_files.items():
        if os.path.exists(path):
            if os.access(path, os.R_OK) and os.access(path, os.W_OK): # Check read/write
                log_diagnostic_entry(name, "OK", f"File exists and is accessible: {path}", diagnostic_results)
            elif os.access(path, os.R_OK):
                 log_diagnostic_entry(name, "WARNING", f"File exists but may not be writable: {path}", diagnostic_results)
            else:
                log_diagnostic_entry(name, "WARNING", f"File exists but may not be readable: {path}", diagnostic_results)

        else:
            # This might be OK if initialize_katana_files is expected to create them right after diagnostics
            # However, initialize_katana_files is called *before* diagnostics in the current plan.
            # So, if a file is missing here, it means initialization might have issues or it's not managed by it.
            log_diagnostic_entry(name, "ERROR", f"File is missing: {path}. Ensure it's initialized.", diagnostic_results)

    # 4. Check agent_memory_state (if loaded)
    if agent_memory_state: # Check if it's not empty
        log_diagnostic_entry("Agent Memory State", "OK", "agent_memory_state is loaded (not empty).", diagnostic_results)
    else:
        # This could be normal on a very first run before memory is ever saved.
        log_diagnostic_entry("Agent Memory State", "INFO", "agent_memory_state is currently empty.", diagnostic_results)

    # 5. Log directory for DIAGNOSTIC_LOG_FILE (ensure it can be created)
    try:
        diag_dir = os.path.dirname(DIAGNOSTIC_LOG_FILE)
        if diag_dir and not os.path.exists(diag_dir):
            os.makedirs(diag_dir, exist_ok=True)
            log_diagnostic_entry("Diagnostic Log Directory", "OK", f"Created directory for diagnostic log: {diag_dir}", diagnostic_results)
        elif not diag_dir: # Root directory
             log_diagnostic_entry("Diagnostic Log Directory", "OK", "Diagnostic log is in the root script directory.", diagnostic_results)
        else: # Directory exists
             log_diagnostic_entry("Diagnostic Log Directory", "OK", f"Directory for diagnostic log exists: {diag_dir}", diagnostic_results)
    except Exception as e:
        log_diagnostic_entry("Diagnostic Log Directory", "ERROR", f"Could not create/access diagnostic log directory {os.path.dirname(DIAGNOSTIC_LOG_FILE)}: {e}", diagnostic_results)
        # Fallback: attempt to log diagnostics to main event log if YAML fails
        log_event("CRITICAL: Could not write to diagnostic_log.yaml due to directory issue.", "error")
        for entry in diagnostic_results:
            log_event(f"FALLBACK_DIAG: {entry['check_name']} - {entry['status']} - {entry['message']}", "error")
        return # Skip writing to YAML file

    # Write to diagnostic_log.yaml (overwrite existing)
    try:
        with open(DIAGNOSTIC_LOG_FILE, "w") as f:
            yaml.dump({"startup_diagnostics_run_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(), "checks": diagnostic_results}, f, indent=2, sort_keys=False, default_flow_style=False)
        log_event(f"Startup diagnostics successfully written to {DIAGNOSTIC_LOG_FILE}", "info")
    except Exception as e:
        log_event(f"Failed to write startup diagnostics to {DIAGNOSTIC_LOG_FILE}: {e}", "error")
        # Fallback: log all collected diagnostic messages to the main event log
        for entry in diagnostic_results:
            log_event(f"FALLBACK_DIAG: {entry['check_name']} - {entry['status']} - {entry['message']}", "error")

if __name__ == '__main__':
    # Initialize logging as early as possible
    log_event("katana_agent.py self-test: Starting agent initialization and diagnostics...", "info")

    initialize_katana_files()
    log_event("katana_agent.py self-test: File initialization complete.", "info")

    # --- Katana-005: Run startup diagnostics (must be after file init) ---
    run_startup_diagnostics() # Added for katana-005

    # --- Katana-001: Scan for outdated commands (called at startup for now) ---
    scan_for_outdated_commands() # Added for katana-001

    # --- Katana-002: Check sync status (called at startup for now) ---
    check_sync_status() # Added for katana-002

    # --- Katana-003: Test command history logging and analysis ---
    # Simulate processing a few commands to populate history for analysis
    log_event("Simulating command processing for history generation (katana-003)...", "info")
    test_command_1 = {"command_id": "hist-test-001", "action": "get_agent_config", "parameters": {}}
    test_command_2 = {"command_id": "hist-test-002", "action": "reload_core_settings", "parameters": {}}
    test_command_3 = {"command_id": "hist-test-003", "action": "get_agent_config", "parameters": {"detail": "full"}}
    test_command_4 = {"command_id": "hist-test-004", "action": "get_agent_config", "parameters": {"detail": "summary"}}

    process_agent_command(test_command_1)
    # Simulate a small delay so timestamps are different
    # import time; time.sleep(0.01) # Not strictly necessary for this test but good practice if timestamps needed to be distinct for logic
    process_agent_command(test_command_2)
    # time.sleep(0.01)
    process_agent_command(test_command_3)
    # time.sleep(0.01)
    process_agent_command(test_command_4)

    analyze_command_history() # Added for katana-003

    log_event("katana_agent.py self-test: Current memory state: " + json.dumps(agent_memory_state), "debug")

    # To verify, after running this, one would check katana_events.log and the content of the .json files.
    # Example: Create a dummy corrupted file to test re-initialization
    # with open(COMMANDS_FILE, 'w') as f: f.write("corrupted")
    # initialize_katana_files() # Should detect and fix
    # print(load_commands())

    # Example of how to add a new command with timestamp and status for testing katana-001
    # new_cmds = load_commands()
    # if isinstance(new_cmds, list):
    #     now_ts = datetime.datetime.now(datetime.timezone.utc)
    #     past_ts_outdated = now_ts - datetime.timedelta(hours=OUTDATED_COMMAND_THRESHOLD_HOURS + 5)
    #     new_cmds.append({
    #         "command_id": f"cmd-{uuid.uuid4()}",
    #         "action": "sample_action_outdated",
    #         "parameters": {"test": True},
    #         "timestamp": past_ts_outdated.isoformat(),
    #         "status": "pending"
    #     })
    #     new_cmds.append({
    #         "command_id": f"cmd-{uuid.uuid4()}",
    #         "action": "sample_action_fresh",
    #         "parameters": {"test": True},
    #         "timestamp": now_ts.isoformat(),
    #         "status": "pending"
    #     })
    #     save_commands(new_cmds)
    #     log_event("Added test commands to katana.commands.json for katana-001 scan.", "info")
    # else:
    #     log_event("Could not add test commands as katana.commands.json is not a list.", "warning")
