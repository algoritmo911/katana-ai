import random
from typing import Dict, Any

from katana.agent_router.registry import AgentRegistry


class Dispatcher:
    def __init__(self, registry: AgentRegistry):
        self.registry = registry

    def select_agent(self, request: Dict[str, Any]) -> str:
        raise NotImplementedError


class RoundRobinDispatcher(Dispatcher):
    def __init__(self, registry: AgentRegistry):
        super().__init__(registry)
        self.last_used_agent_index = -1

    def select_agent(self, request: Dict[str, Any]) -> str:
        agents = list(self.registry.list_agents().keys())
        if not agents:
            raise Exception("No agents available")
        self.last_used_agent_index = (self.last_used_agent_index + 1) % len(agents)
        return agents[self.last_used_agent_index]


class RandomDispatcher(Dispatcher):
    def select_agent(self, request: Dict[str, Any]) -> str:
        agents = list(self.registry.list_agents().keys())
        if not agents:
            raise Exception("No agents available")
        return random.choice(agents)
