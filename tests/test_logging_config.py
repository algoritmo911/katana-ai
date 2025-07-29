import logging
from logging_config import setup_logging


def test_logging_level_configured_correctly(caplog):
    setup_logging()
    logger = logging.getLogger("__main__")
    with caplog.at_level(logging.DEBUG):
        logger.debug("Test log message")
    assert "Test log message" in caplog.text
