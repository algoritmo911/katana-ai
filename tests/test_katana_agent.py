# tests/test_katana_agent.py
import unittest
from unittest.mock import patch
import katana_agent

class TestKatanaAgent(unittest.TestCase):

    @patch('katana_agent.logger') # Mock logger to avoid console output and check calls
    def test_execute_uptime_command(self, mock_logger):
        result = katana_agent.execute_command("uptime")
        self.assertEqual(result, "Katana system uptime: 10 days, 5 hours, 30 minutes (simulated)")
        mock_logger.info.assert_any_call("Attempting to execute command in Katana: 'uptime' with params: {}")
        mock_logger.info.assert_any_call("Executed 'uptime' command successfully (simulated).")

    @patch('katana_agent.logger')
    def test_execute_greet_user_command_with_name(self, mock_logger):
        params = {"name": "TestUser"}
        result = katana_agent.execute_command("greet_user", params=params)
        self.assertEqual(result, "Hello, TestUser! Welcome to the Katana interface (simulated).")
        mock_logger.info.assert_any_call(f"Attempting to execute command in Katana: 'greet_user' with params: {params}")
        mock_logger.info.assert_any_call("Executed 'greet_user' command for 'TestUser' (simulated).")

    @patch('katana_agent.logger')
    def test_execute_greet_user_command_no_name(self, mock_logger):
        result = katana_agent.execute_command("greet_user", params={}) # Explicitly empty params
        self.assertEqual(result, "Hello, User! Welcome to the Katana interface (simulated).")
        mock_logger.info.assert_any_call("Attempting to execute command in Katana: 'greet_user' with params: {}")
        mock_logger.info.assert_any_call("Executed 'greet_user' command for 'User' (simulated).")

    @patch('katana_agent.logger')
    def test_execute_greet_user_command_params_is_none(self, mock_logger):
        # Test default behavior when params is None
        result = katana_agent.execute_command("greet_user") # params defaults to None, then {}
        self.assertEqual(result, "Hello, User! Welcome to the Katana interface (simulated).")
        mock_logger.info.assert_any_call("Attempting to execute command in Katana: 'greet_user' with params: {}")

    @patch('katana_agent.logger')
    def test_execute_run_specific_tool_command(self, mock_logger):
        command_str = "run_specific_tool backup_database --full"
        params = {"source": "/run command"}
        result = katana_agent.execute_command(command_str, params=params)
        # The current mock implementation of run_specific_tool only extracts "backup_database"
        # It doesn't use the full string "backup_database --full" as tool_name yet.
        # This depends on how sophisticated we want the mock to be.
        # For now, it extracts 'backup_database'.
        # If it were to use the full command_str, the test would need to change.
        # Let's assume it's meant to take the first part as tool name for now.
        # To make it more precise, katana_agent.py would need to be smarter.
        # The current `command.split(" ", 1)[1]` if `len > 1` would get `backup_database --full`
        # Let's adjust the test to expect this behavior.

        # If katana_agent.py was: tool_name = command.split(" ", 1)[1]
        # Then expected_tool_name = "backup_database --full"
        # katana_agent.py is: tool_name = command.split(" ", 1)[1] if len(command.split(" ", 1)) > 1 else "unknown_tool"
        # This will extract "backup_database --full" as the tool_name
        expected_tool_name = "backup_database --full"
        self.assertEqual(result, f"Simulated execution of Katana tool: '{expected_tool_name}'. Output: Success.")
        mock_logger.info.assert_any_call(f"Attempting to execute command in Katana: '{command_str}' with params: {params}")
        mock_logger.info.assert_any_call(f"Executed 'run_specific_tool' for tool '{expected_tool_name}' (simulated).")

    @patch('katana_agent.logger')
    def test_execute_unknown_command(self, mock_logger):
        command_str = "some_random_command --option"
        params = {"user_id": 123}
        result = katana_agent.execute_command(command_str, params=params)
        self.assertEqual(result, f"Error: Katana does not recognize the command '{command_str}' (simulated).")
        mock_logger.info.assert_any_call(f"Attempting to execute command in Katana: '{command_str}' with params: {params}")
        mock_logger.warning.assert_called_with(f"Unknown command for Katana: '{command_str}'")

    @patch('katana_agent.logger')
    def test_execute_command_with_empty_params(self, mock_logger):
        result = katana_agent.execute_command("uptime", params={})
        self.assertIn("Katana system uptime", result)
        mock_logger.info.assert_any_call("Attempting to execute command in Katana: 'uptime' with params: {}")


if __name__ == '__main__':
    unittest.main()
