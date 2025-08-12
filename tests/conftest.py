import pytest
from katana.logging_config import setup_logging

@pytest.fixture(autouse=True)
def isolated_logging(caplog):
    """
    This fixture will be automatically applied to each test.
    It sets up logging to intercept messages,
    ensuring isolation.
    """
    # Set up logging for tests, for example, to DEBUG level
    setup_logging(level="DEBUG")
