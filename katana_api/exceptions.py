from fastapi import HTTPException
from starlette.requests import Request
from starlette.responses import JSONResponse
from .schemas import ErrorDetailSchema, ErrorResponseSchema

class KatanaAPIException(Exception):
    """Base exception class for the Katana API."""
    def __init__(self, status_code: int, code: str, message: str):
        self.status_code = status_code
        self.code = code
        self.message = message
        super().__init__(message)

class OrchestratorError(KatanaAPIException):
    """Custom exception for errors related to the orchestrator."""
    def __init__(self, message: str = "An orchestrator-related error occurred."):
        super().__init__(
            status_code=500,
            code="orchestrator_error",
            message=message
        )

# --- Exception Handlers ---

async def http_exception_handler(request: Request, exc: HTTPException):
    """
    Handles FastAPI's built-in HTTPException to conform to our standardized error format.
    """
    error_detail = ErrorDetailSchema(
        code=getattr(exc, "code", "http_exception"), # Use custom code if provided
        message=exc.detail
    )
    return JSONResponse(
        status_code=exc.status_code,
        content=ErrorResponseSchema(error=error_detail).dict(),
        headers=getattr(exc, "headers", None)
    )

async def katana_api_exception_handler(request: Request, exc: KatanaAPIException):
    """
    Handles custom exceptions derived from KatanaAPIException.
    """
    error_detail = ErrorDetailSchema(code=exc.code, message=exc.message)
    return JSONResponse(
        status_code=exc.status_code,
        content=ErrorResponseSchema(error=error_detail).dict()
    )

async def generic_exception_handler(request: Request, exc: Exception):
    """
    Handles any other unhandled exception to prevent leaking stack traces.
    """
    error_detail = ErrorDetailSchema(
        code="internal_server_error",
        message="An unexpected internal server error occurred."
    )
    return JSONResponse(
        status_code=500,
        content=ErrorResponseSchema(error=error_detail).dict()
    )
