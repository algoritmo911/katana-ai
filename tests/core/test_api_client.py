import pytest
import asyncio
from unittest.mock import AsyncMock, patch
from katana.core.api_client import KatanaApiClient

@pytest.mark.asyncio
async def test_send_command():
    """
    Test sending a command to the Katana core.
    """
    with patch("websockets.connect", new_callable=AsyncMock) as mock_connect:
        mock_ws = AsyncMock()
        mock_ws.recv.return_value = '{"status": "success"}'
        mock_connect.return_value = mock_ws

        client = KatanaApiClient("ws://localhost:8765", "test_token")
        response = await client.send_command("status", {})

        assert response == {"status": "success"}
        mock_connect.assert_called_once_with("ws://localhost:8765", extra_headers={"Authorization": "Bearer test_token"})
        mock_ws.send.assert_called_once_with('{"command": "status", "params": {}}')
        mock_ws.recv.assert_called_once()
