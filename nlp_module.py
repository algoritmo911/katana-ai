# nlp_module.py
import logging
import re
import config # For log file name, though ideally logger is configured by main app

# Get a logger instance for this module
logger = logging.getLogger(__name__)

def recognize_intent(message: str) -> tuple[str | None, dict]:
    """
    Recognizes intent from a user message using basic rule-based matching.
    Returns a tuple of (intent_name, parameters_dict).
    """
    # Fix 1: Check for None or empty message first
    if not message:
        logger.debug("Received empty or None message for intent recognition.")
        return None, {}

    message_lower = message.lower()
    logger.debug(f"Recognizing intent for message: '{message}' (lowercase: '{message_lower}')")

    # Rule for /run <command>
    run_match = re.match(r"/run\s+(.+)", message, re.IGNORECASE)
    if run_match:
        command = run_match.group(1).strip()
        # Fix 3: Ensure the command is not empty after stripping whitespace
        if command:
            logger.info(f"Intent 'run_command' recognized with command: '{command}'")
            return "run_command", {"command": command}

    # Rule for "uptime"
    if "uptime" in message_lower:
        logger.info("Intent 'get_uptime' recognized")
        return "get_uptime", {}

    # Rule for "greet" or "hello" or "hi"
    # The pattern now tries to capture a potential name after the greeting.
    greet_pattern = r"^(greet|hello|hi)(?:\s+(?:me|to))?(?:\s+([a-zA-Z\s].*))?$"
    greet_match = re.search(greet_pattern, message_lower)
    if greet_match:
        name = greet_match.group(2) if greet_match.group(2) else None

        # Fix 2: Check for generic greetings that shouldn't have a name param.
        # This prevents "Hello bot" from creating a param {"name": "Bot"}
        if name and name.strip().lower() in ["bot", "there"]:
            name = None

        if name:
            name = name.strip().title()
            logger.info(f"Intent 'greet_user' recognized with name: '{name}'")
            return "greet_user", {"name": name}
        else:
            logger.info("Intent 'greet_user' recognized (no specific name)")
            return "greet_user", {}

    logger.info(f"No specific intent recognized for message: '{message}'")
    return None, {}

if __name__ == '__main__':
    # This block is for standalone testing of the NLP module.
    # It sets up basic logging if the module is run directly.
    # In the main application, logging is configured by telegram_bot.py.
    if not logging.getLogger().hasHandlers(): # Check if root logger is already configured
        logging.basicConfig(
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            level=config.LOG_LEVEL, # Use level from config
            handlers=[
                logging.FileHandler(config.LOG_FILE_NLP),
                logging.StreamHandler()
            ]
        )

    logger.info("NLP Module loaded for standalone testing.")

    # Example Usage
    test_messages = [
        "Can you tell me the system uptime?",
        "/run get_status --verbose",
        "Hello there!",
        "Hi",
        "Greet me",
        "Greet John",
        "hello to Jane Doe",
        "What is the weather?",
        "/run uptime",
        "/run",
        "",
        None
    ]

    for msg in test_messages:
        intent, params = recognize_intent(msg)
        print(f"Message: '{msg}' -> Intent: {intent}, Params: {params}")

    # Test specific regexes if needed
    # run_match_empty = re.match(r"/run\s+(.+)", "/run   ", re.IGNORECASE)
    # print(f"/run empty match: {run_match_empty.group(1).strip() if run_match_empty else 'No match'}")

    # greet_match_test = re.search(r"(greet|hello|hi)(?:\s+(?:me|to))?(?:\s+([a-zA-Z\s]+))?", "hello to   Big   Bird   ")
    # if greet_match_test:
    #     print(f"Greet test name: '{greet_match_test.group(2).strip().title() if greet_match_test.group(2) else 'None'}'")
