import pytest
import httpx
from unittest.mock import AsyncMock

from katana.infrastructure.clients.neurovault_client import (
    NeurovaultClient,
    EventIngestionRequest,
    EventIngestionResponse,
)

BASE_URL = "http://fake-neurovault-api.com"
API_KEY = "fake-api-key"

@pytest.mark.asyncio
async def test_submit_event_success(mocker):
    """
    Test that submit_event successfully sends an event and returns the correct response
    when the API returns a 202 Accepted status.
    """
    # Arrange
    mock_response_data = {"message": "Event accepted"}
    mock_response = httpx.Response(
        202,
        json=mock_response_data,
        request=httpx.Request("POST", f"{BASE_URL}/v1/events"),
    )

    mocker.patch(
        "httpx.AsyncClient.post",
        new_callable=AsyncMock,
        return_value=mock_response
    )

    client = NeurovaultClient(base_url=BASE_URL, api_key=API_KEY)
    event_request = EventIngestionRequest(
        source="test_source",
        content="test_content",
        metadata={"key": "value"}
    )

    # Act
    response = await client.submit_event(event_request)

    # Assert
    assert isinstance(response, EventIngestionResponse)
    assert response.message == mock_response_data["message"]

    # Verify that the underlying client's post method was called correctly
    httpx.AsyncClient.post.assert_called_once_with(
        url="/v1/events",
        content=event_request.model_dump_json(),
    )

    await client.close()


@pytest.mark.asyncio
async def test_submit_event_api_error_422(mocker):
    """
    Test that submit_event raises a NeurovaultAPIError when the API returns a 422 status.
    """
    # Arrange
    from katana.infrastructure.clients.neurovault_client import NeurovaultAPIError
    error_response_body = {"detail": "Unprocessable Entity"}
    mock_response = httpx.Response(
        422,
        json=error_response_body,
        request=httpx.Request("POST", f"{BASE_URL}/v1/events")
    )

    mocker.patch(
        "httpx.AsyncClient.post",
        new_callable=AsyncMock,
        return_value=mock_response
    )

    client = NeurovaultClient(base_url=BASE_URL, api_key=API_KEY)
    event_request = EventIngestionRequest(source="test", content="test")

    # Act & Assert
    with pytest.raises(NeurovaultAPIError) as excinfo:
        await client.submit_event(event_request)

    # Check that the exception message contains the status code and response text
    assert "422" in str(excinfo.value)
    assert "Unprocessable Entity" in str(excinfo.value)

    await client.close()


@pytest.mark.asyncio
async def test_submit_event_api_error_500(mocker):
    """
    Test that submit_event raises a NeurovaultAPIError when the API returns a 500 status.
    """
    # Arrange
    from katana.infrastructure.clients.neurovault_client import NeurovaultAPIError
    mock_response = httpx.Response(
        500,
        text="Internal Server Error",
        request=httpx.Request("POST", f"{BASE_URL}/v1/events")
    )

    mocker.patch(
        "httpx.AsyncClient.post",
        new_callable=AsyncMock,
        return_value=mock_response
    )

    client = NeurovaultClient(base_url=BASE_URL, api_key=API_KEY)
    event_request = EventIngestionRequest(source="test", content="test")

    # Act & Assert
    with pytest.raises(NeurovaultAPIError) as excinfo:
        await client.submit_event(event_request)

    assert "500" in str(excinfo.value)
    assert "Internal Server Error" in str(excinfo.value)

    await client.close()


@pytest.mark.asyncio
async def test_submit_event_connection_error(mocker):
    """
    Test that submit_event raises a NeurovaultConnectionError when a connection error occurs.
    """
    # Arrange
    from katana.infrastructure.clients.neurovault_client import NeurovaultConnectionError
    mocker.patch(
        "httpx.AsyncClient.post",
        new_callable=AsyncMock,
        side_effect=httpx.ConnectError("Failed to connect")
    )

    client = NeurovaultClient(base_url=BASE_URL, api_key=API_KEY)
    event_request = EventIngestionRequest(source="test", content="test")

    # Act & Assert
    with pytest.raises(NeurovaultConnectionError) as excinfo:
        await client.submit_event(event_request)

    assert "Connection to Neurovault failed" in str(excinfo.value)

    await client.close()
