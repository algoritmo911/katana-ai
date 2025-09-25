import unittest
from katana.routing.agent_router import AgentRouter
from katana.bots.specialized_bots import HarvesterAgent, CodeGenerationAgent, TestingAgent
from katana.bots.default_bot import KatanaBot


class AgentRouterTests(unittest.TestCase):

    def setUp(self):
        self.router = AgentRouter()

    def test_route_harvest_task(self):
        task = {"type": "harvest", "content": "some data"}
        bot = self.router.route_task(task)
        self.assertIsInstance(bot, HarvesterAgent)

    def test_route_code_generation_task(self):
        task = {"type": "code_generation", "content": "generate a function"}
        bot = self.router.route_task(task)
        self.assertIsInstance(bot, CodeGenerationAgent)

    def test_route_test_task(self):
        task = {"type": "test", "content": "run a test"}
        bot = self.router.route_task(task)
        self.assertIsInstance(bot, TestingAgent)

    def test_route_unknown_task(self):
        task = {"type": "unknown", "content": "do something"}
        bot = self.router.route_task(task)
        self.assertIsInstance(bot, KatanaBot)

    def test_route_task_with_no_type(self):
        task = {"content": "do something"}
        bot = self.router.route_task(task)
        self.assertIsInstance(bot, KatanaBot)


if __name__ == '__main__':
    unittest.main()
