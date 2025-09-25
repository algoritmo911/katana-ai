import pytest
from unittest.mock import patch, MagicMock
import os

from bot.katana_bot import KatanaBot

@pytest.fixture
def bot():
    """Pytest fixture to create a KatanaBot instance for testing."""
    # Patch the Parser's analyze_text method for all tests that use this fixture
    with patch('bot.katana_bot.Parser.analyze_text') as mock_analyze_text:
        # Set a dummy API key required by the NLP processor dependency
        with patch.dict(os.environ, {"OPENAI_API_KEY": "dummy-key-for-testing"}):
            # Instantiate the bot without telebot for core logic testing
            bot_instance = KatanaBot(use_telebot=False)
            # Attach the mock to the instance for easy access in tests
            bot_instance.mock_parser_analyze = mock_analyze_text
            yield bot_instance

def mock_nlp_response(intent, entities=None, state="new_request"):
    """Helper function to create a consistent mock NLP response."""
    if entities is None:
        entities = {}
    return {
        "intents": [{"name": intent}],
        "entities": entities,
        "metadata": {"raw_openai_response": {"dialogue_state": state}}
    }

def test_single_turn_conversation(bot):
    """Tests a simple, single-turn conversation."""
    # Arrange
    chat_id = "single_turn_chat"
    user_text = "What time is it?"

    # Mock the NLP response for this turn
    nlp_data = mock_nlp_response("get_time")
    bot.mock_parser_analyze.return_value = nlp_data

    # Act
    response = bot.process_chat_message(chat_id, user_text)

    # Assert
    # Check that the parser was called correctly
    bot.mock_parser_analyze.assert_called_once_with(user_text, history=[])

    # Check that the response contains the time
    assert "The current time is" in response["reply"]
    assert response["intent_object"]["intent"] == "get_time"

    # Check that the history was updated
    assert len(bot.sessions[chat_id]["history"]) == 1
    assert bot.sessions[chat_id]["history"][0]["user"] == user_text

def test_multi_turn_context_is_maintained(bot):
    """
    Tests a two-turn conversation to ensure context is correctly passed and updated.
    1. User asks for the weather, but doesn't provide a city.
    2. Bot asks for the city.
    3. User provides the city.
    4. Bot gives the weather for that city.
    """
    chat_id = "multi_turn_chat"

    # --- Turn 1: Vague weather request ---

    # Arrange for turn 1
    user_text_1 = "How's the weather?"
    nlp_data_1 = mock_nlp_response("get_weather") # No city entity
    bot.mock_parser_analyze.return_value = nlp_data_1

    # Act for turn 1
    response_1 = bot.process_chat_message(chat_id, user_text_1)

    # Assert for turn 1
    bot.mock_parser_analyze.assert_called_once_with(user_text_1, history=[])
    assert "Which city" in response_1["reply"]
    assert not bot.sessions[chat_id]["context"]["entities"] # No entities yet

    # --- Turn 2: User provides the missing information ---

    # Arrange for turn 2
    user_text_2 = "I'm in Paris"
    # The NLP now identifies Paris as a city entity
    nlp_data_2 = mock_nlp_response("get_weather", entities={"city": "Paris"}, state="continuation")
    bot.mock_parser_analyze.return_value = nlp_data_2

    # Act for turn 2
    response_2 = bot.process_chat_message(chat_id, user_text_2)

    # Assert for turn 2
    # Check that the parser was called with the history from the first turn
    history_arg = bot.mock_parser_analyze.call_args.kwargs['history']
    assert len(history_arg) == 1
    assert history_arg[0]["user"] == user_text_1

    # Check that the final response correctly uses the merged context
    assert "The weather in Paris is great!" in response_2["reply"]

    # Check that the final context contains the city
    assert bot.sessions[chat_id]["context"]["entities"]["city"] == "Paris"
