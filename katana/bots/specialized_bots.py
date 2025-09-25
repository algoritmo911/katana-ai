import logging
from katana.bots.base_bot import BaseBot

logger = logging.getLogger(__name__)


class HarvesterAgent(BaseBot):
    def __init__(self, bot_name="HarvesterAgent", profile=None):
        super().__init__(bot_name, profile)

    def handle_task(self, task):
        logger.info(f"HarvesterAgent handling task: {task}")
        return f"Task '{task.get('content')}' handled by HarvesterAgent."


class CodeGenerationAgent(BaseBot):
    def __init__(self, bot_name="CodeGenerationAgent", profile=None):
        super().__init__(bot_name, profile)

    def handle_task(self, task):
        logger.info(f"CodeGenerationAgent handling task: {task}")
        return f"Task '{task.get('content')}' handled by CodeGenerationAgent."


class TestingAgent(BaseBot):
    __test__ = False
    def __init__(self, bot_name="TestingAgent", profile=None):
        super().__init__(bot_name, profile)

    def handle_task(self, task):
        logger.info(f"TestingAgent handling task: {task}")
        return f"Task '{task.get('content')}' handled by TestingAgent."
