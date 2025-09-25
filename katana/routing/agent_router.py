import logging
from katana.bots.default_bot import KatanaBot
from katana.bots.specialized_bots import HarvesterAgent, CodeGenerationAgent, TestingAgent

logger = logging.getLogger(__name__)


class AgentRouter:
    def __init__(self):
        self.bots = {
            "harvest": HarvesterAgent(),
            "code_generation": CodeGenerationAgent(),
            "test": TestingAgent(),
            "default": KatanaBot(),
        }
        logger.info("AgentRouter initialized with specialized bots.")

    def route_task(self, task):
        """
        Routes a task to the appropriate bot based on the task type.

        :param task: A dictionary representing the task. Expected to have a 'type' key.
        :return: An instance of a bot.
        """
        task_type = task.get("type", "default")
        bot = self.bots.get(task_type)
        if bot:
            logger.info(f"Routing task of type '{task_type}' to {bot.name}.")
            return bot
        else:
            logger.warning(f"No bot found for task type '{task_type}'. Routing to default bot.")
            return self.bots["default"]

    def get_bot(self, user_id):
        # This method is kept for compatibility with the rest of the system,
        # but it will now just return the default bot.
        # The main logic should move to route_task.
        logger.warning("get_bot is deprecated. Use route_task instead.")
        return self.bots["default"]

    def release_bot(self, user_id):
        # This method is now a no-op as we are not assigning bots to users.
        pass
