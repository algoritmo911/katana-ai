import os
import json
import subprocess
import shutil
import uuid
import time
from pathlib import Path
from datetime import datetime, timezone
import unittest

# --- Test Configuration ---
# The agent script will run with its own parent directory as the CWD.
# All test paths must be relative to the agent's location.
AGENT_SCRIPT_PATH = Path(__file__).resolve().parent.parent.parent.parent / "katana/mci_agent/katana_agent.py"
AGENT_WORKING_DIR = AGENT_SCRIPT_PATH.parent

COMMANDS_DIR = AGENT_WORKING_DIR / "commands"
LOGS_DIR = AGENT_WORKING_DIR / "logs"
MODULES_DIR = AGENT_WORKING_DIR / "modules"
PROCESSED_DIR = AGENT_WORKING_DIR / "processed"

def get_json_log_entries(log_file_path):
    """Reads a log file where each line is a JSON object."""
    entries = []
    if not log_file_path.exists():
        return entries
    with open(log_file_path, "r") as f:
        for line in f:
            try:
                # The body of the log record is a JSON string, so we parse it twice.
                outer_record = json.loads(line)
                inner_payload = json.loads(outer_record.get("body", "{}"))
                entries.append(inner_payload)
            except (json.JSONDecodeError, TypeError):
                pass
    return entries

def is_valid_uuid_str(val):
    try:
        uuid.UUID(str(val))
        return True
    except (ValueError, TypeError):
        return False

class TestKatanaAgentMCI(unittest.TestCase):
    TEST_LOG_FILE = LOGS_DIR / "test_otel_agent.log"

    @classmethod
    def setUpClass(cls):
        MODULES_DIR.mkdir(parents=True, exist_ok=True)
        with open(MODULES_DIR / "mind_clearing.py", "w") as f:
            f.write("def run(**kwargs): return {'status':'success', 'message':'MC default run'}")
        cls.failing_module_name = "failing_module_for_mci_tests"
        with open(MODULES_DIR / f"{cls.failing_module_name}.py", "w") as f:
            f.write("def run(**kwargs): raise ValueError('This module is designed to fail')")

    def setUp(self):
        for d in [COMMANDS_DIR, LOGS_DIR, PROCESSED_DIR]:
            if d.exists():
                shutil.rmtree(d)
            d.mkdir(parents=True, exist_ok=True)

    def run_agent_mci(self, timeout=10):
        env = os.environ.copy()
        project_root = AGENT_WORKING_DIR.parent.parent
        env["PYTHONPATH"] = os.pathsep.join([str(project_root)] + env.get("PYTHONPATH", "").split(os.pathsep))
        env["OTEL_LOG_FILE_PATH"] = str(self.TEST_LOG_FILE)
        result = subprocess.run(
            ["python3", str(AGENT_SCRIPT_PATH)],
            capture_output=True, text=True, timeout=timeout,
            cwd=str(AGENT_WORKING_DIR), env=env,
        )
        if result.stdout:
            print(f"\n--- Agent STDOUT for {self._testMethodName} ---\n{result.stdout}")
        if result.stderr:
            print(f"\n--- Agent STDERR for {self._testMethodName} ---\n{result.stderr}")
        return result

    def create_command_file(self, command_data, filename_prefix="cmd"):
        target_dir = COMMANDS_DIR
        target_dir.mkdir(parents=True, exist_ok=True)
        cmd_id = command_data.get("id", str(uuid.uuid4()))
        command_file_path = target_dir / f"{filename_prefix}_{cmd_id}.json"
        with open(command_file_path, "w") as f:
            json.dump(command_data, f)
        return command_file_path

    def get_archived_command(self, command_id):
        if not PROCESSED_DIR.exists():
            return None
        for processed_file in PROCESSED_DIR.rglob("*.json"):
            try:
                with processed_file.open("r") as f:
                    data = json.load(f)
                if data.get("id") == command_id:
                    return data
            except (json.JSONDecodeError, IOError):
                continue
        return None

    def assert_command_archived(self, original_path, command_id, expected_status="done"):
        self.assertFalse(original_path.exists(), f"Original command file {original_path} was not deleted.")
        archived_cmd = self.get_archived_command(command_id)
        self.assertIsNotNone(archived_cmd, f"Command {command_id} not found in processed archives.")
        self.assertEqual(archived_cmd.get("status"), expected_status)
        self.assertIn("executed_at", archived_cmd)

    def test_mci_trigger_module_success(self):
        cmd_id = "mci_mc_001"
        cmd_data = {"id": cmd_id, "type": "trigger_module", "module": "mind_clearing"}
        cmd_file = self.create_command_file(cmd_data)
        time.sleep(0.25) # Give filesystem time to sync before running agent
        self.run_agent_mci()

        log_entries = get_json_log_entries(self.TEST_LOG_FILE)
        self.assertTrue(len(log_entries) > 0, "Log file is empty.")

        exec_log = next((log for log in log_entries if log.get("event_name") == "agent.module.execute.begin" and log.get("body", {}).get("command_id") == cmd_id), None)
        self.assertIsNotNone(exec_log, "Module execution begin log not found.")

        end_log = next((log for log in log_entries if log.get("event_name") == "agent.command.process.end" and log.get("body", {}).get("command_id") == cmd_id), None)
        self.assertIsNotNone(end_log, "Command process end log not found.")
        self.assertEqual(end_log.get("severity"), "INFO")

        self.assert_command_archived(cmd_file, cmd_id, "done")

    def test_mci_failing_module(self):
        cmd_id = "mci_fail_001"
        cmd_data = {"id": cmd_id, "type": "trigger_module", "module": self.failing_module_name}
        cmd_file = self.create_command_file(cmd_data)
        time.sleep(0.25)
        self.run_agent_mci()

        log_entries = get_json_log_entries(self.TEST_LOG_FILE)
        error_log = next((log for log in log_entries if log.get("event_name") == "agent.module.execute.exception"), None)
        self.assertIsNotNone(error_log, "Module exception log not found.")
        self.assertEqual(error_log.get("severity"), "ERROR")
        self.assertIn("ValueError", error_log.get("body", {}).get("error", ""))
        self.assertIn("traceback", error_log.get("body", {}))

        self.assert_command_archived(cmd_file, cmd_id, "failed")

    def test_mci_malformed_command_file(self):
        malformed_file = COMMANDS_DIR / "malformed.json"
        with malformed_file.open("w") as f:
            f.write("{not_json}")

        time.sleep(0.25)
        self.run_agent_mci()

        log_entries = get_json_log_entries(self.TEST_LOG_FILE)
        warn_log = next((log for log in log_entries if log.get("event_name") == "agent.command.load.error"), None)
        self.assertIsNotNone(warn_log, "Malformed JSON warning log not found.")
        self.assertEqual(warn_log.get("severity"), "WARN")

    def test_log_severities_are_correct(self):
        # Trigger an error to ensure ERROR logs are generated
        self.create_command_file({"id": "error_cmd", "type": "trigger_module", "module": self.failing_module_name})
        time.sleep(0.25)
        self.run_agent_mci()

        log_entries = get_json_log_entries(self.TEST_LOG_FILE)

        severities = {log.get("severity") for log in log_entries}
        self.assertIn("DEBUG", severities)
        self.assertIn("INFO", severities)
        self.assertIn("ERROR", severities)

if __name__ == "__main__":
    unittest.main(verbosity=2)
