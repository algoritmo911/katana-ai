# Placeholder for NLP utility functions
import logging

logger = logging.getLogger(__name__)

def common_logging_wrapper(func):
    """
    A decorator for logging function calls and exceptions in NLP services.
    """
    def wrapper(*args, **kwargs):
        func_name = func.__name__
        logger.info(f"Calling function: {func_name} with args: {args}, kwargs: {kwargs}")
        try:
            result = func(*args, **kwargs)
            logger.info(f"Function {func_name} executed successfully. Result: {type(result)}") # Avoid logging potentially large results directly
            return result
        except Exception as e:
            logger.error(f"Exception in function {func_name}: {e}", exc_info=True) # exc_info=True logs stack trace
            raise
    return wrapper

# Example of a more specific utility if needed:
# def format_anthropic_history(history: list, user_prompt: str) -> list:
#     """
#     Formats conversation history specifically for Anthropic's expected input.
#     Ensures alternating user/assistant roles and combines last user message.
#     """
#     formatted_messages = []
#     # ... implementation ...
#     logger.debug("Formatted messages for Anthropic.")
#     return formatted_messages

# Add other utilities here as they become necessary, for example,
# functions to handle specific error parsing if the default library exceptions are not sufficient.
