import logging
from logging_config import setup_logging

# It's good practice to get a logger specific to the module
logger = logging.getLogger('katana.agent') # Child logger of 'katana'

class KatanaAgent:
    def __init__(self, name="DefaultAgent"):
        self.name = name
        # Assuming setup_logging() might have been called elsewhere globally,
        # or you ensure it's called before agent instantiation.
        # For robustness, an agent could also ensure logging is set up.
        # setup_logging() # Or get a pre-configured logger
        logger.info("KatanaAgent '%s' initialized.", self.name)

    def perform_action(self, action_description):
        logger.debug("Agent '%s' attempting to perform action: %s", self.name, action_description)
        if not action_description:
            logger.error("No action description provided to agent '%s'.", self.name)
            return False
        logger.info("Agent '%s' successfully performed action: %s", self.name, action_description)
        return True

    def report_status(self):
        logger.warning("Agent '%s' reporting status: All systems nominal (example warning).", self.name)

if __name__ == '__main__':
    # Ensure logging is set up before using the agent if not done globally
    setup_logging(logging.DEBUG) # Setup main 'katana' logger, which agent is child of
    agent = KatanaAgent("PrimaryAgent")
    agent.perform_action("Scout area")
    agent.perform_action("") # Test error case
    agent.report_status()
