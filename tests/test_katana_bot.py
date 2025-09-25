import unittest
import logging
from unittest.mock import patch, MagicMock
from katana_bot import (
    KatanaBot,
    setup_logging as bot_setup_logging,
)
from katana_agent import KatanaAgent


class TestKatanaBotLoggingAndFunctionality(unittest.TestCase):

    @patch("katana_bot.logger")
    @patch(
        "katana_bot.KatanaAgent"
    )
    def test_bot_initialization_logging(self, mock_katana_agent_class, mock_logger):
        """Test logging during KatanaBot initialization."""
        mock_agent_instance = MagicMock(spec=KatanaAgent)
        mock_agent_instance.name = "MockedAgent"
        mock_katana_agent_class.return_value = mock_agent_instance

        bot = KatanaBot(bot_name="TestBot")

        mock_logger.info.assert_called_with(
            "KatanaBot '%s' initialized with agent '%s'.", "TestBot", "MockedAgent"
        )
        mock_katana_agent_class.assert_called_with(name="TestBot-SubAgent")

    @patch("katana_bot.logger")
    @patch.object(
        KatanaAgent, "perform_action"
    )
    def test_start_mission_logging(self, mock_agent_perform_action, mock_logger):
        """Test logging for start_mission method."""
        with patch("katana_agent.logger") as mock_agent_logger_on_init:
            bot = KatanaBot(bot_name="MissionBot")

        bot.start_mission("Explore Alpha")
        mock_logger.debug.assert_any_call(
            "Bot '%s' starting mission: %s", "MissionBot", "Explore Alpha"
        )
        mock_agent_perform_action.assert_called_with("Execute mission: Explore Alpha")
        mock_logger.info.assert_any_call(
            "Bot '%s' mission '%s' underway.", "MissionBot", "Explore Alpha"
        )

        bot.start_mission("")
        mock_logger.debug.assert_any_call(
            "Bot '%s' starting mission: %s", "MissionBot", ""
        )
        mock_logger.error.assert_called_with(
            "Mission name cannot be empty for bot '%s'.", "MissionBot"
        )

    @patch("katana_bot.logger")
    def test_greeting_method_logging_and_functionality(self, mock_logger):
        """Test the GREETING method's logging and return value."""
        with patch("katana_agent.logger"):
            bot = KatanaBot(bot_name="GreeterBot")

        greeting_message = bot.GREETING()

        self.assertEqual(greeting_message, "Hello from GreeterBot!")
        mock_logger.debug.assert_called_with(
            "Bot '%s' GREETING method called.", "GreeterBot"
        )

    def test_bot_instance_name(self):
        """Test that bot takes the name given."""
        with patch("katana_agent.logger"):
            bot = KatanaBot(bot_name="NamedBot")
        self.assertEqual(bot.name, "NamedBot")


if __name__ == "__main__":
    unittest.main()
