import logging
from typing import Optional
from katana.logging_config import setup_logging
from katana.memory.core import MemoryCore

# It's good practice to get a logger specific to the module
logger = logging.getLogger('katana.agent') # Child logger of 'katana'

class KatanaAgent:
    def __init__(self, name="DefaultAgent", memory: Optional[MemoryCore] = None):
        self.name = name
        self.memory = memory
        # Assuming setup_logging() might have been called elsewhere globally,
        # or you ensure it's called before agent instantiation.
        # For robustness, an agent could also ensure logging is set up.
        # setup_logging() # Or get a pre-configured logger
        logger.info("KatanaAgent '%s' initialized.", self.name)
        if self.memory:
            logger.info("KatanaAgent '%s' is memory-enabled.", self.name)

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
    # Example of instantiating with memory core
    mem_core = MemoryCore()
    agent = KatanaAgent("PrimaryAgent", memory=mem_core)
    agent.perform_action("Scout area")
    agent.perform_action("") # Test error case
    agent.report_status()
