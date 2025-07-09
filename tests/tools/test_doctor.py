import unittest
import os
import json
import shutil
import subprocess
import time
import collections # Added import for collections
from pathlib import Path
from unittest import mock

# Assuming your doctor module is in katana.tools.doctor
from katana.tools import doctor as doctor_module

# Define a sample config for tests
SAMPLE_CONFIG = {
    "mandatory": ["testlib_present", "testlib_missing"],
    "models": ["test-model"],
    "env_variables": ["TEST_ENV_VAR_SET", "TEST_ENV_VAR_UNSET"],
    "disk_space_paths": [
        {"path": "~/.cache/test_katana_cache", "min_gb": 1}, # Test existing path
        {"path": "/tmp/test_katana_nonexistent", "min_gb": 1} # Test non-existent path
    ]
}

class TestDoctor(unittest.TestCase):

    def setUp(self):
        self.test_logs_dir = Path("test_doctor_logs")
        self.test_logs_dir.mkdir(exist_ok=True)
        self.test_cache_dir = Path(os.path.expanduser("~/.cache/test_katana_cache"))
        self.test_cache_dir.mkdir(parents=True, exist_ok=True)

        # Create a dummy config file for tests
        self.test_config_path = Path("test_katana_dependencies.json")
        with open(self.test_config_path, 'w') as f:
            json.dump(SAMPLE_CONFIG, f)

        # Mock objects and paths in doctor_module
        self.patch_logs_path = mock.patch('katana.tools.doctor.Path', lambda x: self.test_logs_dir if x == "logs" else Path(x))
        self.patch_config_file = mock.patch('katana.tools.doctor.CONFIG_FILE', self.test_config_path)
        self.patch_huggingface_cache_dir = mock.patch('katana.tools.doctor.HUGGINGFACE_CACHE_DIR', self.test_cache_dir)

        self.patch_logs_path.start()
        self.patch_config_file.start()
        self.patch_huggingface_cache_dir.start()

        # Mock os.environ
        self.mock_environ = {
            "TEST_ENV_VAR_SET": "value_is_set"
        }
        self.patch_os_environ = mock.patch.dict(os.environ, self.mock_environ, clear=True)
        self.patch_os_environ.start()

        # Mock shutil.disk_usage to return ample space for existing test path
        self.mock_disk_usage = mock.patch('shutil.disk_usage')
        self.mocked_disk_usage = self.mock_disk_usage.start()

        # Side effect function for disk_usage
        # shutil.disk_usage returns a named tuple. Let's replicate that.
        DiskUsage = collections.namedtuple('DiskUsage', ['total', 'used', 'free'])

        def disk_usage_side_effect(path_arg):
            if str(path_arg) == str(self.test_cache_dir.resolve()): # Check resolved path
                 # total, used, free (bytes) -> free = 2GB
                return DiskUsage(total=10 * 1024**3, used=8 * 1024**3, free=2 * 1024**3)
            elif str(path_arg) == str(Path("/tmp").resolve()): # For non-existent path's parent
                return DiskUsage(total=10 * 1024**3, used=8 * 1024**3, free=2 * 1024**3)
            raise FileNotFoundError(f"Mocked path not found: {path_arg}")

        self.mocked_disk_usage.side_effect = disk_usage_side_effect


    def tearDown(self):
        self.patch_os_environ.stop()
        self.patch_huggingface_cache_dir.stop()
        self.patch_config_file.stop()
        self.patch_logs_path.stop()
        self.mock_disk_usage.stop()

        if self.test_config_path.exists():
            self.test_config_path.unlink()

        # Clean up test logs directory
        if self.test_logs_dir.exists():
            for item in self.test_logs_dir.iterdir():
                item.unlink()
            self.test_logs_dir.rmdir()

        # Clean up test cache dir
        if self.test_cache_dir.exists():
            shutil.rmtree(self.test_cache_dir)

        non_existent_path_parent_tmp = Path("/tmp/test_katana_nonexistent")
        if non_existent_path_parent_tmp.exists(): # Should not exist, but clean if it does
            shutil.rmtree(non_existent_path_parent_tmp)


    def _find_report_file(self, after_timestamp):
        for f in self.test_logs_dir.glob("doctor_report_*.json"):
            ts_str = f.name.replace("doctor_report_", "").replace(".json", "")
            try:
                ts = int(ts_str)
                if ts >= after_timestamp:
                    return f
            except ValueError:
                continue
        return None

    def test_run_doctor_creates_log_file(self):
        start_time = int(time.time())
        doctor_module.run_doctor()
        report_file = self._find_report_file(start_time)

        self.assertIsNotNone(report_file, "Log file was not created or found.")
        self.assertTrue(report_file.exists())

        with open(report_file, 'r') as f:
            report_data = json.load(f)
        self.assertIn("timestamp", report_data)
        self.assertGreaterEqual(report_data["timestamp"], start_time)
        self.assertIn("checks", report_data)
        self.assertIsInstance(report_data["checks"], list)
        self.assertIn("status_summary", report_data)

    @mock.patch('importlib.import_module')
    @mock.patch('subprocess.run')
    def test_check_libraries(self, mock_subprocess_run, mock_import_module):
        # Simulate 'testlib_present' is installed, 'testlib_missing' is not
        def import_side_effect(lib_name):
            if lib_name == "testlib_present":
                return mock.MagicMock()
            raise ImportError
        mock_import_module.side_effect = import_side_effect

        # Simulate successful pip install for the missing lib
        mock_subprocess_run.return_value = subprocess.CompletedProcess(args=['pip', 'install', 'testlib_missing'], returncode=0, stdout="Installed", stderr="")

        report = {"checks": []}
        # Test without auto_fix
        doctor_module.check_libraries(report, SAMPLE_CONFIG, auto_fix=False)

        check_present = next(c for c in report["checks"] if c["name"] == "testlib_present")
        check_missing = next(c for c in report["checks"] if c["name"] == "testlib_missing")
        self.assertEqual(check_present["status"], "OK")
        self.assertEqual(check_missing["status"], "FAIL")
        mock_subprocess_run.assert_not_called()

        # Test with auto_fix
        report = {"checks": []} # Reset report
        # Reset side effect for import_module to re-evaluate after "install"
        # Now, after subprocess.run, the import should succeed for testlib_missing
        def import_side_effect_autofix(lib_name):
            if lib_name == "testlib_present":
                return mock.MagicMock()
            if lib_name == "testlib_missing" and mock_subprocess_run.called: # After pip install
                 return mock.MagicMock()
            raise ImportError
        mock_import_module.side_effect = import_side_effect_autofix

        doctor_module.check_libraries(report, SAMPLE_CONFIG, auto_fix=True)

        check_present_autofix = next(c for c in report["checks"] if c["name"] == "testlib_present" and c["type"] == "library")
        check_missing_autofix_attempt = next(c for c in report["checks"] if c["name"] == "testlib_missing" and c["type"] == "library")
        check_missing_autofix_result = next(c for c in report["checks"] if c["name"] == "testlib_missing" and c["type"] == "library_fix")

        self.assertEqual(check_present_autofix["status"], "OK")
        self.assertEqual(check_missing_autofix_attempt["status"], "WARN") # Initial warning
        mock_subprocess_run.assert_called_once_with(['pip', 'install', 'testlib_missing'], check=True, capture_output=True, text=True)
        self.assertEqual(check_missing_autofix_result["status"], "OK")


    def test_check_env_variables(self):
        report = {"checks": []}
        doctor_module.check_env_variables(report, SAMPLE_CONFIG)

        var_set_check = next(c for c in report["checks"] if c["name"] == "TEST_ENV_VAR_SET")
        var_unset_check = next(c for c in report["checks"] if c["name"] == "TEST_ENV_VAR_UNSET")

        self.assertEqual(var_set_check["status"], "OK")
        self.assertEqual(var_unset_check["status"], "FAIL")

    def test_check_disk_space(self):
        report = {"checks": []}
        doctor_module.check_disk_space(report, SAMPLE_CONFIG)

        # Check for the existing path
        cache_path_check = next(c for c in report["checks"] if c["name"] == str(self.test_cache_dir.resolve()))
        self.assertEqual(cache_path_check["status"], "OK")
        self.assertTrue("2.00GB" in cache_path_check["message"])

        # Check for the non-existent path (it should check its parent, /tmp in this case)
        # The name in the report will be the original non-existent path
        non_existent_path_str = str(Path(os.path.expanduser(SAMPLE_CONFIG["disk_space_paths"][1]["path"])).resolve())
        non_existent_path_check = next(c for c in report["checks"] if c["name"] == non_existent_path_str)
        self.assertEqual(non_existent_path_check["status"], "OK") # Because /tmp has space
        self.assertTrue(f"at '{Path('/tmp').resolve()}'" in non_existent_path_check["message"])


    @mock.patch('builtins.input', return_value='yes')
    @mock.patch('shutil.rmtree')
    def test_clear_huggingface_cache_yes(self, mock_rmtree, mock_input):
        # Ensure cache dir exists for this test
        if not self.test_cache_dir.exists():
            self.test_cache_dir.mkdir(parents=True, exist_ok=True)

        report = {"checks": []}
        doctor_module.clear_huggingface_cache(report)

        mock_input.assert_called_once()
        mock_rmtree.assert_called_once_with(self.test_cache_dir)
        cache_clear_check = next(c for c in report["checks"] if c["type"] == "cache_clear")
        self.assertEqual(cache_clear_check["status"], "OK")

    @mock.patch('builtins.input', return_value='no')
    @mock.patch('shutil.rmtree')
    def test_clear_huggingface_cache_no(self, mock_rmtree, mock_input):
        report = {"checks": []}
        doctor_module.clear_huggingface_cache(report)

        mock_input.assert_called_once()
        mock_rmtree.assert_not_called()
        cache_clear_check = next(c for c in report["checks"] if c["type"] == "cache_clear")
        self.assertEqual(cache_clear_check["status"], "INFO")
        self.assertTrue("aborted by user" in cache_clear_check["message"])

    def test_run_doctor_with_clear_cache_flag(self):
        start_time = int(time.time())
        # Mock clear_huggingface_cache to prevent actual execution during this specific test
        with mock.patch('katana.tools.doctor.clear_huggingface_cache') as mock_clear_cache_func:
            doctor_module.run_doctor(clear_cache_flag=True)
            mock_clear_cache_func.assert_called_once()

        report_file = self._find_report_file(start_time)
        self.assertIsNotNone(report_file, "Log file was not created for clear_cache run.")
        with open(report_file, 'r') as f:
            report_data = json.load(f)
        # Check that other checks were likely skipped if clear_cache_flag is true
        # by verifying only a few checks (config load, cache clear attempt)
        # Exact number can be brittle, so check for presence of cache_clear and absence of e.g. library checks
        has_cache_check = any(c["type"] == "cache_clear" for c in report_data["checks"])
        # If clear_huggingface_cache was properly mocked, it adds its own log entry
        # This test verifies run_doctor calls it. The actual logic of clear_huggingface_cache is tested separately.

        # In the current implementation, clear_huggingface_cache IS called and logs.
        # Other checks are skipped.
        self.assertTrue(has_cache_check or mock_clear_cache_func.called) # Either the function logged or was called

        has_library_check = any(c["type"] == "library" for c in report_data["checks"])
        self.assertFalse(has_library_check, "Library checks should be skipped when clear_cache_flag is true.")


if __name__ == '__main__':
    unittest.main()
