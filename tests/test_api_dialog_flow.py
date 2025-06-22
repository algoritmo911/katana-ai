import pytest
import pytest_asyncio
from httpx import AsyncClient
from unittest.mock import patch, AsyncMock
import sys
from pathlib import Path

# Ensure the main app can be imported
# Assuming 'api_server.py' is in the parent directory of 'tests/' (i.e., project root)
# And NLPService is in 'bot.nlp_service' relative to project root
current_file_dir = Path(__file__).parent
project_root = current_file_dir.parent
sys.path.insert(0, str(project_root))

# Now we can import the app from api_server
from api_server import app as fastapi_app
from bot.nlp_service import DEFAULT_FALLBACK_RESPONSE, RETRYABLE_EXCEPTIONS

# Mark all tests in this module as asyncio
pytestmark = pytest.mark.asyncio

@pytest_asyncio.fixture
async def client():
    """Create an async test client for the FastAPI app."""
    async with AsyncClient(app=fastapi_app, base_url="http://127.0.0.1:8000") as ac:
        yield ac

@pytest_asyncio.fixture
def mock_nlp_service():
    """
    Fixture to mock the NLPService instance used by the api_server.
    It patches 'api_server.nlp_service' which is the instance created in api_server.py.
    """
    mock_service = AsyncMock() # Use AsyncMock for async methods
    # Set up default return values or side effects as needed for tests
    mock_service.get_chat_completion = AsyncMock(return_value="Default mock response")

    with patch('api_server.nlp_service', new=mock_service) as _mock_nlp:
        yield _mock_nlp # This is the patched nlp_service instance in api_server

async def test_simple_message(client: AsyncClient, mock_nlp_service: AsyncMock):
    """Test a basic message and response."""
    mock_nlp_service.get_chat_completion.return_value = "Hello from mock NLP!"

    response = await client.post("/api/message", json={"text": "Hello server"})

    assert response.status_code == 200
    json_response = response.json()
    assert json_response["response"] == "Hello from mock NLP!"
    mock_nlp_service.get_chat_completion.assert_called_once_with("Hello server")

async def test_empty_message_input(client: AsyncClient, mock_nlp_service: AsyncMock):
    """Test sending an empty message string."""
    response = await client.post("/api/message", json={"text": ""})

    assert response.status_code == 200 # API currently returns 200 with specific message
    json_response = response.json()
    assert json_response["response"] == "Input text cannot be empty."
    mock_nlp_service.get_chat_completion.assert_not_called()

async def test_nlp_fallback_on_error(client: AsyncClient, mock_nlp_service: AsyncMock):
    """Test that if NLP service raises an unexpected error (after retries), API returns 500."""
    # Simulate an error that is not automatically handled by NLPService's internal fallbacks
    # to the point of returning a string, but rather re-raises or raises a new one.
    # The get_chat_completion in NLPService is designed to return a fallback string,
    # but if it somehow re-raised an exception that the @retry didn't catch or after reraise=True

    # Let's simulate a scenario where get_chat_completion itself, despite its internal try-except,
    # ends up raising an unhandled exception. This tests the FastAPI endpoint's own try-except.
    mock_nlp_service.get_chat_completion.side_effect = Exception("Unhandled NLP core meltdown")

    response = await client.post("/api/message", json={"text": "Trigger unhandled error"})

    assert response.status_code == 500 # FastAPI's HTTPException
    json_response = response.json()
    assert json_response["detail"] == "An internal error occurred while processing your message."

async def test_nlp_returns_default_fallback(client: AsyncClient, mock_nlp_service: AsyncMock):
    """Test scenario where NLP service itself returns its default fallback string."""
    # This simulates NLPService having tried and failed all retries, then returning its own DEFAULT_FALLBACK_RESPONSE
    mock_nlp_service.get_chat_completion.return_value = DEFAULT_FALLBACK_RESPONSE

    response = await client.post("/api/message", json={"text": "A query that leads to fallback"})

    assert response.status_code == 200
    json_response = response.json()
    assert json_response["response"] == DEFAULT_FALLBACK_RESPONSE

async def test_context_simulation_dialogue(client: AsyncClient, mock_nlp_service: AsyncMock):
    """Simulate a short dialogue to check if 'context' (mocked) is passed."""
    # First message
    mock_nlp_service.get_chat_completion.return_value = "The capital of France is Paris."
    response1 = await client.post("/api/message", json={"text": "What is the capital of France?"})
    assert response1.status_code == 200
    assert response1.json()["response"] == "The capital of France is Paris."
    mock_nlp_service.get_chat_completion.assert_called_with("What is the capital of France?")

    # Second message, simulating context. The actual context handling is within the real NLPService/OpenAI.
    # Here, we just ensure the new prompt is passed.
    mock_nlp_service.get_chat_completion.return_value = "It's a famous landmark in Paris."
    response2 = await client.post("/api/message", json={"text": "Tell me about the Eiffel Tower."})
    assert response2.status_code == 200
    assert response2.json()["response"] == "It's a famous landmark in Paris."
    mock_nlp_service.get_chat_completion.assert_called_with("Tell me about the Eiffel Tower.")
    # This test doesn't deeply verify context within NLP, but that the API passes prompts correctly.
    # True context tests would need a more sophisticated mock or real NLP calls.

async def test_clarification_simulation(client: AsyncClient, mock_nlp_service: AsyncMock):
    """Simulate a scenario where the bot asks for clarification."""
    mock_nlp_service.get_chat_completion.return_value = "Which city are you asking about? London, UK or London, Ontario?"

    response = await client.post("/api/message", json={"text": "What's the weather in London?"})

    assert response.status_code == 200
    json_response = response.json()
    assert json_response["response"] == "Which city are you asking about? London, UK or London, Ontario?"
    mock_nlp_service.get_chat_completion.assert_called_with("What's the weather in London?")

# To run these tests:
# 1. Ensure OPENAI_API_KEY is set (though it won't be used if mock_nlp_service is effective)
#    or ensure NLPService can initialize without it (it currently logs a warning).
# 2. Navigate to the project root in your terminal.
# 3. Run `pytest`
#
# Note on RETRYABLE_EXCEPTIONS:
# The current NLPService is designed to catch these and retry, then return a fallback.
# To test the retry logic itself within NLPService, that would be a unit test for NLPService,
# not an integration test for the API.
# This test file focuses on the API's behavior given certain behaviors of the (mocked) NLPService.

# Example of how one might test retry behavior if NLPService was NOT mocked at instance level,
# but its actual HTTP calls were mocked (e.g. using respx for openai.AsyncOpenAI().chat.completions.create)
# This is more complex to set up here.
# For now, mocking api_server.nlp_service is the chosen strategy.

# async def test_nlp_retry_and_fallback(client: AsyncClient, mock_nlp_service: AsyncMock):
#     """
#     Test that if NLP service fails with retryable errors and then a final error,
#     the default fallback is returned.
#     This test relies on the internal retry logic of NLPService.
#     To properly test this, the mock needs to simulate the tenacity @retry behavior.
#     """
#     # This is tricky to test with a simple mock_nlp_service.get_chat_completion patch,
#     # as the @retry decorator is part of the real NLPService.
#     # A more direct unit test of NLPService.get_chat_completion would be better for this.
#
#     # However, we can simulate the *outcome* of retries failing:
#     # The @retry in NLPService has reraise=True. If all retries for RETRYABLE_EXCEPTIONS fail,
#     # the original exception is reraised.
#     # The get_chat_completion method's outer try-except then catches this and returns DEFAULT_FALLBACK_RESPONSE.
#
#     # So, simulate a RETRYABLE_EXCEPTION being the final outcome reraised by tenacity.
#     mock_nlp_service.get_chat_completion.side_effect = RETRYABLE_EXCEPTIONS[0]("Simulated rate limit after retries")
#
#     response = await client.post("/api/message", json={"text": "Query that hits rate limit"})
#
#     # The API's main try-catch in handle_message_api should catch this Exception
#     # and return an HTTPException(500) because NLPService's get_chat_completion
#     # should have returned DEFAULT_FALLBACK_RESPONSE *before* this exception propagates to api_server.
#     # Let's re-verify NLPService behavior:
#     # NLPService.get_chat_completion:
#     # @retry (...)
#     # async def func():
#     #   try:
#     #     ... call openai ...
#     #   except openai.AuthenticationError: return "Auth failed" <--- not retryable by default
#     #   except Exception as e: logger.error(..., e); return DEFAULT_FALLBACK_RESPONSE <--- This is the key
#     #
#     # If a RETRYABLE_EXCEPTION occurs, tenacity retries. If it *still* fails after all retries,
#     # tenacity reraises it. This reraised exception *is then caught* by the broad `except Exception as e`
#     # within `get_chat_completion` itself, which then returns `DEFAULT_FALLBACK_RESPONSE`.
#     # So the API level should see the DEFAULT_FALLBACK_RESPONSE, not a 500 error for this case.
#
#     assert response.status_code == 200
#     json_response = response.json()
#     assert json_response["response"] == DEFAULT_FALLBACK_RESPONSE
#     mock_nlp_service.get_chat_completion.assert_called_once()

# The above commented test `test_nlp_retry_and_fallback` is a good thought exercise.
# The key is that `NLPService.get_chat_completion` is designed to return `DEFAULT_FALLBACK_RESPONSE`
# if retries are exhausted and the reraised exception is one of the `RETRYABLE_EXCEPTIONS` (or any other Exception
# not specifically handled like AuthenticationError).
# So, the test `test_nlp_returns_default_fallback` already covers the *outcome* of such a scenario
# if the mock is set to return `DEFAULT_FALLBACK_RESPONSE`.

# To truly test the retry mechanism of NLPService itself, one would need to:
# 1. Instantiate a real NLPService.
# 2. Mock the `openai.AsyncOpenAI().chat.completions.create` method called by it.
# 3. Make that mock raise RETRYABLE_EXCEPTIONS multiple times, then succeed or fail permanently.
# This is a unit/integration test for NLPService, not for api_server's direct handling.
# The current tests are sufficient for `api_server.py`'s integration with the `nlp_service` interface.
