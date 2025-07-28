import pytest
from unittest.mock import MagicMock

@pytest.fixture
def mock_datafusion():
    """Mock for the DataFusion service."""
    mock = MagicMock()
    mock.get_response.return_value = "Mocked DataFusion response"
    return mock
