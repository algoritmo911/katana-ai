import unittest
import logging
from unittest.mock import patch, MagicMock
from katana_bot import KatanaBot
from katana_agent import KatanaAgent

class TestKatanaBotRefactored(unittest.TestCase):

    @patch('katana_bot.logger')
    @patch('katana_bot.KatanaAgent')
    def test_bot_initialization_logging(self, mock_katana_agent_class, mock_logger):
        """Test logging during KatanaBot initialization with refactored agent."""
        mock_agent_instance = MagicMock(spec=KatanaAgent)
        mock_agent_instance.name = "MockedAgent"
        mock_katana_agent_class.return_value = mock_agent_instance

        bot = KatanaBot(bot_name="TestBot", memory=None)

        mock_logger.info.assert_called_with("KatanaBot '%s' initialized with agent '%s'.", "TestBot", "MockedAgent")
        # Assert that the KatanaAgent was initialized with the new default parameters
        mock_katana_agent_class.assert_called_with(
            name="TestBot-SubAgent",
            role="A general sub-agent for the main bot.",
            memory=None
        )

    @patch.object(KatanaAgent, 'execute')
    def test_start_mission_logging(self, mock_agent_execute):
        """Test logging for start_mission method with refactored agent."""
        with patch('katana_bot.logger') as mock_logger:
            with patch('katana_agent.logger'): # Also patch agent's logger to suppress its init logs
                bot = KatanaBot(bot_name="MissionBot")

            # Successful mission
            bot.start_mission("Explore Alpha")
            mock_logger.debug.assert_any_call("Bot '%s' starting mission: %s", "MissionBot", "Explore Alpha")

            # Check that execute was called with a structured task
            expected_task = {"action": "execute_mission", "mission_name": "Explore Alpha"}
            mock_agent_execute.assert_called_with(expected_task)

            mock_logger.info.assert_any_call("Bot '%s' mission '%s' underway.", "MissionBot", "Explore Alpha")

            # Failed mission (empty name)
            bot.start_mission("")
            mock_logger.error.assert_called_with("Mission name cannot be empty for bot '%s'.", "MissionBot")

    def test_greeting_method_functionality(self):
        """Test the GREETING method's return value."""
        with patch('katana_agent.logger'):
             bot = KatanaBot(bot_name="GreeterBot")
        self.assertEqual(bot.GREETING(), "Hello from GreeterBot!")

    def test_bot_instance_name(self):
        """ Test that bot takes the name given. """
        with patch('katana_agent.logger'):
             bot = KatanaBot(bot_name="NamedBot")
        self.assertEqual(bot.name, "NamedBot")

if __name__ == '__main__':
    unittest.main()
