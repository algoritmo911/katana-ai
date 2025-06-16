
import os
import json
import subprocess
import time
import shutil
import uuid # For checking command_id format
from pathlib import Path
from datetime import datetime, timezone # Ensure timezone for ISO checks
import unittest

# --- Test Configuration (Global constants for easy access) ---
AGENT_BASE_DIR = Path(__file__).resolve().parent.parent
AGENT_SCRIPT_PATH = AGENT_BASE_DIR / "katana_agent.py"

COMMANDS_DIR = AGENT_BASE_DIR / "commands"
LOGS_DIR = AGENT_BASE_DIR / "logs"
LOG_ARCHIVE_DIR = LOGS_DIR / "archive"
STATUS_DIR = AGENT_BASE_DIR / "status"
MODULES_DIR = AGENT_BASE_DIR / "modules"
PROCESSED_DIR = AGENT_BASE_DIR / "processed"

EVENTS_LOG_FILE = LOGS_DIR / "katana_events.log"
AGENT_STATUS_FILE = STATUS_DIR / "agent_status.json"

# Helper function (can be outside class or static if preferred)
def find_command_in_list(command_id, commands_list):
    for cmd in commands_list:
        if cmd.get("id") == command_id:
            return cmd
    return None

def is_valid_uuid_str(val): # Renamed to avoid conflict with uuid module
    if not val: return False
    try:
        uuid.UUID(str(val))
        return True
    except ValueError:
        return False

def is_iso_timestamp_str(val): # Renamed for clarity
    if not val: return False
    try:
        datetime.fromisoformat(val.replace('Z', '+00:00'))
        return True
    except (ValueError, TypeError):
        return False

class TestKatanaAgentMCI(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        AGENT_BASE_DIR.mkdir(exist_ok=True)
        MODULES_DIR.mkdir(parents=True, exist_ok=True)

        # Always overwrite to ensure test-specific content
        mc_module_path = MODULES_DIR / "mind_clearing.py"
        with open(mc_module_path, 'w') as f:
            f.write("def run(**kwargs):\n    print(f\"🧠 Mind Clearing (test default) args: {kwargs}\")\n    return {'status':'success', 'message':'MC default run'}\n")
        # print(f"setUpClass: Ensured module {mc_module_path} with test content.") # Optional: too verbose for normal runs

        nr_module_path = MODULES_DIR / "neuro_refueling.py"
        with open(nr_module_path, 'w') as f:
            f.write("def run(**kwargs):\n    print(f\"🧠 Neuro-Refueling (test default) args: {kwargs}\")\n    return {'status':'success', 'message':'NR default run'}\n")
        # print(f"setUpClass: Ensured module {nr_module_path} with test content.")

        cls.failing_module_name = "failing_module_for_mci_tests"
        failing_module_path = MODULES_DIR / f"{cls.failing_module_name}.py"
        with open(failing_module_path, 'w') as f:
            f.write("def run(**kwargs):\n")
            f.write(f"    print(f'Executing {cls.failing_module_name} - I will raise an error!')\n")
            f.write("    raise ValueError('This module is designed to fail for MCI testing')\n")
        print(f"setUpClass: Ensured base directories and modules including {cls.failing_module_name}.py. Standard test modules overwritten.")


    @classmethod
    def tearDownClass(cls):
        failing_module_path = MODULES_DIR / f"{cls.failing_module_name}.py"
        if failing_module_path.exists():
            failing_module_path.unlink()
        print(f"tearDownClass: Cleaned up {cls.failing_module_name}.py")

    def setUp(self):
        self.cleanup_test_environment_mci()

    def cleanup_test_environment_mci(self):
        # print(f"Cleaning up test environment for test: {self._testMethodName}...")
        dirs_to_recreate = [COMMANDS_DIR, LOGS_DIR, STATUS_DIR, PROCESSED_DIR]
        for d_path in dirs_to_recreate:
            if d_path.exists():
                shutil.rmtree(d_path)
            d_path.mkdir(parents=True, exist_ok=True)

        (LOGS_DIR / "archive").mkdir(parents=True, exist_ok=True)
        if EVENTS_LOG_FILE.exists(): EVENTS_LOG_FILE.unlink()
        # Do not create COMMAND_FILE or AGENT_STATUS_FILE here; agent should handle missing ones.

    def run_agent_mci(self, timeout=35): # Slightly longer timeout for multi-file ops
        env = os.environ.copy()
        project_root = AGENT_BASE_DIR.parent.parent
        current_pythonpath = env.get('PYTHONPATH', '')
        new_pythonpath = os.pathsep.join([str(project_root)] + ([current_pythonpath] if current_pythonpath else []))
        env['PYTHONPATH'] = new_pythonpath

        print(f"Executing agent for test: {self._testMethodName} (CWD: {AGENT_BASE_DIR})") # Added test name and CWD
        result = subprocess.run(
            ["python3", str(AGENT_SCRIPT_PATH)],
            capture_output=True, text=True, timeout=timeout, cwd=str(AGENT_BASE_DIR), env=env
        )
        if result.stderr: # Check if there's anything in stderr
            print(f"Agent STDERR for {self._testMethodName}:\n{result.stderr}")
        return result

    def create_command_file(self, command_data, sub_dir="general", filename_prefix="cmd"):
        target_dir = COMMANDS_DIR / sub_dir
        target_dir.mkdir(parents=True, exist_ok=True)

        cmd_id_for_file = command_data.get("id", str(uuid.uuid4()))
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S%f")
        command_file_path = target_dir / f"{filename_prefix}_{cmd_id_for_file}_{timestamp}.json"

        with open(command_file_path, 'w') as f:
            json.dump(command_data, f, indent=2)
        return command_file_path

    def get_all_processed_commands_data(self):
        processed_data = []
        if not PROCESSED_DIR.exists(): return processed_data
        for root, _, files in os.walk(PROCESSED_DIR): # os.walk to handle subdirs
            for filename in files:
                if filename.endswith(".json"):
                    file_path = Path(root) / filename
                    try:
                        with open(file_path, 'r') as f:
                            processed_data.append(json.load(f))
                    except (json.JSONDecodeError, IOError) as e:
                        print(f"Warning: Failed to read/parse processed file {file_path}: {e}")
        return processed_data

    def find_processed_command_by_id(self, command_id, processed_list=None):
        if processed_list is None:
            processed_list = self.get_all_processed_commands_data()
        return find_command_in_list(command_id, processed_list)

    def assert_command_processed_and_archived(self, original_cmd_file_path, command_id,
                                              expected_status="done", expected_summary_part=None):
        self.assertFalse(original_cmd_file_path.exists(), f"Original command file {original_cmd_file_path} was not deleted after processing.")

        archived_cmd = self.find_processed_command_by_id(command_id)
        self.assertIsNotNone(archived_cmd, f"Command {command_id} not found in processed archives.")
        self.assertEqual(archived_cmd.get("status"), expected_status, f"Archived command {command_id} status mismatch. Full cmd: {archived_cmd}")
        self.assertTrue(is_iso_timestamp_str(archived_cmd.get("executed_at")), f"Archived command {command_id} 'executed_at' invalid: {archived_cmd.get('executed_at')}")
        if expected_summary_part:
            self.assertIn(expected_summary_part, archived_cmd.get("execution_summary", ""), f"Execution summary mismatch for {command_id}. Summary: '{archived_cmd.get('execution_summary', '')}'")

    def test_mci_ensure_command_id(self):
        cmd_data_no_id = {"type": "log_event", "message": "MCI test ensure_command_id"}
        cmd_file_path = self.create_command_file(cmd_data_no_id, filename_prefix="ensure_id")
        self.run_agent_mci()
        processed_commands = self.get_all_processed_commands_data()
        self.assertEqual(len(processed_commands), 1, "Expected one command in processed.")
        archived_cmd = processed_commands[0]
        self.assertIn("id", archived_cmd)
        generated_id = archived_cmd["id"]
        self.assertTrue(is_valid_uuid_str(generated_id), "Generated ID is not a UUID.")
        self.assertEqual(archived_cmd.get("type"), "log_event")
        self.assert_command_processed_and_archived(cmd_file_path, generated_id)

    def test_mci_trigger_module_success(self):
        cmd_id = "mci_mc_001"
        module_name = "mind_clearing"
        cmd_data = {"id": cmd_id, "type": "trigger_module", "module": module_name, "args": {"test_param": "mci_value"}}
        cmd_file_path = self.create_command_file(cmd_data, sub_dir=module_name) # Store in subdir for variety
        result = self.run_agent_mci()

        self.assertIn(f"'test_param': 'mci_value'", result.stdout)
        self.assertIn(f"'command_id': '{cmd_id}'", result.stdout)

        log_content = EVENTS_LOG_FILE.read_text() if EVENTS_LOG_FILE.exists() else ""
        self.assertIn(f"Executing module '{module_name}' for command_id: {cmd_id}", log_content)
        self.assertIn(f"Module '{module_name}' (command_id: {cmd_id}) finished.", log_content)
        self.assertIn("'status': 'success'", log_content)
        self.assertIn("MC default run", log_content)

        self.assert_command_processed_and_archived(cmd_file_path, cmd_id, expected_summary_part="MC default run")

    def test_mci_status_check(self):
        cmd_id = "mci_sc_001"
        cmd_data = {"id": cmd_id, "type": "status_check"}
        cmd_file_path = self.create_command_file(cmd_data, filename_prefix="status")
        self.run_agent_mci()
        self.assertTrue(AGENT_STATUS_FILE.exists())
        status_data = json.loads(AGENT_STATUS_FILE.read_text())
        self.assertEqual(status_data.get("status"), "active")
        self.assertEqual(status_data.get("last_command_id"), cmd_id)
        self.assertTrue(is_iso_timestamp_str(status_data.get("timestamp")))
        self.assert_command_processed_and_archived(cmd_file_path, cmd_id, expected_summary_part="Status checked")

    def test_mci_failing_module(self):
        cmd_id = "mci_fail_001"
        module_name = self.failing_module_name
        cmd_data = {"id": cmd_id, "type": "trigger_module", "module": module_name, "args": {}}
        cmd_file_path = self.create_command_file(cmd_data, sub_dir="testing_failures")
        result = self.run_agent_mci()
        self.assertIn(f"Executing {module_name}", result.stdout)
        log_content = EVENTS_LOG_FILE.read_text() if EVENTS_LOG_FILE.exists() else ""
        self.assertIn(f"CRITICAL_ERROR executing module '{module_name}' (command_id: {cmd_id})", log_content)
        self.assertIn("ValueError: This module is designed to fail for MCI testing", log_content)
        self.assertIn("Traceback:", log_content)
        self.assert_command_processed_and_archived(cmd_file_path, cmd_id, expected_status="failed",
                                                   expected_summary_part="ValueError: This module is designed to fail for MCI testing")

    def test_mci_file_restoration_status(self):
        # Agent's main() should restore status file from internal default if missing
        if AGENT_STATUS_FILE.exists(): AGENT_STATUS_FILE.unlink()
        self.assertFalse(AGENT_STATUS_FILE.exists())
        self.create_command_file({"id":"dummy_for_restore_test", "type":"log_event", "message":"run agent for restore"})
        self.run_agent_mci()
        self.assertTrue(AGENT_STATUS_FILE.exists(), "AGENT_STATUS_FILE was not restored by agent.")
        status_data = json.loads(AGENT_STATUS_FILE.read_text())
        # Check against DEFAULT_STATUS content used in agent's main()
        self.assertEqual(status_data.get("status"), "idle_restored_from_internal_default")
        self.assertTrue(is_iso_timestamp_str(status_data.get("timestamp")))
        self.assertIn("internal default structure", status_data.get("notes", ""))

    def test_mci_malformed_command_file(self):
        malformed_dir = COMMANDS_DIR / "malformed_tests"
        malformed_dir.mkdir(parents=True, exist_ok=True)
        malformed_file_path = malformed_dir / "malformed_cmd_test.json"
        with open(malformed_file_path, 'w') as f:
            # Valid JSON, but an array, not a dict (object) as expected for a command
            json.dump([{"item_in_array": "this should be skipped as non-dict command_data"}], f)

        valid_cmd_id = "mci_valid_after_malformed"
        valid_cmd_data = {"id": valid_cmd_id, "type": "log_event", "message": "Valid command after malformed"}
        valid_cmd_file_path = self.create_command_file(valid_cmd_data, sub_dir="general_valid", filename_prefix="valid")
        self.run_agent_mci()

        log_content = EVENTS_LOG_FILE.read_text() if EVENTS_LOG_FILE.exists() else ""
        expected_log_for_non_dict_object = f"Warning: Content of {malformed_file_path} is not a JSON object. Skipping."
        self.assertIn(expected_log_for_non_dict_object, log_content)

        # Verify the malformed file was NOT moved by main's non-dict logic, as load_commands skips it.
        self.assertTrue(malformed_file_path.exists(), "Malformed file (valid JSON array) should NOT have been deleted by load_commands or moved by main's non-dict logic.")

        processed_malformed_dir = PROCESSED_DIR / "malformed"
        moved_malformed_exists = False
        if processed_malformed_dir.exists(): # The "malformed" dir might not even be created if no file ever triggers that specific logic in main.
            moved_malformed_exists = any(f.name.startswith("malformed_cmd_test")
                                         for f in processed_malformed_dir.iterdir())
        self.assertFalse(moved_malformed_exists, "Malformed file (JSON array) should not have been moved to processed/malformed by main's non-dict handling.")

        # Verify the valid command was processed
        self.assert_command_processed_and_archived(valid_cmd_file_path, valid_cmd_id)

if __name__ == "__main__":
    # print(f"Unittest script running from: {Path(__file__).resolve().parent}")
    # print(f"AGENT_BASE_DIR for tests: {AGENT_BASE_DIR}")
    unittest.main(verbosity=2)
