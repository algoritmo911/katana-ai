import sys
import os
from pathlib import Path

# Add project root to sys.path to allow imports like 'from katana.core...'
project_root = Path(__file__).resolve().parent
sys.path.insert(0, str(project_root))

# Attempt to import KatanaCore and setup_logging
try:
    from katana.core.cli_agent.katana import KatanaCore
    from katana.logger import setup_logging # For general app logging, not strictly for the decorator test output
    import logging
except ImportError as e:
    print(f"Error importing Katana modules: {e}")
    print(f"Ensure this script is in the project root and PYTHONPATH is set up correctly if needed.")
    print(f"Current sys.path: {sys.path}")
    # Attempt to give more specific advice if possible
    if 'katana.core' in str(e) or 'katana.logger' in str(e):
        # This implies the script is likely not in the correct root or 'katana' isn't seen as a package
        print("This script expects to be in the 'algoritmo911/katana-ai' root directory.")
        print("And for 'katana' to be an importable package from there.")
    sys.exit(1)

def main():
    # Setup basic logging for the application
    # The @trace_command decorator prints JSON to stdout directly,
    # so this setup_logging call is more for general KatanaCore behavior.
    log_file_path = project_root / "test_run_katana_events.log"
    setup_logging(log_level=logging.DEBUG, log_file_path=str(log_file_path))
    print(f"General application logs will go to: {log_file_path}")

    # Define the path to the directory where KatanaCore expects its files
    # This should be 'katana/core/cli_agent' relative to the project root
    core_agent_dir = project_root / "katana" / "core" / "cli_agent"

    # Ensure the directory exists (it should as part of the repo)
    if not core_agent_dir.exists():
        print(f"Error: The directory {core_agent_dir} does not exist. Cannot run test.")
        sys.exit(1)

    print(f"Attempting to initialize KatanaCore with core_dir_path_str='{core_agent_dir}'...")
    print(f"The @trace_command decorator should print JSON output below if it decorates _save_json and files are missing.")

    # Instantiate KatanaCore. This should trigger _ensure_files_exist -> _save_json
    # if any of the core files (commands.json, memory.json, sync_status.json) are missing
    # from the core_agent_dir.
    try:
        kc = KatanaCore(core_dir_path_str=str(core_agent_dir))
        print("KatanaCore initialized successfully.")
        # The decorator would have printed its output during the __init__ call.
    except Exception as e:
        print(f"An error occurred during KatanaCore initialization: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    # For the test, we want to ensure that _save_json is called.
    # _save_json is called by _ensure_files_exist if a file is not present.
    # Let's target 'commands.json' within the core_agent_dir.

    core_agent_dir_for_cleanup = project_root / "katana" / "core" / "cli_agent"
    commands_json_path = core_agent_dir_for_cleanup / "commands.json"
    status_json_path = core_agent_dir_for_cleanup / "sync_status.json" # KatanaCore uses this name
    memory_json_path = core_agent_dir_for_cleanup / "memory.json"

    # We'll delete one to ensure it's recreated and logged.
    # Let's choose commands.json
    existed_before = False
    if commands_json_path.exists():
        print(f"Test setup: Removing existing {commands_json_path} to trigger @trace_command on _save_json.")
        commands_json_path.unlink()
        existed_before = True
    else:
        print(f"Test setup: {commands_json_path} does not exist, @trace_command should trigger.")

    main()

    # Post-test check: verify the file was created
    if commands_json_path.exists():
        print(f"Test verification: {commands_json_path} was created/recreated successfully.")
        if not existed_before:
            print(f"It was created anew as it didn't exist prior to the test run.")
        else:
            print(f"It was recreated as it was deleted by the test setup.")
    else:
        print(f"Test verification WARNING: {commands_json_path} was NOT created. Check KatanaCore logic and paths.")

    # Optional: Clean up other files if they were created for the first time
    # For now, just focusing on commands.json for the trigger.
    print(f"\nCheck the console output above for a JSON line starting with {{'id': ...}} from the @trace_command decorator.")
    print(f"This JSON line is the primary indicator of the test's success for the decorator itself.")
