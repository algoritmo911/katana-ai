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
    global agent_memory_state  # agent_memory_state is initially {}
    loaded_data = load_json_file(MEMORY_FILE, {}, "MemoryLoad") # Default to {} if file missing/corrupt

    agent_memory_state.clear() # Clear the existing global dict in-place

    if isinstance(loaded_data, dict):
        agent_memory_state.update(loaded_data) # Update with new data in-place
    else:
        # This case should ideally not be reached if load_json_file always returns a dict or the default_value (which is {} here)
        # However, as a safeguard:
        log_event(f"Memory file {MEMORY_FILE} content was not a valid dictionary after loading. State remains empty.", "warning")
        # agent_memory_state is already empty due to clear()

    # Ensure essential keys are present even if loaded_data was minimal (e.g. just "{}")
    # This logic is duplicated in handle_load_state, consider centralizing if it grows
    if "dialog_history" not in agent_memory_state:
        agent_memory_state["dialog_history"] = []
    if "user_settings" not in agent_memory_state:
        agent_memory_state["user_settings"] = {}

    return agent_memory_state # Return reference to the modified global dict

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

# --- Agent Command Handlers (based on user feedback) ---
# Note: agent_memory_state is the global dictionary for memory.
# log_event is the existing logging function.

# --- Memory State Command Handlers ---
def handle_save_state(command_params=None):
    """Saves the current agent_memory_state to MEMORY_FILE and updates HISTORY_FILE."""
    global agent_memory_state
    log_event("Processing 'save_state' command.", "info")
    try:
        # Ensure dialog_history key exists in agent_memory_state
        if "dialog_history" not in agent_memory_state:
            agent_memory_state["dialog_history"] = []
            log_event("'dialog_history' key not found in agent_memory_state, initialized to empty list.", "debug")

        # Save the main memory state
        if save_memory():
            # Also save the dialog_history part to katana.history.json for consistency or external use
            if save_history(agent_memory_state.get("dialog_history", [])):
                log_event("Successfully saved agent state and synchronized history file.", "info")
                return {"status": "success", "message": "Your settings and conversation history have been saved."}
            else:
                log_event("Saved agent memory, but failed to save history file.", "warning")
                return {"status": "partial_success", "message": "Your settings were saved, but there was an issue saving the conversation history details. Please try again or contact support if this persists."}
        else:
            log_event("Failed to save agent memory state.", "error")
            return {"status": "error", "message": "Sorry, I couldn't save your settings and history. Please try again. If the problem continues, please let support know."}
    except Exception as e:
        log_event(f"Error during save_state: {str(e)}", "error")
        return {"status": "error", "message": "An unexpected problem occurred while trying to save your state. Please try again."}

def handle_load_state(command_params=None):
    """Loads agent_memory_state from MEMORY_FILE and updates HISTORY_FILE."""
    global agent_memory_state
    log_event("Processing 'load_state' command.", "info")
    try:
        # load_memory() updates the global agent_memory_state, ensures it's a dictionary,
        # and initializes essential keys like 'dialog_history' and 'user_settings'.
        load_memory()

        # Synchronize katana.history.json with the loaded dialog history
        # agent_memory_state.get("dialog_history", []) is safe because load_memory ensures the key.
        if save_history(agent_memory_state["dialog_history"]):
            log_event("Successfully loaded agent state and synchronized history file.", "info")
            return {"status": "success", "message": "Your settings and conversation history have been loaded."}
        else:
            log_event("Loaded agent memory, but failed to update history file from loaded state.", "warning")
            return {"status": "partial_success", "message": "Your settings were loaded, but there was an issue synchronizing the conversation history. Some past messages might not be up to date."}

    except Exception as e:
        log_event(f"Error during load_state: {str(e)}", "error")
        # In case of error, try to ensure agent_memory_state is at least a valid dict
        # load_memory called at the start of the try block should have already ensured agent_memory_state is a dict
        # and has essential keys. The save_memory() call here is a last resort if something truly unexpected happened.
        if not isinstance(agent_memory_state, dict): # Should ideally not be needed
            agent_memory_state = {}
            agent_memory_state.setdefault("dialog_history", [])
            agent_memory_state.setdefault("user_settings", {})

        save_memory() # Try to save a minimal valid state to prevent further issues on next load.
        return {"status": "error", "message": "An unexpected problem occurred while trying to load your state. Some settings or history might be missing. Please try again or initialize a new state if needed."}

def handle_clear_state(command_params=None):
    """Clears dialog history and user settings from agent_memory_state and corresponding files."""
    global agent_memory_state
    log_event("Processing 'clear_state' command.", "info")
    try:
        # Preserve other potentially important keys in agent_memory_state (like 'name', 'katana_config', etc.)
        # Only clear specific parts: 'dialog_history' and 'user_settings'
        original_name = agent_memory_state.get("name", "Katana V2") # Preserve name
        original_config = agent_memory_state.get("katana_config", {}) # Preserve config

        agent_memory_state["dialog_history"] = []
        agent_memory_state["user_settings"] = {}
        # Restore preserved keys
        agent_memory_state["name"] = original_name
        if original_config: # Only restore if it existed
             agent_memory_state["katana_config"] = original_config

        # For other keys that might have been added by other processes, we can either list them explicitly
        # or re-initialize agent_memory_state more carefully.
        # For now, this targeted clear is safer.

        if save_memory(): # Save the modified agent_memory_state
            if save_history([]): # Clear the history file as well
                log_event("Successfully cleared agent state (history and user settings).", "info")
                return {"status": "success", "message": "Your settings and conversation history have been cleared."}
            else:
                log_event("Cleared agent memory state, but failed to clear history file.", "warning")
                return {"status": "partial_success", "message": "Your settings were cleared, but there was an issue clearing the conversation history details. Some past messages might still appear temporarily."}
        else:
            log_event("Failed to save cleared agent memory state.", "error")
            return {"status": "error", "message": "Sorry, I couldn't save the cleared state. Some settings or history might not be fully cleared. Please try again."}
    except Exception as e:
        log_event(f"Error during clear_state: {str(e)}", "error")
        return {"status": "error", "message": "An unexpected problem occurred while trying to clear your state. Please try again."}

# --- Existing Agent Command Handlers ---
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
    # --- Memory State Commands ---
    elif action == "save_state":
        result = handle_save_state(params)
    elif action == "load_state":
        result = handle_load_state(params)
    elif action == "clear_state":
        result = handle_clear_state(params)
    else:
        log_event(f"Agent received unknown action: '{action}' for command_id: {command_id}", "warning")

    log_event(f"Agent processing finished for command: {command_id}. Result status: {result.get('status')}", "info")
    return result

# --- NLP Placeholder & Integration Point ---
def get_contextual_nlp_response(user_message_text, dialog_history):
    """
    Placeholder for NLP processing.
    Uses dialog_history for context to generate a response.
    """
    log_event(f"NLP processing message: '{user_message_text}' with history length: {len(dialog_history)}", "debug")

    # More advanced placeholder logic using history:
    user_message_lower = user_message_text.lower()
    name_identified_this_turn = None

    # Check for name identification patterns
    patterns_name_is = ["my name is ", "i am ", "call me "]
    patterns_remember_name = ["remember my name is "]

    all_name_patterns = patterns_remember_name + patterns_name_is

    for pattern in all_name_patterns:
        if pattern in user_message_lower:
            try:
                start_index_in_lower = user_message_lower.find(pattern)
                name_part = user_message_text[start_index_in_lower + len(pattern):].strip()

                if name_part.endswith("."): name = name_part[:-1].strip()
                else: name = name_part.strip()

                if name:
                    agent_memory_state.setdefault("user_settings", {})["user_name"] = name
                    name_identified_this_turn = name
                    log_event(f"NLP identified user name: {name} via pattern '{pattern}'. Updated user_settings.", "info")
                    # For "remember my name is", the response is slightly different
                    if pattern in patterns_remember_name:
                        return f"Got it, I'll try to remember your name is {name}!"
                    else:
                        return f"Nice to meet you, {name}!"
            except Exception as e:
                log_event(f"Error parsing name with pattern '{pattern}': {e}", "warning")
                # Potentially return a message about confusion, or just fall through

    # Check for recent greetings
    greeted_recently = False
    if len(dialog_history) > 1: # Need at least one previous message (the current user message is already added)
        # Check last few messages for a greeting from the bot
        for entry in reversed(dialog_history[:-1]): # Exclude current user message
            if entry["role"] == "assistant" and "hello" in entry["content"].lower():
                greeted_recently = True
                break
            if entry["role"] == "user": # Stop if we hit a previous user message without finding bot greeting
                break

    if "hello" in user_message_lower or "hi" in user_message_lower:
        if greeted_recently:
            return "Hello again! What can I do for you?"
        else:
            return "Hello there! How can I help you today?"

    if "what was my last message" in user_message_lower:
        # The dialog_history passed INCLUDES the current user's message at the end.
        # So, user's own last message (before the current one) is at dialog_history[-2].
        # And the message before that (if any) is dialog_history[-3].
        if len(dialog_history) >= 3: # current user msg, bot response, previous user msg
             # find the last message by user_id that isn't the current one.
            user_messages = [m["content"] for m in dialog_history[:-1] if m["role"] == "user"]
            if user_messages:
                 return f"Looking back... your last message to me was: '{user_messages[-1]}'"
            else: # Should not happen if history has user messages
                 return "I don't see a previous message from you in our recent chat."
        elif len(dialog_history) == 2: # Current user message + one previous (must be bot or system)
             return "It looks like this is our first exchange in this session, or I don't remember your very last message."
        else: # Only current user message in history
             return "This is your first message to me in this conversation!"


    # This block is now covered by the loop above, but the response might differ slightly.
    # The loop provides "Nice to meet you, {name}!" or "Got it, I'll try to remember..."
    # If a specific response for "remember my name is" is still desired *after* the loop (e.g. if it failed), it could be here.
    # For now, the loop handles it. If name_identified_this_turn has a value, we've already responded.
    if name_identified_this_turn: # If name was identified and responded to, we can exit early.
        pass # Already returned from the loop

    current_user_name = agent_memory_state.get("user_settings", {}).get("user_name")
    if current_user_name:
        if "what is my name" in user_message_lower:
            return f"If I remember correctly, your name is {current_user_name}."
        if "thank you" in user_message_lower: # and not name_identified_this_turn:
             # Avoid saying "You're welcome, Bob!" if they just said "My name is Bob" and bot said "Nice to meet you Bob"
            if not name_identified_this_turn : # only if name wasn't just set this turn
                return f"You're welcome, {current_user_name}!"
            else: # if name was just set, a simple "You're welcome!" is better.
                 return "You're welcome!"
        # If user said "thanks" and also their name in the same message, this logic might need refinement
        # e.g. "Thanks, my name is Dave" -> "Nice to meet you, Dave!" (from name logic)
        # vs "You're welcome, Dave!" (from here). The first one to match would respond.


    # Default fallback if no specific contextual rule matched
    previous_bot_responses = [entry["content"] for entry in dialog_history if entry["role"] == "assistant"]
    if previous_bot_responses and previous_bot_responses[-1] == f"Katana echoes: {user_message_text}":
        return "I seem to be repeating myself. Perhaps we can talk about something else?"

    return f"Katana processes: {user_message_text} (History items: {len(dialog_history)})"


# --- Main Chat Message Handling Logic ---
def handle_user_chat_message(user_id, user_message_text):
    """
    Handles an incoming chat message from a user, updates dialog history,
    and (currently) echoes the message. This is where NLP would be integrated.
    """
    global agent_memory_state
    log_event(f"Received chat message from user {user_id}: '{user_message_text}'", "info")

    # 1. Add user message to history
    # Ensure dialog_history is initialized (should be by load_memory)
    if "dialog_history" not in agent_memory_state: # Should be redundant due to load_memory
        agent_memory_state["dialog_history"] = []

    current_dialog_history = agent_memory_state["dialog_history"]
    current_dialog_history.append({
        "role": "user",
        "id": user_id,
        "content": user_message_text,
        "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat()
    })

    # 2. Process message with NLP, providing current dialog history for context
    bot_response_text = get_contextual_nlp_response(user_message_text, current_dialog_history)

    log_event(f"Generated bot response: '{bot_response_text}'", "info")

    # 3. Add bot response to history
    current_dialog_history.append({
        "role": "assistant",
        "content": bot_response_text,
        "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat()
    })

    # 4. Save state (includes history)
    save_result = handle_save_state() # This calls save_memory() and save_history()
    if save_result["status"] != "success":
        log_event(f"Failed to automatically save state after chat message: {save_result.get('message')}", "error")
        # Depending on policy, we might want to inform the user or just log

    return bot_response_text


if __name__ == '__main__':
    log_event("katana_agent.py self-test: Initializing files and loading memory...", "info")
    initialize_katana_files() # This calls load_memory()
    log_event("katana_agent.py self-test: File initialization and memory load complete.", "info")

    initial_memory_snapshot = json.dumps(agent_memory_state, indent=2)
    log_event(f"katana_agent.py self-test: Initial memory state:\n{initial_memory_snapshot}", "debug")

    # Example of processing a command
    # test_command = {"action": "get_agent_config", "command_id": "test-cmd-123"}
    # log_event(f"Simulating command processing: {test_command}", "info")
    # command_result = process_agent_command(test_command)
    # log_event(f"Command processing result: {command_result}", "info")

    # Example of processing a user chat message
    log_event("Simulating user chat message processing...", "info")
    user_id_example = "user_alpha_001"

    chat_response_1 = handle_user_chat_message(user_id_example, "Hello Katana!")
    log_event(f"Chat response to user: {chat_response_1}", "info")

    chat_response_2 = handle_user_chat_message(user_id_example, "What was my last message?")
    log_event(f"Chat response to user: {chat_response_2}", "info")

    chat_response_3 = handle_user_chat_message(user_id_example, "This is a new message.")
    log_event(f"Chat response to user: {chat_response_3}", "info")

    final_memory_snapshot = json.dumps(agent_memory_state, indent=2)
    log_event(f"katana_agent.py self-test: Final memory state after interactions:\n{final_memory_snapshot}", "debug")

    log_event("katana_agent.py self-test: Run complete. Check katana_events.log, katana_memory.json, and katana.history.json.", "info")
