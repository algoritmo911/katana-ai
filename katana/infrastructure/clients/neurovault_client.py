import httpx
from typing import Dict, Optional

from pydantic import BaseModel


class EventIngestionRequest(BaseModel):
    """
    Pydantic model for the event ingestion request body.
    Represents the data structure for submitting an event to Neurovault.
    """
    source: str
    content: str
    metadata: Optional[Dict] = None


class EventIngestionResponse(BaseModel):
    """
    Pydantic model for the successful event ingestion response.
    """
    message: str


# Custom Exceptions
class NeurovaultConnectionError(Exception):
    """Custom exception for errors related to connecting to the Neurovault API."""
    pass


class NeurovaultAPIError(Exception):
    """Custom exception for errors returned by the Neurovault API."""
    pass


class NeurovaultClient:
    """
    An asynchronous client for interacting with the Neurovault API.
    """
    def __init__(self, base_url: str, api_key: str):
        self._base_url = base_url
        self._api_key = api_key
        self._client = httpx.AsyncClient(
            base_url=self._base_url,
            headers={
                "Authorization": f"Bearer {self._api_key}",
                "Content-Type": "application/json",
            },
            timeout=30.0,
        )

    async def submit_event(self, event: EventIngestionRequest) -> EventIngestionResponse:
        """
        Submits a single event to the Neurovault API.

        Args:
            event: An EventIngestionRequest object containing the event data.

        Returns:
            An EventIngestionResponse object on success.

        Raises:
            NeurovaultConnectionError: If there is a problem connecting to the API.
            NeurovaultAPIError: If the API returns a non-successful status code.
        """
        try:
            response = await self._client.post(
                url="/v1/events",
                content=event.model_dump_json(),
            )
            response.raise_for_status()

            # The API is expected to return 202 Accepted
            return EventIngestionResponse(**response.json())

        except httpx.ConnectError as e:
            raise NeurovaultConnectionError(f"Connection to Neurovault failed: {e}") from e
        except httpx.HTTPStatusError as e:
            raise NeurovaultAPIError(
                f"Neurovault API returned an error: {e.response.status_code} - {e.response.text}"
            ) from e

    async def close(self):
        """
        Closes the underlying httpx client. Should be called on application shutdown.
        """
        await self._client.aclose()
