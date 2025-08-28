import pytest
from katana_single_app.services.nlp_service import RuleBasedNLPService, Intent

# Mark all tests in this file as async
pytestmark = pytest.mark.asyncio

@pytest.fixture
def nlp_service():
    """Provides a RuleBasedNLPService instance for testing."""
    return RuleBasedNLPService()

@pytest.mark.parametrize("input_text, expected_intent_name", [
    # Status intent
    ("какой у тебя статус, катана?", "status"),
    ("СТАТУС", "status"),
    ("покажи статус", "status"),

    # Analyze intent
    ("анализ логов", "analyze"),
    ("АНАЛИЗИРУЙ файловую систему", "analyze"),
    ("проведи анализ", "analyze"),

    # Think intent
    ("думай о будущем", "think"),
    ("МЫСЛИ быстрее", "think"),
    ("попробуй помыслить", "think"),

    # Unknown intent
    ("привет, мир", "unknown"),
    ("что ты умеешь?", "unknown"),
    ("", "unknown"),
    ("просто текст без ключевых слов", "unknown"),
])
async def test_parse_intent_various_inputs(nlp_service, input_text, expected_intent_name):
    """
    Tests that the NLP service correctly identifies intents from various text inputs,
    including different cases and surrounding words.
    """
    # Act
    result_intent = await nlp_service.parse_intent(input_text)

    # Assert
    assert isinstance(result_intent, Intent)
    assert result_intent.name == expected_intent_name
    assert result_intent.original_text == input_text
    assert result_intent.entities == {}

async def test_unknown_intent_for_garbage_input(nlp_service):
    """
    Tests that garbage or completely irrelevant input results in an 'unknown' intent.
    """
    # Arrange
    input_text = "asdfqwer1234!@#$"

    # Act
    result_intent = await nlp_service.parse_intent(input_text)

    # Assert
    assert result_intent.name == "unknown"
    assert result_intent.original_text == input_text
