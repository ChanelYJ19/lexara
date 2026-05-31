"""OpenAI provider (alpha-hardened).

Features: client reuse, timeouts, retries on transient errors, JSON response
format, failure-safe parsing, and token/cost logging hooks.
"""

from __future__ import annotations

from lexara.logging_config import get_logger
from lexara.rewriting.providers.base import (
    LLMProvider,
    ProviderResult,
    ProviderUsage,
    RewriteInstruction,
    UsageLogger,
)
from lexara.rewriting.providers.errors import (
    ProviderError,
    ProviderParseError,
    ProviderTimeoutError,
)
from lexara.rewriting.providers.parsing import parse_rewrite_text
from lexara.rewriting.providers.retry import call_with_retries
from lexara.rewriting.providers.usage import attach_cost, default_usage_logger, log_provider_failure

logger = get_logger(__name__)

_TRANSIENT: tuple[type[BaseException], ...] = ()
_TIMEOUT: tuple[type[BaseException], ...] = ()


def _openai_error_types() -> tuple[
    tuple[type[BaseException], ...], tuple[type[BaseException], ...]
]:
    global _TRANSIENT, _TIMEOUT
    if _TRANSIENT:
        return _TRANSIENT, _TIMEOUT
    try:
        from openai import APIConnectionError, APITimeoutError, RateLimitError

        _TIMEOUT = (APITimeoutError,)
        _TRANSIENT = (APITimeoutError, APIConnectionError, RateLimitError)
    except ImportError:
        _TIMEOUT = (TimeoutError,)
        _TRANSIENT = (TimeoutError, ConnectionError)
    return _TRANSIENT, _TIMEOUT


def _retry_after_seconds(exc: BaseException) -> float | None:
    response = getattr(exc, "response", None)
    headers = getattr(response, "headers", None)
    if headers is None:
        return None
    raw = headers.get("retry-after") or headers.get("Retry-After")
    if raw is None:
        return None
    try:
        return max(float(raw), 0.0)
    except (TypeError, ValueError):
        return None


class OpenAIProvider(LLMProvider):
    name = "openai"

    def __init__(
        self,
        api_key: str,
        model: str = "gpt-4o-mini",
        *,
        timeout_seconds: float = 60.0,
        max_retries: int = 2,
        max_completion_tokens: int = 4096,
        usage_logger: UsageLogger | None = None,
    ) -> None:
        if not api_key:
            raise ValueError("OpenAI API key is required for the openai provider.")
        self._api_key = api_key
        self._model = model
        self._timeout = timeout_seconds
        self._max_retries = max(0, max_retries)
        self._max_completion_tokens = max(256, max_completion_tokens)
        self._usage_logger = usage_logger or default_usage_logger(self.name)
        self._client = None

    def _get_client(self):
        if self._client is not None:
            return self._client
        try:
            from openai import OpenAI
        except ImportError as exc:  # pragma: no cover
            raise RuntimeError(
                "openai package not installed. Run: pip install 'lexara[openai]'"
            ) from exc
        self._client = OpenAI(
            api_key=self._api_key,
            timeout=self._timeout,
            max_retries=0,  # Lexara owns retry policy (vendor-agnostic)
        )
        return self._client

    def complete(self, instruction: RewriteInstruction) -> ProviderResult:
        transient, timeout_types = _openai_error_types()

        def _is_retryable(exc: BaseException) -> bool:
            if isinstance(exc, ProviderTimeoutError):
                return True
            if isinstance(exc, ProviderError):
                return exc.retryable
            return isinstance(exc, transient)

        def _on_retry(attempt: int, exc: BaseException) -> float | None:
            log_provider_failure(
                self.name,
                model=self._model,
                attempt=attempt,
                error=exc,
            )
            return _retry_after_seconds(exc)

        try:
            return call_with_retries(
                lambda: self._call_once(instruction),
                max_retries=self._max_retries,
                is_retryable=_is_retryable,
                on_retry=_on_retry,
            )
        except ProviderError:
            raise
        except timeout_types as exc:
            raise ProviderTimeoutError(
                f"OpenAI request timed out after {self._timeout:g}s.",
                details={"exception": type(exc).__name__},
            ) from exc
        except transient as exc:
            raise ProviderError(
                f"OpenAI transient error: {exc}",
                code="provider_transient_error",
                retryable=True,
                details={"exception": type(exc).__name__},
            ) from exc
        except Exception as exc:
            raise ProviderError(
                f"OpenAI request failed: {exc}",
                code="provider_error",
                details={"exception": type(exc).__name__},
            ) from exc

    def _call_once(self, instruction: RewriteInstruction) -> ProviderResult:
        client = self._get_client()
        transient, timeout_types = _openai_error_types()

        try:
            response = client.chat.completions.create(
                model=self._model,
                temperature=0.4,
                max_tokens=self._max_completion_tokens,
                response_format={"type": "json_object"},
                messages=[
                    {"role": "system", "content": instruction.system_prompt},
                    {"role": "user", "content": instruction.user_prompt},
                ],
            )
        except timeout_types as exc:
            raise ProviderTimeoutError(
                f"OpenAI request timed out after {self._timeout:g}s.",
                details={"exception": type(exc).__name__},
            ) from exc
        except transient:
            raise
        except Exception as exc:
            raise ProviderError(
                f"OpenAI request failed: {exc}",
                code="provider_error",
                details={"exception": type(exc).__name__},
            ) from exc

        if not response.choices:
            raise ProviderParseError(
                "OpenAI returned no completion choices.",
                details={"model": response.model or self._model},
            )

        choice = response.choices[0]
        finish_reason = getattr(choice, "finish_reason", None)
        if finish_reason == "length":
            raise ProviderParseError(
                "OpenAI response was truncated (finish_reason=length).",
                details={"model": response.model or self._model},
            )

        raw = (choice.message.content or "").strip()
        text = self._parse_response_text(raw)

        usage = response.usage
        result = ProviderResult(
            text=text,
            model=response.model or self._model,
            raw_content=raw,
            usage=ProviderUsage(
                prompt_tokens=getattr(usage, "prompt_tokens", None),
                completion_tokens=getattr(usage, "completion_tokens", None),
                total_tokens=getattr(usage, "total_tokens", None),
            ),
        )
        result = attach_cost(result)
        self._usage_logger(result)
        return result

    @staticmethod
    def _parse_response_text(raw: str) -> str:
        if not raw:
            raise ProviderParseError(
                "OpenAI returned empty message content.",
                details={"content_length": 0},
            )

        try:
            text = parse_rewrite_text(raw, strict_json=True)
        except ProviderParseError:
            logger.warning(
                "openai json parse strict failed; trying lenient fallback",
                extra={"extra": {"preview": raw[:120]}},
            )
            text = parse_rewrite_text(raw, strict_json=False)

        if not text.strip():
            raise ProviderParseError(
                "OpenAI returned empty rewritten_text.",
                details={"preview": raw[:200]},
            )
        return text
