import json
import os
import datetime
import uuid  # For generating command IDs in tests if needed

# --- File Paths (Copied from test_file_ops.py for context, not all directly used by these functions) ---
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
MEMORY_FILE = os.path.join(
    SCRIPT_DIR, "katana_memory.json"
)  # For process_single_command to know where memory would be saved by agent
EVENTS_LOG_FILE = os.path.join(SCRIPT_DIR, "katana_events.log")  # For general logging


def log_test_event(message, level="info"):
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{timestamp}] {level.upper()}: [TestCommandLogic] {message}")
    with open(EVENTS_LOG_FILE, "a") as f:
        f.write(f"[{timestamp}] {level.upper()}: [TestCommandLogic] {message}\n")


# --- Command Logic Functions (to be moved to katana_agent.py later) ---


def find_unprocessed_command(commands_list):
    log_test_event(
        f"Searching for unprocessed command in list of {len(commands_list)} items.",
        "debug",
    )
    if not isinstance(commands_list, list):
        log_test_event("commands_list is not a list.", "error")
        return None
    for command_item in commands_list:
        if isinstance(command_item, dict) and not command_item.get("processed", False):
            log_test_event(
                f"Found unprocessed command: ID '{command_item.get('id')}'", "debug"
            )  # Corrected quotes
            return command_item
    log_test_event("No unprocessed commands found.", "debug")
    return None


def process_single_command(command_dict, current_memory_data):
    # This function simulates processing and directly modifies the passed current_memory_data dictionary.
    # It returns a result dictionary for history logging.
    action = command_dict.get("command")
    args = command_dict.get("args", {})
    command_id = command_dict.get("id", "unknown_id")
    log_test_event(
        f"Processing action: '{action}' with args: {args} for command ID: {command_id}",
        "info",
    )

    if action == "remember":
        key = args.get("key")
        value = args.get("value")
        if key is not None:
            current_memory_data[key] = value  # Modify memory_data directly
            log_test_event(
                f"Remembered key '{key}' with value '{value}'. Memory updated.", "info"
            )
            return {
                "status": "success",
                "result": f"Remembered key '{key}' with value '{value}'.",
            }
        else:
            log_test_event("'remember' command missing 'key' in args.", "warning")
            return {
                "status": "failed",
                "result": "'remember' command requires a 'key' in args.",
            }

    elif action == "ask":
        key = args.get("key")
        if key is not None:
            response = current_memory_data.get(key, "I don't remember that.")
            log_test_event(
                f"Asked about key '{key}'. Responded with: '{response}'.", "info"
            )
            return {"status": "success", "result": response}
        else:
            log_test_event("'ask' command missing 'key' in args.", "warning")
            return {
                "status": "failed",
                "result": "'ask' command requires a 'key' in args.",
            }

    else:
        log_test_event(
            f"Unknown command action: '{action}' for command ID: {command_id}",
            "warning",
        )
        return {"status": "failed", "result": f"Unknown command action: '{action}'."}


def update_command_in_list(commands_list, command_id, updates_dict):
    log_test_event(
        f"Attempting to update command ID '{command_id}' in list with updates: {updates_dict}",
        "debug",
    )
    if not isinstance(commands_list, list):
        log_test_event("commands_list is not a list for update.", "error")
        return False
    found = False
    for command_item in commands_list:
        if isinstance(command_item, dict) and command_item.get("id") == command_id:
            command_item.update(updates_dict)
            log_test_event(f"Command ID '{command_id}' updated successfully.", "debug")
            found = True
            break
    if not found:
        log_test_event(f"Command ID '{command_id}' not found for update.", "warning")
    return found


def add_to_history_list(
    history_list,
    command_id,
    command_action,
    command_args,
    executed_at,
    status,
    result_message,
):
    # This function just appends to an in-memory list for testing purposes.
    # The agent will handle loading/saving history.json.
    log_test_event(
        f"Adding command {command_id} to in-memory history list with status: {status}",
        "debug",
    )
    if not isinstance(history_list, list):
        log_test_event("history_list is not a list.", "error")
        return False  # Or raise error
    history_entry = {
        "id": command_id,
        "command": command_action,
        "args": command_args,
        "executed_at": executed_at,
        "status": status,
        "result": result_message,
    }
    history_list.append(history_entry)
    log_test_event(
        f"Command {command_id} added to in-memory history list. New length: {len(history_list)}",
        "debug",
    )
    return True


if __name__ == "__main__":
    log_test_event("--- Running Tests for Command Logic ---", "info")

    # Test Data
    sample_commands = [
        {
            "id": "cmd_001",
            "command": "remember",
            "args": {"key": "greeting", "value": "Hello Katana!"},
            "created_at": "2024-01-01T10:00:00Z",
            "processed": False,
        },
        {
            "id": "cmd_002",
            "command": "ask",
            "args": {"key": "greeting"},
            "created_at": "2024-01-01T10:01:00Z",
            "processed": False,
        },
        {
            "id": "cmd_003",
            "command": "ask",
            "args": {"key": "non_existent_key"},
            "created_at": "2024-01-01T10:02:00Z",
            "processed": False,
        },
        {
            "id": "cmd_004",
            "command": "unknown_action",
            "args": {},
            "created_at": "2024-01-01T10:03:00Z",
            "processed": False,
        },
        {
            "id": "cmd_005",
            "command": "remember",
            "args": {"key": "farewell"},
            "created_at": "2024-01-01T10:04:00Z",
            "processed": True,
        },  # Already processed
    ]
    current_memory = {}
    current_history = []

    # Test 1: Find unprocessed command
    print("\n--- Test 1: Find Unprocessed Command ---")
    cmd_to_run = find_unprocessed_command(sample_commands)
    print(f"Found command to run: {cmd_to_run.get('id') if cmd_to_run else 'None'}")
    assert (
        cmd_to_run and cmd_to_run["id"] == "cmd_001"
    ), "Test 1 FAILED: Did not find cmd_001"
    print("Test 1 PASSED.")

    # Test 2: Process 'remember' command
    print("\n--- Test 2: Process 'remember' Command ---")
    if cmd_to_run:
        exec_result = process_single_command(cmd_to_run, current_memory)
        print(f"Execution result: {exec_result}")
        print(f"Memory state after remember: {current_memory}")
        assert (
            exec_result["status"] == "success"
        ), "Test 2 FAILED: 'remember' status not success"
        assert (
            current_memory.get("greeting") == "Hello Katana!"
        ), "Test 2 FAILED: Memory not updated correctly"
        update_command_in_list(
            sample_commands,
            cmd_to_run["id"],
            {
                "processed": True,
                "executed_at": "NOW",
                "status_after_execution": exec_result["status"],
            },
        )
        add_to_history_list(
            current_history,
            cmd_to_run["id"],
            cmd_to_run["command"],
            cmd_to_run["args"],
            "NOW",
            exec_result["status"],
            exec_result["result"],
        )
    print("Test 2 PASSED.")

    # Test 3: Find next unprocessed command ('ask')
    print("\n--- Test 3: Find Next Unprocessed Command ---")
    cmd_to_run = find_unprocessed_command(sample_commands)
    print(f"Found command to run: {cmd_to_run.get('id') if cmd_to_run else 'None'}")
    assert (
        cmd_to_run and cmd_to_run["id"] == "cmd_002"
    ), "Test 3 FAILED: Did not find cmd_002"
    print("Test 3 PASSED.")

    # Test 4: Process 'ask' command (existing key)
    print("\n--- Test 4: Process 'ask' Command (existing key) ---")
    if cmd_to_run:
        exec_result = process_single_command(cmd_to_run, current_memory)
        print(f"Execution result: {exec_result}")
        assert (
            exec_result["status"] == "success"
            and exec_result["result"] == "Hello Katana!"
        ), "Test 4 FAILED: 'ask' did not return correct value"
        update_command_in_list(
            sample_commands,
            cmd_to_run["id"],
            {
                "processed": True,
                "executed_at": "NOW",
                "status_after_execution": exec_result["status"],
            },
        )
        add_to_history_list(
            current_history,
            cmd_to_run["id"],
            cmd_to_run["command"],
            cmd_to_run["args"],
            "NOW",
            exec_result["status"],
            exec_result["result"],
        )
    print("Test 4 PASSED.")

    # Test 5: Process 'ask' command (non-existent key)
    print("\n--- Test 5: Process 'ask' Command (non-existent key) ---")
    cmd_to_run = find_unprocessed_command(sample_commands)  # Should be cmd_003
    if cmd_to_run:
        exec_result = process_single_command(cmd_to_run, current_memory)
        print(f"Execution result: {exec_result}")
        assert (
            exec_result["status"] == "success"
            and exec_result["result"] == "I don't remember that."
        ), "Test 5 FAILED: 'ask' for non-existent key failed"
        update_command_in_list(
            sample_commands,
            cmd_to_run["id"],
            {
                "processed": True,
                "executed_at": "NOW",
                "status_after_execution": exec_result["status"],
            },
        )
        add_to_history_list(
            current_history,
            cmd_to_run["id"],
            cmd_to_run["command"],
            cmd_to_run["args"],
            "NOW",
            exec_result["status"],
            exec_result["result"],
        )
    print("Test 5 PASSED.")

    # Test 6: Process unknown command
    print("\n--- Test 6: Process Unknown Command ---")
    cmd_to_run = find_unprocessed_command(sample_commands)  # Should be cmd_004
    if cmd_to_run:
        exec_result = process_single_command(cmd_to_run, current_memory)
        print(f"Execution result: {exec_result}")
        assert (
            exec_result["status"] == "failed"
        ), "Test 6 FAILED: Unknown command did not fail"
        update_command_in_list(
            sample_commands,
            cmd_to_run["id"],
            {
                "processed": True,
                "executed_at": "NOW",
                "status_after_execution": exec_result["status"],
            },
        )
        add_to_history_list(
            current_history,
            cmd_to_run["id"],
            cmd_to_run["command"],
            cmd_to_run["args"],
            "NOW",
            exec_result["status"],
            exec_result["result"],
        )
    print("Test 6 PASSED.")

    # Test 7: No unprocessed commands left
    print("\n--- Test 7: No Unprocessed Commands Left ---")
    cmd_to_run = find_unprocessed_command(sample_commands)
    print(f"Found command to run: {cmd_to_run.get('id') if cmd_to_run else 'None'}")
    assert (
        cmd_to_run is None
    ), "Test 7 FAILED: Found an unprocessed command when none should be left"
    print("Test 7 PASSED.")

    # Test 8: Check history list
    print("\n--- Test 8: Check History List ---")
    print(f"Current history: {json.dumps(current_history, indent=2)}")
    assert len(current_history) == 4, "Test 8 FAILED: History should have 4 entries"
    print("Test 8 PASSED.")

    log_test_event("--- Command Logic Tests Complete ---", "info")
