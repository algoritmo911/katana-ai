import sys
import logging
from loguru import logger

from src.katana.configs.settings import settings

class InterceptHandler(logging.Handler):
    """
    Redirects standard logging messages to the Loguru sink.
    This ensures that logs from any library using the standard `logging` module
    are captured and formatted by Loguru.
    See: https://loguru.readthedocs.io/en/stable/overview.html#entirely-compatible-with-standard-logging
    """
    def emit(self, record: logging.LogRecord):
        # Get corresponding Loguru level if it exists
        try:
            level = logger.level(record.levelname).name
        except ValueError:
            level = record.levelno

        # Find caller from where the logged message originated
        frame, depth = logging.currentframe(), 2
        while frame and frame.f_code.co_filename == logging.__file__:
            frame = frame.f_back
            depth += 1

        logger.opt(depth=depth, exception=record.exc_info).log(
            level, record.getMessage()
        )

def setup_logger():
    """
    Configures the Loguru logger for the application.

    This function sets up a single, consistent logger configuration.
    - It removes any existing handlers to prevent duplicate output.
    - It adds a new sink to output structured JSON logs to stdout.
    - It intercepts standard Python `logging` messages and redirects them
      through Loguru, so that dependencies' logs are also captured.
    - The log level is read from the application settings.
    """
    # Remove the default handler to avoid duplicate logs
    logger.remove()

    # Add a sink for structured JSON logging.
    # `serialize=True` ensures the output is a JSON object, which is ideal
    # for log processing and analysis systems. Loguru automatically includes
    # fields like timestamp, level, message, function, line, etc.
    # Contextual data (like a request_id) added via `logger.bind()` will
    # also be automatically included in the JSON record.
    logger.add(
        sys.stdout,
        level=settings.log_level.upper(),
        format="{message}",  # The format is implicitly handled by `serialize=True`
        serialize=True,      # Output logs in JSON format
        enqueue=True,        # Make logging calls non-blocking (important for async)
        catch=True,          # Safely catch exceptions in the logger
    )

    # Configure the standard logging library to redirect all its logs to our InterceptHandler
    logging.basicConfig(handlers=[InterceptHandler()], level=0, force=True)

    logger.info("Logger has been configured for structured JSON output.")
