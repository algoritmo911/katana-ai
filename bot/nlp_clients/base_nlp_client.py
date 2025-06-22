class NLPServiceError(Exception):
    """Base exception class for all NLP service-related errors."""
    def __init__(self, user_message: str = "Произошла ошибка при обращении к NLP сервису.", original_error: Exception | None = None):
        super().__init__(user_message)
        self.user_message = user_message
        self.original_error = original_error

    def __str__(self):
        if self.original_error:
            return f"{self.__class__.__name__}: {self.user_message} (Original error: {type(self.original_error).__name__} - {self.original_error})"
        return f"{self.__class__.__name__}: {self.user_message}"

class NLPAuthenticationError(NLPServiceError):
    """Raised when authentication with the NLP service fails."""
    def __init__(self, user_message: str = "Ошибка аутентификации с NLP сервисом. Проверьте ваш API-ключ.", original_error: Exception | None = None):
        super().__init__(user_message, original_error)

class NLPRateLimitError(NLPServiceError):
    """Raised when the NLP service rate limit is exceeded."""
    def __init__(self, user_message: str = "Сервис NLP временно перегружен (лимит запросов). Попробуйте позже.", original_error: Exception | None = None):
        super().__init__(user_message, original_error)

class NLPBadRequestError(NLPServiceError):
    """Raised when the NLP service receives a malformed request."""
    def __init__(self, user_message: str = "Некорректный запрос к NLP сервису. Пожалуйста, проверьте данные.", original_error: Exception | None = None):
        super().__init__(user_message, original_error)

class NLPInternalServerError(NLPServiceError):
    """Raised when the NLP service encounters an internal server error."""
    def __init__(self, user_message: str = "Внутренняя ошибка NLP сервиса. Попробуйте позже.", original_error: Exception | None = None):
        super().__init__(user_message, original_error)

class NLPAPIError(NLPServiceError):
    """Generic NLP API error if a more specific error is not available."""
    def __init__(self, user_message: str = "Произошла непредвиденная ошибка при работе с NLP сервисом.", original_error: Exception | None = None):
        super().__init__(user_message, original_error)
