import logging
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)


class AgentRegistry:
    def __init__(self):
        self._agents: Dict[str, Dict[str, Any]] = {}

    def register_agent(self, agent_id: str, agent_info: Dict[str, Any]):
        logger.info(f"Registering agent {agent_id}")
        self._agents[agent_id] = agent_info

    def deregister_agent(self, agent_id: str):
        logger.info(f"Deregistering agent {agent_id}")
        self._agents.pop(agent_id, None)

    def get_agent(self, agent_id: str) -> Optional[Dict[str, Any]]:
        return self._agents.get(agent_id)

    def list_agents(self) -> Dict[str, Dict[str, Any]]:
        return self._agents
