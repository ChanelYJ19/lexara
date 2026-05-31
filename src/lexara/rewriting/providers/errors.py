"""Provider errors surfaced to the rewrite pipeline."""

from __future__ import annotations


class ProviderError(Exception):
    """LLM provider failure; the pipeline may skip the pass and continue."""

    def __init__(
        self,
        message: str,
        *,
        code: str = "provider_error",
        retryable: bool = False,
        details: dict | None = None,
    ) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.retryable = retryable
        self.details = details or {}


class ProviderParseError(ProviderError):
    def __init__(self, message: str, *, details: dict | None = None) -> None:
        super().__init__(
            message, code="provider_parse_error", retryable=False, details=details
        )


class ProviderTimeoutError(ProviderError):
    def __init__(self, message: str, *, details: dict | None = None) -> None:
        super().__init__(
            message, code="provider_timeout", retryable=True, details=details
        )
