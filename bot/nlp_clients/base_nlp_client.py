from abc import ABC, abstractmethod

class NLPServiceError(Exception):
    """Base exception class for all NLP service-related errors."""
    def __init__(self, user_message: str, original_error: Exception | None = None):
        super().__init__(user_message)
        self.user_message = user_message
        self.original_error = original_error

    def __str__(self):
        if self.original_error:
            return f"{self.__class__.__name__}: {self.user_message} (Original error: {self.original_error})"
        return f"{self.__class__.__name__}: {self.user_message}"

class NLPAuthenticationError(NLPServiceError):
    """Raised when authentication with the NLP service fails."""
    pass

class NLPRateLimitError(NLPServiceError):
    """Raised when the NLP service rate limit is exceeded."""
    pass

class NLPBadRequestError(NLPServiceError):
    """Raised when the NLP service receives a malformed request."""
    pass

class NLPInternalServerError(NLPServiceError):
    """Raised when the NLP service encounters an internal server error."""
    pass

class NLPAPIError(NLPServiceError):
    """Generic NLP API error if a more specific error is not available."""
    pass


class BaseNLPClient(ABC):
    """
    Abstract Base Class for NLP clients.
    Defines the common interface for interacting with different NLP models/services.
    """

    def __init__(self, api_key: str = None, **kwargs):
        """
        Initializes the NLP client.

        Args:
            api_key: The API key for the NLP service. Can be None if handled otherwise (e.g., env variables).
            **kwargs: Additional keyword arguments for specific client implementations.
        """
        self.api_key = api_key
        # Allow subclasses to handle other kwargs as needed
        for key, value in kwargs.items():
            setattr(self, key, value)

    @abstractmethod
    def generate_text(self, prompt: str, max_tokens: int = 1024, temperature: float = 0.7, **kwargs) -> str:
        """
        Generates text based on a given prompt.

        Args:
            prompt: The input text prompt.
            max_tokens: The maximum number of tokens to generate.
            temperature: The sampling temperature for generation (creativity vs. coherence).
            **kwargs: Additional keyword arguments for specific model parameters.

        Returns:
            The generated text as a string.

        Raises:
            NLPServiceError or its subclasses for API-related issues.
        """
        pass

    @abstractmethod
    def close(self):
        """
        Closes the client and releases any resources.
        This method should be idempotent.
        """
        pass

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
        return False # Do not suppress exceptions

# Example of how a concrete client might use it (for illustration, not to be run directly here)
# class ConcreteNLPClient(BaseNLPClient):
#     def __init__(self, api_key: str, model_name: str = "default-model"):
#         super().__init__(api_key=api_key, model_name=model_name)
#         if not self.api_key:
#             raise ValueError("API key is required for ConcreteNLPClient")
#         # Initialize connection or client library specific to this service
#         print(f"ConcreteNLPClient initialized with model: {self.model_name}")

#     def generate_text(self, prompt: str, max_tokens: int = 100, temperature: float = 0.7, **kwargs) -> str:
#         # Actual implementation for generating text using a specific service
#         print(f"Generating text for prompt: '{prompt}' with {max_tokens} tokens, temp {temperature}")
#         # Simulate API call
#         if "error" in prompt:
#             raise NLPAPIError("Simulated API error occurred.")
#         return f"Generated text for '{prompt}'"

#     def close(self):
#         # Clean up resources, close connections, etc.
#         print("ConcreteNLPClient closed.")
#         pass
