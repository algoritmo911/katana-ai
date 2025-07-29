import logging
from typing import Dict, Any

from katana.agent_router.registry import AgentRegistry
from katana.agent_router.dispatcher import Dispatcher
from katana.agent_router.communication import CommunicationLayer

logger = logging.getLogger(__name__)


class AgentRouter:
    def __init__(
        self,
        registry: AgentRegistry,
        dispatcher: Dispatcher,
        communication_layer: CommunicationLayer,
    ):
        self.registry = registry
        self.dispatcher = dispatcher
        self.communication_layer = communication_layer

    async def route_request(self, request: Dict[str, Any]) -> Any:
        """
        Routes a request to the appropriate agent using a dispatcher and communication layer.
        """
        agent_id = self.dispatcher.select_agent(request)
        channel = self.communication_layer.get_channel(agent_id)
        if channel:
            await channel.send_request(request)
            response = await channel.get_response()
            return response
        else:
            logger.error(f"No communication channel found for agent {agent_id}.")
            return "Communication channel not found."
