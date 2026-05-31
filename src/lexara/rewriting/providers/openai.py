"""OpenAI provider (alpha-hardened).

Features: client reuse, timeouts, retries on transient errors, JSON response
format, failure-safe parsing, and token/cost logging hooks.
"""

from __future__ import annotations

import time

from lexara.logging_config import get_logger
from lexara.rewriting.providers.base import (
    LLMProvider,
    ProviderResult,
    ProviderUsage,
    RewriteInstruction,
    UsageLogger,
)
from lexara.rewriting.providers.errors import ProviderError, ProviderTimeoutError
from lexara.rewriting.providers.parsing import parse_rewrite_text
from lexara.rewriting.providers.usage import attach_cost, default_usage_logger

logger = get_logger(__name__)

# Transient OpenAI exception types (resolved lazily when openai is installed).
_TRANSIENT: tuple[type[BaseException], ...] = ()


def _transient_errors() -> tuple[type[BaseException], ...]:
    global _TRANSIENT
    if _TRANSIENT:
        return _TRANSIENT
    try:
        from openai import APIConnectionError, APITimeoutError, RateLimitError

        _TRANSIENT = (APITimeoutError, APIConnectionError, RateLimitError)
    except ImportError:
        _TRANSIENT = (TimeoutError, ConnectionError)
    return _TRANSIENT


class OpenAIProvider(LLMProvider):
    name = "openai"

    def __init__(
        self,
        api_key: str,
        model: str = "gpt-4o-mini",
        *,
        timeout_seconds: float = 60.0,
        max_retries: int = 2,
        usage_logger: UsageLogger | None = None,
    ) -> None:
        if not api_key:
            raise ValueError("OpenAI API key is required for the openai provider.")
        self._api_key = api_key
        self._model = model
        self._timeout = timeout_seconds
        self._max_retries = max(0, max_retries)
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
            max_retries=0,  # we own retry policy below
        )
        return self._client

    def complete(self, instruction: RewriteInstruction) -> ProviderResult:
        last_error: ProviderError | None = None
        attempts = self._max_retries + 1

        for attempt in range(1, attempts + 1):
            try:
                result = self._call_once(instruction)
                self._usage_logger(result)
                return result
            except ProviderTimeoutError as exc:
                last_error = exc
                logger.warning(
                    "openai timeout",
                    extra={"extra": {"attempt": attempt, "max": attempts}},
                )
            except _transient_errors() as exc:
                last_error = ProviderError(
                    f"OpenAI transient error: {exc}",
                    code="provider_transient_error",
                    retryable=True,
                    details={"attempt": attempt, "exception": type(exc).__name__},
                )
                logger.warning(
                    "openai transient failure",
                    extra={"extra": {"attempt": attempt, "error": type(exc).__name__}},
                )
            except ProviderError:
                raise
            except Exception as exc:
                raise ProviderError(
                    f"OpenAI request failed: {exc}",
                    code="provider_error",
                    details={"exception": type(exc).__name__},
                ) from exc

            if attempt < attempts:
                time.sleep(min(2 ** (attempt - 1), 8))

        assert last_error is not None
        raise last_error

    def _call_once(self, instruction: RewriteInstruction) -> ProviderResult:
        client = self._get_client()
        try:
            response = client.chat.completions.create(
                model=self._model,
                temperature=0.4,
                response_format={"type": "json_object"},
                messages=[
                    {"role": "system", "content": instruction.system_prompt},
                    {"role": "user", "content": instruction.user_prompt},
                ],
            )
        except Exception as exc:
            transient = _transient_errors()
            if isinstance(exc, transient):
                raise
            raise ProviderError(
                f"OpenAI request failed: {exc}",
                code="provider_error",
                details={"exception": type(exc).__name__},
            ) from exc

        choice = response.choices[0]
        raw = (choice.message.content or "").strip()
        usage = response.usage

        try:
            text = parse_rewrite_text(raw, strict_json=False)
        except ProviderError:
            # Last-resort: model sometimes ignores JSON mode on edge cases.
            text = raw.strip() if raw else ""
            if not text:
                raise

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
        return attach_cost(result)
