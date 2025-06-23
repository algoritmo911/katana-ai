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

import abc
import typing

class AbstractLLMClient(abc.ABC):
    """
    Abstract Base Class for Large Language Model (LLM) clients.
    Defines the common interface for interacting with different LLM providers.
    """

    @abc.abstractmethod
    def generate_response(self, prompt: str, history: list[dict] | None = None, **kwargs) -> str:
        """
        Generates a single text response from the LLM.

        Args:
            prompt: The user's prompt.
            history: A list of previous messages in the conversation, if any.
                     Each message is a dict with 'role' and 'content' keys.
            **kwargs: Additional provider-specific parameters.

        Returns:
            The LLM's response as a string.

        Raises:
            NLPServiceError: If an error occurs during the API call.
        """
        pass

    @abc.abstractmethod
    async def stream_response(
        self, prompt: str, history: list[dict] | None = None, **kwargs
    ) -> typing.AsyncIterator[str]:
        """
        Generates a response from the LLM as an asynchronous stream of text chunks.

        Args:
            prompt: The user's prompt.
            history: A list of previous messages in the conversation, if any.
            **kwargs: Additional provider-specific parameters.

        Yields:
            Text chunks from the LLM's response.

        Raises:
            NLPServiceError: If an error occurs during the API call.
        """
        # This construct is necessary because abstract async generators cannot be empty
        # and must yield something.
        if False: # pylint: disable=using-constant-test
            yield ""
