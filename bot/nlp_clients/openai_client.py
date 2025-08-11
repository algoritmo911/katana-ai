from .base_nlp_client import (
    NLPAPIError,
    NLPAuthenticationError,
    NLPBadRequestError,
    NLPInternalServerError,
    NLPRateLimitError,
    NLPServiceError,
)

# OpenAI Specific Exceptions
class OpenAIClientError(NLPServiceError):
    """Base exception for all OpenAI client errors."""
    pass

class OpenAIAPIError(OpenAIClientError, NLPAPIError):
    """Generic OpenAI API error."""
    pass

class OpenAIAuthenticationError(OpenAIClientError, NLPAuthenticationError):
    """Raised for OpenAI authentication failures."""
    pass

class OpenAIRateLimitError(OpenAIClientError, NLPRateLimitError):
    """Raised for OpenAI rate limit errors."""
    pass

class OpenAIInvalidRequestError(OpenAIClientError, NLPBadRequestError):
    """Raised for invalid requests to the OpenAI API."""
    pass

class OpenAIInternalServerError(OpenAIClientError, NLPInternalServerError):
    """Raised for OpenAI internal server errors."""
    pass


import os
from openai import OpenAI, RateLimitError, AuthenticationError, APIError, BadRequestError

class OpenAIClient:
    """
    A client for interacting with the OpenAI API.
    """
    def __init__(self, api_key: str = None):
        api_key = api_key or os.environ.get("OPENAI_API_KEY")
        if not api_key:
            raise OpenAIAuthenticationError(user_message="OpenAI API key is missing.")
        self.client = OpenAI(api_key=api_key)

    def generate_text(self, prompt: str, model: str = "gpt-3.5-turbo", max_tokens: int = 500):
        """
        Generates text using the OpenAI API.

        Args:
            prompt: The input prompt.
            model: The model to use for generation.
            max_tokens: The maximum number of tokens to generate.

        Returns:
            The generated text.

        Raises:
            OpenAIAuthenticationError: For authentication failures.
            OpenAIRateLimitError: For rate limit errors.
            OpenAIInvalidRequestError: For invalid requests.
            OpenAIInternalServerError: For OpenAI internal server errors.
            OpenAIAPIError: For other generic API errors.
        """
        try:
            response = self.client.chat.completions.create(
                model=model,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=max_tokens,
            )
            return response.choices[0].message.content.strip()
        except AuthenticationError as e:
            raise OpenAIAuthenticationError(user_message="OpenAI authentication failed.", original_error=e)
        except RateLimitError as e:
            raise OpenAIRateLimitError(user_message="OpenAI rate limit exceeded.", original_error=e)
        except BadRequestError as e:
            raise OpenAIInvalidRequestError(user_message=f"Invalid request to OpenAI: {e}", original_error=e)
        except APIError as e:
            # This can be a generic catch-all for other 5xx errors
            raise OpenAIInternalServerError(user_message=f"OpenAI API returned an error: {e}", original_error=e)
        except Exception as e:
            raise OpenAIAPIError(user_message=f"An unexpected error occurred with OpenAI: {e}", original_error=e)

if __name__ == '__main__':
    # Example Usage (for quick testing)
    print("Simulating OpenAI client:")
    try:
        client = OpenAIClient(api_key="test_openai_key")
        response = client.generate_text("Hello from OpenAI", scenario="success")
        print(f"  Response: {response}")
    except OpenAIClientError as e:
        print(f"  Error: {e}")

    try:
        client = OpenAIClient(api_key="test_openai_key")
        client.generate_text("Test auth error", scenario="auth_error")
    except OpenAIAuthenticationError as e:
        print(f"  Caught expected auth error: {e.user_message}")
        if e.original_error:
            print(f"  Original error: {type(e.original_error).__name__} - {str(e.original_error)}")

    try:
        OpenAIClient(api_key="")
    except OpenAIAuthenticationError as e:
        print(f"  Caught missing API key: {e.user_message}")
