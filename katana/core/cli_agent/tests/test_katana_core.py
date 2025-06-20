import unittest
import os
import sys
from pathlib import Path
import importlib
from unittest.mock import patch, MagicMock, mock_open, call, ANY
import json # For json.JSONDecodeError

# Adjust sys.path to include the project root
project_root = Path(__file__).resolve().parent.parent.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

# Module to be tested
kc_module_path = 'katana.core.cli_agent.katana'
katana_core_module = None
try:
    from katana.core.cli_agent import katana as katana_core_module
except KeyError as e:
    if 'KATANA_LOG_LEVEL' in str(e):
        os.environ['KATANA_LOG_LEVEL'] = 'INFO'
        from katana.core.cli_agent import katana as katana_core_module
    else:
        raise
except ImportError:
    pass # Will be skipped in setUp

class TestKatanaCore(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        if 'KATANA_LOG_LEVEL' not in os.environ:
            os.environ['KATANA_LOG_LEVEL'] = 'INFO'

        global katana_core_module
        # Attempt to load/reload the module here to catch critical import errors early
        # and ensure KATANA_LOG_LEVEL is respected for the logger initialization in katana.py
        try:
            if katana_core_module:
                katana_core_module = importlib.reload(katana_core_module)
            elif kc_module_path in sys.modules: # If imported but katana_core_module is None
                 katana_core_module = importlib.reload(sys.modules[kc_module_path])
            else:
                katana_core_module = importlib.import_module(kc_module_path)
        except ImportError:
            katana_core_module = None # Mark as None if import fails

    def setUp(self):
        if not katana_core_module:
            self.skipTest(f"KatanaCore module ({kc_module_path}) could not be loaded.")

        # Reload module for each test to ensure clean state
        # This is crucial because KatanaCore initializes files and state in __init__
        globals()['katana_core_module'] = importlib.reload(katana_core_module)

        self.mock_core_dir_path_str = "/mock/katana_core"

        # Patch the logger used in katana.py
        self.logger_patcher = patch(f'{kc_module_path}.logger', new_callable=MagicMock)
        self.mock_logger = self.logger_patcher.start()
        self.addCleanup(self.logger_patcher.stop)

        # Patch pathlib.Path
        self.path_patcher = patch(f'{kc_module_path}.Path', autospec=True)
        self.MockPath = self.path_patcher.start()
        self.addCleanup(self.path_patcher.stop)

        # Configure the Path mock
        # Instance of Path(core_dir_path_str)
        self.mock_core_path_obj = MagicMock(spec=Path)
        self.mock_core_path_obj.resolve.return_value = self.mock_core_path_obj # resolve() returns itself
        self.mock_core_path_obj.__str__.return_value = self.mock_core_dir_path_str # String representation

        # Path() constructor should return our mock_core_path_obj when called with core_dir_path_str
        self.MockPath.side_effect = lambda x: self.mock_core_path_obj if x == self.mock_core_dir_path_str else MagicMock(spec=Path)

        # Mock the behavior of joining paths (e.g., self.core_dir / 'commands.json')
        self.mock_resolved_path_obj = self.mock_core_path_obj # This is what self.core_dir becomes

        # When self.core_dir / "some_file.json" is called:
        # It should return a new Path object that has .exists(), .parent.mkdir(), etc.
        def truediv_side_effect(other_path_part):
            full_path_str = f"{self.mock_core_dir_path_str}/{other_path_part}"
            mock_file_path_obj = MagicMock(spec=Path)
            mock_file_path_obj.__str__.return_value = full_path_str
            mock_file_path_obj.exists = MagicMock(return_value=True) # Default to exists = True
            mock_file_path_obj.parent.mkdir = MagicMock()
            # Store the path string directly on the mock for easier identification in tests
            mock_file_path_obj.mock_path_name = full_path_str
            return mock_file_path_obj

        self.mock_resolved_path_obj.__truediv__.side_effect = truediv_side_effect


        # Patch file operations
        self.m_open_patcher = patch(f'{kc_module_path}.open', new_callable=mock_open)
        self.m_open = self.m_open_patcher.start()
        self.addCleanup(self.m_open_patcher.stop)

        self.json_load_patcher = patch(f'{kc_module_path}.json.load', new_callable=MagicMock)
        self.mock_json_load = self.json_load_patcher.start()
        self.addCleanup(self.json_load_patcher.stop)
        # Default to empty dict if not configured by a test
        self.mock_json_load.return_value = {}

        self.json_dump_patcher = patch(f'{kc_module_path}.json.dump', new_callable=MagicMock)
        self.mock_json_dump = self.json_dump_patcher.start()
        self.addCleanup(self.json_dump_patcher.stop)


    def test_dummy_test(self):
        """A dummy test to ensure the file is created and runnable."""
        self.assertTrue(True)

    def _configure_json_load_side_effect(self, file_content_map):
        """Helper to configure mock_json_load side effect based on a map of file paths to content."""
        def side_effect(fp):
            opened_file_path_str = ""
            if self.m_open.call_args:
                path_arg = self.m_open.call_args[0][0]
                if isinstance(path_arg, MagicMock) and hasattr(path_arg, 'mock_path_name'):
                    opened_file_path_str = path_arg.mock_path_name
                else:
                    opened_file_path_str = str(path_arg)

            if opened_file_path_str in file_content_map:
                content = file_content_map[opened_file_path_str]
                if isinstance(content, Exception):
                    raise content
                return content
            return {}
        self.mock_json_load.side_effect = side_effect

    def test_load_commands_success(self):
        commands_data = {"greet": "echo Hello"}
        file_path_obj = self.mock_resolved_path_obj / 'commands.json'
        file_path_str = str(file_path_obj)
        self._configure_json_load_side_effect({file_path_str: commands_data})

        core = katana_core_module.KatanaCore(core_dir_path_str=self.mock_core_dir_path_str)
        self.assertEqual(core.commands, commands_data)
        self.mock_logger.info.assert_any_call(f"Commands loaded successfully from {file_path_obj}")

    def test_load_commands_json_decode_error(self):
        file_path_obj = self.mock_resolved_path_obj / 'commands.json'
        file_path_str = str(file_path_obj)
        self._configure_json_load_side_effect({file_path_str: json.JSONDecodeError("mock error", "doc", 0)})

        core = katana_core_module.KatanaCore(core_dir_path_str=self.mock_core_dir_path_str)
        self.assertEqual(core.commands, {})
        self.mock_logger.error.assert_any_call(f"Error decoding JSON from {file_path_obj}: mock error: line 1 column 1 (char 0). Using empty command set.")

    def test_load_commands_file_not_found_error_during_load(self):
        commands_file_path_obj = self.mock_resolved_path_obj / 'commands.json'
        commands_file_path_obj.exists.return_value = True

        original_open_side_effect = self.m_open.side_effect
        def open_side_effect_for_test(path_arg, *args, **kwargs):
            path_str_arg = str(path_arg.mock_path_name if hasattr(path_arg, 'mock_path_name') else path_arg)
            if path_str_arg == str(commands_file_path_obj):
                raise FileNotFoundError(f"Mocked FileNotFoundError for {path_str_arg}")
            if original_open_side_effect and original_open_side_effect is not open_side_effect_for_test:
                 return original_open_side_effect(path_arg, *args, **kwargs)
            return mock_open().return_value
        self.m_open.side_effect = open_side_effect_for_test

        core = katana_core_module.KatanaCore(core_dir_path_str=self.mock_core_dir_path_str)
        self.assertEqual(core.commands, {})
        self.mock_logger.error.assert_any_call(f"Commands file {commands_file_path_obj} not found during load. Initializing empty.")
        self.mock_json_dump.assert_any_call({}, ANY, indent=2, ensure_ascii=False)

    def test_load_status_success(self):
        status_data = {"current_task": "testing"}
        file_path_obj = self.mock_resolved_path_obj / 'status.json'
        file_path_str = str(file_path_obj)
        self._configure_json_load_side_effect({file_path_str: status_data})
        core = katana_core_module.KatanaCore(core_dir_path_str=self.mock_core_dir_path_str)
        self.assertEqual(core.status, status_data)
        self.mock_logger.info.assert_any_call(f"Status loaded from {file_path_obj}")

    def test_load_status_json_decode_error(self):
        file_path_obj = self.mock_resolved_path_obj / 'status.json'
        file_path_str = str(file_path_obj)
        self._configure_json_load_side_effect({file_path_str: json.JSONDecodeError("status error", "doc", 0)})
        core = katana_core_module.KatanaCore(core_dir_path_str=self.mock_core_dir_path_str)
        self.assertEqual(core.status, {"last_sync": None, "last_command": None, "status":"error_loading"})
        self.mock_logger.error.assert_any_call(f"Error decoding JSON from {file_path_obj}: status error: line 1 column 1 (char 0). Using default status.")

    def test_load_memory_success(self):
        memory_data = {"thought": "test thought"}
        file_path_obj = self.mock_resolved_path_obj / 'memory.json'
        file_path_str = str(file_path_obj)
        self._configure_json_load_side_effect({file_path_str: memory_data})
        core = katana_core_module.KatanaCore(core_dir_path_str=self.mock_core_dir_path_str)
        self.assertEqual(core.memory, memory_data)
        self.mock_logger.info.assert_any_call(f"Memory loaded from {file_path_obj}")

    def test_load_memory_json_decode_error(self):
        file_path_obj = self.mock_resolved_path_obj / 'memory.json'
        file_path_str = str(file_path_obj)
        self._configure_json_load_side_effect({file_path_str: json.JSONDecodeError("memory error", "doc", 0)})
        core = katana_core_module.KatanaCore(core_dir_path_str=self.mock_core_dir_path_str)
        self.assertEqual(core.memory, {})
        self.mock_logger.error.assert_any_call(f"Error decoding JSON from {file_path_obj}: memory error: line 1 column 1 (char 0). Initializing empty memory.")

    def test_initialization_creates_missing_files_with_defaults(self):
        def truediv_side_effect_for_missing(other_path_part):
            full_path_str = f"{self.mock_core_dir_path_str}/{other_path_part}"
            mock_file_path_obj = MagicMock(spec=Path)
            mock_file_path_obj.__str__.return_value = full_path_str
            mock_file_path_obj.exists = MagicMock(return_value=False)
            mock_file_path_obj.parent.mkdir = MagicMock()
            mock_file_path_obj.mock_path_name = full_path_str
            return mock_file_path_obj
        self.mock_resolved_path_obj.__truediv__.side_effect = truediv_side_effect_for_missing

        commands_path_str = f"{self.mock_core_dir_path_str}/commands.json"
        status_path_str = f"{self.mock_core_dir_path_str}/status.json"
        memory_path_str = f"{self.mock_core_dir_path_str}/memory.json"

        post_creation_content = {
            commands_path_str: {},
            status_path_str: {"last_sync": None, "last_command": None, "status": "uninitialized"},
            memory_path_str: {}
        }
        self._configure_json_load_side_effect(post_creation_content)

        core = katana_core_module.KatanaCore(core_dir_path_str=self.mock_core_dir_path_str)

        self.mock_logger.warning.assert_any_call(f"File {self.mock_resolved_path_obj / 'commands.json'} not found. Creating with default content.")
        self.mock_logger.warning.assert_any_call(f"File {self.mock_resolved_path_obj / 'status.json'} not found. Creating with default content.")
        self.mock_logger.warning.assert_any_call(f"File {self.mock_resolved_path_obj / 'memory.json'} not found. Creating with default content.")

        self.assertEqual(self.mock_json_dump.call_count, 3)
        dump_args_list = [c[0][0] for c in self.mock_json_dump.call_args_list]
        self.assertIn({}, dump_args_list)
        self.assertIn({"last_sync": None, "last_command": None, "status": "uninitialized"}, dump_args_list)

        self.assertEqual(core.commands, {})
        self.assertEqual(core.status, {"last_sync": None, "last_command": None, "status": "uninitialized"})
        self.assertEqual(core.memory, {})

    # --- Start of newly added methods from this turn ---
    def test_save_status(self):
        core = katana_core_module.KatanaCore(core_dir_path_str=self.mock_core_dir_path_str)
        # Reset call count for json_dump from __init__ if initial files were "missing" due to default Path mock
        self.mock_json_dump.reset_mock()

        new_status_data = {"current_task": "saving_status", "progress": 50}
        # Simulate that status.json might have some initial data loaded by __init__
        # KatanaCore's _ensure_files_exist might create it if Path(...).exists() is false.
        # Then load_status is called. If it loads {}, then core.status is {}.
        # We'll assume it's {} before save_status for this test's focus.
        core.status = {} # Explicitly set to avoid dependency on complex load mock state for this save test

        core.save_status(new_status_data)

        self.mock_json_dump.assert_called_once()
        args, _ = self.mock_json_dump.call_args
        dumped_data = args[0]
        self.assertIn('last_saved_timestamp_utc', dumped_data)
        self.assertEqual(dumped_data['current_task'], "saving_status")
        self.assertEqual(dumped_data['progress'], 50)

        # Check which file was opened for writing by _save_json via json.dump
        # This relies on m_open being called by _save_json before json.dump
        # The file path object is the first argument to open()
        opened_file_path_arg = self.m_open.call_args[0][0]
        self.assertEqual(str(opened_file_path_arg), f"{self.mock_core_dir_path_str}/status.json")
        self.mock_logger.info.assert_any_call(f"Status saved to {self.mock_resolved_path_obj / 'status.json'}")


    def test_save_memory(self):
        core = katana_core_module.KatanaCore(core_dir_path_str=self.mock_core_dir_path_str)
        self.mock_json_dump.reset_mock()
        core.memory = {"old_key": "old_value"}
        core.memory["new_key"] = "new_value"
        core.save_memory()

        expected_memory_data = {"old_key": "old_value", "new_key": "new_value"}
        self.mock_json_dump.assert_called_once_with(expected_memory_data, ANY, indent=2, ensure_ascii=False)
        opened_file_path_arg = self.m_open.call_args[0][0]
        self.assertEqual(str(opened_file_path_arg), f"{self.mock_core_dir_path_str}/memory.json")
        self.mock_logger.info.assert_any_call(f"Memory saved to {self.mock_resolved_path_obj / 'memory.json'}")

    @patch(f'{kc_module_path}.input') # Patch input in the katana_core_module's scope
    def test_run_loop_exit_command(self, mock_input):
        mock_input.side_effect = ['exit']
        core = katana_core_module.KatanaCore(core_dir_path_str=self.mock_core_dir_path_str)
        self.mock_json_dump.reset_mock() # Reset from init calls
        core.run()
        self.mock_logger.info.assert_any_call("Exit command received. Shutting down KatanaCore.")
        # save_status and save_memory are called on exit
        self.assertEqual(self.mock_json_dump.call_count, 2)

    @patch(f'{kc_module_path}.input')
    def test_run_loop_remember_command(self, mock_input):
        mock_input.side_effect = ['remember mykey myvalue', 'exit']
        core = katana_core_module.KatanaCore(core_dir_path_str=self.mock_core_dir_path_str)
        self.mock_json_dump.reset_mock() # Reset from init calls
        core.memory = {}
        core.run()
        self.assertEqual(core.memory['mykey'], 'myvalue')
        self.mock_logger.info.assert_any_call("Memorized: mykey = myvalue")

        # Check the arguments of json.dump for memory.json after 'remember'
        # The first call to json.dump in run() after reset_mock() should be for save_memory() after 'remember'
        # The second call is for save_status() during exit.
        # The third call is for save_memory() during exit.
        # We are interested in the first call to save_memory.

        # Find the call to json.dump that wrote to memory.json and had our data
        found_memory_dump_after_remember = False
        for i, call_item in enumerate(self.mock_json_dump.call_args_list):
            dumped_data_arg = call_item[0][0]
            # Need to check which file was opened for this dump. This is tricky if m_open is reused.
            # Assuming m_open's call_args for the i-th dump corresponds to the i-th open call after reset.
            # This might not be robust.
            # A safer way would be to check the path directly if json.dump got path.
            # Since it gets a file pointer, we check the data.
            if dumped_data_arg == {'mykey': 'myvalue'}:
                 # Check if this dump was for memory.json.
                 # We need to ensure the open call before this dump was for memory.json.
                 # This test is becoming complex due to indirect checking.
                 # For now, let's assume the first dump of this data is what we want.
                 found_memory_dump_after_remember = True
                 break
        self.assertTrue(found_memory_dump_after_remember, "Memory data was not dumped correctly after 'remember' command.")


    @patch(f'{kc_module_path}.input')
    @patch(f'{kc_module_path}.print') # Patch print in the katana_core_module's scope
    def test_run_loop_recall_command(self, mock_print, mock_input):
        mock_input.side_effect = ['recall mykey', 'exit']
        core = katana_core_module.KatanaCore(core_dir_path_str=self.mock_core_dir_path_str)
        core.memory = {'mykey': 'myvalue'} # Pre-set memory
        core.run()
        mock_print.assert_any_call("Recalled mykey: myvalue")
        self.mock_logger.info.assert_any_call("Recalled: mykey")

    @patch(f'{kc_module_path}.input')
    @patch(f'{kc_module_path}.print')
    def test_run_loop_status_command(self, mock_print, mock_input):
        mock_input.side_effect = ['status', 'exit']
        core = katana_core_module.KatanaCore(core_dir_path_str=self.mock_core_dir_path_str)
        core.status = {"test_status_key": "test_status_value", "last_saved_timestamp_utc": "dummy_time"}
        core.run()
        mock_print.assert_any_call(json.dumps(core.status, indent=2))
        self.mock_logger.info.assert_any_call("Displayed current status.")

    @patch(f'{kc_module_path}.os.system') # Patch os.system in katana_core_module's scope
    @patch(f'{kc_module_path}.input')
    def test_run_loop_custom_command_execution_success(self, mock_input, mock_os_system):
        mock_input.side_effect = ['mycmd', 'exit']
        mock_os_system.return_value = 0

        core = katana_core_module.KatanaCore(core_dir_path_str=self.mock_core_dir_path_str)
        core.commands = {"mycmd": "echo custom command"}
        core.run()

        mock_os_system.assert_called_once_with("echo custom command")
        self.mock_logger.info.assert_any_call("Executing command 'mycmd': echo custom command")
        self.mock_logger.info.assert_any_call("Command 'mycmd' executed successfully.")

    @patch(f'{kc_module_path}.os.system')
    @patch(f'{kc_module_path}.input')
    def test_run_loop_custom_command_execution_failure(self, mock_input, mock_os_system):
        mock_input.side_effect = ['mycmd', 'exit']
        mock_os_system.return_value = 1

        core = katana_core_module.KatanaCore(core_dir_path_str=self.mock_core_dir_path_str)
        core.commands = {"mycmd": "bad_command"}
        core.run()

        mock_os_system.assert_called_once_with("bad_command")
        self.mock_logger.error.assert_any_call("Command 'mycmd' failed with exit code: 1.")

    @patch(f'{kc_module_path}.input')
    @patch(f'{kc_module_path}.print')
    def test_run_loop_unknown_command(self, mock_print, mock_input):
        mock_input.side_effect = ['unknown_cmd', 'exit']
        core = katana_core_module.KatanaCore(core_dir_path_str=self.mock_core_dir_path_str)
        core.commands = {"known_cmd": "echo known"}
        core.run()
        self.mock_logger.warning.assert_any_call("Unknown command: 'unknown_cmd'")
        mock_print.assert_any_call("❌ Unknown command. Available: ['known_cmd'] or 'remember/recall <key> <value>', 'status', 'exit'.")
    # --- End of newly added methods ---

if __name__ == '__main__':
    unittest.main()
