import asyncio
from typing import Dict, Any


class CommunicationChannel:
    def __init__(self):
        self.request_queue = asyncio.Queue()
        self.response_queue = asyncio.Queue()

    async def send_request(self, request: Dict[str, Any]):
        await self.request_queue.put(request)

    async def get_request(self) -> Dict[str, Any]:
        return await self.request_queue.get()

    async def send_response(self, response: Any):
        await self.response_queue.put(response)

    async def get_response(self) -> Any:
        return await self.response_queue.get()


class CommunicationLayer:
    def __init__(self):
        self._channels: Dict[str, CommunicationChannel] = {}

    def create_channel(self, agent_id: str) -> CommunicationChannel:
        channel = CommunicationChannel()
        self._channels[agent_id] = channel
        return channel

    def get_channel(self, agent_id: str) -> CommunicationChannel:
        return self._channels.get(agent_id)
