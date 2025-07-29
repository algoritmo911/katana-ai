import pytest
import asyncio
import websockets
import json
from click.testing import CliRunner
from katana.cli import main

async def mock_server(websocket):
    """
    A mock WebSocket server.
    """
    while True:
        try:
            message = await websocket.recv()
            data = json.loads(message)
            if data["command"] == "status":
                response = {
                    "status": "RUNNING",
                    "active_tasks": 0,
                    "command_queue": [],
                    "errors": [],
                }
                await websocket.send(json.dumps(response))
            else:
                await websocket.send(json.dumps({"error": "Unknown command"}))
        except websockets.ConnectionClosed:
            break

@pytest.mark.asyncio
async def test_cli_with_mock_server(monkeypatch):
    """
    Test the CLI with a mock WebSocket server.
    """
    async with websockets.serve(mock_server, "localhost", 8765):
        monkeypatch.setenv("HOME", "/tmp")
        runner = CliRunner()
        result = runner.invoke(main, ["--ws-endpoint", "ws://localhost:8765", "--auth-token", "test_token", "status"])
        assert result.exit_code == 0
        assert "Katana AI Status" in result.output
        assert "RUNNING" in result.output
