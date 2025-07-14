import json
import os
import datetime  # Not strictly needed for these basic funcs, but good practice

# Define file paths consistently (relative to this script if run directly from alg911.catana-ai, or adjust as needed)
# For now, assume script is in alg911.catana-ai or paths are relative to a known root if agent calls them.
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
COMMANDS_FILE = os.path.join(SCRIPT_DIR, "katana.commands.json")
HISTORY_FILE = os.path.join(SCRIPT_DIR, "katana.history.json")
MEMORY_FILE = os.path.join(SCRIPT_DIR, "katana_memory.json")
EVENTS_LOG_FILE = os.path.join(SCRIPT_DIR, "katana_events.log")  # For general logging


def log_test_event(message, level="info"):
    # Simple logger for testing this script, can be expanded or use agent's logger later
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{timestamp}] {level.upper()}: [TestFileOps] {message}")
    # Optionally, also write to a dedicated test log or EVENTS_LOG_FILE
    with open(EVENTS_LOG_FILE, "a") as f:
        f.write(f"[{timestamp}] {level.upper()}: [TestFileOps] {message}\n")


def load_json_file(file_path, default_value_if_missing_or_error=None):
    log_test_event(f"Attempting to load JSON from: {file_path}", "debug")
    if not os.path.exists(file_path):
        log_test_event(
            f"File not found: {file_path}. Returning default value.", "warning"
        )
        return default_value_if_missing_or_error
    try:
        with open(file_path, "r") as f:
            data = json.load(f)
        log_test_event(f"Successfully loaded JSON from: {file_path}", "debug")
        return data
    except json.JSONDecodeError:
        log_test_event(
            f"Error decoding JSON from {file_path}. Returning default value.", "error"
        )
        return default_value_if_missing_or_error
    except Exception as e:
        log_test_event(
            f"Unexpected error loading {file_path}: {e}. Returning default value.",
            "error",
        )
        return default_value_if_missing_or_error


def save_json_file(file_path, data):
    log_test_event(f"Attempting to save JSON to: {file_path}", "debug")
    try:
        # Ensure directory exists if file_path includes subdirectories
        dir_name = os.path.dirname(file_path)
        if dir_name:  # Only create if path actually has a directory part
            os.makedirs(dir_name, exist_ok=True)
        with open(file_path, "w") as f:
            json.dump(
                data, f, indent=2
            )  # Using indent=2 for consistency with previous agent saves
        log_test_event(f"Successfully saved JSON to: {file_path}", "info")
        return True
    except Exception as e:
        log_test_event(f"Error saving JSON to {file_path}: {e}", "error")
        return False


def initialize_katana_files():
    log_test_event("Initializing Katana data files...", "info")
    initialized_any = False
    # Commands file: should be a list
    if not os.path.exists(COMMANDS_FILE):
        if save_json_file(COMMANDS_FILE, []):
            log_test_event(
                f"{COMMANDS_FILE} initialized successfully as empty list.", "info"
            )
            initialized_any = True
        else:
            log_test_event(f"Failed to initialize {COMMANDS_FILE}.", "error")
    else:
        log_test_event(f"{COMMANDS_FILE} already exists.", "debug")

    # History file: should be a list
    if not os.path.exists(HISTORY_FILE):
        if save_json_file(HISTORY_FILE, []):
            log_test_event(
                f"{HISTORY_FILE} initialized successfully as empty list.", "info"
            )
            initialized_any = True
        else:
            log_test_event(f"Failed to initialize {HISTORY_FILE}.", "error")
    else:
        log_test_event(f"{HISTORY_FILE} already exists.", "debug")

    # Memory file: should be an object (dictionary)
    if not os.path.exists(MEMORY_FILE):
        if save_json_file(MEMORY_FILE, {}):
            log_test_event(
                f"{MEMORY_FILE} initialized successfully as empty object.", "info"
            )
            initialized_any = True
        else:
            log_test_event(f"Failed to initialize {MEMORY_FILE}.", "error")
    else:
        log_test_event(f"{MEMORY_FILE} already exists.", "debug")

    if initialized_any:
        log_test_event("Katana data file initialization process complete.", "info")
    else:
        log_test_event(
            "All Katana data files already existed. No new initializations.", "info"
        )
    return True


if __name__ == "__main__":
    log_test_event("--- Running Tests for File Operations ---", "info")

    # Test 1: Initialize files
    print("\n--- Test 1: Initializing Katana Files ---")
    initialize_katana_files()
    # Re-initialize to test 'already exists' path
    print("\n--- Test 1a: Re-initializing Katana Files (should show files exist) ---")
    initialize_katana_files()

    # Test 2: Save and Load Commands File (List)
    print("\n--- Test 2: Save and Load Commands File ---")
    test_commands = [{"id": "test_cmd_001", "command": "test", "processed": False}]
    if save_json_file(COMMANDS_FILE, test_commands):
        loaded_commands = load_json_file(COMMANDS_FILE, [])
        print(f"Loaded commands: {loaded_commands}")
        assert loaded_commands == test_commands, "Commands save/load failed!"
        print("Commands save/load test PASSED.")
    else:
        print("Commands save/load test FAILED (save error).")

    # Test 3: Save and Load Memory File (Dict)
    print("\n--- Test 3: Save and Load Memory File ---")
    test_memory = {"test_key": "test_value"}
    if save_json_file(MEMORY_FILE, test_memory):
        loaded_memory = load_json_file(MEMORY_FILE, {})
        print(f"Loaded memory: {loaded_memory}")
        assert loaded_memory == test_memory, "Memory save/load failed!"
        print("Memory save/load test PASSED.")
    else:
        print("Memory save/load test FAILED (save error).")

    # Test 4: Load non-existent file (should return default)
    print("\n--- Test 4: Load Non-Existent File ---")
    non_existent_file = os.path.join(SCRIPT_DIR, "non_existent.json")
    default_val_test = {"default": True}
    loaded_non_existent = load_json_file(non_existent_file, default_val_test)
    print(f"Loaded non-existent: {loaded_non_existent}")
    assert loaded_non_existent == default_val_test, "Load non-existent test FAILED!"
    print("Load non-existent test PASSED.")

    # Test 5: Load corrupted JSON file (should return default)
    print("\n--- Test 5: Load Corrupted JSON File ---")
    corrupted_file_path = os.path.join(SCRIPT_DIR, "corrupted.json")
    with open(corrupted_file_path, "w") as f:
        f.write("this is not json")
    loaded_corrupted = load_json_file(
        corrupted_file_path, []
    )  # Expecting list default for this test
    print(f"Loaded corrupted: {loaded_corrupted}")
    assert loaded_corrupted == [], "Load corrupted JSON test FAILED!"
    os.remove(corrupted_file_path)  # Clean up
    print("Load corrupted JSON test PASSED.")

    log_test_event("--- File Operations Tests Complete ---", "info")
