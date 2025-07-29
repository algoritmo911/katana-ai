import pytest
from katana.agents.suggest_agent import SuggestAgent

@pytest.fixture
def agent():
    return SuggestAgent()

def test_suggest_static_basic(agent):
    input_text = "покажи логи"
    suggestions = agent.suggest(input_text, mode="static")
    assert any("log" in s.lower() or "лог" in s.lower() for s in suggestions)

def test_suggest_unknown_mode(agent):
    with pytest.raises(ValueError):
        agent.suggest("test", mode="unknown")

def test_suggest_semantic_placeholder(agent):
    input_text = "какой статус?"
    suggestions = agent.suggest(input_text, mode="semantic")
    assert isinstance(suggestions, list)

def test_suggest_llm_placeholder(agent):
    input_text = "отменить задачу"
    suggestions = agent.suggest(input_text, mode="llm")
    assert isinstance(suggestions, list)
