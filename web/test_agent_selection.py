import unittest
from unittest.mock import MagicMock
from web.utils.router import AgentRouter
from web.agents.psy_bot import PsyBot
from web.agents.zen_bot import ZenBot

class TestAgentSelection(unittest.TestCase):
    def test_agent_selection(self):
        # Create an agent router
        agent_router = AgentRouter()

        # Register some agents
        agent_router.register_agent("PsyBot", PsyBot())
        agent_router.register_agent("ZenBot", ZenBot())

        # Get an agent
        psy_bot = agent_router.get_agent("PsyBot")

        # Check that the correct agent was returned
        self.assertIsInstance(psy_bot, PsyBot)

if __name__ == '__main__':
    unittest.main()
