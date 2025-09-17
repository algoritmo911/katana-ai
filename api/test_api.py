import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock
import os

# Set a dummy API key for testing
os.environ["API_KEY"] = "test_api_key"

from api.main import app, sessions
from bot.katana_bot import KatanaBot
from api import security

client = TestClient(app)

@pytest.fixture(autouse=True)
def clear_sessions_and_override_auth():
    """Fixture to clear sessions and mock auth before each test."""
    sessions.clear()
    app.dependency_overrides[security.get_api_key] = lambda: "test_api_key"
    yield
    app.dependency_overrides = {}

def test_read_root():
    """Test the root endpoint."""
    response = client.get("/")
    assert response.status_code == 200
    assert response.json() == {"status": "Katana Cognitive Core API is running."}

# The start endpoint now correctly instantiates the bot with use_telebot=False
@patch('api.main.KatanaBot', spec=KatanaBot)
def test_start_session_success(MockKatanaBot):
    """Test successfully starting a new session."""
    response = client.post("/session/start")

    assert response.status_code == 200
    json_response = response.json()
    assert "session_id" in json_response
    session_id = json_response["session_id"]
    assert session_id in sessions
    # Assert that the bot was instantiated correctly for API use
    MockKatanaBot.assert_called_once_with(use_telebot=False)

def test_chat_session_not_found():
    """Test chatting with a non-existent session."""
    response = client.post("/session/non_existent_id/query", json={"text": "Hello"})
    assert response.status_code == 404
    assert "Session not found" in response.json()["detail"]

def test_chat_success():
    """Test a successful chat interaction by mocking the bot's process_chat_message method."""
    session_id = "test_session"

    # Create a mock bot instance
    mock_bot_instance = MagicMock(spec=KatanaBot)

    # Set up the return value for the method the API calls
    mock_response = {
        "reply": "This is a mock reply",
        "intent_object": {"intent": "mock_intent", "entities": {}}
    }
    mock_bot_instance.process_chat_message.return_value = mock_response

    # Manually insert the mocked bot into the sessions dictionary
    sessions[session_id] = mock_bot_instance

    # Make the request
    response = client.post(f"/session/{session_id}/query", json={"text": "Does this work?"})

    # Assertions
    assert response.status_code == 200
    assert response.json() == mock_response
    mock_bot_instance.process_chat_message.assert_called_once_with(session_id, "Does this work?")

def test_get_history_not_found():
    """Test getting history for a non-existent session."""
    response = client.get("/session/non_existent_id/history")
    assert response.status_code == 404
    assert "Session not found" in response.json()["detail"]

def test_get_history_success():
    """Test successfully getting history for a session."""
    session_id = "test_session"
    mock_bot = MagicMock(spec=KatanaBot)

    # This mock history must match the `HistoryTurn` pydantic schema
    mock_history = [{"user": "Hello", "bot": "Hi there!"}]

    # The endpoint retrieves history from the bot instance's session tracking
    mock_bot.sessions = {session_id: {"history": mock_history}}
    sessions[session_id] = mock_bot

    response = client.get(f"/session/{session_id}/history")

    assert response.status_code == 200
    json_response = response.json()
    assert json_response["session_id"] == session_id
    assert json_response["history"] == mock_history
