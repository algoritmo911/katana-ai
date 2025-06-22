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
