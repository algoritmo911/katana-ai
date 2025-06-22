import unittest
from unittest.mock import patch, mock_open, MagicMock, call
import json
import logging
from pathlib import Path
from freezegun import freeze_time # For consistent timestamps

# Assuming katana_core.katana can be imported.
# If run from project root, PYTHONPATH should handle this.
from katana_core.katana import KatanaCore
import katana_core.katana # Import the module itself to access its patched members

# Define a base directory for tests to create mock files
TEST_CORE_DIR_PATH = Path("/tmp/test_katana_core_data")

class TestKatanaCore(unittest.TestCase):

    def setUp(self):
        # Ensure a clean state for each test by removing and recreating the test directory
        # This is for actual file creation if not fully mocking Path.
        # For full mocking, this might not be strictly necessary but good for clarity.
        # For these tests, we'll primarily mock Path methods.

        self.mock_logger = MagicMock(spec=logging.Logger)

        # Patch setup_logger to return our mock_logger
        self.setup_logger_patcher = patch('katana_core.katana.setup_logger', return_value=self.mock_logger)
        self.setup_logger_patcher.start()

        # Mock pathlib.Path methods that interact with the filesystem
        self.path_patcher = patch('katana_core.katana.Path')
        self.mock_path_class = self.path_patcher.start()

        # Configure the mock Path class and its instances
        self.mock_core_dir_instance = MagicMock(spec=Path)
        self.mock_core_dir_instance.resolve.return_value = self.mock_core_dir_instance # Return self for resolved path

        self.mock_commands_path = MagicMock(spec=Path)
        self.mock_status_path = MagicMock(spec=Path)
        self.mock_memory_path = MagicMock(spec=Path)
        self.mock_log_dir_path = MagicMock(spec=Path) # For logger setup path

        # When Path(core_dir_path_str) is called, return our mock instance
        self.mock_path_class.return_value = self.mock_core_dir_instance

        # Define how division (/) works on the mock_core_dir_instance to return specific file paths
        def path_truediv_side_effect(other):
            if other == 'commands.json':
                return self.mock_commands_path
            elif other == 'sync_status.json':
                return self.mock_status_path
            elif other == 'memory.json':
                return self.mock_memory_path
            elif other == 'logs': # For log directory creation
                return self.mock_log_dir_path
            return MagicMock(spec=Path) # Default for any other path

        self.mock_core_dir_instance.__truediv__ = MagicMock(side_effect=path_truediv_side_effect)
        self.mock_log_dir_instance = self.mock_log_dir_path # alias for clarity
        self.mock_log_file_path_instance = MagicMock(spec=Path)
        self.mock_log_dir_instance.__truediv__ = MagicMock(return_value=self.mock_log_file_path_instance)


        # Default behavior for file existence (can be overridden per test)
        self.mock_commands_path.exists.return_value = False
        self.mock_status_path.exists.return_value = False
        self.mock_memory_path.exists.return_value = False

        # Mock parent directory for mkdir calls
        self.mock_commands_path.parent.mkdir = MagicMock()
        self.mock_status_path.parent.mkdir = MagicMock()
        self.mock_memory_path.parent.mkdir = MagicMock()
        self.mock_log_dir_instance.mkdir = MagicMock()


    def tearDown(self):
        self.setup_logger_patcher.stop()
        self.path_patcher.stop()

    def test_initialization_files_do_not_exist(self):
        """Test KatanaCore initialization when core files do not exist."""

        # Mock open for _save_json calls during _ensure_files_exist
        m_open = mock_open()
        with patch('builtins.open', m_open):
            with patch('json.dump') as mock_json_dump:
                kc = KatanaCore(core_dir_path_str=str(TEST_CORE_DIR_PATH))

        # Verify Path was called with the test directory string
        self.mock_path_class.assert_called_once_with(str(TEST_CORE_DIR_PATH))
        self.mock_core_dir_instance.resolve.assert_called_once()

        # Verify logger was set up
        # Access the patched object directly for assertion
        katana_core.katana.setup_logger.assert_called_once_with(
            "KatanaCore", str(self.mock_log_file_path_instance), level=logging.DEBUG
        )
        self.assertEqual(kc.logger, self.mock_logger)

        # Verify _ensure_files_exist created files (mocked)
        self.mock_logger.warning.assert_any_call(
            f"File {self.mock_commands_path} not found. Creating with default content.",
            extra={"file_path": str(self.mock_commands_path)}
        )
        self.mock_logger.warning.assert_any_call(
            f"File {self.mock_status_path} not found. Creating with default content.",
            extra={"file_path": str(self.mock_status_path)}
        )
        self.mock_logger.warning.assert_any_call(
            f"File {self.mock_memory_path} not found. Creating with default content.",
            extra={"file_path": str(self.mock_memory_path)}
        )

        # Check that json.dump was called for each default file
        self.assertEqual(mock_json_dump.call_count, 3)
        mock_json_dump.assert_any_call({}, m_open(), indent=2, ensure_ascii=False) # commands.json
        mock_json_dump.assert_any_call({"last_sync": None, "last_command": None, "status": "uninitialized"}, m_open(), indent=2, ensure_ascii=False) # status.json
        mock_json_dump.assert_any_call({}, m_open(), indent=2, ensure_ascii=False) # memory.json

        # Verify load methods were called and logged errors (since files were "created" empty by mock_open)
        # and then attempted to load, resulting in JSONDecodeError if mock_open reads empty.
        # Let's refine mock_open for loads to simulate empty files leading to errors.

        # For this test, we'll assume _save_json works.
        # The subsequent load methods will read the files that were just "created".
        # We need to ensure that json.load in the load_* methods sees the correct default content.

        default_status_content = {"last_sync": None, "last_command": None, "status": "uninitialized"}

        def mock_json_load_side_effect(fp):
            if fp == m_open.return_value: # Check if it's the file pointer from mock_open
                # This side effect needs to know WHICH file is being loaded.
                # This is tricky because json.load gets a file pointer, not a path.
                # Instead, let's make the mock_open return specific read_data for load calls.
                # This test case is becoming complex due to mocking open for both write then read.
                pass # Placeholder for now
            # Fallback for any other json.load calls if necessary
            if self.current_loading_file == self.mock_commands_path:
                return {}
            elif self.current_loading_file == self.mock_status_path:
                return default_status_content
            elif self.current_loading_file == self.mock_memory_path:
                return {}
            raise AssertionError(f"json.load called with unexpected file pointer: {fp}")

        # More robust: Mock json.load to return defaults when load_* methods are called.
        # The _ensure_files_exist will call _save_json, which uses json.dump (mocked).
        # Then load_* methods will call json.load.

        # Mock json.dump for the _save_json calls within _ensure_files_exist
        with patch('json.dump') as mock_json_dump_ensure:
            # Mock json.load for the load_* calls.
            # The order of loading in KatanaCore.__init__ is: commands, memory, status.
            # Make returned data distinct to ensure mocks are working as expected.
            mock_commands_data_loaded = {"cmd_loaded": "yes"}
            mock_memory_data_loaded = {"mem_loaded": "yes"}
            mock_status_data_loaded = {**default_status_content, "status_loaded": "yes"}

            mock_load_side_effects = [
                mock_commands_data_loaded,
                mock_memory_data_loaded,
                mock_status_data_loaded
            ]
            with patch('json.load', side_effect=mock_load_side_effects) as mock_json_load_init:
                m_open_for_io = mock_open() # Mock for both save (json.dump) and load (json.load)
                with patch('builtins.open', m_open_for_io):
                    kc = KatanaCore(core_dir_path_str=str(TEST_CORE_DIR_PATH))

        # Verify json.dump calls from _ensure_files_exist
        mock_json_dump_ensure.assert_any_call({}, m_open_for_io.return_value, indent=2, ensure_ascii=False) # For commands and memory
        mock_json_dump_ensure.assert_any_call(default_status_content, m_open_for_io.return_value, indent=2, ensure_ascii=False) # For status
        self.assertEqual(mock_json_dump_ensure.call_count, 3)

        # Verify json.load was called 3 times
        self.assertEqual(mock_json_load_init.call_count, 3)

        # Capture string representations of mock paths once
        str_mock_commands_path = str(self.mock_commands_path)
        str_mock_memory_path = str(self.mock_memory_path)
        str_mock_status_path = str(self.mock_status_path)

        # Verify logs for successful loads
        # Commands log
        commands_log_found = False
        for call_args in self.mock_logger.info.call_args_list:
            if call_args[0][0] == f"Commands loaded successfully from {str_mock_commands_path}.": # Added period back
                self.assertEqual(call_args[1]['extra']['file_path'], unittest.mock.ANY)
                commands_log_found = True
                break
        self.assertTrue(commands_log_found, f"Commands loaded log not found. Expected msg: 'Commands loaded successfully from {str_mock_commands_path}.'. Actual calls: {self.mock_logger.info.call_args_list}")

        # Memory log
        memory_log_found = False
        for call_args in self.mock_logger.info.call_args_list:
            if call_args[0][0] == f"Memory loaded from {str_mock_memory_path}": # No period
                self.assertEqual(call_args[1]['extra']['file_path'], unittest.mock.ANY)
                memory_log_found = True
                break
        self.assertTrue(memory_log_found, f"Memory loaded log not found. Expected msg: 'Memory loaded from {str_mock_memory_path}'. Actual calls: {self.mock_logger.info.call_args_list}")

        # Status log
        status_log_found = False
        for call_args in self.mock_logger.info.call_args_list:
            if call_args[0][0] == f"Status loaded from {str_mock_status_path}": # No period
                self.assertEqual(call_args[1]['extra']['file_path'], unittest.mock.ANY)
                status_log_found = True
                break
        self.assertTrue(status_log_found, f"Status loaded log not found. Expected msg: 'Status loaded from {str_mock_status_path}'. Actual calls: {self.mock_logger.info.call_args_list}")

        # Verify correct data is loaded
        self.assertEqual(kc.commands, mock_commands_data_loaded)
        self.assertEqual(kc.status, mock_status_data_loaded)
        self.assertEqual(kc.memory, mock_memory_data_loaded)

        self.mock_logger.info.assert_any_call(f"KatanaCore initialized. Operational directory: {self.mock_core_dir_instance}", extra={"core_dir": str(self.mock_core_dir_instance)})


    def test_initialization_files_exist_valid_json(self):
        """Test KatanaCore initialization when core files exist and are valid JSON."""
        self.mock_commands_path.exists.return_value = True
        self.mock_status_path.exists.return_value = True
        self.mock_memory_path.exists.return_value = True

        mock_commands_data = {"cmd1": "do_something"}
        mock_status_data = {"status": "idle", "last_command": "cmd1"}
        mock_memory_data = {"key1": "value1"}

        def mock_open_side_effect(file_path_obj, mode, encoding):
            if file_path_obj == self.mock_commands_path:
                return mock_open(read_data=json.dumps(mock_commands_data))()
            elif file_path_obj == self.mock_status_path:
                return mock_open(read_data=json.dumps(mock_status_data))()
            elif file_path_obj == self.mock_memory_path:
                return mock_open(read_data=json.dumps(mock_memory_data))()
            return mock_open()() # Default mock_open

        m_open_patched = mock_open()
        m_open_patched.side_effect = mock_open_side_effect

        with patch('builtins.open', m_open_patched):
            kc = KatanaCore(core_dir_path_str=str(TEST_CORE_DIR_PATH))

        self.mock_logger.warning.assert_not_called() # No files should be "created"

        self.assertEqual(kc.commands, mock_commands_data)
        self.assertEqual(kc.status, mock_status_data)
        self.assertEqual(kc.memory, mock_memory_data)

        self.mock_logger.info.assert_any_call(f"Commands loaded successfully from {self.mock_commands_path}.", extra={"file_path": str(self.mock_commands_path)})
        self.mock_logger.info.assert_any_call(f"Status loaded from {self.mock_status_path}", extra={"file_path": str(self.mock_status_path)})
        self.mock_logger.info.assert_any_call(f"Memory loaded from {self.mock_memory_path}", extra={"file_path": str(self.mock_memory_path)})
        self.mock_logger.info.assert_any_call(f"KatanaCore initialized. Operational directory: {self.mock_core_dir_instance}", extra={"core_dir": str(self.mock_core_dir_instance)})


    def test_load_commands_json_decode_error(self):
        """Test load_commands with invalid JSON content."""
        self.mock_commands_path.exists.return_value = True
        m_open = mock_open(read_data="this is not json")
        with patch('builtins.open', m_open):
            kc = KatanaCore(core_dir_path_str=str(TEST_CORE_DIR_PATH))

        self.assertEqual(kc.commands, {})
        self.mock_logger.error.assert_any_call(
            f"Error decoding JSON from {self.mock_commands_path}: Expecting value: line 1 column 1 (char 0). Using empty command set.",
            exc_info=True,
            extra={"file_path": str(self.mock_commands_path), "error": "Expecting value: line 1 column 1 (char 0)"}
        )

    def test_save_status(self):
        """Test saving status."""
        kc = KatanaCore(core_dir_path_str=str(TEST_CORE_DIR_PATH)) # Init will do some loads/saves
        self.mock_logger.reset_mock() # Reset after init logs

        m_open = mock_open()
        with patch('builtins.open', m_open):
            with patch('json.dump') as mock_json_dump:
                with freeze_time("2023-01-01 12:00:00 UTC"):
                    kc.save_status({"new_status_key": "new_value", "status": "testing_save"})

        expected_status_to_save = {
            "last_sync": None, "last_command": None, # from default init
            "status": "testing_save",
            "new_status_key": "new_value",
            "last_saved_timestamp_utc": "2023-01-01T12:00:00" # from freeze_time
        }

        # Check that json.dump was called correctly for status_file_path
        # Need to find the correct call among potentially multiple open calls if init also saved.
        # For simplicity, assume m_open was configured for the status file path for this save.
        m_open.assert_called_with(self.mock_status_path, 'w', encoding='utf-8')
        mock_json_dump.assert_called_with(expected_status_to_save, m_open(), indent=2, ensure_ascii=False)

        self.mock_logger.info.assert_called_with(
            f"Status saved to {self.mock_status_path}",
            extra={"file_path": str(self.mock_status_path)}
        )
        self.assertEqual(kc.status, expected_status_to_save)

    def test_save_memory(self):
        """Test saving memory."""
        kc = KatanaCore(core_dir_path_str=str(TEST_CORE_DIR_PATH))
        self.mock_logger.reset_mock()

        kc.memory = {"test_mem_key": "test_mem_value"}

        m_open = mock_open()
        with patch('builtins.open', m_open):
            with patch('json.dump') as mock_json_dump:
                kc.save_memory()

        m_open.assert_called_with(self.mock_memory_path, 'w', encoding='utf-8')
        mock_json_dump.assert_called_with({"test_mem_key": "test_mem_value"}, m_open(), indent=2, ensure_ascii=False)
        self.mock_logger.info.assert_called_with(
            f"Memory saved to {self.mock_memory_path}",
            extra={"file_path": str(self.mock_memory_path)}
        )

    def test_save_json_failure(self):
        """Test _save_json when an exception occurs."""
        kc = KatanaCore(core_dir_path_str=str(TEST_CORE_DIR_PATH))
        self.mock_logger.reset_mock()

        m_open = mock_open()
        with patch('builtins.open', m_open):
            with patch('json.dump', side_effect=IOError("Disk full")) as mock_json_dump:
                result = kc._save_json(self.mock_memory_path, {"data": "content"})

        self.assertFalse(result)
        self.mock_logger.error.assert_called_once_with(
            f"Error saving data to {self.mock_memory_path}: Disk full",
            exc_info=True,
            extra={"file_path": str(self.mock_memory_path), "error": "Disk full"}
        )

    @patch('builtins.input')
    @patch('os.system')
    def test_run_exit_command(self, mock_os_system, mock_input):
        """Test the run loop with the 'exit' command."""
        mock_input.side_effect = ["exit"]
        kc = KatanaCore(core_dir_path_str=str(TEST_CORE_DIR_PATH))
        self.mock_logger.reset_mock() # Reset after init logs

        kc.run()

        mock_os_system.assert_not_called()
        self.mock_logger.info.assert_any_call("⚔️ KatanaCore activated. Type 'exit' or 'quit' to stop. Waiting for command...", extra={"event": "activation"})
        self.mock_logger.debug.assert_any_call("Received CLI input: 'exit'", extra={"cli_input": "exit"})
        self.mock_logger.info.assert_any_call("Exit command received. Shutting down KatanaCore.", extra={"command": "exit"})
        # save_status and save_memory are called, they have their own logs which are tested elsewhere or implicitly via init.

    @patch('builtins.input')
    @patch('os.system')
    def test_run_known_command_success(self, mock_os_system, mock_input):
        """Test executing a known command successfully."""
        mock_input.side_effect = ["testcmd", "exit"]
        mock_os_system.return_value = 0 # Success

        kc = KatanaCore(core_dir_path_str=str(TEST_CORE_DIR_PATH))
        kc.commands = {"testcmd": "echo 'hello'"}
        self.mock_logger.reset_mock()

        kc.run()

        mock_os_system.assert_called_once_with("echo 'hello'")
        self.mock_logger.info.assert_any_call(
            "Executing command 'testcmd': echo 'hello'",
            extra={"command_key": "testcmd", "command_action": "echo 'hello'"}
        )
        self.mock_logger.info.assert_any_call(
            "Command 'testcmd' executed successfully.",
            extra={"command_key": "testcmd", "exit_code": 0}
        )

    @patch('builtins.input')
    @patch('os.system')
    def test_run_known_command_failure(self, mock_os_system, mock_input):
        """Test executing a known command that fails."""
        mock_input.side_effect = ["failcmd", "exit"]
        mock_os_system.return_value = 1 # Failure

        kc = KatanaCore(core_dir_path_str=str(TEST_CORE_DIR_PATH))
        kc.commands = {"failcmd": "exit 1"}
        self.mock_logger.reset_mock()

        kc.run()

        mock_os_system.assert_called_once_with("exit 1")
        self.mock_logger.error.assert_any_call(
            "Command 'failcmd' failed with exit code: 1.",
            extra={"command_key": "failcmd", "exit_code": 1}
        )

    @patch('builtins.input')
    @patch('builtins.print') # To capture output of recall
    def test_run_remember_and_recall(self, mock_print, mock_input):
        """Test 'remember' and 'recall' commands."""
        mock_input.side_effect = [
            "remember mykey myvalue",
            "recall mykey",
            "recall unknownkey",
            "exit"
        ]
        kc = KatanaCore(core_dir_path_str=str(TEST_CORE_DIR_PATH))
        # Mock _save_json for memory saves to prevent file access during this specific test unit
        # if we only want to test the logic and logger calls for remember/recall.
        # However, save_memory has its own logs, so let's allow it but check logs.
        self.mock_logger.reset_mock()


        with patch.object(kc, '_save_json', return_value=True) as mock_save_mem_json: # Ensure save_memory thinks it saved
            kc.run()

        # Remember logs
        self.mock_logger.info.assert_any_call(
            "Memorized: 'mykey' = 'myvalue'",
            extra={"memory_key": "mykey", "memory_value": "myvalue"}
        )
        # save_memory logs (called by remember)
        self.mock_logger.info.assert_any_call(
            f"Memory saved to {kc.memory_file_path}", # memory_file_path is now an attribute of kc
            extra={"file_path": str(kc.memory_file_path)}
        )
        mock_save_mem_json.assert_any_call(kc.memory_file_path, {"mykey": "myvalue"})


        # Recall logs and print
        mock_print.assert_any_call("Recalled 'mykey': myvalue")
        self.mock_logger.info.assert_any_call("Recalled: 'mykey'", extra={"memory_key": "mykey", "found": True})

        mock_print.assert_any_call("Key 'unknownkey' not found in memory.")
        self.mock_logger.info.assert_any_call("Recall attempt for key 'unknownkey': Not found.", extra={"memory_key": "unknownkey", "found": False})


    @patch('builtins.input')
    @patch('builtins.print')
    def test_run_status_command(self, mock_print, mock_input):
        """Test the 'status' command."""
        mock_input.side_effect = ["status", "exit"]
        kc = KatanaCore(core_dir_path_str=str(TEST_CORE_DIR_PATH))
        # Status data will be the default from init
        expected_status_output = json.dumps(kc.status, indent=2)
        self.mock_logger.reset_mock()

        kc.run()

        mock_print.assert_any_call(f"Current Status:\n{expected_status_output}")
        self.mock_logger.info.assert_any_call("Displayed current status.", extra={"current_status": kc.status})

    @patch('builtins.input')
    @patch('builtins.print')
    def test_run_unknown_command(self, mock_print, mock_input):
        """Test handling of an unknown command."""
        mock_input.side_effect = ["idontexist", "exit"]
        kc = KatanaCore(core_dir_path_str=str(TEST_CORE_DIR_PATH))
        kc.commands = {"known": "cmd"} # To show in available commands
        self.mock_logger.reset_mock()

        kc.run()

        self.mock_logger.warning.assert_any_call(
            "Unknown command: 'idontexist'",
            extra={"unknown_command": "idontexist"}
        )
        mock_print.assert_any_call("❌ Unknown command. Available: ['known'] or 'remember/recall <key> <value>', 'status', 'exit'.")

    @patch('builtins.input', side_effect=KeyboardInterrupt)
    def test_run_keyboard_interrupt(self, mock_input):
        """Test KeyboardInterrupt handling in the run loop."""
        kc = KatanaCore(core_dir_path_str=str(TEST_CORE_DIR_PATH))
        # Mock save methods to check they are called without file system side effects for this unit
        with patch.object(kc, 'save_status') as mock_save_status, \
             patch.object(kc, 'save_memory') as mock_save_memory, \
             patch('builtins.print') as mock_print: # Also mock print to check user message

            # The run loop itself catches KeyboardInterrupt and breaks.
            # It does not re-raise or SystemExit.
            kc.run()

            # Check if the loop terminated (mock_input should have been called once due to side_effect=KeyboardInterrupt)
            mock_input.assert_called_once()

            self.mock_logger.info.assert_any_call(
                "KeyboardInterrupt received. Shutting down KatanaCore gracefully...",
                extra={"event": "KeyboardInterrupt"}
            )
            mock_save_status.assert_called_once_with(
                {"last_command": "KeyboardInterrupt", "status": "terminated_by_interrupt"}
            )
            mock_save_memory.assert_called_once()
            # The print("\nKatanaCore terminated by user.") is also in the exception block.
            # We can patch print if we want to assert that specific output.


if __name__ == '__main__':
    unittest.main()
