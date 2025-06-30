# run_integration_test.py
import json
import os
import shutil
import time
import uuid
from datetime import datetime, timezone

# Assuming the script is run from the root of the project
# Adjust paths if necessary based on actual execution context
# Add src to Python path to allow direct imports of modules
import sys
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '.')) # Modified to point to project root
sys.path.insert(0, project_root)
sys.path.insert(0, os.path.join(project_root, 'src')) # Ensure src is on the path

# --- Mocked/Real Modules (to be replaced/configured) ---
# These imports will be adjusted as we implement the actual modules
try:
    from src.dao import dao_task_handler
    # Import KatanaTaskProcessor specifically, TaskResult is also needed by test code if we check results directly
    from src.orchestrator.task_orchestrator import TaskOrchestrator, KatanaTaskProcessor, TaskResult
    from src.connectors import core_connector # core_connector is used by KatanaTaskProcessor
    from src.telemetry import command_telemetry
    # from bot.katana_bot import memory_manager # If direct interaction with memory_manager is needed
except ImportError as e:
    print(f"Error importing modules: {e}. Make sure PYTHONPATH is set correctly or run from project root.")
    print("Current sys.path:", sys.path)
    exit(1)

# --- Configuration ---
TEST_COMMAND_TELEMETRY_LOG = "test_run_command_telemetry.log"
TEST_KATANA_HISTORY_JSON = "test_run_katana.history.json" # Still used for basic check
TEST_ORCHESTRATOR_LOG = "test_run_orchestrator_log.json"

# --- Helper Functions ---
def generate_test_task_id() -> str:
    return f"test_task_{uuid.uuid4().hex[:8]}"

def cleanup_test_files():
    """Removes log files created during the test run."""
    print("\n--- Cleaning up test files ---")
    files_to_remove = [
        TEST_COMMAND_TELEMETRY_LOG,
        TEST_KATANA_HISTORY_JSON,
        TEST_ORCHESTRATOR_LOG,
        "katana.history.json", # remove default if used by mistake
        "command_telemetry.log" # remove default if used by mistake
    ]
    for f_path in files_to_remove:
        if os.path.exists(f_path):
            try:
                os.remove(f_path)
                print(f"Removed: {f_path}")
            except OSError as e:
                print(f"Error removing {f_path}: {e}")
        else:
            print(f"File not found, skipping removal: {f_path}")

def setup_test_environment():
    """Sets up the environment for the test run (e.g., configures logging)."""
    print("--- Setting up test environment ---")
    cleanup_test_files() # Clean up from previous runs first

    command_telemetry.configure_telemetry_logging(
        log_file=TEST_COMMAND_TELEMETRY_LOG,
        level=command_telemetry.logging.DEBUG, # Use DEBUG for tests
        enable_console_logging=False # Keep test output clean
    )
    print(f"Telemetry configured to log to: {TEST_COMMAND_TELEMETRY_LOG}")

    # Initialize katana.history.json for this test run
    with open(TEST_KATANA_HISTORY_JSON, 'w', encoding='utf-8') as f:
        json.dump({"log_entries": []}, f, indent=2)
    print(f"Initialized test katana history file: {TEST_KATANA_HISTORY_JSON}")

    # Initialize orchestrator log for this test run
    with open(TEST_ORCHESTRATOR_LOG, 'w', encoding='utf-8') as f:
        json.dump([], f, indent=2) # Orchestrator expects a list
    print(f"Initialized test orchestrator log file: {TEST_ORCHESTRATOR_LOG}")


# --- Main Test Logic ---
async def main_test_flow():
    print("\n--- Starting Integration Test ---")

    # 1. Setup
    setup_test_environment()

    # 2. Initialize KatanaTaskProcessor (real one) and Orchestrator
    # No longer using MockKatanaTaskProcessor
    try:
        katana_agent_impl = KatanaTaskProcessor()
        print("KatanaTaskProcessor initialized.")
    except Exception as e:
        print(f"ERROR: Failed to initialize KatanaTaskProcessor: {e}", exc_info=True)
        return


    orchestrator = TaskOrchestrator(
        agent=katana_agent_impl, # Using the real KatanaTaskProcessor
        batch_size=2, # Small batch for testing
        metrics_log_file=TEST_ORCHESTRATOR_LOG
    )
    print("TaskOrchestrator initialized with KatanaTaskProcessor.")

    # 3. Simulate DAO Task Fetching
    # Using the mock data from dao_task_handler
    print("\n--- Simulating DAO Task Fetching ---")
    simulated_dao_tasks = dao_task_handler.fetch_tasks_from_colony() # Gets mock tasks
    if not simulated_dao_tasks:
        print("ERROR: No simulated DAO tasks fetched. Test cannot proceed.")
        return

    print(f"Fetched {len(simulated_dao_tasks)} tasks from DAO mock:")
    for task in simulated_dao_tasks:
        print(f"  - Task ID: {task.get('id')}, Type: {task.get('type')}")

    # Add tasks to orchestrator
    # TaskOrchestrator.add_tasks now expects List[Dict[str, Any]]
    # The dao_task_handler.fetch_tasks_from_colony() returns List[Dict[str, Any]]
    # So, this should align correctly.
    orchestrator.add_tasks(simulated_dao_tasks)
    print(f"Added {len(simulated_dao_tasks)} tasks to orchestrator queue. Queue length: {orchestrator.get_status()['task_queue_length']}")


    # 4. Invoke Katana Handler (Orchestrator Run Round)
    print("\n--- Invoking Katana Handler (Orchestrator Run Round) ---")
    if orchestrator.get_status()['task_queue_length'] > 0:
        await orchestrator.run_round()
        print("Orchestrator round 1 completed.")
        # Run another round if tasks are remaining
        if orchestrator.get_status()['task_queue_length'] > 0:
            await orchestrator.run_round()
            print("Orchestrator round 2 completed.")
    else:
        print("Skipping orchestrator run, no tasks in queue.")

    # 5. Retrieve and Verify Results (Conceptual)
    # The results are logged by the orchestrator and telemetry. We'll check the log files.
    print("\n--- Verifying Results (by checking log files) ---")

    # Check command_telemetry.log
    print(f"\n--- Verifying {TEST_COMMAND_TELEMETRY_LOG} ---")
    telemetry_events_found = 0
    expected_event_types = ["katana_task_text_generation_started", "katana_task_text_generation_completed",
                              "katana_task_image_analysis_started", "katana_task_image_analysis_completed", # Assuming image_analysis is a generic task now
                              "katana_task_log_event_started", "katana_task_log_event_completed"]
    found_event_types = set()

    try:
        with open(TEST_COMMAND_TELEMETRY_LOG, 'r', encoding='utf-8') as f:
            for line_number, line in enumerate(f, 1):
                line = line.strip()
                if not line:
                    continue
                print(f"  Log Line {line_number}: {line}")
                try:
                    log_entry = json.loads(line)
                    telemetry_events_found += 1
                    event_type = log_entry.get("event_type")
                    if event_type:
                        found_event_types.add(event_type)
                        # Example check:
                        if event_type == "katana_task_text_generation_started":
                            assert "task_data" in log_entry.get("details", {}), "Missing task_data in text_generation_started event"
                except json.JSONDecodeError:
                    print(f"VERIFICATION WARNING: Could not parse telemetry log line {line_number} as JSON: {line}")

        if not simulated_dao_tasks and telemetry_events_found == 0 :
             print(f"VERIFICATION INFO: No DAO tasks simulated, and no telemetry events found, which is expected.")
        elif telemetry_events_found > 0:
            print(f"VERIFICATION PASSED (basic): Found {telemetry_events_found} telemetry log entries.")
            # Check if specific event types from KatanaTaskProcessor were logged
            missing_expected_types = [et for et in expected_event_types if et not in found_event_types and any(task['type'] in et for task in simulated_dao_tasks)]
            if any(task['type'] == "text_generation" for task in simulated_dao_tasks) and not any("text_generation" in fet for fet in found_event_types):
                 print(f"VERIFICATION WARNING: 'text_generation' task was processed but no specific telemetry found. Found types: {found_event_types}")
            elif any(task['type'] == "log_event" for task in simulated_dao_tasks) and not any("log_event" in fet for fet in found_event_types):
                 print(f"VERIFICATION WARNING: 'log_event' task was processed but no specific telemetry found. Found types: {found_event_types}")
            # Add more specific checks as needed
        else: # simulated_dao_tasks is not empty but telemetry_events_found is 0
            print(f"VERIFICATION FAILED: Tasks were processed but no telemetry events found in {TEST_COMMAND_TELEMETRY_LOG}.")

    except FileNotFoundError:
        if simulated_dao_tasks: # Only fail if tasks were processed and log was expected
            print(f"VERIFICATION FAILED: {TEST_COMMAND_TELEMETRY_LOG} not found when tasks were processed.")
        else:
            print(f"VERIFICATION INFO: {TEST_COMMAND_TELEMETRY_LOG} not found, but no tasks were processed.")


    # Check katana.history.json
    # Its role is still for general test structure; not actively populated by the app in this flow.
    print(f"\n--- Verifying {TEST_KATANA_HISTORY_JSON} (structure check) ---")
    try:
        with open(TEST_KATANA_HISTORY_JSON, 'r', encoding='utf-8') as f:
            history_data = json.load(f)
            # print(json.dumps(history_data, indent=2)) # Can be verbose
            if "log_entries" in history_data and isinstance(history_data["log_entries"], list):
                print(f"VERIFICATION PASSED: {TEST_KATANA_HISTORY_JSON} is valid JSON with 'log_entries' list.")
                if not history_data["log_entries"]:
                    print(f"INFO: {TEST_KATANA_HISTORY_JSON} 'log_entries' is empty as expected (not populated by current test flow directly).")
                else:
                    print(f"INFO: {TEST_KATANA_HISTORY_JSON} 'log_entries' contains data (populated manually or by other means).")
            else:
                print(f"VERIFICATION FAILED: {TEST_KATANA_HISTORY_JSON} does not have the expected structure ('log_entries' list).")
    except FileNotFoundError:
        print(f"VERIFICATION WARNING: {TEST_KATANA_HISTORY_JSON} not found. This may be acceptable if not used by this specific test.")
    except json.JSONDecodeError:
        print(f"VERIFICATION FAILED: {TEST_KATANA_HISTORY_JSON} contains invalid JSON.")

    # Check orchestrator_log.json (TaskOrchestrator's own metrics)
    print(f"\n--- Verifying {TEST_ORCHESTRATOR_LOG} ---")
    orchestrator_log_entries = 0
    try:
        with open(TEST_ORCHESTRATOR_LOG, 'r', encoding='utf-8') as f:
            log_content_list = json.load(f) # Expecting a list of log entries
            # print(json.dumps(log_content_list, indent=2)) # Can be verbose
            if isinstance(log_content_list, list):
                orchestrator_log_entries = len(log_content_list)
                if orchestrator_log_entries > 0:
                    print(f"VERIFICATION PASSED (basic): Found {orchestrator_log_entries} orchestrator log entries in {TEST_ORCHESTRATOR_LOG}.")
                    # Example: Check content of the first orchestrator log entry
                    first_entry = log_content_list[0]
                    assert "batch_tasks_content" in first_entry, "Missing 'batch_tasks_content' in orchestrator log"
                    assert "results_summary" in first_entry, "Missing 'results_summary' in orchestrator log"
                elif not simulated_dao_tasks: # If no tasks, log might be empty
                    print(f"INFO: {TEST_ORCHESTRATOR_LOG} is empty, which is fine as no tasks were processed.")
                else: # Tasks were simulated, but log is empty
                    print(f"VERIFICATION FAILED: Orchestrator log {TEST_ORCHESTRATOR_LOG} is empty when tasks were processed.")
            else:
                print(f"VERIFICATION FAILED: {TEST_ORCHESTRATOR_LOG} content is not a JSON list.")


    except FileNotFoundError:
        if simulated_dao_tasks: # Only fail if tasks were processed and log was expected
            print(f"VERIFICATION FAILED: {TEST_ORCHESTRATOR_LOG} not found when tasks were processed.")
        else:
            print(f"VERIFICATION INFO: {TEST_ORCHESTRATOR_LOG} not found, but no tasks were processed.")
    except json.JSONDecodeError:
        print(f"VERIFICATION FAILED: {TEST_ORCHESTRATOR_LOG} is not valid JSON.")


    print("\n--- Integration Test Flow Completed ---")


if __name__ == "__main__":
    # Ensure asyncio event loop is handled correctly for main_test_flow
    # For Python 3.7+
    import asyncio
    try:
        asyncio.run(main_test_flow())
    finally:
        # Optional: Final cleanup, though setup_test_environment already cleans at start
        # cleanup_test_files() # Uncomment if cleanup at the very end is desired
        print("\nTest script finished.")
