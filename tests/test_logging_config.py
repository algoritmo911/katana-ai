import unittest
import logging
from logging_config import setup_logging


class LoggingConfigTests(unittest.TestCase):
    def test_logging_level_configured_correctly(self):
        setup_logging()
        logger = logging.getLogger("katana")
        self.assertEqual(logger.level, logging.INFO)

        setup_logging(logging.DEBUG)
        self.assertEqual(logger.level, logging.DEBUG)


if __name__ == "__main__":
    unittest.main()
