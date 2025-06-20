import logging
import os

DEFAULT_LOG_FORMAT = "[%(asctime)s] [%(name)s] [%(levelname)s] [%(user_id)s]: %(message)s"
DEFAULT_DATE_FORMAT = "%Y-%m-%dT%H:%M:%S.%fZ"

# --- User ID Filter ---
# This filter allows adding a user_id to the log record if it's not already present.
class UserIdFilter(logging.Filter):
    def __init__(self, default_user_id="SYSTEM"):
        super().__init__()
        self.default_user_id = default_user_id

    def filter(self, record):
        if not hasattr(record, 'user_id'):
            record.user_id = self.default_user_id
        return True

def get_logger(module_name: str, user_id: str = "SYSTEM"):
    """
    Configures and returns a logger instance.

    Args:
        module_name (str): The name of the module this logger is for (e.g., __name__).
        user_id (str, optional): The user ID to associate with log messages.
                                 Defaults to "SYSTEM". This can be overridden
                                 per log message if needed.

    Returns:
        logging.Logger: Configured logger instance.
    """
    logger = logging.getLogger(module_name)

    # Set level from environment variable, defaulting to INFO
    log_level_str = os.environ.get("KATANA_LOG_LEVEL", "INFO").upper()
    log_level = getattr(logging, log_level_str, logging.INFO)
    logger.setLevel(log_level)

    # Prevent duplicate handlers if logger already configured
    if not logger.handlers:
        # Create console handler
        ch = logging.StreamHandler()
        ch.setLevel(log_level)

        # Create formatter
        formatter = logging.Formatter(DEFAULT_LOG_FORMAT, datefmt=DEFAULT_DATE_FORMAT)
        ch.setFormatter(formatter)

        # Add filter and handler to logger
        ch.addFilter(UserIdFilter(default_user_id=user_id)) # Add filter to handler
        logger.addFilter(UserIdFilter(default_user_id=user_id)) # Also add to logger for direct calls if not using handler
        logger.addHandler(ch)

        # Propagate logs to parent loggers or not, based on needs.
        # Default is True. If set to False, logs won't go to the root logger.
        # For now, let's keep it True for simpler global control if needed.
        logger.propagate = True

    return logger

if __name__ == '__main__':
    # Example Usage:
    # Set environment variable for testing different log levels:
    # export KATANA_LOG_LEVEL=DEBUG

    # Logger for a generic system component
    system_logger = get_logger("KatanaSystem")
    system_logger.info("System logger initialized.")
    system_logger.debug("This is a debug message for system (will not show if level is INFO).")
    system_logger.warning("A warning from the system.")

    # Logger for a specific user context
    user_specific_logger = get_logger("UserModule", user_id="user123")
    user_specific_logger.info("User-specific action started.")
    user_specific_logger.error("An error occurred for user123.")

    # Logging with extra context (overriding the default user_id for this message)
    user_specific_logger.info("Another action by a different user.", extra={'user_id': 'user456'})

    # Test propagation (if root logger is configured)
    logging.basicConfig(level=logging.DEBUG, format='[ROOT_LOGGER] %(message)s') # Basic config for root
    test_prop_logger = get_logger("PropagationTest")
    test_prop_logger.info("Testing propagation.") # Should appear with KatanaSystem format and Root format if propagate=True

    # Test if get_logger called multiple times for same module returns same logger instance (it should)
    another_system_logger = get_logger("KatanaSystem")
    another_system_logger.info("This message should appear from the same KatanaSystem logger instance.")

    # Test with a different module name
    payment_logger = get_logger("PaymentService", user_id="service_acct")
    payment_logger.info("Payment processing initiated.")
    payment_logger.error("Credit card validation failed for order 789.", extra={'user_id': 'customer007'})

    print(f"Current log level for KatanaSystem: {logging.getLevelName(system_logger.level)}")
    print(f"Current log level for UserModule: {logging.getLevelName(user_specific_logger.level)}")
    print(f"Current log level for PaymentService: {logging.getLevelName(payment_logger.level)}")
