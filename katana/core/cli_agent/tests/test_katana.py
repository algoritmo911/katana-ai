import unittest
from unittest.mock import patch, MagicMock, mock_open, call, ANY
import os
import json
from pathlib import Path

# Assuming katana is in PYTHONPATH or discoverable
from katana.core.cli_agent.katana import KatanaCore
# from katana.utils.telemetry import trace_command # We'll patch its effect

# Path to the directory where this test file is located
TEST_DIR = Path(__file__).resolve().parent
# Dummy core_dir for KatanaCore instance during tests
DUMMY_CORE_DIR = TEST_DIR / "dummy_katana_core_data"

class TestKatanaCoreCLIIntegration(unittest.TestCase):

    def setUp(self):
        """Setup a KatanaCore instance with a dummy core_dir."""
        # Ensure dummy core_dir exists for file operations
        DUMMY_CORE_DIR.mkdir(parents=True, exist_ok=True)

        # Mock file content for commands.json, memory.json, sync_status.json
        self.mock_commands_data = {"testcmd": "echo 'hello'"}
        self.mock_memory_data = {"initial_key": "initial_value"}
        self.mock_status_data = {"status": "idle"}

        # Patch 'open' to control file reading/writing during tests
        # and also patch os.system for system commands
        self.patcher_open = patch('builtins.open', new_callable=mock_open)
        self.patcher_os_system = patch('os.system')
        self.patcher_path_exists = patch('pathlib.Path.exists')
        self.patcher_path_mkdir = patch('pathlib.Path.mkdir')

        # Patch the entire supabase_client_instance used by @trace_command
        self.patcher_supabase_client_instance = patch('katana.utils.telemetry.supabase_client_instance')

        self.mock_open = self.patcher_open.start()
        self.mock_os_system = self.patcher_os_system.start()
        self.mock_path_exists = self.patcher_path_exists.start()
        self.mock_path_mkdir = self.patcher_path_mkdir.start()

        self.mock_supabase_client_instance = self.patcher_supabase_client_instance.start()
        # Configure the mock supabase client instance
        self.mock_supabase_client_instance.client = "mock_client_ready" # Ensure it's seen as configured
        self.mock_supabase_client_instance.save_trace = MagicMock(return_value=True)
        # For convenience in assertions, alias the mocked save_trace
        self.mock_save_trace = self.mock_supabase_client_instance.save_trace


        # Default behavior for Path.exists
        self.mock_path_exists.return_value = True

        # Configure mock_open to return different content based on file path
        def mock_open_side_effect(path_obj, mode='r', *args, **kwargs):
            path_str = str(path_obj)
            if DUMMY_CORE_DIR / 'commands.json' == path_obj:
                if mode == 'r':
                    return mock_open(read_data=json.dumps(self.mock_commands_data)).return_value
            elif DUMMY_CORE_DIR / 'memory.json' == path_obj:
                if mode == 'r':
                    return mock_open(read_data=json.dumps(self.mock_memory_data)).return_value
            elif DUMMY_CORE_DIR / 'sync_status.json' == path_obj:
                if mode == 'r':
                    return mock_open(read_data=json.dumps(self.mock_status_data)).return_value
            # Fallback for write modes or other paths
            return mock_open().return_value

        self.mock_open.side_effect = mock_open_side_effect

        # Supabase client mock setup
        self.mock_save_trace.return_value = True

        self.katana_core = KatanaCore(core_dir_path_str=str(DUMMY_CORE_DIR))

    def tearDown(self):
        self.patcher_open.stop()
        self.patcher_os_system.stop()
        self.patcher_supabase_client_instance.stop() # Stop this new patcher
        self.patcher_path_exists.stop()
        self.patcher_path_mkdir.stop()

        # Clean up dummy directory and files if necessary, though mocks should prevent creation
        # For this test, mocks prevent actual file IO, so cleanup is minimal.
        # shutil.rmtree(DUMMY_CORE_DIR, ignore_errors=True)


    def test_save_json_trace(self):
        """Test that _save_json calls trace_command correctly."""
        test_file = DUMMY_CORE_DIR / "test_save.json"
        test_data = {"key": "value"}

        # _save_json is decorated, so calling it will trigger save_trace
        self.katana_core._save_json(test_file, test_data, user_id="custom_user", context_id="custom_ctx")

        # _save_json is directly traced
        self.mock_save_trace.assert_called_once()
        trace_data = self.mock_save_trace.call_args[0][0]

        self.assertEqual(trace_data["name"], "_save_json")
        self.assertEqual(trace_data["user_id"], "custom_user")
        self.assertEqual(trace_data["context_id"], "custom_ctx")
        # `self` (KatanaCore instance) is the first arg for instance methods
        self.assertEqual(trace_data["args"], [ANY, str(test_file), test_data])
        self.assertEqual(trace_data["kwargs"], {'user_id': 'custom_user', 'context_id': 'custom_ctx'})


    def test_execute_system_command_trace(self):
        """Test _execute_system_command tracing."""
        self.mock_os_system.return_value = 0

        cmd_key = "testcmd"
        cmd_to_exec = self.mock_commands_data[cmd_key]

        self.katana_core._execute_system_command(cmd_key, cmd_to_exec, user_id="cli_user", context_id="cli_session")

        self.mock_os_system.assert_called_once_with(cmd_to_exec)

        # _execute_system_command calls save_status, which calls _save_json (traced).
        # So, at least two traces: one for _execute_system_command, one for _save_json.
        # We need to find the specific trace for _execute_system_command.
        found_trace = False
        for call_arg in self.mock_save_trace.call_args_list:
            trace_data = call_arg[0][0]
            if trace_data["name"] == "_execute_system_command":
                self.assertEqual(trace_data["user_id"], "cli_user")
                self.assertEqual(trace_data["context_id"], "cli_session")
                self.assertEqual(trace_data["args"], [ANY, cmd_key, cmd_to_exec])
                 # kwargs for _execute_system_command includes user_id, context_id passed to it
                self.assertEqual(trace_data["kwargs"], {'user_id': "cli_user", 'context_id': "cli_session"})
                self.assertEqual(trace_data["return_value"], 0) # Exit code
                found_trace = True
                break
        self.assertTrue(found_trace, "Trace for _execute_system_command not found.")


    def test_handle_remember_command_trace(self):
        """Test _handle_remember_command tracing."""
        mem_key, mem_value = "new_key", "new_value"

        # This will call _save_json internally, which is also traced.
        # So, save_trace will be called twice: once for _handle_remember_command, once for _save_json.
        self.katana_core._handle_remember_command(mem_key, mem_value, user_id="cli_user", context_id="cli_session")

        self.assertEqual(self.katana_core.memory[mem_key], mem_value)

        # Check the trace for _handle_remember_command specifically
        # It should be the first call if _save_json is called by it.
        # Or, more robustly, check all calls.
        found_remember_trace = False
        for call_args in self.mock_save_trace.call_args_list:
            trace_data = call_args[0][0]
            if trace_data["name"] == "_handle_remember_command":
                found_remember_trace = True
                self.assertEqual(trace_data["user_id"], "cli_user")
                self.assertEqual(trace_data["context_id"], "cli_session")
                self.assertEqual(trace_data["args"], [ANY, mem_key, mem_value])
                self.assertEqual(trace_data["kwargs"], {'user_id': 'cli_user', 'context_id': 'cli_session'})
                self.assertEqual(trace_data["return_value"], f"Memorized: {mem_key} = {mem_value}")
                break
        self.assertTrue(found_remember_trace, "Trace for _handle_remember_command not found.")
        # It calls save_memory -> _save_json, so at least 2 calls to save_trace
        self.assertTrue(self.mock_save_trace.call_count >= 2, f"Expected at least 2 trace calls, got {self.mock_save_trace.call_count}")


    def test_handle_recall_command_trace(self):
        """Test _handle_recall_command tracing."""
        mem_key = "initial_key"
        expected_value = self.mock_memory_data[mem_key]

        with patch('builtins.print') as mock_print: # Mock print for CLI output
             self.katana_core._handle_recall_command(mem_key, user_id="cli_user", context_id="cli_session")

        mock_print.assert_called_once_with(f"Recalled {mem_key}: {expected_value}")

        self.mock_save_trace.assert_called_once() # _handle_recall_command is traced directly
        trace_data = self.mock_save_trace.call_args[0][0]

        self.assertEqual(trace_data["name"], "_handle_recall_command")
        self.assertEqual(trace_data["user_id"], "cli_user")
        self.assertEqual(trace_data["context_id"], "cli_session")
        self.assertEqual(trace_data["args"], [ANY, mem_key])
        self.assertEqual(trace_data["kwargs"], {'user_id': 'cli_user', 'context_id': 'cli_session'})
        self.assertEqual(trace_data["return_value"], expected_value)


    def test_handle_status_command_trace(self):
        """Test _handle_status_command tracing."""
        with patch('builtins.print') as mock_print: # Mock print for CLI output
            self.katana_core._handle_status_command(user_id="cli_user", context_id="cli_session")

        mock_print.assert_called_once_with(f"Current Status: {json.dumps(self.mock_status_data, indent=2)}")

        self.mock_save_trace.assert_called_once() # _handle_status_command is traced directly
        trace_data = self.mock_save_trace.call_args[0][0]

        self.assertEqual(trace_data["name"], "_handle_status_command")
        self.assertEqual(trace_data["user_id"], "cli_user")
        self.assertEqual(trace_data["context_id"], "cli_session")
        self.assertEqual(trace_data["args"], [ANY]) # self is the only positional arg
        self.assertEqual(trace_data["kwargs"], {'user_id': 'cli_user', 'context_id': 'cli_session'})
        self.assertEqual(trace_data["return_value"], self.mock_status_data)

    # Test the main run loop's command dispatching to ensure correct user/context IDs are used
    # This is more of an integration test for the run loop's use of helper methods.
    @patch('builtins.input', side_effect=["testcmd", "exit"])
    def test_run_loop_system_command_dispatch_trace(self, mock_input):
        """Test run loop dispatching a system command, checking trace context."""
        self.mock_os_system.return_value = 0

        self.katana_core.run() # Will loop twice due to side_effect

        # _execute_system_command is traced. _save_json (for status) is also traced.
        # We are interested in the trace of _execute_system_command.
        found_exec_trace = False
        for call_args in self.mock_save_trace.call_args_list:
            trace_data = call_args[0][0]
            if trace_data["name"] == "_execute_system_command":
                found_exec_trace = True
                self.assertEqual(trace_data["user_id"], "cli_user")
                self.assertEqual(trace_data["context_id"], "cli_session")
                self.assertEqual(trace_data["args"], [ANY]) # self is the only positional arg
                expected_kwargs = {
                    'command_key': "testcmd",
                    'command_to_execute': "echo 'hello'",
                    'user_id': 'cli_user',
                    'context_id': 'cli_session'
                }
                self.assertEqual(trace_data["kwargs"], expected_kwargs)
                break
        self.assertTrue(found_exec_trace, "Trace for _execute_system_command via run loop not found.")

    @patch('builtins.input', side_effect=["remember new_cli_key new_cli_val", "exit"])
    def test_run_loop_remember_command_dispatch_trace(self, mock_input):
        """Test run loop dispatching 'remember' command, checking trace context."""
        self.katana_core.run()

        found_remember_trace = False
        for call_args in self.mock_save_trace.call_args_list:
            trace_data = call_args[0][0]
            if trace_data["name"] == "_handle_remember_command":
                found_remember_trace = True
                self.assertEqual(trace_data["user_id"], "cli_user")
                self.assertEqual(trace_data["context_id"], "cli_session")
                self.assertEqual(trace_data["args"], [ANY, "new_cli_key", "new_cli_val"])
                self.assertEqual(trace_data["kwargs"], {'user_id': 'cli_user', 'context_id': 'cli_session'})
                break
        self.assertTrue(found_remember_trace, "Trace for _handle_remember_command via run loop not found.")


if __name__ == '__main__':
    unittest.main()
