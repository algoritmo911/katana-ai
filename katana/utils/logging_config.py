import logging
import json
from logging.handlers import RotatingFileHandler
from pathlib import Path
from datetime import datetime, timezone
import sys


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        log_record = {
            "timestamp": datetime.fromtimestamp(
                record.created, tz=timezone.utc
            ).isoformat(),
            "level": record.levelname,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line_number": record.lineno,
        }
        if record.exc_info:
            log_record["exception"] = self.formatException(record.exc_info)

        standard_attrs = [
            "args",
            "asctime",
            "created",
            "exc_info",
            "exc_text",
            "filename",
            "funcName",
            "levelname",
            "levelno",
            "lineno",
            "message",
            "module",
            "msecs",
            "msg",
            "name",
            "pathname",
            "process",
            "processName",
            "relativeCreated",
            "stack_info",
            "thread",
            "threadName",
        ]
        for key, value in record.__dict__.items():
            if key not in standard_attrs and key not in log_record:
                log_record[key] = value

        return json.dumps(log_record)


def setup_logger(
    logger_name: str,
    log_file_path_str: str,
    level: int = logging.DEBUG,
    max_bytes: int = 1024 * 1024,  # 1MB
    backup_count: int = 5,
):
    """
    Configures and returns a logger with JSON file logging and human-readable console logging.
    """
    logger = logging.getLogger(logger_name)
    logger.setLevel(level)

    # Remove any existing handlers to prevent duplication
    for handler in logger.handlers[:]:
        handler.close()  # Close file handles before removing
        logger.removeHandler(handler)

    # Prevent messages from being passed to the root logger
    logger.propagate = False

    # File Handler (JSON)
    log_file_path = Path(log_file_path_str)
    log_file_path.parent.mkdir(parents=True, exist_ok=True)

    file_handler = RotatingFileHandler(
        log_file_path_str, maxBytes=max_bytes, backupCount=backup_count
    )
    file_handler.setFormatter(JsonFormatter())
    file_handler.setLevel(level)  # Ensure handler also respects the level
    logger.addHandler(file_handler)

    # Console Handler (Human-Readable)
    console_handler = logging.StreamHandler(sys.stdout)
    console_format_string = (
        "%(asctime)s - %(name)s - %(levelname)s - "
        "%(message)s (%(funcName)s:%(lineno)d)"
    )
    console_formatter = logging.Formatter(console_format_string)
    console_handler.setFormatter(console_formatter)
    console_handler.setLevel(level)  # Ensure handler also respects the level
    logger.addHandler(console_handler)

    return logger
