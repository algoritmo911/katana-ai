import logging
from logging_config import setup_logging

logger = logging.getLogger("katana.agent")


class KatanaAgent:
    def __init__(self, name="DefaultAgent"):
        self.name = name
        logger.info("KatanaAgent '%s' initialized.", self.name)

    def perform_action(self, action_description):
        logger.debug(
            "Agent '%s' attempting to perform action: %s", self.name, action_description
        )
        if not action_description:
            logger.error("No action description provided to agent '%s'.", self.name)
            return False
        logger.info(
            "Agent '%s' successfully performed action: %s",
            self.name,
            action_description,
        )
        return True

    def report_status(self):
        logger.warning(
            "Agent '%s' reporting status: All systems nominal (example warning).",
            self.name,
        )


if __name__ == "__main__":
    setup_logging(logging.DEBUG)
    agent = KatanaAgent("PrimaryAgent")
    agent.perform_action("Scout area")
    agent.perform_action("")
    agent.report_status()
