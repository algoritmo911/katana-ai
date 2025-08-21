import unittest
import logging
from unittest.mock import patch, MagicMock
from katana_agent import KatanaAgent

class TestKatanaAgentRefactored(unittest.TestCase):

    @patch('katana_agent.logger')
    def test_agent_initialization_logging(self, mock_logger):
        """Test logging during refactored KatanaAgent initialization."""
        agent = KatanaAgent(name="TestAgent", role="Tester", tools=[lambda: 1])
        mock_logger.info.assert_any_call("KatanaAgent '%s' initialized with role: '%s'.", "TestAgent", "Tester")
        mock_logger.info.assert_any_call("Agent '%s' has access to tools: %s", "TestAgent", ['<lambda>'])

    @patch('katana_agent.logger')
    def test_execute_action_logging(self, mock_logger):
        """Test logging for the new execute method."""
        # Define a simple tool
        def sample_tool(param1: str):
            return f"tool executed with {param1}"

        agent = KatanaAgent(name="ActionLogger", tools=[sample_tool])

        # Successful action
        task = {"action": "sample_tool", "param1": "hello"}
        agent.execute(task)
        mock_logger.debug.assert_called_with("Agent '%s' attempting to perform action: %s", "ActionLogger", "sample_tool")
        mock_logger.info.assert_called_with("Agent '%s' successfully executed action '%s'.", "ActionLogger", "sample_tool")

        # Failed action (no action specified)
        agent.execute({})
        mock_logger.error.assert_called_with("No action specified in the task for agent '%s'.", "ActionLogger")

        # Failed action (tool not found)
        agent.execute({"action": "non_existent_tool"})
        mock_logger.warning.assert_called_with("Agent '%s' has no tool to perform action: %s", "ActionLogger", "non_existent_tool")


    @patch('katana_agent.logger')
    def test_report_status_logging(self, mock_logger):
        """Test logging for the refactored report_status method."""
        agent = KatanaAgent(name="StatusReporter", role="Status Checker")
        agent.report_status()
        mock_logger.info.assert_called_with("Agent '%s' (Role: %s) reporting status: All systems nominal.", "StatusReporter", "Status Checker")

if __name__ == '__main__':
    unittest.main()
