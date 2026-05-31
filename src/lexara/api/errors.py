"""Domain exceptions and FastAPI exception handlers producing the error envelope."""

from __future__ import annotations

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from lexara.logging_config import get_logger, get_request_id
from lexara.models.errors import ErrorBody, ErrorResponse

logger = get_logger(__name__)


class LexaraError(Exception):
    """Base class for errors that map to a structured HTTP response."""

    status_code: int = status.HTTP_400_BAD_REQUEST
    code: str = "bad_request"

    def __init__(self, message: str, details: dict | None = None) -> None:
        super().__init__(message)
        self.message = message
        self.details = details


class AuthenticationError(LexaraError):
    status_code = status.HTTP_401_UNAUTHORIZED
    code = "unauthorized"


# 422 spelled as a literal to stay compatible across Starlette versions
# (the named constant was renamed and deprecation-warns on newer releases).
HTTP_422 = 422


class ValidationError(LexaraError):
    status_code = HTTP_422
    code = "validation_error"


def _envelope(status_code: int, code: str, message: str, details: dict | None):
    body = ErrorResponse(
        error=ErrorBody(code=code, message=message, details=details),
        request_id=get_request_id(),
    )
    return JSONResponse(status_code=status_code, content=body.model_dump())


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(LexaraError)
    async def _handle_lexara(_: Request, exc: LexaraError):
        return _envelope(exc.status_code, exc.code, exc.message, exc.details)

    @app.exception_handler(RequestValidationError)
    async def _handle_validation(_: Request, exc: RequestValidationError):
        return _envelope(
            HTTP_422,
            "validation_error",
            "Request validation failed.",
            {"errors": exc.errors()},
        )

    @app.exception_handler(Exception)
    async def _handle_unexpected(_: Request, exc: Exception):
        logger.error("unhandled error", exc_info=exc)
        return _envelope(
            status.HTTP_500_INTERNAL_SERVER_ERROR,
            "internal_error",
            "An unexpected error occurred.",
            None,
        )
