"""Friendly exceptions raised by the Lexara Python SDK."""

from __future__ import annotations


class LexaraError(Exception):
    """Base error for Lexara SDK failures."""

    def __init__(
        self,
        message: str,
        *,
        status_code: int | None = None,
        code: str = "error",
        details: dict | None = None,
    ) -> None:
        self.message = message
        self.status_code = status_code
        self.code = code
        self.details = details
        super().__init__(message)

    def __str__(self) -> str:
        if self.status_code is not None:
            return f"[{self.status_code} {self.code}] {self.message}"
        return f"[{self.code}] {self.message}"


class AuthenticationError(LexaraError):
    """Invalid or missing API key (HTTP 401)."""

    def __init__(
        self,
        message: str = "Invalid API key.",
        *,
        details: dict | None = None,
    ) -> None:
        super().__init__(
            message, status_code=401, code="unauthorized", details=details
        )


class ValidationError(LexaraError):
    """Request failed validation (HTTP 422)."""

    def __init__(
        self,
        message: str = "Request validation failed.",
        *,
        details: dict | None = None,
    ) -> None:
        super().__init__(
            message, status_code=422, code="validation_error", details=details
        )


class LexaraAPIError(LexaraError):
    """Non-retryable API error (4xx/5xx with a structured error body)."""


class LexaraTimeoutError(LexaraError):
    """Request timed out waiting for the Lexara API."""

    def __init__(self, message: str = "Request to Lexara timed out.") -> None:
        super().__init__(message, code="timeout")


class LexaraConnectionError(LexaraError):
    """Network error reaching the Lexara API."""

    def __init__(self, message: str = "Could not connect to Lexara.") -> None:
        super().__init__(message, code="connection_error")


def raise_for_response(status_code: int, code: str, message: str, details: dict | None) -> None:
    """Map an API error envelope to a typed SDK exception."""
    if status_code == 401:
        raise AuthenticationError(message, details=details)
    if status_code == 422:
        raise ValidationError(message, details=details)
    raise LexaraAPIError(
        message, status_code=status_code, code=code, details=details
    )
