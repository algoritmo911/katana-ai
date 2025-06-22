import unittest
from unittest.mock import patch, MagicMock
import os

# Temporarily add nlp_services to sys.path for testing if not installed as a package
# This is often handled by test runners or project structure (e.g., using src layout)
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

# Import the module itself to use patch.object
import nlp_services.anthropic_client
# Still import the function for direct calling if preferred, but be mindful of context for globals
# from nlp_services.anthropic_client import get_anthropic_chat_response # Keep for now, but calls will be module.func
from anthropic import AuthenticationError, BadRequestError, RateLimitError, APIError # Original errors for mocking
from nlp_services.base_nlp_client import NLPAuthenticationError, NLPBadRequestError, NLPRateLimitError, NLPAPIError, NLPServiceError # Custom errors to expect
from anthropic.types import Message, Usage # Changed CompletionUsage to Usage

class TestAnthropicClient(unittest.TestCase):

    def test_get_anthropic_chat_response_success(self):
        # Patch the ANTHROPIC_API_KEY attribute directly on the imported module object
        with patch.object(nlp_services.anthropic_client, "ANTHROPIC_API_KEY", "key_for_success_test"), \
             patch("nlp_services.anthropic_client.Anthropic") as MockAnthropic: # Patching Anthropic class in the module

            # Debug: Check the patched value
            # print(f"Inside test_get_anthropic_chat_response_success: Patched ANTHROPIC_API_KEY = {nlp_services.anthropic_client.ANTHROPIC_API_KEY}")
            self.assertEqual(nlp_services.anthropic_client.ANTHROPIC_API_KEY, "key_for_success_test")

            # Mock the Anthropic client and its response
            mock_client_instance = MockAnthropic.return_value
            mock_response_content = MagicMock(spec=Message)
            mock_response_content.content = [MagicMock(text="Hello from Claude")]
            mock_response_content.usage = MagicMock(spec=Usage, input_tokens=10, output_tokens=20) # Changed CompletionUsage to Usage
            mock_response_content.model = "claude-3-opus-20240229"
            mock_response_content.stop_reason = "end_turn"

            mock_client_instance.messages.create.return_value = mock_response_content

            history = [{"role": "user", "content": "Previous user message"}, {"role": "assistant", "content": "Previous assistant response"}]
            user_prompt = "Hello, Claude!"

            # Call the function via the module to ensure it's from the patched context
            response = nlp_services.anthropic_client.get_anthropic_chat_response(history, user_prompt)

            self.assertEqual(response, "Hello from Claude")
            MockAnthropic.assert_called_once_with(api_key="key_for_success_test")
        mock_client_instance.messages.create.assert_called_once()

        # Check messages passed to the API
        args, kwargs = mock_client_instance.messages.create.call_args
        sent_messages = kwargs['messages']
        self.assertEqual(len(sent_messages), 3)
        self.assertEqual(sent_messages[0]['role'], 'user')
        self.assertEqual(sent_messages[0]['content'], 'Previous user message')
        self.assertEqual(sent_messages[1]['role'], 'assistant')
        self.assertEqual(sent_messages[1]['content'], 'Previous assistant response')
        self.assertEqual(sent_messages[2]['role'], 'user')
        self.assertEqual(sent_messages[2]['content'], 'Hello, Claude!')
        self.assertEqual(kwargs['model'], "claude-3-opus-20240229") # Default model
        self.assertEqual(kwargs['max_tokens'], 1024) # Default max_tokens

    def test_get_anthropic_chat_response_with_system_prompt(self):
        with patch.object(nlp_services.anthropic_client, "ANTHROPIC_API_KEY", "key_for_system_prompt_test"), \
             patch("nlp_services.anthropic_client.Anthropic") as MockAnthropic:
            self.assertEqual(nlp_services.anthropic_client.ANTHROPIC_API_KEY, "key_for_system_prompt_test") # Verify patch
            mock_client_instance = MockAnthropic.return_value
            mock_response_content = MagicMock(spec=Message)
            mock_response_content.content = [MagicMock(text="System prompt acknowledged.")]
            mock_response_content.usage = MagicMock(spec=Usage, input_tokens=15, output_tokens=5) # Changed CompletionUsage to Usage
            mock_response_content.model = "claude-3-opus-20240229"
            mock_response_content.stop_reason = "end_turn"
            mock_client_instance.messages.create.return_value = mock_response_content

            user_prompt = "Confirm you read the system prompt."
            system_prompt_text = "You are a helpful assistant."

            response = nlp_services.anthropic_client.get_anthropic_chat_response([], user_prompt, system_prompt=system_prompt_text)

            self.assertEqual(response, "System prompt acknowledged.")
            args, kwargs = mock_client_instance.messages.create.call_args
        self.assertEqual(kwargs['system'], system_prompt_text)

    def test_get_anthropic_chat_response_no_api_key(self):
        with patch.object(nlp_services.anthropic_client, "ANTHROPIC_API_KEY", None):
            self.assertEqual(nlp_services.anthropic_client.ANTHROPIC_API_KEY, None) # Verify patch
            with self.assertRaisesRegex(ValueError, "Anthropic API key is not configured"):
                nlp_services.anthropic_client.get_anthropic_chat_response([], "Hello")

    def test_anthropic_authentication_error(self):
        with patch.object(nlp_services.anthropic_client, "ANTHROPIC_API_KEY", "key_for_auth_error_test"), \
             patch("nlp_services.anthropic_client.Anthropic") as MockAnthropic:
            self.assertEqual(nlp_services.anthropic_client.ANTHROPIC_API_KEY, "key_for_auth_error_test") # Verify patch
            mock_client_instance = MockAnthropic.return_value

            mock_http_response = MagicMock()
            mock_http_response.status_code = 401
            # mock_http_response.request = MagicMock() # if needed
            mock_error_body = {'error': {'type': 'authentication_error', 'message': 'Invalid API Key'}}

            mock_error = AuthenticationError(
                "Invalid API Key", # message
                response=mock_http_response,
                body=mock_error_body
            )
            # mock_error.status_code = 401 # Already set by response mock
            # mock_error.body = {'error': {'message': 'Invalid API Key'}} # Already set by body mock
            # mock_error.response = MagicMock(status_code=401) # If needed by SUT
            mock_client_instance.messages.create.side_effect = mock_error

            with self.assertRaises(NLPAuthenticationError) as cm:
                nlp_services.anthropic_client.get_anthropic_chat_response([], "Test prompt")

            self.assertIsInstance(cm.exception.original_error, AuthenticationError)
            self.assertEqual(cm.exception.user_message, "Ошибка аутентификации с NLP сервисом. Проверьте API ключ или обратитесь к администратору.")

    def test_anthropic_bad_request_error(self):
        with patch.object(nlp_services.anthropic_client, "ANTHROPIC_API_KEY", "key_for_bad_req_test"), \
             patch("nlp_services.anthropic_client.Anthropic") as MockAnthropic:
            self.assertEqual(nlp_services.anthropic_client.ANTHROPIC_API_KEY, "key_for_bad_req_test") # Verify patch
            mock_client_instance = MockAnthropic.return_value

            mock_http_response = MagicMock()
            mock_http_response.status_code = 400
            mock_error_body = {'error': {'type': 'invalid_request_error', 'message': 'Bad request details'}}

            mock_error = BadRequestError(
                "Bad request",
                response=mock_http_response,
                body=mock_error_body
            )
            # mock_error.status_code = 400 # usually set by response
            # mock_error.body = {'error': {'message': 'Bad request details'}} # usually set by body
            mock_client_instance.messages.create.side_effect = mock_error

            with self.assertRaises(NLPBadRequestError) as cm:
                # Ensure the input passes client-side validation to actually trigger the API call
                # Use an empty history so the first message is the user_prompt
                nlp_services.anthropic_client.get_anthropic_chat_response([], "this should be a bad request for the API")

            self.assertIsInstance(cm.exception.original_error, BadRequestError)
            # The user_message here is the default one for NLPBadRequestError, as the mock error
            # doesn't contain "alternating user/assistant"
            self.assertEqual(cm.exception.user_message, "Ошибка в запросе к NLP сервису (Anthropic). Проверьте формат данных или обратитесь к логам.")

    def test_anthropic_bad_request_error_alternating_roles(self):
        with patch.object(nlp_services.anthropic_client, "ANTHROPIC_API_KEY", "key_for_bad_req_alt_test"), \
             patch("nlp_services.anthropic_client.Anthropic") as MockAnthropic:
            self.assertEqual(nlp_services.anthropic_client.ANTHROPIC_API_KEY, "key_for_bad_req_alt_test") # Verify patch
            mock_client_instance = MockAnthropic.return_value

            mock_http_response = MagicMock()
            mock_http_response.status_code = 400
            # This error detail should trigger the specific user message
            mock_error_body = {'error': {'type': 'invalid_request_error', 'message': "Input validation failed: messages must have alternating user/assistant roles, but found sequence user -> user."}}

            original_anthropic_error = BadRequestError(
                "Bad request with alternating roles issue",
                response=mock_http_response,
                body=mock_error_body
            )
            mock_client_instance.messages.create.side_effect = original_anthropic_error

            with self.assertRaises(NLPBadRequestError) as cm:
                nlp_services.anthropic_client.get_anthropic_chat_response([], "Test prompt")

            self.assertIsInstance(cm.exception.original_error, BadRequestError)
            self.assertEqual(cm.exception.user_message, "Ошибка в последовательности сообщений для NLP сервиса (Anthropic). Роли должны чередоваться.")


    def test_invalid_history_same_role_consecutive(self):
        with patch.object(nlp_services.anthropic_client, "ANTHROPIC_API_KEY", "key_for_history_test"):
            self.assertEqual(nlp_services.anthropic_client.ANTHROPIC_API_KEY, "key_for_history_test") # Verify patch
            history = [
                {"role": "user", "content": "Hello"},
                {"role": "user", "content": "Hello again"} # Invalid: user followed by user
            ]
            with self.assertRaisesRegex(ValueError, "Roles must alternate"):
                nlp_services.anthropic_client.get_anthropic_chat_response(history, "Test prompt")

    def test_invalid_history_starts_with_assistant(self):
        with patch.object(nlp_services.anthropic_client, "ANTHROPIC_API_KEY", "key_for_history_test_2"):
            self.assertEqual(nlp_services.anthropic_client.ANTHROPIC_API_KEY, "key_for_history_test_2") # Verify patch
            # This is valid if history is empty and user_prompt is first.
            # The check is for the *final* list of messages sent to API.
            # If history itself starts with assistant, and user_prompt makes it valid, it's okay.
            # The actual check in client: `if messages[0]["role"] == "assistant":`
            # So, if history = [{"role": "assistant", "content": "I am an assistant"}],
            # and then user_prompt = "Hi", messages becomes:
            # [{"role": "assistant", ...}, {"role": "user", ...}] -> This is an error.
            history = [{"role": "assistant", "content": "I am an assistant"}]
            with self.assertRaisesRegex(ValueError, "first message in the list cannot be from 'assistant'"):
                 nlp_services.anthropic_client.get_anthropic_chat_response(history, "User prompt")

    def test_invalid_history_user_prompt_after_user_message(self):
        with patch.object(nlp_services.anthropic_client, "ANTHROPIC_API_KEY", "key_for_history_test_3"):
            self.assertEqual(nlp_services.anthropic_client.ANTHROPIC_API_KEY, "key_for_history_test_3") # Verify patch
            history = [{"role": "user", "content": "Last message was user"}]
            # User prompt "Another user message" would follow a user message.
            with self.assertRaisesRegex(ValueError, "New user_prompt cannot follow a 'user' message"):
                nlp_services.anthropic_client.get_anthropic_chat_response(history, "Another user message")

    def test_anthropic_rate_limit_error(self):
        with patch.object(nlp_services.anthropic_client, "ANTHROPIC_API_KEY", "key_for_rate_limit_test"), \
             patch("nlp_services.anthropic_client.Anthropic") as MockAnthropic:
            self.assertEqual(nlp_services.anthropic_client.ANTHROPIC_API_KEY, "key_for_rate_limit_test") # Verify patch
            mock_client_instance = MockAnthropic.return_value

            mock_http_response = MagicMock()
            mock_http_response.status_code = 429
            mock_error_body = {'error': {'type': 'rate_limit_error', 'message': 'Rate limit exceeded'}}

            mock_error = RateLimitError(
                "Rate limit exceeded",
                response=mock_http_response,
                body=mock_error_body
            )
            mock_client_instance.messages.create.side_effect = mock_error

            with self.assertRaises(NLPRateLimitError) as cm:
                nlp_services.anthropic_client.get_anthropic_chat_response([], "Test prompt")

            self.assertIsInstance(cm.exception.original_error, RateLimitError)
            self.assertEqual(cm.exception.user_message, "Превышен лимит запросов к NLP сервису. Пожалуйста, попробуйте позже.")

    def test_anthropic_generic_api_error(self):
        with patch.object(nlp_services.anthropic_client, "ANTHROPIC_API_KEY", "key_for_generic_error_test"), \
             patch("nlp_services.anthropic_client.Anthropic") as MockAnthropic:
            self.assertEqual(nlp_services.anthropic_client.ANTHROPIC_API_KEY, "key_for_generic_error_test") # Verify patch
            mock_client_instance = MockAnthropic.return_value

            mock_http_request = MagicMock() # Simulate an httpx.Request
            mock_error_body = {'error': {'type': 'generic_error', 'message': 'A server error occurred'}}


            mock_error = APIError(
                "Generic API error",
                request=mock_http_request,
                body=mock_error_body # Add body as it seems to be required
            )
            # Attributes like status_code or body might not be standard on generic APIError
            # or could be None if the error occurred before a response was received.
            # If the SUT specifically checks e.g. e.status_code for APIError, then mock it if needed.
            # For now, the client code doesn't specifically check status_code on generic APIError instance
            # but on its more specific children. The logging for APIError was:
            # logger.error(f"Anthropic APIError (Status {e.status_code if hasattr(e, 'status_code') else 'N/A'}): {error_message}")
            # So, if we want to test that logging, we can add a status_code to the mock_error.
            # Let's assume for a generic APIError it might not have a status_code or specific body.
            # The message "Generic API error" and the request object are the main parts for its init.

            mock_client_instance.messages.create.side_effect = mock_error

            with self.assertRaises(NLPAPIError) as cm:
                nlp_services.anthropic_client.get_anthropic_chat_response([], "Test prompt")

            self.assertIsInstance(cm.exception.original_error, APIError)
            self.assertEqual(cm.exception.user_message, "Произошла непредвиденная ошибка при работе с NLP API. Попробуйте позже.")


if __name__ == "__main__":
    unittest.main()
