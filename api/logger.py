import sys
from loguru import logger

# Configure the logger
# We can configure this to log to a file, a service, etc.
# For now, a simple, clear console format is sufficient.
logger.remove()
logger.add(
    sys.stderr,
    format="<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>",
    level="INFO"
)

# Example of a file logger that can be enabled
# logger.add("logs/api.log", rotation="10 MB", retention="10 days", level="DEBUG")

# Export the configured logger
log = logger
