import unittest
from unittest.mock import patch, MagicMock
import os

# Add project root to sys.path for discovering nlp_services
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import nlp_services.openai_client # Import the module to use patch.object
from nlp_services.base_nlp_client import (
    NLPAuthenticationError, NLPBadRequestError, NLPRateLimitError,
    NLPAPIError, NLPServiceError
)
# Import OpenAI specific errors for verifying original_error type
from openai import AuthenticationError, BadRequestError, RateLimitError as OpenAIClientRateLimitError, APIError as OpenAIAPIError

# Mock response objects from openai.types.chat.chat_completion import ChatCompletion, Choice, ChatCompletionMessage, CompletionUsage
# For simplicity in mocking, we can create MagicMocks that conform to the expected structure.

class TestOpenAIClient(unittest.TestCase):

    def test_get_openai_chat_response_success(self):
        with patch.object(nlp_services.openai_client, "OPENAI_API_KEY", "test_openai_key"), \
             patch("nlp_services.openai_client.OpenAI") as MockOpenAI:

            self.assertEqual(nlp_services.openai_client.OPENAI_API_KEY, "test_openai_key")

            mock_client_instance = MockOpenAI.return_value

            # Mock the structure of ChatCompletion, Choice, ChatCompletionMessage, CompletionUsage
            mock_chat_completion_message = MagicMock()
            mock_chat_completion_message.content = "Hello from OpenAI"

            mock_choice = MagicMock()
            mock_choice.message = mock_chat_completion_message
            mock_choice.finish_reason = "stop"

            mock_completion_usage = MagicMock()
            mock_completion_usage.prompt_tokens = 10
            mock_completion_usage.completion_tokens = 20

            mock_chat_completion = MagicMock()
            mock_chat_completion.choices = [mock_choice]
            mock_chat_completion.usage = mock_completion_usage
            mock_chat_completion.model = "gpt-3.5-turbo" # Or the model used in request

            mock_client_instance.chat.completions.create.return_value = mock_chat_completion

            history = [{"role": "user", "content": "Previous message"}]
            user_prompt = "Hello, OpenAI!"
            system_prompt = "You are a helpful assistant."

            response = nlp_services.openai_client.get_openai_chat_response(
                history, user_prompt, system_prompt=system_prompt, model_name="gpt-3.5-turbo-test"
            )

            self.assertEqual(response, "Hello from OpenAI")
            MockOpenAI.assert_called_once_with(api_key="test_openai_key")
            mock_client_instance.chat.completions.create.assert_called_once()

            args, kwargs = mock_client_instance.chat.completions.create.call_args
            sent_messages = kwargs['messages']
            self.assertEqual(len(sent_messages), 3) # system, history_user, current_user
            self.assertEqual(sent_messages[0]['role'], 'system')
            self.assertEqual(sent_messages[0]['content'], system_prompt)
            self.assertEqual(sent_messages[1]['role'], 'user')
            self.assertEqual(sent_messages[1]['content'], "Previous message")
            self.assertEqual(sent_messages[2]['role'], 'user')
            self.assertEqual(sent_messages[2]['content'], user_prompt)
            self.assertEqual(kwargs['model'], "gpt-3.5-turbo-test")
            self.assertEqual(kwargs['max_tokens'], 1024) # Default from function signature

    def test_get_openai_chat_response_no_api_key(self):
        with patch.object(nlp_services.openai_client, "OPENAI_API_KEY", None):
            self.assertEqual(nlp_services.openai_client.OPENAI_API_KEY, None)
            with self.assertRaisesRegex(ValueError, "OpenAI API key is not configured"):
                nlp_services.openai_client.get_openai_chat_response([], "Hello")

    def test_openai_authentication_error(self):
        with patch.object(nlp_services.openai_client, "OPENAI_API_KEY", "test_openai_key"), \
             patch("nlp_services.openai_client.OpenAI") as MockOpenAI:

            mock_client_instance = MockOpenAI.return_value
            original_openai_error = AuthenticationError(message="Invalid API Key", response=MagicMock(), body=None) # OpenAI errors often take message, response, body
            mock_client_instance.chat.completions.create.side_effect = original_openai_error

            with self.assertRaises(NLPAuthenticationError) as cm:
                nlp_services.openai_client.get_openai_chat_response([], "Test prompt")

            self.assertIsInstance(cm.exception.original_error, AuthenticationError)
            self.assertEqual(cm.exception.user_message, "Ошибка аутентификации с OpenAI. Проверьте API ключ.")

    def test_openai_bad_request_error(self):
        with patch.object(nlp_services.openai_client, "OPENAI_API_KEY", "test_openai_key"), \
             patch("nlp_services.openai_client.OpenAI") as MockOpenAI:

            mock_client_instance = MockOpenAI.return_value
            # Simulate a response that might be part of BadRequestError
            mock_response = MagicMock()
            mock_response.json.return_value = {'error': {'message': 'The model `gpt-unknown` does not exist'}}

            original_openai_error = BadRequestError(message="Model not found", response=mock_response, body={'error': {'message': 'The model `gpt-unknown` does not exist'}})
            mock_client_instance.chat.completions.create.side_effect = original_openai_error

            with self.assertRaises(NLPBadRequestError) as cm:
                nlp_services.openai_client.get_openai_chat_response([], "Test prompt", model_name="gpt-unknown")

            self.assertIsInstance(cm.exception.original_error, BadRequestError)
            self.assertEqual(cm.exception.user_message, "Ошибка в запросе к NLP сервису (OpenAI). Проверьте формат данных или параметры запроса.")
            self.assertIn("API Message: The model `gpt-unknown` does not exist", str(cm.exception))


    def test_openai_rate_limit_error(self):
        with patch.object(nlp_services.openai_client, "OPENAI_API_KEY", "test_openai_key"), \
             patch("nlp_services.openai_client.OpenAI") as MockOpenAI:

            mock_client_instance = MockOpenAI.return_value
            original_openai_error = OpenAIClientRateLimitError(message="Rate limit exceeded", response=MagicMock(), body=None)
            mock_client_instance.chat.completions.create.side_effect = original_openai_error

            with self.assertRaises(NLPRateLimitError) as cm:
                nlp_services.openai_client.get_openai_chat_response([], "Test prompt")

            self.assertIsInstance(cm.exception.original_error, OpenAIClientRateLimitError)
            self.assertEqual(cm.exception.user_message, "Превышен лимит запросов к OpenAI. Пожалуйста, попробуйте позже.")

    def test_openai_generic_api_error(self):
        with patch.object(nlp_services.openai_client, "OPENAI_API_KEY", "test_openai_key"), \
             patch("nlp_services.openai_client.OpenAI") as MockOpenAI:

            mock_client_instance = MockOpenAI.return_value
            mock_request = MagicMock() # Simulate an httpx.Request object
            # The body could be None or a dict depending on what the error represents
            mock_body = {'error': {'message': 'A generic API error occurred', 'type': 'api_error'}}
            original_openai_error = OpenAIAPIError(message="Some API error", request=mock_request, body=mock_body)
            # If the SUT code were to access error.response, we would set it here:
            # original_openai_error.response = MagicMock(status_code=500) # Example
            mock_client_instance.chat.completions.create.side_effect = original_openai_error

            with self.assertRaises(NLPAPIError) as cm:
                nlp_services.openai_client.get_openai_chat_response([], "Test prompt")

            self.assertIsInstance(cm.exception.original_error, OpenAIAPIError)
            self.assertEqual(cm.exception.user_message, "Произошла непредвиденная ошибка при работе с OpenAI API.")

    def test_openai_unexpected_error(self):
        with patch.object(nlp_services.openai_client, "OPENAI_API_KEY", "test_openai_key"), \
             patch("nlp_services.openai_client.OpenAI") as MockOpenAI:

            mock_client_instance = MockOpenAI.return_value
            original_exception = Exception("A totally unexpected issue!")
            mock_client_instance.chat.completions.create.side_effect = original_exception

            with self.assertRaises(NLPServiceError) as cm:
                nlp_services.openai_client.get_openai_chat_response([], "Test prompt")

            self.assertIsInstance(cm.exception.original_error, Exception)
            self.assertEqual(cm.exception.user_message, "Произошла ошибка при обращении к NLP сервису. Пожалуйста, попробуйте позже.") # Default user message
            self.assertIn("A totally unexpected issue!", str(cm.exception))


if __name__ == "__main__":
    unittest.main()
