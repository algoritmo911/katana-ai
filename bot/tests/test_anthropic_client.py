import pytest
from bot.nlp_clients.anthropic_client import (
    AnthropicClient,
    AnthropicAPIError,
    AnthropicAuthenticationError,
    AnthropicInvalidRequestError,
    AnthropicInternalServerError,
    AnthropicRateLimitError,
    AnthropicClientError, # Base for Anthropic specific errors
)
from bot.nlp_clients.base_nlp_client import (
    NLPServiceError, # General base for all NLP errors
    NLPAuthenticationError,
    NLPRateLimitError,
    NLPBadRequestError,
    NLPInternalServerError,
    NLPAPIError,
)

class TestAnthropicClientErrorHandling:
    """
    Tests for error handling in the AnthropicClient.
    """

    def test_missing_api_key_raises_authentication_error(self):
        """
        Verifies that initializing client without an API key raises AnthropicAuthenticationError.
        """
        with pytest.raises(AnthropicAuthenticationError) as excinfo:
            AnthropicClient(api_key="")
        assert "Anthropic API key is missing" in excinfo.value.user_message
        assert excinfo.value.original_error is None # No underlying error in this case

    def test_generate_text_success(self):
        """
        Tests a successful call to generate_text.
        """
        client = AnthropicClient(api_key="fake_key")
        prompt = "Test prompt"
        response = client.generate_text(prompt, scenario="success")
        assert response == f"Anthropic processed prompt: '{prompt}' successfully."

    @pytest.mark.parametrize(
        "scenario, expected_exception, expected_user_message_part, original_error_type",
        [
            ("auth_error", AnthropicAuthenticationError, "Authentication failed", RuntimeError),
            ("rate_limit", AnthropicRateLimitError, "Rate limit exceeded", ValueError),
            ("bad_request", AnthropicInvalidRequestError, "Invalid request", TypeError),
            ("server_error", AnthropicInternalServerError, "internal server error", ConnectionError),
            ("api_error", AnthropicAPIError, "unexpected error occurred with the Anthropic API", IOError),
            ("unexpected_error", AnthropicAPIError, "unexpected internal error occurred", Exception),
        ],
    )
    def test_generate_text_simulated_errors(
        self, scenario, expected_exception, expected_user_message_part, original_error_type
    ):
        """
        Tests various simulated error scenarios in generate_text.
        Verifies that the correct custom exception is raised with appropriate attributes.
        """
        client = AnthropicClient(api_key="fake_key")
        with pytest.raises(expected_exception) as excinfo:
            client.generate_text("Test prompt", scenario=scenario)

        assert isinstance(excinfo.value, AnthropicClientError) # Check it's an Anthropic error
        assert isinstance(excinfo.value, NLPServiceError)    # And also an NLPServiceError
        assert expected_user_message_part.lower() in excinfo.value.user_message.lower()
        assert excinfo.value.original_error is not None
        assert isinstance(excinfo.value.original_error, original_error_type)
        if scenario == "unexpected_error":
             assert "A very unexpected problem occurred!" in str(excinfo.value.original_error)


    def test_unknown_scenario_raises_api_error(self):
        """
        Tests that an unknown scenario falls back to AnthropicAPIError.
        """
        client = AnthropicClient(api_key="fake_key")
        with pytest.raises(AnthropicAPIError) as excinfo:
            client.generate_text("Test prompt", scenario="non_existent_scenario")

        assert "Unknown simulation scenario" in excinfo.value.user_message
        assert isinstance(excinfo.value.original_error, ValueError)

    def test_all_anthropic_exceptions_have_user_message_and_original_error(self):
        """
        Checks that all defined Anthropic exceptions can be instantiated with
        user_message and original_error and that these attributes are set.
        """
        custom_errors = [
            AnthropicAPIError,
            AnthropicAuthenticationError,
            AnthropicInvalidRequestError,
            AnthropicInternalServerError,
            AnthropicRateLimitError,
            AnthropicClientError, # Test the base Anthropic error too
        ]
        dummy_original_error = ValueError("Original issue")
        user_msg = "Test user message"

        for error_cls in custom_errors:
            # Test with original_error
            try:
                raise error_cls(user_message=user_msg, original_error=dummy_original_error)
            except NLPServiceError as e: # Catching NLPServiceError as it's the ultimate base with these args
                assert e.user_message == user_msg, f"{error_cls.__name__} did not set user_message correctly."
                assert e.original_error is dummy_original_error, f"{error_cls.__name__} did not set original_error correctly."
                assert isinstance(e, AnthropicClientError) or error_cls is AnthropicClientError

            # Test without original_error (should be None)
            try:
                raise error_cls(user_message=user_msg)
            except NLPServiceError as e:
                assert e.user_message == user_msg, f"{error_cls.__name__} did not set user_message correctly (no original_error)."
                assert e.original_error is None, f"{error_cls.__name__} did not set original_error to None (no original_error)."
                assert isinstance(e, AnthropicClientError) or error_cls is AnthropicClientError

    def test_anthropic_exception_inheritance(self):
        """
        Verifies the inheritance chain for Anthropic exceptions.
        """
        assert issubclass(AnthropicAuthenticationError, AnthropicClientError)
        assert issubclass(AnthropicAuthenticationError, NLPAuthenticationError)
        assert issubclass(AnthropicRateLimitError, AnthropicClientError)
        assert issubclass(AnthropicRateLimitError, NLPRateLimitError)
        assert issubclass(AnthropicInvalidRequestError, AnthropicClientError)
        assert issubclass(AnthropicInvalidRequestError, NLPBadRequestError)
        assert issubclass(AnthropicInternalServerError, AnthropicClientError)
        assert issubclass(AnthropicInternalServerError, NLPInternalServerError)
        assert issubclass(AnthropicAPIError, AnthropicClientError)
        assert issubclass(AnthropicAPIError, NLPAPIError)
        assert issubclass(AnthropicClientError, NLPServiceError)

# To run these tests, you would typically use pytest from your terminal
# in the root directory of the project:
# pytest bot/tests/test_anthropic_client.py
