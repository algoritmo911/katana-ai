import pytest
import httpx
from unittest.mock import MagicMock

from src.integrations.n8n_client import N8nClient

@pytest.mark.asyncio
async def test_trigger_workflow_success(mocker):
    """
    Tests that the n8n workflow is triggered successfully with a 200 response.
    """
    # Arrange
    mocker.patch('os.getenv', return_value="http://fake-n8n.com/webhook")

    mock_response = MagicMock()
    mock_response.raise_for_status.return_value = None

    mock_async_client = MagicMock()
    mock_async_client.__aenter__.return_value.post.return_value = mock_response

    mocker.patch('httpx.AsyncClient', return_value=mock_async_client)

    client = N8nClient()
    payload = {"key": "value"}

    # Act
    success = await client.trigger_workflow(payload)

    # Assert
    assert success is True
    mock_async_client.__aenter__.return_value.post.assert_called_once_with(
        "http://fake-n8n.com/webhook", json=payload, timeout=10.0
    )

@pytest.mark.asyncio
async def test_trigger_workflow_http_error(mocker):
    """
    Tests that the client handles an HTTP status error (e.g., 500) gracefully.
    """
    # Arrange
    mocker.patch('os.getenv', return_value="http://fake-n8n.com/webhook")

    mock_response = MagicMock()
    mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
        "Server Error", request=MagicMock(), response=MagicMock(status_code=500)
    )

    mock_async_client = MagicMock()
    mock_async_client.__aenter__.return_value.post.return_value = mock_response

    mocker.patch('httpx.AsyncClient', return_value=mock_async_client)

    client = N8nClient()
    payload = {"key": "value"}

    # Act
    success = await client.trigger_workflow(payload)

    # Assert
    assert success is False

@pytest.mark.asyncio
async def test_trigger_workflow_no_url(mocker):
    """
    Tests that the client returns False and does not attempt to send a request
    if the N8N_WORKFLOW_TRIGGER_URL is not set.
    """
    # Arrange
    mocker.patch('os.getenv', return_value=None)
    mock_async_client_constructor = mocker.patch('httpx.AsyncClient')

    client = N8nClient()
    payload = {"key": "value"}

    # Act
    success = await client.trigger_workflow(payload)

    # Assert
    assert success is False
    mock_async_client_constructor.assert_not_called()
