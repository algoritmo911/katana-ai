import logging
import os # For os.path.join if used in __main__
from logging_config import setup_logging
from katana_agent import KatanaAgent
from katana.exchange.coinbase_api import get_spot_price

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

    def handle_command(self, command_string: str):
        # Get a module-specific logger, child of 'katana'
        # This logger is already defined at the top of katana_bot.py
        # logger = logging.getLogger('katana.bot') # This line should already exist or be similar

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
                pair = args[0].upper() # e.g., btc-usd -> BTC-USD
                logger.info(f"Attempting to fetch price for pair: {pair} via command.")
                price = get_spot_price(pair)
                if price is not None:
                    response_message = f"{self.name}: Current price for {pair}: {price} (currency from pair)"
                    logger.info(f"Successfully generated price message for {pair}: {price}")
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
            unknown_cmd_msg = f"Unknown command '{command}'. Try !price BTC-USD or !greet."
            logger.warning(f"Unknown command received: {command}")
            response_message = f"{self.name}: {unknown_cmd_msg}"

        return response_message

# The __main__ block is removed as the bot will be run by the FastAPI application (main.py)
# For testing, you would now run main.py and interact via Telegram or API endpoints.
# Example of old main block for reference (now removed):
# if __name__ == '__main__':
#     setup_logging(logging.DEBUG)
#     bot = KatanaBot("MainBot")
#     print("\n--- Testing Bot Commands ---")
#     # Test calls would need to capture print output or be adapted if handle_command returned values
#     # For example: print(bot.handle_command("!price btc-usd"))
#     # bot.handle_command("!price btc-usd")
#     # bot.handle_command("!price eth-eur")
#     # ... and so on
#     print("--- Bot Command Testing Finished ---")
