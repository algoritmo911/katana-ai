import asyncio
import websockets
import json

class KatanaApiClient:
    def __init__(self, ws_url: str, auth_token: str, loop=None):
        self.ws_url = ws_url
        self.auth_token = auth_token
        self.ws = None
        self.loop = loop or asyncio.get_event_loop()

    async def connect_ws(self):
        self.ws = await websockets.connect(f"{self.ws_url}?auth_token={self.auth_token}")
        self.loop.create_task(self._heartbeat())

    async def _heartbeat(self):
        while True:
            try:
                await self.ws.send(json.dumps({"type": "ping"}))
                await asyncio.sleep(30)
            except Exception:
                # reconnect logic
                break

    async def send_command(self, command: str, params: dict) -> dict:
        if not self.ws:
            await self.connect_ws()
        message = json.dumps({"command": command, "params": params})
        await self.ws.send(message)
        response_raw = await self.ws.recv()
        response = json.loads(response_raw)
        return response

    async def close(self):
        if self.ws:
            await self.ws.close()
