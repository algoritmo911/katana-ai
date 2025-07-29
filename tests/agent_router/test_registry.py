import pytest
from katana.agent_router.registry import AgentRegistry


@pytest.fixture
def registry():
    return AgentRegistry()


def test_register_agent(registry: AgentRegistry):
    registry.register_agent("test_agent", {"foo": "bar"})
    assert registry.get_agent("test_agent") == {"foo": "bar"}


def test_deregister_agent(registry: AgentRegistry):
    registry.register_agent("test_agent", {"foo": "bar"})
    registry.deregister_agent("test_agent")
    assert registry.get_agent("test_agent") is None


def test_list_agents(registry: AgentRegistry):
    registry.register_agent("agent1", {"info": "1"})
    registry.register_agent("agent2", {"info": "2"})
    assert registry.list_agents() == {
        "agent1": {"info": "1"},
        "agent2": {"info": "2"},
    }
