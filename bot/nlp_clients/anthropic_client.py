from .base_nlp_client import (
    NLPAPIError,
    NLPAuthenticationError,
    NLPBadRequestError,
    NLPInternalServerError,
    NLPRateLimitError,
    NLPServiceError,
)

# Anthropic Specific Exceptions
class AnthropicClientError(NLPServiceError):
    """Base exception for all Anthropic client errors."""
    def __init__(self, user_message: str = "Произошла ошибка при обращении к Anthropic.", original_error: Exception | None = None):
        super().__init__(user_message, original_error)

class AnthropicAPIError(AnthropicClientError, NLPAPIError):
    """Generic Anthropic API error."""
    def __init__(self, user_message: str = "Произошла непредвиденная ошибка API Anthropic.", original_error: Exception | None = None):
        # Call NLPAPIError's __init__ which then calls NLPServiceError's __init__
        NLPAPIError.__init__(self, user_message=user_message, original_error=original_error)
        # Ensure AnthropicClientError part of MRO is also handled if it had its own __init__ logic (it doesn't here beyond NLPServiceError)

class AnthropicAuthenticationError(AnthropicClientError, NLPAuthenticationError):
    """Raised for Anthropic authentication failures."""
    def __init__(self, user_message: str = "Ошибка аутентификации с Anthropic. Проверьте ваш API-ключ.", original_error: Exception | None = None):
        NLPAuthenticationError.__init__(self, user_message=user_message, original_error=original_error)

class AnthropicRateLimitError(AnthropicClientError, NLPRateLimitError):
    """Raised for Anthropic rate limit errors."""
    def __init__(self, user_message: str = "Сервис Anthropic временно перегружен (лимит запросов). Попробуйте позже.", original_error: Exception | None = None):
        NLPRateLimitError.__init__(self, user_message=user_message, original_error=original_error)

class AnthropicInvalidRequestError(AnthropicClientError, NLPBadRequestError):
    """Raised for invalid requests to the Anthropic API."""
    def __init__(self, user_message: str = "Некорректный запрос к Anthropic. Пожалуйста, проверьте данные.", original_error: Exception | None = None):
        NLPBadRequestError.__init__(self, user_message=user_message, original_error=original_error)

class AnthropicInternalServerError(AnthropicClientError, NLPInternalServerError):
    """Raised for Anthropic internal server errors."""
    def __init__(self, user_message: str = "Внутренняя ошибка сервера Anthropic. Попробуйте позже.", original_error: Exception | None = None):
        NLPInternalServerError.__init__(self, user_message=user_message, original_error=original_error)


class AnthropicClient:
    """
    A basic client for interacting with a simulated Anthropic API.
    This is intended for demonstrating error handling.
    """
    def __init__(self, api_key: str = "dummy_anthropic_key"):
        if not api_key:
            raise AnthropicAuthenticationError(user_message="Anthropic API key is missing.")
        self.api_key = api_key

    def generate_text(self, prompt: str, scenario: str = "success"):
        """
        Simulates generating text using the Anthropic API.

        Args:
            prompt: The input prompt.
            scenario: A string to simulate different API responses for testing.
                      Can be "success", "auth_error", "rate_limit",
                      "bad_request", "server_error", "api_error", "unexpected_error".

        Returns:
            A simulated successful response string.

        Raises:
            AnthropicAuthenticationError: If scenario is "auth_error".
            AnthropicRateLimitError: If scenario is "rate_limit".
            AnthropicInvalidRequestError: If scenario is "bad_request".
            AnthropicInternalServerError: If scenario is "server_error".
            AnthropicAPIError: If scenario is "api_error" or "unexpected_error".
        """
        if scenario == "auth_error":
            raise AnthropicAuthenticationError(
                user_message="Authentication failed. Check your Anthropic API key.",
                original_error=RuntimeError("Simulated upstream auth failure")
            )
        elif scenario == "rate_limit":
            raise AnthropicRateLimitError(
                user_message="Rate limit exceeded for Anthropic API.",
                original_error=ValueError("Simulated upstream rate limit")
            )
        elif scenario == "bad_request":
            raise AnthropicInvalidRequestError(
                user_message="Invalid request sent to Anthropic API.",
                original_error=TypeError("Simulated upstream bad request")
            )
        elif scenario == "server_error":
            raise AnthropicInternalServerError(
                user_message="Anthropic API encountered an internal server error.",
                original_error=ConnectionError("Simulated upstream server error")
            )
        elif scenario == "api_error":
            raise AnthropicAPIError(
                user_message="An unexpected error occurred with the Anthropic API.",
                original_error=IOError("Simulated generic API issue")
            )
        elif scenario == "unexpected_error":
            # Simulate an error that isn't one of the directly mapped ones
            try:
                # pylint: disable=broad-exception-raised
                raise Exception("A very unexpected problem occurred!")
            except Exception as e:
                raise AnthropicAPIError(
                    user_message="An unexpected internal error occurred while processing your request with Anthropic.",
                    original_error=e
                )
        elif scenario == "success":
            return f"Anthropic processed prompt: '{prompt}' successfully."
        else:
            # Should not happen with defined scenarios, but good for robustness
            raise AnthropicAPIError(
                user_message=f"Unknown simulation scenario: {scenario}",
                original_error=ValueError(f"Unknown scenario: {scenario}")
            )

if __name__ == '__main__':
    # Example Usage (for quick testing, real tests will be separate)
    client = AnthropicClient(api_key="test_key")

    print("Simulating success:")
    try:
        response = client.generate_text("Hello world", scenario="success")
        print(f"  Response: {response}")
    except AnthropicClientError as e:
        print(f"  Error: {e}")
        if e.original_error:
            print(f"  Original error: {type(e.original_error)} - {e.original_error}")
    print("-" * 20)

    scenarios_to_test = [
        "auth_error", "rate_limit", "bad_request",
        "server_error", "api_error", "unexpected_error"
    ]

    for scen in scenarios_to_test:
        print(f"Simulating {scen}:")
        try:
            client.generate_text("Test prompt", scenario=scen)
        except AnthropicClientError as e:
            print(f"  Caught: {e.user_message}")
            print(f"  Type: {type(e).__name__}")
            if e.original_error:
                print(f"  Original error: {type(e.original_error).__name__} - {str(e.original_error)}")
        print("-" * 20)

    print("Simulating missing API key:")
    try:
        AnthropicClient(api_key="")
    except AnthropicAuthenticationError as e:
        print(f"  Caught: {e.user_message}")
        print(f"  Type: {type(e).__name__}")
    print("-" * 20)
