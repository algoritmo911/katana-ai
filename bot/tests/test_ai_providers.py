import pytest
import asyncio
from unittest.mock import patch, AsyncMock, MagicMock

# Environment variables are now expected to be set by conftest.py for the pytest session.
# KATANA_TELEGRAM_TOKEN is crucial for katana_bot module import.
# AI provider keys are also set there.

# Import functions to test
from bot.ai_providers.openai import generate_text_openai
from bot.ai_providers.anthropic import generate_text_anthropic
from bot.ai_providers.huggingface import generate_text_huggingface, text_to_image_huggingface

@pytest.mark.asyncio
async def test_generate_text_openai_success():
    """Test successful OpenAI text generation."""
    mock_response = MagicMock()
    mock_response.choices = [MagicMock()]
    mock_response.choices[0].message = MagicMock()
    mock_response.choices[0].message.content = "OpenAI test response"

    # Patch the AsyncOpenAI client and its methods
    with patch('bot.ai_providers.openai.AsyncOpenAI', new_callable=AsyncMock) as mock_client_constructor:
        mock_async_client_instance = mock_client_constructor.return_value
        # Mock the specific method called in the function
        mock_async_client_instance.chat.completions.create = AsyncMock(return_value=mock_response)

        # Re-initialize the client inside openai.py to use the mock if it's globally defined
        # This might require temporarily setting bot.ai_providers.openai.client to mock_async_client_instance
        # or ensuring the function uses a locally created client or passed-in client.
        # For simplicity, assuming the global client 'client' in openai.py is patched effectively by patching AsyncOpenAI.
        # If 'bot.ai_providers.openai.client' is initialized at module load, this patch needs to be applied before module import
        # or the client instance itself needs to be patched.
        # The current approach of patching the class AsyncOpenAI should ensure any new instance uses the mock.
        # Let's refine this by directly patching the 'client' instance if it's module-level.

        # Simpler: Patch the client instance directly if it's accessible
        # For this test, we assume 'generate_text_openai' uses the 'client' defined in its own module.
        # We need to ensure that 'client' is an instance of the mocked AsyncOpenAI.
        # The patch above on AsyncOpenAI class constructor should handle this if client is defined as:
        # client = AsyncOpenAI(api_key=...)
        # If generate_text_openai is refactored to take a client, that's easier to mock.

        # For a module-level client like: `client = AsyncOpenAI()`, we patch the instance.
        with patch('bot.ai_providers.openai.client', new_callable=AsyncMock) as mock_module_client:
            mock_module_client.chat.completions.create = AsyncMock(return_value=mock_response)

            prompt = "Test prompt for OpenAI"
            response = await generate_text_openai(prompt)
            assert response == "OpenAI test response"
            mock_module_client.chat.completions.create.assert_called_once()

@pytest.mark.asyncio
async def test_generate_text_anthropic_success():
    """Test successful Anthropic text generation."""
    mock_response_content_block = MagicMock()
    mock_response_content_block.text = "Anthropic test response"

    mock_response = MagicMock()
    mock_response.content = [mock_response_content_block]
    mock_response.text = None # Ensure only content list is primary

    with patch('bot.ai_providers.anthropic.client', new_callable=AsyncMock) as mock_module_client:
        mock_module_client.messages.create = AsyncMock(return_value=mock_response)

        prompt = "Test prompt for Anthropic"
        response = await generate_text_anthropic(prompt)
        assert response == "Anthropic test response"
        mock_module_client.messages.create.assert_called_once()

@pytest.mark.asyncio
async def test_generate_text_huggingface_success():
    """Test successful HuggingFace text generation."""
    # Mock asyncio.to_thread as it's used to wrap the sync client call
    with patch('asyncio.to_thread', new_callable=AsyncMock) as mock_to_thread:
        mock_to_thread.return_value = "HuggingFace test response" # The result of client.text_generation

        # We also need to ensure the 'client' inside huggingface.py is not None
        # If 'client' is None (due to missing API key in real env), it returns early.
        # The mock env var should prevent this.
        # We don't need to mock InferenceClient itself if to_thread is properly mocked.

        prompt = "Test prompt for HuggingFace"
        response = await generate_text_huggingface(prompt)
        assert response == "HuggingFace test response"
        mock_to_thread.assert_called_once()
        # We could also assert the arguments passed to mock_to_thread if needed

@pytest.mark.asyncio
async def test_text_to_image_huggingface_success():
    """Test successful HuggingFace text-to-image generation."""
    with patch('asyncio.to_thread', new_callable=AsyncMock) as mock_to_thread:
        mock_to_thread.return_value = b"image_bytes_data" # The result of client.text_to_image

        prompt = "Test prompt for HuggingFace image"
        response = await text_to_image_huggingface(prompt)
        assert response == b"image_bytes_data"
        mock_to_thread.assert_called_once()

# Example of a test for a failure case (e.g., API key not set, client not initialized)
@pytest.mark.asyncio
async def test_generate_text_openai_no_client():
    """Test OpenAI call when client is not initialized (e.g., no API key)."""
    with patch('bot.ai_providers.openai.client', None): # Simulate client being None
        response = await generate_text_openai("A prompt")
        assert response is None
        # Add assertion for logged message if possible (would require capturing stdout/logging)

@pytest.mark.asyncio
async def test_generate_text_anthropic_no_client():
    """Test Anthropic call when client is not initialized."""
    with patch('bot.ai_providers.anthropic.client', None):
        response = await generate_text_anthropic("A prompt")
        assert response is None

@pytest.mark.asyncio
async def test_generate_text_huggingface_no_client():
    """Test HuggingFace text gen when client is not initialized."""
    with patch('bot.ai_providers.huggingface.client', None):
        response = await generate_text_huggingface("A prompt")
        assert response is None

@pytest.mark.asyncio
async def test_text_to_image_huggingface_no_client():
    """Test HuggingFace image gen when client is not initialized."""
    with patch('bot.ai_providers.huggingface.client', None):
        response = await text_to_image_huggingface("A prompt")
        assert response is None

# To run these tests:
# 1. Ensure pytest and pytest-asyncio are installed: pip install pytest pytest-asyncio
# 2. Navigate to the project root directory.
# 3. Run: pytest
#
# Note on patching module-level clients:
# The `patch('module.client', new_callable=AsyncMock)` approach is generally effective for
# clients initialized at the module level like `client = SomeAsyncClient()`.
# If the client is created *inside* the function, then the class itself (`SomeAsyncClient`)
# would need to be patched as shown in the initial commented section of test_generate_text_openai_success.
# The current AI provider files (openai.py, anthropic.py, huggingface.py) initialize
# their clients at the module level, so patching the instance should work.
# The mock environment variables ensure that the clients are attempted to be initialized.
# The patching then replaces these attempted initializations with mocks.
#
# One edge case: If a module's client is `None` because an API key was missing *before patching*,
# and the function checks `if not client: return None`, the test might pass for the wrong reason.
# Setting mock API keys helps ensure the client *would* initialize, making the subsequent patch of the
# client instance itself the key part of the mock.
# The `*_no_client` tests specifically test this early return by setting the client to `None`.

# A more robust way for OpenAI/Anthropic if client is always re-instantiated or hard to patch instance:
# @pytest.mark.asyncio
# async def test_generate_text_openai_alternative_patch():
#     mock_chat_response = AsyncMock()
#     mock_chat_response.choices = [AsyncMock()]
#     mock_chat_response.choices[0].message.content = "OpenAI response"

#     # Patch the class constructor and the method on the instance
#     with patch('bot.ai_providers.openai.AsyncOpenAI', new_callable=AsyncMock) as MockAsyncOpenAI:
#         # Configure the instance that the constructor will return
        # mock_instance = MockAsyncOpenAI.return_value
        # mock_instance.chat.completions.create = AsyncMock(return_value=mock_chat_response)

        # response = await generate_text_openai("Hello")
        # assert response == "OpenAI response"
        # MockAsyncOpenAI.assert_called_once() # Ensure client was constructed
        # mock_instance.chat.completions.create.assert_called_once()
# This alternative is more complex if the client is a global var, but useful if client is created per call.
# Given current structure, direct patch of `module.client` is cleaner.
# The test `test_generate_text_openai_success` has been updated to use this simpler direct patch.
