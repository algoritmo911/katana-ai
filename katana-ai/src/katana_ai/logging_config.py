import logging
import sys
import structlog


def configure_logging():
    """
    Configures structlog for structured, JSON-based logging.
    """
    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=logging.INFO,
    )

    structlog.configure(
        processors=[
            # Add a timestamp in ISO 8601 format.
            structlog.processors.TimeStamper(fmt="iso"),
            # Add the log level to the log entry.
            structlog.processors.add_log_level,
            # Add contextual data from logger.bind() calls.
            structlog.contextvars.merge_contextvars,
            # Render the final log entry as a JSON string.
            structlog.processors.JSONRenderer(),
        ],
        # Use a context-local logger factory.
        wrapper_class=structlog.make_filtering_bound_logger(logging.INFO),
        # Cache the logger for performance.
        cache_logger_on_first_use=True,
    )
    print("Structured logging configured for Katana-AI.")
