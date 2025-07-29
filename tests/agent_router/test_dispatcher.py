import pytest
from katana.agent_router.registry import AgentRegistry
from katana.agent_router.dispatcher import RoundRobinDispatcher, RandomDispatcher


@pytest.fixture
def registry():
    reg = AgentRegistry()
    reg.register_agent("agent1", {})
    reg.register_agent("agent2", {})
    reg.register_agent("agent3", {})
    return reg


def test_round_robin_dispatcher(registry: AgentRegistry):
    dispatcher = RoundRobinDispatcher(registry)
    assert dispatcher.select_agent({}) == "agent1"
    assert dispatcher.select_agent({}) == "agent2"
    assert dispatcher.select_agent({}) == "agent3"
    assert dispatcher.select_agent({}) == "agent1"


def test_random_dispatcher(registry: AgentRegistry):
    dispatcher = RandomDispatcher(registry)
    agents = list(registry.list_agents().keys())
    selected_agent = dispatcher.select_agent({})
    assert selected_agent in agents
