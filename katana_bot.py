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
            print(f"{self.name}: Empty command.")
            return

        command = parts[0]
        args = parts[1:]

        if command == "!price":
            if len(args) == 1:
                pair = args[0].upper() # e.g., btc-usd -> BTC-USD
                logger.info(f"Attempting to fetch price for pair: {pair} via command.")
                # Call the imported get_spot_price function
                price = get_spot_price(pair)
                if price is not None:
                    # Note: The Coinbase API returns currency in the 'currency' field,
                    # for /prices/:pair/spot it's the counter currency (e.g., USD for BTC-USD)
                    print(f"{self.name}: Current price for {pair}: {price} (currency from pair)")
                    logger.info(f"Successfully displayed price for {pair}: {price}")
                else:
                    print(f"{self.name}: Could not fetch price for {pair}. See logs/coinbase.log for details.")
                    logger.warning(f"Failed to fetch or display price for {pair} via command.")
            else:
                error_msg = "!price command requires one argument (the trading pair). Usage: !price BTC-USD"
                logger.warning(error_msg)
                print(f"{self.name}: {error_msg}")
        elif command == "!greet":
            greeting_message = self.GREETING() # Assuming GREETING method exists
            print(f"{self.name}: {greeting_message}")
            logger.info("Executed !greet command.")
        else:
            logger.warning(f"Unknown command received: {command}")
            print(f"{self.name}: Unknown command '{command}'. Try !price BTC-USD or !greet.")

if __name__ == '__main__':
    # Configure general logging (e.g., to console and app.log)
    # This setup_logging is from logging_config.py
    setup_logging(logging.DEBUG)

    # Specific loggers like 'KatanaCoinbaseAPI' are configured within their own modules
    # (e.g., in coinbase_api.py). Importing them makes their loggers active.
    # No explicit re-configuration of those loggers should be needed here.

    bot = KatanaBot("MainBot") # Creates KatanaBot instance

    # Keep or comment out existing __main__ calls as desired
    # bot.start_mission("ExploreSectorGamma")
    # bot.start_mission("")
    # print(bot.GREETING())

    # Demonstrate the new command handling
    print("\n--- Testing Bot Commands ---")
    bot.handle_command("!price btc-usd")
    bot.handle_command("!price eth-eur")
    bot.handle_command("!price SOL-USD")
    bot.handle_command("!price INVALIDPAIR") # Test an invalid pair
    bot.handle_command("!greet")
    bot.handle_command("!unknown_command")
    bot.handle_command("!price") # Test !price without arguments
    bot.handle_command("  !price ada-usd  ") # Test with leading/trailing spaces
    print("--- Bot Command Testing Finished ---")
