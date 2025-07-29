import unittest
import os
import json
import tempfile
import shutil
from katana import post_task_verifier # Assuming katana is in PYTHONPATH or installed

# Helper to reset DUMMY_TASK_EXPECTATIONS to its original state if modified by tests
ORIGINAL_DUMMY_TASK_EXPECTATIONS = post_task_verifier.DUMMY_TASK_EXPECTATIONS.copy()

class TestPostTaskVerifier(unittest.TestCase):

    def setUp(self):
        # Create a temporary directory for test files
        self.test_dir = tempfile.mkdtemp()
        # Ensure DUMMY_TASK_EXPECTATIONS is reset for each test
        post_task_verifier.DUMMY_TASK_EXPECTATIONS = ORIGINAL_DUMMY_TASK_EXPECTATIONS.copy()

        # Define paths for files used in tests within the temp directory
        self.config_env_path = os.path.join(self.test_dir, "config.env")
        self.migrations_log_path = os.path.join(self.test_dir, "migrations.log")

        # Update DUMMY_TASK_EXPECTATIONS to use these temporary paths
        if "create_config_file" in post_task_verifier.DUMMY_TASK_EXPECTATIONS:
            post_task_verifier.DUMMY_TASK_EXPECTATIONS["create_config_file"]["filepath"] = self.config_env_path
        if "run_migrations" in post_task_verifier.DUMMY_TASK_EXPECTATIONS:
            post_task_verifier.DUMMY_TASK_EXPECTATIONS["run_migrations"]["log_file"] = self.migrations_log_path

        # A specific task for testing log failure due to missing keyword
        post_task_verifier.DUMMY_TASK_EXPECTATIONS["run_migrations_keyword_miss_test"] = {
            "type": "log_check",
            "log_file": self.migrations_log_path, # Use the same temp log path
            "success_keyword": "SPECIFIC_SUCCESS_KEYWORD",
            "failure_reason": "ключевое слово SPECIFIC_SUCCESS_KEYWORD не найдено.",
            "failure_fix": f"проверить {self.migrations_log_path}."
        }


    def tearDown(self):
        # Remove the temporary directory and its contents
        shutil.rmtree(self.test_dir)
        # Restore original DUMMY_TASK_EXPECTATIONS if it was changed by specific tests beyond path updates
        post_task_verifier.DUMMY_TASK_EXPECTATIONS = ORIGINAL_DUMMY_TASK_EXPECTATIONS

    def test_verify_task_success_generic(self):
        task_id = "successful_task"
        result = post_task_verifier.verify_task(task_id)
        self.assertEqual(result["status"], "success")
        self.assertEqual(result["task_id"], task_id)
        self.assertIn("message", result)

    def test_verify_task_file_check_failure(self):
        task_id = "create_config_file"
        # Ensure the file does NOT exist
        if os.path.exists(self.config_env_path):
            os.remove(self.config_env_path)

        result = post_task_verifier.verify_task(task_id)
        self.assertEqual(result["status"], "failure")
        self.assertEqual(result["task_id"], task_id)
        self.assertEqual(result["verification_method"], "file_check")
        self.assertEqual(result["reason"], post_task_verifier.DUMMY_TASK_EXPECTATIONS[task_id]["failure_reason"])

    def test_verify_task_file_check_success(self):
        task_id = "create_config_file"
        # Ensure the file DOES exist
        with open(self.config_env_path, "w") as f:
            f.write("TEST_VAR=1")

        result = post_task_verifier.verify_task(task_id)
        self.assertEqual(result["status"], "success")
        self.assertEqual(result["task_id"], task_id)
        self.assertEqual(result["verification_method"], "file_check")
        self.assertIn("message", result)
        self.assertEqual(result["message"], post_task_verifier.DUMMY_TASK_EXPECTATIONS[task_id]["success_message"])


    def test_verify_task_log_check_simulated_creation_and_success(self):
        task_id = "run_migrations" # This task simulates log creation if not present in verify_task
        # Ensure log file does not exist initially to test creation path
        if os.path.exists(self.migrations_log_path):
            os.remove(self.migrations_log_path)

        result = post_task_verifier.verify_task(task_id)
        self.assertEqual(result["status"], "success")
        self.assertEqual(result["task_id"], task_id)
        self.assertEqual(result["verification_method"], "log_check")
        self.assertTrue(os.path.exists(self.migrations_log_path)) # Check if log was created

    def test_verify_task_log_check_failure_missing_keyword(self):
        task_id = "run_migrations_keyword_miss_test"
        # Create the log file but WITHOUT the success keyword
        with open(self.migrations_log_path, "w") as f:
            f.write("Some other log content, but not the keyword.\n")

        result = post_task_verifier.verify_task(task_id)
        self.assertEqual(result["status"], "failure")
        self.assertEqual(result["task_id"], task_id)
        self.assertEqual(result["verification_method"], "log_check")
        self.assertEqual(result["reason"], post_task_verifier.DUMMY_TASK_EXPECTATIONS[task_id]["failure_reason"])

    def test_verify_task_port_check_simulated_success(self):
        # Relies on the default simulation in check_service_port
        task_id = "start_server" # Assumes this task is in DUMMY_TASK_EXPECTATIONS with type port_check
        if task_id not in post_task_verifier.DUMMY_TASK_EXPECTATIONS or \
           post_task_verifier.DUMMY_TASK_EXPECTATIONS[task_id]["type"] != "port_check":
            self.skipTest(f"Task {task_id} not configured for port_check in DUMMY_TASK_EXPECTATIONS")

        result = post_task_verifier.verify_task(task_id)
        self.assertEqual(result["status"], "success") # Default simulation is success
        self.assertEqual(result["task_id"], task_id)
        self.assertEqual(result["verification_method"], "port_check")

    def test_verify_task_unknown_task_forced_failure(self):
        task_id = "unknown_task_force_fail" # This is a special case in verify_task
        result = post_task_verifier.verify_task(task_id)
        self.assertEqual(result["status"], "failure")
        self.assertEqual(result["task_id"], task_id)
        self.assertEqual(result["verification_method"], "unknown")
        self.assertIn("неизвестна системе верификации", result["reason"])

    def test_verify_task_unknown_task_default_success(self):
        task_id = "completely_new_unknown_task" # Not in DUMMY_TASK_EXPECTATIONS at all
        result = post_task_verifier.verify_task(task_id)
        # Current default for truly unknown tasks is success with a note
        self.assertEqual(result["status"], "success")
        self.assertEqual(result["task_id"], task_id)
        self.assertEqual(result["verification_method"], "none")
        self.assertTrue(result["reason"].startswith(f"Задача '{task_id}' не имеет специфических критериев"))


    def test_write_katana_result(self):
        test_result_data = {"task_id": "test_write", "status": "success", "message": "written"}
        # Use a temporary file within the test_dir for this test
        temp_output_json = os.path.join(self.test_dir, "output_test.json")

        post_task_verifier.write_katana_result(test_result_data, temp_output_json)

        self.assertTrue(os.path.exists(temp_output_json))
        with open(temp_output_json, 'r') as f:
            loaded_data = json.load(f)
        self.assertEqual(loaded_data, test_result_data)

    def test_write_katana_result_ensure_ascii_false(self):
        test_result_data = {"task_id": "test_cyrillic", "status": "failure", "reason": "Ошибка: файл не найден"}
        temp_output_json = os.path.join(self.test_dir, "output_cyrillic_test.json")

        post_task_verifier.write_katana_result(test_result_data, temp_output_json)

        with open(temp_output_json, 'r', encoding='utf-8') as f:
            content = f.read()
            # Check if Cyrillic characters are preserved directly
            self.assertIn("Ошибка: файл не найден", content)

        with open(temp_output_json, 'r', encoding='utf-8') as f:
            loaded_data = json.load(f)
        self.assertEqual(loaded_data, test_result_data)


if __name__ == '__main__':
    unittest.main()

# Ensure __init__.py exists in tests directory if needed for discovery, though not strictly for unittest.main()
# For pytest discovery, ensure `katana` module can be found.
# One way is to run tests from the project root: `python -m unittest tests.test_post_task_verifier`
# Or configure PYTHONPATH.
# For simplicity, assuming the structure allows `from katana import post_task_verifier` to work
# if tests are run from the root or `src` is in PYTHONPATH.
# If `katana` is a top-level directory sibling to `tests`, then this import should work.
# Let's adjust the import path assuming `katana` is a top-level directory.
# The file `post_task_verifier.py` is inside `katana/` directory.
# So, `from katana import post_task_verifier` is correct if PYTHONPATH includes the project root.
# If the project root has `katana/` and `tests/`, running `python -m unittest discover -s tests` from root should work.

# Adding an __init__.py to katana directory if it's missing, for robust imports.
# (This should be done by a separate tool call if needed)
# Adding an __init__.py to tests directory.
# (This should be done by a separate tool call if needed)
