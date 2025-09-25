import logging
import os
from logging_config import setup_logging
from katana_agent import KatanaAgent
from katana.exchange.coinbase_api import get_spot_price

logger = logging.getLogger("katana.bot")


class KatanaBot:
    def __init__(self, bot_name="KatanaBot"):
        self.name = bot_name
        self.agent = KatanaAgent(name=f"{self.name}-SubAgent")
        logger.info(
            "KatanaBot '%s' initialized with agent '%s'.", self.name, self.agent.name
        )

    def start_mission(self, mission_name):
        logger.debug("Bot '%s' starting mission: %s", self.name, mission_name)
        if not mission_name:
            logger.error("Mission name cannot be empty for bot '%s'.", self.name)
            return
        self.agent.perform_action(f"Execute mission: {mission_name}")
        logger.info("Bot '%s' mission '%s' underway.", self.name, mission_name)

    def GREETING(self):
        logger.debug("Bot '%s' GREETING method called.", self.name)
        return f"Hello from {self.name}!"

    def handle_command(self, command_string: str):
        logger.info(f"Bot '{self.name}' received command: {command_string}")
        parts = command_string.strip().lower().split()
        if not parts:
            logger.warning("Empty command received.")
            return f"{self.name}: Empty command."

        command = parts[0]
        args = parts[1:]
        response_message = ""

        if command == "!price":
            if len(args) == 1:
                pair = args[0].upper()
                logger.info(f"Attempting to fetch price for pair: {pair} via command.")
                price = get_spot_price(pair)
                if price is not None:
                    response_message = f"{self.name}: Current price for {pair}: {price} (currency from pair)"
                    logger.info(
                        f"Successfully generated price message for {pair}: {price}"
                    )
                else:
                    response_message = f"{self.name}: Could not fetch price for {pair}. See server logs for details."
                    logger.warning(f"Failed to fetch price for {pair} via command.")
            else:
                error_msg = "!price command requires one argument (the trading pair). Usage: !price BTC-USD"
                logger.warning(error_msg)
                response_message = f"{self.name}: {error_msg}"
        elif command == "!greet":
            greeting_message = self.GREETING()
            response_message = f"{self.name}: {greeting_message}"
            logger.info("Executed !greet command.")
        else:
            unknown_cmd_msg = (
                f"Unknown command '{command}'. Try !price BTC-USD or !greet."
            )
            logger.warning(f"Unknown command received: {command}")
            response_message = f"{self.name}: {unknown_cmd_msg}"

        return response_message
