import unittest
import os
from unittest.mock import patch, MagicMock, ANY
from bot.nlp_clients.gemma_client import GemmaClient, GOOGLE_GENERATIVEAI_AVAILABLE
from bot.nlp_clients.base_nlp_client import NLPAuthenticationError, NLPAPIError, NLPInternalServerError

# Conditionally skip tests if the google.generativeai library is not available
# However, for robust CI, we should mock its presence for most tests.
# We'll have specific tests for when it's NOT available.

@patch('bot.nlp_clients.gemma_client.GOOGLE_GENERATIVEAI_AVAILABLE', True) # Assume library is available for most tests
@patch('google.generativeai.configure')
@patch('google.generativeai.GenerativeModel')
class TestGemmaClientWithLibrary(unittest.TestCase):

    @patch.dict(os.environ, {"GEMMA_API_KEY": "test_api_key"})
    def test_init_with_api_key_env(self, mock_generative_model, mock_configure):
        """Test initialization with API key from environment variable."""
        client = GemmaClient()
        mock_configure.assert_called_once_with(api_key="test_api_key")
        mock_generative_model.assert_called_once_with("gemini-1.0-pro")
        self.assertEqual(client.api_key, "test_api_key")
        self.assertEqual(client.model_name, "gemini-1.0-pro")

    def test_init_with_api_key_arg(self, mock_generative_model, mock_configure):
        """Test initialization with API key as argument."""
        client = GemmaClient(api_key="arg_api_key", model_name="custom-model")
        mock_configure.assert_called_once_with(api_key="arg_api_key")
        mock_generative_model.assert_called_once_with("custom-model")
        self.assertEqual(client.api_key, "arg_api_key")
        self.assertEqual(client.model_name, "custom-model")

    @patch.dict(os.environ, {}, clear=True)
    def test_init_no_api_key(self, mock_generative_model, mock_configure):
        """Test initialization without API key."""
        with self.assertRaisesRegex(NLPAuthenticationError, "Gemma API key not provided"):
            GemmaClient()

    def test_init_configure_failure(self, mock_generative_model, mock_configure):
        """Test initialization when genai.configure fails."""
        mock_configure.side_effect = Exception("Config error")
        with self.assertRaisesRegex(NLPAuthenticationError, "Failed to configure Gemma client"):
            GemmaClient(api_key="test_key")

    @patch.dict(os.environ, {"GEMMA_API_KEY": "test_api_key"})
    def test_generate_text_success(self, mock_generative_model, mock_configure):
        """Test successful text generation."""
        mock_model_instance = MagicMock()
        mock_response = MagicMock()
        mock_candidate = MagicMock()
        mock_part = MagicMock()

        mock_part.text = "Generated text here"
        mock_candidate.content.parts = [mock_part]
        mock_response.candidates = [mock_candidate]
        mock_response.prompt_feedback = None # No blocking

        mock_model_instance.generate_content.return_value = mock_response
        mock_generative_model.return_value = mock_model_instance

        client = GemmaClient()
        prompt = "Test prompt"
        response = client.generate_text(prompt, max_tokens=50, temperature=0.5)

        self.assertEqual(response, "Generated text here")
        mock_model_instance.generate_content.assert_called_once()
        call_args = mock_model_instance.generate_content.call_args
        self.assertEqual(call_args[0][0], prompt) # prompt is the first positional arg

        # Check generation_config properties
        gen_config = call_args[1]['generation_config']
        self.assertEqual(gen_config.max_output_tokens, 50)
        self.assertEqual(gen_config.temperature, 0.5)

    @patch.dict(os.environ, {"GEMMA_API_KEY": "test_api_key"})
    def test_generate_text_blocked_response(self, mock_generative_model, mock_configure):
        """Test text generation when response is blocked."""
        mock_model_instance = MagicMock()
        mock_response = MagicMock()

        mock_response.candidates = []
        mock_response.prompt_feedback = MagicMock()
        mock_response.prompt_feedback.block_reason = MagicMock()
        mock_response.prompt_feedback.block_reason.name = "SAFETY"

        mock_model_instance.generate_content.return_value = mock_response
        mock_generative_model.return_value = mock_model_instance

        client = GemmaClient()
        prompt = "Risky prompt"

        with self.assertRaisesRegex(NLPAPIError, "No content generated. Block reason: SAFETY"):
            client.generate_text(prompt)

        mock_model_instance.generate_content.assert_called_once_with(prompt, generation_config=ANY)

    @patch.dict(os.environ, {"GEMMA_API_KEY": "test_api_key"})
    def test_generate_text_no_content_no_block_reason(self, mock_generative_model, mock_configure):
        """Test text generation with no content and no specific block reason."""
        mock_model_instance = MagicMock()
        mock_response = MagicMock()

        mock_response.candidates = []
        mock_response.prompt_feedback = None # No block reason provided

        mock_model_instance.generate_content.return_value = mock_response
        mock_generative_model.return_value = mock_model_instance

        client = GemmaClient()
        prompt = "Another prompt"

        with self.assertRaisesRegex(NLPAPIError, "No content generated. Block reason: Unknown reason"):
            client.generate_text(prompt)
        mock_model_instance.generate_content.assert_called_once()

    @patch.dict(os.environ, {"GEMMA_API_KEY": "test_api_key"})
    def test_generate_text_api_error(self, mock_generative_model, mock_configure):
        """Test text generation with a generic API error."""
        mock_model_instance = MagicMock()
        # Simulate an error from the Gemma library, e.g. a google.api_core.exceptions.GoogleAPIError
        # For simplicity, using a generic Exception here.
        mock_model_instance.generate_content.side_effect = Exception("Underlying API connection error")
        mock_generative_model.return_value = mock_model_instance

        client = GemmaClient()
        with self.assertRaisesRegex(NLPAPIError, "Gemma API call failed: Underlying API connection error"):
            client.generate_text("Error prompt")

        mock_model_instance.generate_content.assert_called_once()

    @patch.dict(os.environ, {"GEMMA_API_KEY": "test_api_key"})
    def test_generate_text_model_not_initialized(self, mock_generative_model, mock_configure):
        """Test generate_text when model was not initialized (e.g. __init__ error)."""
        # This is a bit artificial as __init__ would usually raise, but tests robustness
        client = GemmaClient()
        del client.model # Simulate model not being set

        with self.assertRaisesRegex(NLPInternalServerError, "Gemma model not initialized"):
            client.generate_text("A prompt")

    def test_close_method(self, mock_generative_model, mock_configure):
        """Test the close method (should do nothing and not raise errors)."""
        client = GemmaClient(api_key="dummy_key")
        try:
            client.close()
        except Exception as e:
            self.fail(f"close() method raised an exception: {e}")


@patch('bot.nlp_clients.gemma_client.GOOGLE_GENERATIVEAI_AVAILABLE', False) # Mock library as NOT available
class TestGemmaClientWithoutLibrary(unittest.TestCase):

    def test_init_without_library_raises_import_error(self):
        """Test GemmaClient raises ImportError if google-generativeai is not installed."""
        with self.assertRaisesRegex(ImportError, "The 'google-generativeai' package is required"):
            GemmaClient(api_key="any_key")

    # This test ensures that if GOOGLE_GENERATIVEAI_AVAILABLE is False,
    # generate_text raises an error even if __init__ was somehow bypassed or mocked.
    # This might be redundant if __init__ always checks, but good for defense.
    @patch.dict(os.environ, {"GEMMA_API_KEY": "test_api_key"})
    def test_generate_text_without_library(self):
        """Test generate_text fails if library was not available, even if init was bypassed."""

        # We need to bypass the __init__ check for this specific test scenario
        with patch.object(GemmaClient, '__init__', return_value=None) as mock_init:
            client = GemmaClient() # __init__ is mocked
            client.api_key = "fake_key" # Manually set attributes if needed by the method
            # mock_init.assert_called_once() # Ensure our mock __init__ was called

            with self.assertRaisesRegex(RuntimeError, "GemmaClient cannot generate text because 'google-generativeai' is not installed."):
                client.generate_text("test prompt")


if __name__ == '__main__':
    unittest.main()
