import logging
from logging_config import setup_logging # Assuming this is the central config
from katana_agent import KatanaAgent

# Get a module-specific logger, child of 'katana'
logger = logging.getLogger('katana.bot')

class KatanaBot:
    def __init__(self, bot_name="KatanaBot"):
        self.name = bot_name
        # Ensure logging is configured. setup_logging can be called here,
        # or assumed to be called at application entry point.
        # setup_logging() # Or get a pre-configured logger
        self.agent = KatanaAgent(name=f"{self.name}-SubAgent")
        logger.info("KatanaBot '%s' initialized with agent '%s'.", self.name, self.agent.name)

    def start_mission(self, mission_name):
        logger.debug("Bot '%s' starting mission: %s", self.name, mission_name)
        if not mission_name:
            logger.error("Mission name cannot be empty for bot '%s'.", self.name)
            return
        self.agent.perform_action(f"Execute mission: {mission_name}")
        logger.info("Bot '%s' mission '%s' underway.", self.name, mission_name)

    def GREETING(self): # Keep existing method for compatibility with old test
        logger.debug("Bot '%s' GREETING method called.", self.name)
        return f"Hello from {self.name}!"

if __name__ == '__main__':
    # This ensures logging is configured when running this script directly
    # In a larger app, setup_logging() would typically be called once at the entry point.
    setup_logging(logging.DEBUG)
    bot = KatanaBot("MainBot")
    bot.start_mission("ExploreSectorGamma")
    bot.start_mission("") # Test error case
    print(bot.GREETING())
