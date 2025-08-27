import pytest
from katana_single_app.services.nlp_service import RuleBasedNLPService, Intent

# Mark all tests in this file as async
pytestmark = pytest.mark.asyncio

@pytest.fixture
def nlp_service() -> RuleBasedNLPService:
    """Provides a default instance of the RuleBasedNLPService."""
    return RuleBasedNLPService()

@pytest.mark.parametrize("text, expected_intent", [
    ("какой у тебя статус, катана?", "status"),
    ("покажи мне status", "status"),
    ("STATUS", "status"),
    ("Проанализируй эти данные", "analyze"),
    ("analyze this", "analyze"),
    ("ANALYZE", "analyze"),
    ("Подумай над этим", "think"),
    ("think about it", "think"),
    ("THINK", "think"),
])
async def test_parse_intent_standard_rules(nlp_service: RuleBasedNLPService, text: str, expected_intent: str):
    """
    Tests that the service correctly identifies intents based on default rules,
    handling different cases and surrounding text.
    """
    intent = await nlp_service.parse_intent(text)
    assert intent.name == expected_intent
    assert intent.entities == {}

async def test_parse_intent_unknown(nlp_service: RuleBasedNLPService):
    """
    Tests that the service returns an 'unknown' intent for text that does not match any rules.
    """
    text = "расскажи мне анекдот"
    intent = await nlp_service.parse_intent(text)
    assert intent.name == "unknown"
    assert intent.entities == {"original_text": text}

async def test_parse_intent_no_match(nlp_service: RuleBasedNLPService):
    """
    Tests with another non-matching string to be sure.
    """
    text = "просто обычный текст без ключевых слов"
    intent = await nlp_service.parse_intent(text)
    assert intent.name == "unknown"

async def test_parse_intent_with_custom_rules():
    """
    Tests that the service can be initialized with a custom set of rules
    and correctly parses intents based on them.
    """
    custom_rules = {
        "greeting": ["hello", "hi"],
        "farewell": ["bye", "goodbye"],
    }
    service = RuleBasedNLPService(rules=custom_rules)

    # Test custom rules
    intent_hello = await service.parse_intent("Hello there!")
    assert intent_hello.name == "greeting"

    intent_bye = await service.parse_intent("Bye for now")
    assert intent_bye.name == "farewell"

    # Test that default rules are not present
    intent_status = await service.parse_intent("what is your status?")
    assert intent_status.name == "unknown"

async def test_parse_intent_empty_string(nlp_service: RuleBasedNLPService):
    """
    Tests how the service handles an empty input string.
    """
    intent = await nlp_service.parse_intent("")
    assert intent.name == "unknown"
    assert intent.entities == {"original_text": ""}
