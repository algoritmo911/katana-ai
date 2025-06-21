import os
import json
import subprocess
import shutil
import uuid  # For checking command_id format
from pathlib import Path
from datetime import datetime, timezone  # Ensure timezone for ISO checks
import unittest
import logging  # Added for test_log_rotation
from logging.handlers import RotatingFileHandler  # Added for test_log_rotation
from katana.utils.logging_config import JsonFormatter  # Added for test_log_rotation

# --- Test Configuration (Global constants for easy access) ---
AGENT_BASE_DIR = Path(__file__).resolve().parent.parent
# Corrected path to the agent script:
AGENT_SCRIPT_PATH = AGENT_BASE_DIR.parent.parent / "katana/mci_agent/katana_agent.py"

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


def is_valid_uuid_str(val):  # Renamed to avoid conflict with uuid module
    if not val:
        return False
    try:
        uuid.UUID(str(val))
        return True
    except ValueError:
        return False


def is_iso_timestamp_str(val):  # Renamed for clarity
    if not val:
        return False
    try:
        datetime.fromisoformat(val.replace("Z", "+00:00"))
        return True
    except (ValueError, TypeError):
        return False


# --- Helper function for parsing JSON log entries ---
def get_json_log_entries(log_file_path):
    """Reads a log file, splits by lines, and parses each line as JSON."""
    entries = []
    if not log_file_path.exists():
        return entries
    with open(log_file_path, "r") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue  # Skip empty lines
            try:
                entries.append(json.loads(line))
            except json.JSONDecodeError:
                print(
                    f"Warning: Could not parse log line as JSON: '{line}'"
                )  # Or handle as an assertion failure if strict
    return entries


class TestKatanaAgentMCI(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        AGENT_BASE_DIR.mkdir(exist_ok=True)
        MODULES_DIR.mkdir(parents=True, exist_ok=True)

        # Always overwrite to ensure test-specific content
        mc_module_path = MODULES_DIR / "mind_clearing.py"
        with open(mc_module_path, "w") as f:
            f.write(
                "def run(**kwargs):\n    print(f\"🧠 Mind Clearing (test default) args: {kwargs}\")\n    return {'status':'success', 'message':'MC default run'}\n"
            )
        # print(f"setUpClass: Ensured module {mc_module_path} with test content.") # Optional: too verbose for normal runs

        nr_module_path = MODULES_DIR / "neuro_refueling.py"
        with open(nr_module_path, "w") as f:
            f.write(
                "def run(**kwargs):\n    print(f\"🧠 Neuro-Refueling (test default) args: {kwargs}\")\n    return {'status':'success', 'message':'NR default run'}\n"
            )
        # print(f"setUpClass: Ensured module {nr_module_path} with test content.")

        cls.failing_module_name = "failing_module_for_mci_tests"
        failing_module_path = MODULES_DIR / f"{cls.failing_module_name}.py"
        with open(failing_module_path, "w") as f:
            f.write("def run(**kwargs):\n")
            f.write(
                f"    print(f'Executing {cls.failing_module_name} - I will raise an error!')\n"
            )
            f.write(
                "    raise ValueError('This module is designed to fail for MCI testing')\n"
            )
        print(
            f"setUpClass: Ensured base directories and modules including {cls.failing_module_name}.py. Standard test modules overwritten."
        )

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
        if EVENTS_LOG_FILE.exists():
            EVENTS_LOG_FILE.unlink()
        # Do not create COMMAND_FILE or AGENT_STATUS_FILE here; agent should handle missing ones.

    def run_agent_mci(self, timeout=35):  # Slightly longer timeout for multi-file ops
        env = os.environ.copy()
        project_root = AGENT_BASE_DIR.parent.parent
        current_pythonpath = env.get("PYTHONPATH", "")
        new_pythonpath = os.pathsep.join(
            [str(project_root)] + ([current_pythonpath] if current_pythonpath else [])
        )
        env["PYTHONPATH"] = new_pythonpath

        print(
            f"Executing agent for test: {self._testMethodName} (CWD: {AGENT_BASE_DIR})"
        )  # Added test name and CWD
        result = subprocess.run(
            ["python3", str(AGENT_SCRIPT_PATH)],
            capture_output=True,
            text=True,
            timeout=timeout,
            cwd=str(AGENT_BASE_DIR),
            env=env,
        )
        if result.stderr:  # Check if there's anything in stderr
            print(f"Agent STDERR for {self._testMethodName}:\n{result.stderr}")
        return result

    def create_command_file(
        self, command_data, sub_dir="general", filename_prefix="cmd"
    ):
        target_dir = COMMANDS_DIR / sub_dir
        target_dir.mkdir(parents=True, exist_ok=True)

        cmd_id_for_file = command_data.get("id", str(uuid.uuid4()))
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S%f")
        command_file_path = (
            target_dir / f"{filename_prefix}_{cmd_id_for_file}_{timestamp}.json"
        )

        with open(command_file_path, "w") as f:
            json.dump(command_data, f, indent=2)
        return command_file_path

    def get_all_processed_commands_data(self):
        processed_data = []
        if not PROCESSED_DIR.exists():
            return processed_data
        for root, _, files in os.walk(PROCESSED_DIR):  # os.walk to handle subdirs
            for filename in files:
                if filename.endswith(".json"):
                    file_path = Path(root) / filename
                    try:
                        with open(file_path, "r") as f:
                            processed_data.append(json.load(f))
                    except (json.JSONDecodeError, IOError) as e:
                        print(
                            f"Warning: Failed to read/parse processed file {file_path}: {e}"
                        )
        return processed_data

    def find_processed_command_by_id(self, command_id, processed_list=None):
        if processed_list is None:
            processed_list = self.get_all_processed_commands_data()
        return find_command_in_list(command_id, processed_list)

    def assert_command_processed_and_archived(
        self,
        original_cmd_file_path,
        command_id,
        expected_status="done",
        expected_summary_part=None,
    ):
        self.assertFalse(
            original_cmd_file_path.exists(),
            f"Original command file {original_cmd_file_path} was not deleted after processing.",
        )

        archived_cmd = self.find_processed_command_by_id(command_id)
        self.assertIsNotNone(
            archived_cmd,
            f"Command {command_id} not found in processed archives.",
        )
        self.assertEqual(
            archived_cmd.get("status"),
            expected_status,
            f"Archived command {command_id} status mismatch. Full cmd: {archived_cmd}",
        )
        self.assertTrue(
            is_iso_timestamp_str(archived_cmd.get("executed_at")),
            f"Archived command {command_id} 'executed_at' invalid: {archived_cmd.get('executed_at')}",
        )
        if expected_summary_part:
            self.assertIn(
                expected_summary_part,
                archived_cmd.get("execution_summary", ""),
                f"Execution summary mismatch for {command_id}. Summary: '{archived_cmd.get('execution_summary', '')}'",
            )

    def test_mci_ensure_command_id(self):
        cmd_data_no_id = {
            "type": "log_event",
            "message": "MCI test ensure_command_id",
        }
        cmd_file_path = self.create_command_file(
            cmd_data_no_id, filename_prefix="ensure_id"
        )
        self.run_agent_mci()
        processed_commands = self.get_all_processed_commands_data()
        self.assertEqual(
            len(processed_commands), 1, "Expected one command in processed."
        )
        archived_cmd = processed_commands[0]
        self.assertIn("id", archived_cmd)
        generated_id = archived_cmd["id"]
        self.assertTrue(is_valid_uuid_str(generated_id), "Generated ID is not a UUID.")
        self.assertEqual(archived_cmd.get("type"), "log_event")
        self.assert_command_processed_and_archived(cmd_file_path, generated_id)

    def test_mci_trigger_module_success(self):
        cmd_id = "mci_mc_001"
        module_name = "mind_clearing"
        cmd_data = {
            "id": cmd_id,
            "type": "trigger_module",
            "module": module_name,
            "args": {"test_param": "mci_value"},
        }
        cmd_file_path = self.create_command_file(
            cmd_data, sub_dir=module_name
        )  # Store in subdir for variety
        result = self.run_agent_mci()

        self.assertIn("'test_param': 'mci_value'", result.stdout)  # Fixed F541
        self.assertIn(
            f"'command_id': '{cmd_id}'", result.stdout
        )  # noqa: F541, this is a valid f-string

        # log_content = EVENTS_LOG_FILE.read_text() if EVENTS_LOG_FILE.exists() else "" # Removed F841
        # The assertions below were duplicated and one referred to log_content, removing redundancy
        # self.assertIn(
        #    f"'test_param': 'mci_value'", result.stdout
        # )  # Check stdout for direct module output
        # self.assertIn(f"'command_id': '{cmd_id}'", result.stdout)

        log_entries = get_json_log_entries(EVENTS_LOG_FILE)
        self.assertTrue(
            len(log_entries) > 0,
            "Log file is empty or all lines are invalid JSON.",
        )

        exec_log = next(
            (
                le
                for le in log_entries
                if le.get("message") == f"Executing module '{module_name}'"
                and le.get("command_id") == cmd_id
            ),
            None,
        )
        self.assertIsNotNone(
            exec_log,
            f"Log entry for 'Executing module {module_name}' not found.",
        )
        self.assertEqual(exec_log.get("level"), "INFO")
        self.assertEqual(exec_log.get("module"), "katana_agent")
        self.assertEqual(exec_log.get("function"), "execute_module")

        finish_log = next(
            (
                le
                for le in log_entries
                if le.get("message") == f"Module '{module_name}' finished."
                and le.get("command_id") == cmd_id
            ),
            None,
        )
        self.assertIsNotNone(
            finish_log,
            f"Log entry for 'Module {module_name} finished' not found.",
        )
        self.assertEqual(finish_log.get("level"), "INFO")
        self.assertIn("raw_result", finish_log)
        self.assertEqual(finish_log.get("raw_result", {}).get("status"), "success")
        self.assertEqual(
            finish_log.get("raw_result", {}).get("message"), "MC default run"
        )

        # Check for the final processing log
        processed_done_log = next(
            (
                le
                for le in log_entries
                if le.get("message", "").startswith("Command processing finished.")
                and le.get("command_id") == cmd_id
                and le.get("level") == "INFO"
            ),
            None,
        )
        self.assertIsNotNone(
            processed_done_log,
            "Log entry for command processing finished successfully not found.",
        )
        self.assertEqual(processed_done_log.get("summary"), "MC default run")

        self.assert_command_processed_and_archived(
            cmd_file_path, cmd_id, expected_summary_part="MC default run"
        )

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
        self.assert_command_processed_and_archived(
            cmd_file_path, cmd_id, expected_summary_part="Status checked"
        )

    def test_mci_failing_module(self):
        cmd_id = "mci_fail_001"
        module_name = self.failing_module_name
        cmd_data = {
            "id": cmd_id,
            "type": "trigger_module",
            "module": module_name,
            "args": {},
        }
        cmd_file_path = self.create_command_file(cmd_data, sub_dir="testing_failures")
        result = self.run_agent_mci()  # Agent run triggers logging
        self.assertIn(
            f"Executing {module_name}", result.stdout
        )  # Module's print output

        log_entries = get_json_log_entries(EVENTS_LOG_FILE)
        self.assertTrue(len(log_entries) > 0, "Log file is empty.")

        # Find the error log from execute_module
        error_log_module = next(
            (
                le
                for le in log_entries
                if le.get("level") == "ERROR"
                and le.get("command_id") == cmd_id
                and le.get("function") == "execute_module"
                and "Error executing module" in le.get("message", "")
            ),
            None,
        )
        self.assertIsNotNone(error_log_module, "Module execution error log not found.")
        self.assertIn(
            f"Error executing module '{module_name}'",
            error_log_module.get("message"),
        )
        self.assertIn(
            "ValueError: This module is designed to fail for MCI testing",
            error_log_module.get("message"),
        )
        self.assertIn("traceback", error_log_module)  # Check for the key
        self.assertIn(
            "ValueError: This module is designed to fail for MCI testing",
            error_log_module.get("traceback"),
        )  # Check content of traceback

        # Check for the final processing log indicating failure
        processed_failed_log = next(
            (
                le
                for le in log_entries
                if le.get("message", "").startswith("Command processing finished.")
                and le.get("command_id") == cmd_id
                and le.get("level") == "ERROR"
            ),
            None,
        )
        self.assertIsNotNone(
            processed_failed_log,
            "Log entry for command processing finished with failure not found.",
        )
        self.assertEqual(
            processed_failed_log.get("summary"),
            "ValueError: This module is designed to fail for MCI testing",
        )

        self.assert_command_processed_and_archived(
            cmd_file_path,
            cmd_id,
            expected_status="failed",
            expected_summary_part="ValueError: This module is designed to fail for MCI testing",
        )

    def test_mci_file_restoration_status(self):
        # Agent's main() should restore status file from internal default if missing
        if AGENT_STATUS_FILE.exists():
            AGENT_STATUS_FILE.unlink()
        self.assertFalse(AGENT_STATUS_FILE.exists())
        self.create_command_file(
            {
                "id": "dummy_for_restore_test",
                "type": "log_event",
                "message": "run agent for restore",
            }
        )
        self.run_agent_mci()
        self.assertTrue(
            AGENT_STATUS_FILE.exists(),
            "AGENT_STATUS_FILE was not restored by agent.",
        )
        status_data = json.loads(AGENT_STATUS_FILE.read_text())
        # Check against DEFAULT_STATUS content used in agent's main()
        self.assertEqual(
            status_data.get("status"), "idle_restored_from_internal_default"
        )
        self.assertTrue(is_iso_timestamp_str(status_data.get("timestamp")))
        self.assertIn("internal default structure", status_data.get("notes", ""))

    def test_mci_malformed_command_file(self):
        malformed_dir = COMMANDS_DIR / "malformed_tests"
        malformed_dir.mkdir(parents=True, exist_ok=True)
        malformed_file_path = malformed_dir / "malformed_cmd_test.json"
        with open(malformed_file_path, "w") as f:
            # Valid JSON, but an array, not a dict (object) as expected for a command
            json.dump(
                [{"item_in_array": "this should be skipped as non-dict command_data"}],
                f,
            )

        valid_cmd_id = "mci_valid_after_malformed"
        valid_cmd_data = {
            "id": valid_cmd_id,
            "type": "log_event",
            "message": "Valid command after malformed",
        }
        valid_cmd_file_path = self.create_command_file(
            valid_cmd_data, sub_dir="general_valid", filename_prefix="valid"
        )
        self.run_agent_mci()

        log_entries = get_json_log_entries(EVENTS_LOG_FILE)

        # Check for the warning log from load_commands
        malformed_log_found = False
        for entry in log_entries:
            if (
                entry.get("level") == "WARNING"
                and entry.get("function") == "load_commands"
                and f"Content of {malformed_file_path} is not a JSON object. Skipping."
                in entry.get("message", "")
            ):
                self.assertEqual(entry.get("file_path"), str(malformed_file_path))
                malformed_log_found = True
                break
        self.assertTrue(
            malformed_log_found,
            "Log entry for malformed command (non-dict object) not found.",
        )

        # Verify the malformed file was NOT moved by main's non-dict logic, as load_commands skips it.
        self.assertTrue(
            malformed_file_path.exists(),
            "Malformed file (valid JSON array) should NOT have been deleted by load_commands or moved by main's non-dict logic.",
        )

        processed_malformed_dir = PROCESSED_DIR / "malformed"
        moved_malformed_exists = False
        if (
            processed_malformed_dir.exists()
        ):  # The "malformed" dir might not even be created if no file ever triggers that specific logic in main.
            moved_malformed_exists = any(
                f.name.startswith("malformed_cmd_test")
                for f in processed_malformed_dir.iterdir()
            )
        self.assertFalse(
            moved_malformed_exists,
            "Malformed file (JSON array) should not have been moved to processed/malformed by main's non-dict handling.",
        )

        # Verify the valid command was processed
        self.assert_command_processed_and_archived(valid_cmd_file_path, valid_cmd_id)

    def test_log_levels_and_structured_fields(self):
        cmd_id = "mci_log_levels_001"
        # For this test, we'll rely on existing log messages generated by a simple command.
        # We are checking if the levels are correctly recorded and standard fields are present.
        # The katana_agent.py is set to logging.DEBUG, so all levels should be recorded.

        # Create a simple command that will generate some logs
        cmd_data = {
            "id": cmd_id,
            "type": "log_event",
            "message": "Test message for log levels",
        }
        self.create_command_file(cmd_data, sub_dir="logging_tests")
        self.run_agent_mci()

        log_entries = get_json_log_entries(EVENTS_LOG_FILE)
        self.assertTrue(len(log_entries) > 0, "No log entries found.")

        # Example: Find a log entry related to processing this command
        # Agent logs "Processing command..." at INFO level
        processing_log = next(
            (
                le
                for le in log_entries
                if le.get("command_id") == cmd_id
                and "Processing command" in le.get("message")
            ),
            None,
        )
        self.assertIsNotNone(processing_log, "Processing log for command not found.")

        self.assertEqual(processing_log.get("level"), "INFO")
        self.assertEqual(processing_log.get("command_id"), cmd_id)  # Check extra field
        self.assertEqual(processing_log.get("module"), "katana_agent")
        self.assertTrue(isinstance(processing_log.get("function"), str))  # e.g. main
        self.assertTrue(isinstance(processing_log.get("line_number"), int))
        self.assertTrue(is_iso_timestamp_str(processing_log.get("timestamp")))

        # Check for a DEBUG level log (e.g., "Start of main agent processing cycle.")
        # This assumes the agent's main loop produces DEBUG logs as configured.
        debug_log = next(
            (
                le
                for le in log_entries
                if le.get("level") == "DEBUG"
                and "Start of main agent processing cycle" in le.get("message")
            ),
            None,
        )
        self.assertIsNotNone(debug_log, "A DEBUG level log was expected but not found.")
        self.assertEqual(debug_log.get("module"), "katana_agent")

        # To test WARNING, ERROR, CRITICAL more directly, we'd need commands that reliably trigger them.
        # test_mci_failing_module already tests ERROR with exception.
        # A command causing a warning (e.g. malformed json that's skippable) is in test_mci_malformed_command_file

        # Find a warning log (e.g. from status file check if it was corrupted - harder to force here)
        # For now, we assume other tests like test_mci_malformed_command_file cover WARNING.
        # And startup logs cover CRITICAL if a required dir fails.

    def test_explicit_exception_logging(self):
        # This test relies on the failing_module created in setUpClass
        cmd_id = "mci_exception_log_001"
        module_name = self.failing_module_name
        cmd_data = {
            "id": cmd_id,
            "type": "trigger_module",
            "module": module_name,
            "args": {"force_exception_log": True},
        }
        cmd_file_path = self.create_command_file(cmd_data, sub_dir="testing_exceptions")

        self.run_agent_mci()

        log_entries = get_json_log_entries(EVENTS_LOG_FILE)
        self.assertTrue(len(log_entries) > 0, "Log file is empty.")

        # Find the error log from execute_module for this specific command
        error_log = next(
            (
                le
                for le in log_entries
                if le.get("level") == "ERROR"
                and le.get("command_id") == cmd_id
                and le.get("function") == "execute_module"
                and "Error executing module" in le.get("message", "")
            ),
            None,
        )

        self.assertIsNotNone(
            error_log,
            "Module execution error log not found for exception test.",
        )
        self.assertIn(
            "traceback",
            error_log,
            "The 'traceback' field is missing from the error log.",
        )
        self.assertTrue(
            isinstance(error_log.get("traceback"), str),
            "Traceback should be a string.",
        )
        self.assertIn(
            "ValueError: This module is designed to fail for MCI testing",
            error_log.get("traceback"),
            "Traceback content mismatch.",
        )
        self.assert_command_processed_and_archived(
            cmd_file_path, cmd_id, expected_status="failed"
        )

    # test_log_rotation will be added in a subsequent step due to its complexity.

    def test_log_rotation(self):
        # This test uses a separate logger and handler to avoid interfering with global agent logging
        # and to allow for specific parameters for rotation.

        # 1. Setup a temporary logger for this test
        temp_log_file_name = "rotation_test_temp.log"
        temp_log_file_path = (
            LOGS_DIR / temp_log_file_name
        )  # Ensure it's cleaned up by setUp

        # Make sure the file doesn't exist from a previous failed run before setting up handler
        if temp_log_file_path.exists():
            temp_log_file_path.unlink()
        for i in range(1, 6):  # Clean up potential backups too
            backup_file = Path(f"{temp_log_file_path}.{i}")
            if backup_file.exists():
                backup_file.unlink()

        test_logger = logging.getLogger("RotationTestLogger")
        test_logger.propagate = (
            False  # Don't let messages go to the root logger / other handlers
        )
        test_logger.setLevel(logging.DEBUG)

        # MaxBytes set low to trigger rotation quickly. backupCount=2 for manageable checks.
        # Using a small message and many iterations to fill it.
        # Each JSON log entry is approx 200-300 bytes. 1KB maxBytes should trigger rotation.
        # Let's aim for a bit over 1KB. A 200-byte message * 10 times = 2KB.
        handler_max_bytes = 1024
        handler_backup_count = 2

        # Ensure JsonFormatter is available or define a simple one if needed for isolation.
        # For this test, the globally defined JsonFormatter is fine.
        # from katana.mci_agent.katana_agent import JsonFormatter # Not ideal to import from agent in test like this
        # For now, assume JsonFormatter class is accessible as it's defined in this test file's scope or imported.
        # If not, it would need to be defined or imported here.
        # It's defined globally in this file (JsonFormatter).

        # Remove existing handlers if any from previous test runs (if logger name is reused)
        if test_logger.hasHandlers():
            for handler in test_logger.handlers[:]:  # Iterate over a copy
                handler.close()
                test_logger.removeHandler(handler)

        rotating_handler = RotatingFileHandler(  # Use imported RotatingFileHandler
            temp_log_file_path,
            maxBytes=handler_max_bytes,
            backupCount=handler_backup_count,
        )
        rotating_handler.setFormatter(
            JsonFormatter()
        )  # JsonFormatter is defined in this file
        rotating_handler.setLevel(logging.DEBUG)  # Use imported logging
        test_logger.addHandler(rotating_handler)

        # 2. Generate log data to trigger rotation
        # A sample JSON log line is about ~250 bytes.
        # To exceed 1024 bytes, we need about 5-6 such lines.
        # To ensure rotation and backups, let's write more, e.g., 3 * (backupCount + 1) * (max_lines_per_file)
        # (2+1) * 6 = 18 messages should be plenty for 2 backups. Let's do 20.
        log_message_content = "This is a test log message for rotation. It needs to be somewhat long to ensure file size is met quickly with JSON overhead."
        num_log_entries_to_write = 20

        for i in range(num_log_entries_to_write):
            test_logger.info(
                f"{log_message_content} - Entry {i+1}",
                extra={"test_rotation_index": i + 1},
            )

        # Close the handler to ensure logs are flushed and files are closed.
        rotating_handler.close()
        test_logger.removeHandler(rotating_handler)  # Clean up handler from logger

        # 3. Verify rotation
        self.assertTrue(
            temp_log_file_path.exists(),
            f"Main log file {temp_log_file_path} should exist.",
        )

        # Check for backup files
        backup_files_found = 0
        for i in range(1, handler_backup_count + 1):
            expected_backup_file = Path(f"{str(temp_log_file_path)}.{i}")
            if expected_backup_file.exists():
                backup_files_found += 1
                # Optionally, check content or size of backup files
                self.assertTrue(
                    expected_backup_file.stat().st_size > 0,
                    f"Backup file {expected_backup_file} is empty.",
                )

        self.assertEqual(
            backup_files_found,
            handler_backup_count,
            f"Expected {handler_backup_count} backup files, but found {backup_files_found}. Files: {list(LOGS_DIR.glob(temp_log_file_name + '*'))}",
        )

        # Check current log file size (it should be less than or equal to maxBytes,
        # or slightly more if a single message caused it to exceed)
        current_log_size = temp_log_file_path.stat().st_size
        self.assertLessEqual(
            current_log_size,
            handler_max_bytes + 300,  # Allow some leeway for the last message
            f"Current log file {temp_log_file_path} size {current_log_size} "
            f"is unexpectedly larger than maxBytes {handler_max_bytes} (plus margin).",
        )

        # Verify total number of log files (original + backups)
        all_log_files = list(LOGS_DIR.glob(f"{temp_log_file_name}*"))
        self.assertEqual(
            len(all_log_files),
            handler_backup_count + 1,
            f"Expected total {handler_backup_count + 1} log files (original + backups), found {len(all_log_files)}.",
        )

        # Cleanup of the temporary log files will be handled by setUp's rmtree(LOGS_DIR)
        # or can be done explicitly here if preferred.
        # For safety, explicitly remove them here.
        temp_log_file_path.unlink(missing_ok=True)
        for i in range(
            1, handler_backup_count + 2
        ):  # Iterate a bit more to catch any extras
            backup_file = Path(f"{str(temp_log_file_path)}.{i}")
            backup_file.unlink(missing_ok=True)


if __name__ == "__main__":
    # print(f"Unittest script running from: {Path(__file__).resolve().parent}")
    # print(f"AGENT_BASE_DIR for tests: {AGENT_BASE_DIR}")
    unittest.main(verbosity=2)
