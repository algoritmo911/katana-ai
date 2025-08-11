import pytest
from unittest.mock import patch, MagicMock
from bot.nlp_clients.openai_client import (
    OpenAIClient,
    OpenAIAPIError,
    OpenAIAuthenticationError,
    OpenAIInvalidRequestError,
    OpenAIInternalServerError,
    OpenAIRateLimitError,
)
from openai import RateLimitError, AuthenticationError, APIError, BadRequestError

class TestOpenAIClient:
    """
    Tests for the OpenAIClient.
    """

    @patch("bot.nlp_clients.openai_client.OpenAI")
    def test_init_with_api_key(self, MockOpenAI):
        """Tests that the client initializes correctly with an API key."""
        client = OpenAIClient(api_key="test_key")
        MockOpenAI.assert_called_with(api_key="test_key")
        assert client is not None

    def test_init_missing_api_key(self):
        """Tests that initializing the client without an API key raises an error."""
        with patch.dict("os.environ", {}, clear=True):
            with pytest.raises(OpenAIAuthenticationError, match="OpenAI API key is missing"):
                OpenAIClient()

    @patch("bot.nlp_clients.openai_client.OpenAI")
    def test_generate_text_success(self, MockOpenAI):
        """Tests a successful text generation call."""
        mock_openai_instance = MockOpenAI.return_value
        mock_response = MagicMock()
        mock_response.choices[0].message.content = "  Hello, world!  "
        mock_openai_instance.chat.completions.create.return_value = mock_response

        client = OpenAIClient(api_key="test_key")
        response = client.generate_text("test prompt")

        assert response == "Hello, world!"
        mock_openai_instance.chat.completions.create.assert_called_with(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": "test prompt"}],
            max_tokens=500,
        )

    @patch("bot.nlp_clients.openai_client.OpenAI")
    def test_generate_text_authentication_error(self, MockOpenAI):
        """Tests that an AuthenticationError is correctly handled."""
        mock_openai_instance = MockOpenAI.return_value
        mock_openai_instance.chat.completions.create.side_effect = AuthenticationError(
            message="Invalid API key", response=MagicMock(), body=None
        )

        with pytest.raises(OpenAIAuthenticationError, match="OpenAI authentication failed."):
            client = OpenAIClient(api_key="test_key")
            client.generate_text("test prompt")

    @patch("bot.nlp_clients.openai_client.OpenAI")
    def test_generate_text_rate_limit_error(self, MockOpenAI):
        """Tests that a RateLimitError is correctly handled."""
        mock_openai_instance = MockOpenAI.return_value
        mock_openai_instance.chat.completions.create.side_effect = RateLimitError(
            message="Rate limit exceeded", response=MagicMock(), body=None
        )

        with pytest.raises(OpenAIRateLimitError, match="OpenAI rate limit exceeded."):
            client = OpenAIClient(api_key="test_key")
            client.generate_text("test prompt")

    @patch("bot.nlp_clients.openai_client.OpenAI")
    def test_generate_text_bad_request_error(self, MockOpenAI):
        """Tests that a BadRequestError is correctly handled."""
        mock_openai_instance = MockOpenAI.return_value
        mock_openai_instance.chat.completions.create.side_effect = BadRequestError(
            message="Invalid request", response=MagicMock(), body=None
        )

        with pytest.raises(OpenAIInvalidRequestError, match="Invalid request to OpenAI"):
            client = OpenAIClient(api_key="test_key")
            client.generate_text("test prompt")

    @patch("bot.nlp_clients.openai_client.OpenAI")
    def test_generate_text_api_error(self, MockOpenAI):
        """Tests that a generic APIError is correctly handled."""
        mock_openai_instance = MockOpenAI.return_value
        # The actual APIError from openai library does not take 'response'
        mock_openai_instance.chat.completions.create.side_effect = APIError(
            message="Internal server error", request=MagicMock(), body=None
        )

        with pytest.raises(OpenAIInternalServerError, match="OpenAI API returned an error"):
            client = OpenAIClient(api_key="test_key")
            client.generate_text("test prompt")
