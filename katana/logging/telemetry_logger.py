import logging
import json
import os
from datetime import datetime, timezone

class JsonFormatter(logging.Formatter):
    """
    Formats log records as JSON strings.
    """
    def format(self, record):
        log_record = {
            "timestamp": datetime.fromtimestamp(record.created, timezone.utc).isoformat(),
            "level": record.levelname,
            "name": record.name,
            "message": record.getMessage(),
        }
        if record.exc_info:
            log_record["exception"] = self.formatException(record.exc_info)
        if hasattr(record, 'props') and isinstance(record.props, dict):
            log_record.update(record.props) # For custom properties
        return json.dumps(log_record)

def get_command_logger(name="katana.telemetry"):
    """
    Configures and returns a logger that writes JSON-formatted logs
    to logs/command_telemetry.log.
    """
    logger = logging.getLogger(name)
    logger.setLevel(logging.INFO) # Set default logging level

    # Prevent duplicate handlers if logger is already configured
    if logger.hasHandlers():
        return logger

    # Ensure logs directory exists
    log_dir = "logs"
    if not os.path.exists(log_dir):
        os.makedirs(log_dir)

    log_file_path = os.path.join(log_dir, "command_telemetry.log")

    # Create file handler
    file_handler = logging.FileHandler(log_file_path)

    # Create JSON formatter
    formatter = JsonFormatter()
    file_handler.setFormatter(formatter)

    # Add handler to the logger
    logger.addHandler(file_handler)

    return logger

if __name__ == "__main__":
    # Example usage:
    logger = get_command_logger()
    logger.info("This is an informational message.")
    logger.warning("This is a warning message.")
    logger.error("This is an error message.", extra={'props': {'custom_field': 'custom_value'}})

    try:
        1 / 0
    except ZeroDivisionError:
        logger.exception("An exception occurred:")

    print(f"Logs should be written to logs/command_telemetry.log")
