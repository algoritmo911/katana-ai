import unittest
import logging
from unittest.mock import patch, MagicMock
from katana_agent import (
    KatanaAgent,
    setup_logging as agent_setup_logging,
)


class TestKatanaAgentLogging(unittest.TestCase):

    @patch("katana_agent.logger")
    def test_agent_initialization_logging(self, mock_logger):
        """Test logging during KatanaAgent initialization."""
        agent = KatanaAgent(name="TestAgent")
        mock_logger.info.assert_called_with(
            "KatanaAgent '%s' initialized.", "TestAgent"
        )

    @patch("katana_agent.logger")
    def test_perform_action_logging(self, mock_logger):
        """Test logging for perform_action method."""
        agent = KatanaAgent(name="ActionLogger")

        agent.perform_action("test action")
        mock_logger.debug.assert_any_call(
            "Agent '%s' attempting to perform action: %s", "ActionLogger", "test action"
        )
        mock_logger.info.assert_any_call(
            "Agent '%s' successfully performed action: %s",
            "ActionLogger",
            "test action",
        )

        agent.perform_action("")
        mock_logger.debug.assert_any_call(
            "Agent '%s' attempting to perform action: %s", "ActionLogger", ""
        )
        mock_logger.error.assert_called_with(
            "No action description provided to agent '%s'.", "ActionLogger"
        )

    @patch("katana_agent.logger")
    def test_report_status_logging(self, mock_logger):
        """Test logging for report_status method."""
        agent = KatanaAgent(name="StatusReporter")
        agent.report_status()
        mock_logger.warning.assert_called_with(
            "Agent '%s' reporting status: All systems nominal (example warning).",
            "StatusReporter",
        )


if __name__ == "__main__":
    unittest.main()
