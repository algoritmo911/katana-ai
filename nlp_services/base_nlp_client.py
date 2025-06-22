# Placeholder for Base NLP Client (Interface/Abstract Class)
from abc import ABC, abstractmethod
import logging

logger = logging.getLogger(__name__)

class BaseNLPClient(ABC):
    """
    Abstract base class for NLP clients.
    Defines a common interface for interacting with different NLP services.
    """

    def __init__(self, api_key: str, default_model: str):
        if not api_key:
            logger.error(f"{self.__class__.__name__}: API key is missing.")
            raise ValueError("API key must be provided.")
        self.api_key = api_key
        self.default_model = default_model
        logger.info(f"{self.__class__.__name__} initialized.")

    @abstractmethod
    def get_chat_response(self, history: list, user_prompt: str, model_name: str = None) -> str:
        """
        Gets a chat response from the NLP service.

        Args:
            history: A list of previous messages in the conversation.
                     Format may vary slightly based on the specific service,
                     but generally a list of dicts with "role" and "content".
            user_prompt: The user's current prompt.
            model_name: The specific model to use. If None, uses the client's default model.

        Returns:
            The assistant's response message content.

        Raises:
            NotImplementedError: If the method is not implemented by a subclass.
            ConnectionError: If there's an issue connecting to the NLP service.
            AuthenticationError: If there's an issue with API key authentication.
            InvalidRequestError: If the request is malformed or invalid.
            RateLimitError: If the API rate limit has been exceeded.
            APIError: For other API related errors.
        """
        pass

    @abstractmethod
    def count_tokens(self, text: str, model_name: str = None) -> int:
        """
        Counts the number of tokens in a given text for a specific model.

        Args:
            text: The text to tokenize.
            model_name: The specific model to use for token counting. If None, uses the client's default.

        Returns:
            The number of tokens.
        """
        pass

    def _prepare_messages(self, history: list, user_prompt: str) -> list:
        """
        Helper method to prepare messages in a standard format.
        Subclasses might override this if their API expects a different format.
        """
        messages = []
        for msg in history:
            if isinstance(msg, dict) and "role" in msg and "content" in msg:
                messages.append({"role": msg["role"], "content": msg["content"]})
            else:
                logger.warning(f"Skipping malformed message in history: {msg}")
        messages.append({"role": "user", "content": user_prompt})
        return messages

# Example of how you might want to define custom exceptions,
# though for now, we'll rely on re-raising specific exceptions from libraries
# or the generic ones mentioned in the docstring.

# Custom NLP Exceptions

class NLPServiceError(Exception):
    """Base class for NLP service related errors."""
    def __init__(self, message="An NLP service error occurred.", original_error=None, user_message=None):
        super().__init__(message)
        self.original_error = original_error
        self.user_message = user_message or "Произошла ошибка при обращении к NLP сервису. Пожалуйста, попробуйте позже."
        # Log the creation of this error, perhaps? Or leave logging to the point of raising.
        # logger.error(f"NLPServiceError created: {message}, Original: {original_error}")

    def __str__(self):
        if self.original_error:
            return f"{super().__str__()} (Original error: {str(self.original_error)})"
        return super().__str__()

class NLPAuthenticationError(NLPServiceError):
    """Error for authentication issues with the NLP service."""
    def __init__(self, message="NLP service authentication failed.", original_error=None, user_message=None):
        super().__init__(
            message,
            original_error,
            user_message or "Ошибка аутентификации с NLP сервисом. Проверьте API ключ или обратитесь к администратору."
        )

class NLPBadRequestError(NLPServiceError):
    """Error for bad requests sent to the NLP service (e.g., malformed input)."""
    def __init__(self, message="NLP service received a bad request.", original_error=None, user_message=None):
        super().__init__(
            message,
            original_error,
            user_message or "Ошибка в запросе к NLP сервису. Возможно, данные некорректны."
        )

class NLPRateLimitError(NLPServiceError):
    """Error for exceeding API rate limits."""
    def __init__(self, message="NLP service rate limit exceeded.", original_error=None, user_message=None):
        super().__init__(
            message,
            original_error,
            user_message or "Превышен лимит запросов к NLP сервису. Пожалуйста, попробуйте позже."
        )

class NLPAPIError(NLPServiceError):
    """Generic error from the NLP service's API."""
    def __init__(self, message="An error occurred with the NLP service API.", original_error=None, user_message=None):
        super().__init__(
            message,
            original_error,
            user_message or "Произошла непредвиденная ошибка при работе с NLP API. Попробуйте позже."
        )

class NLPTimeoutError(NLPServiceError):
    """Error for timeouts when communicating with the NLP service."""
    def __init__(self, message="NLP service request timed out.", original_error=None, user_message=None):
        super().__init__(
            message,
            original_error,
            user_message or "Время ожидания ответа от NLP сервиса истекло. Пожалуйста, попробуйте позже."
        )
