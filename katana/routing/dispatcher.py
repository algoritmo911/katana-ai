import random
from enum import Enum
from typing import Dict, Any, List

from katana.health.evaluator import AgentHealthEvaluator, AgentHealth


class DispatcherStrategy(Enum):
    ROUND_ROBIN = "round_robin"
    RANDOM = "random"
    LOAD_AWARE = "load_aware"


class Dispatcher:
    def __init__(self, health_evaluator: AgentHealthEvaluator):
        self.health_evaluator = health_evaluator

    def select_agent(self, agents: List[str], request: Dict[str, Any]) -> str:
        raise NotImplementedError


class RoundRobinDispatcher(Dispatcher):
    def __init__(self, health_evaluator: AgentHealthEvaluator):
        super().__init__(health_evaluator)
        self.last_used_agent_index = -1

    def select_agent(self, agents: List[str], request: Dict[str, Any]) -> str:
        if not agents:
            raise Exception("No agents available")
        self.last_used_agent_index = (self.last_used_agent_index + 1) % len(agents)
        return agents[self.last_used_agent_index]


class RandomDispatcher(Dispatcher):
    def select_agent(self, agents: List[str], request: Dict[str, Any]) -> str:
        if not agents:
            raise Exception("No agents available")
        return random.choice(agents)


class LoadAwareDispatcher(Dispatcher):
    def select_agent(self, agents: List[str], request: Dict[str, Any]) -> str:
        if not agents:
            raise Exception("No agents available")

        healthy_agents = [
            agent_id
            for agent_id in agents
            if self.health_evaluator.evaluate(agent_id) == AgentHealth.HEALTH_OK
        ]

        if healthy_agents:
            return random.choice(healthy_agents)
        else:
            # Fallback to random agent if no healthy agents are available
            return random.choice(agents)
