import pytest
from katana_single_app.core import handle_intent
from katana_single_app.services.nlp_service import Intent

# Mark all tests in this file as async
pytestmark = pytest.mark.asyncio

@pytest.mark.parametrize("intent_name, expected_response", [
    ("status", "Katana Core v15 is online..."),
    ("analyze", "Analysis command received..."),
    ("think", "Thinking command received..."),
    ("unknown", "Unknown command..."),
])
async def test_handle_intent_known_intents(intent_name, expected_response):
    """
    Tests that handle_intent returns the correct response for each known intent.
    """
    # Arrange
    intent = Intent(name=intent_name, entities={}, original_text="test")

    # Act
    response = await handle_intent(intent)

    # Assert
    assert response == expected_response

async def test_handle_intent_fallback_case():
    """
    Tests the fallback case for an unexpected intent name.
    """
    # Arrange
    intent = Intent(name="some_other_intent", entities={}, original_text="test")

    # Act
    response = await handle_intent(intent)

    # Assert
    assert response == "Command not recognized."
