"""Vendor-agnostic retry helper for LLM provider calls."""

from __future__ import annotations

import time
from collections.abc import Callable
from typing import TypeVar

T = TypeVar("T")


def call_with_retries(
    fn: Callable[[], T],
    *,
    max_retries: int,
    is_retryable: Callable[[BaseException], bool],
    on_retry: Callable[[int, BaseException], float | None] | None = None,
    backoff_base: float = 1.0,
    backoff_max: float = 8.0,
) -> T:
    """Call ``fn`` up to ``max_retries + 1`` times when ``is_retryable`` returns True."""
    attempts = max(0, max_retries) + 1
    last_error: BaseException | None = None

    for attempt in range(1, attempts + 1):
        try:
            return fn()
        except BaseException as exc:
            if not is_retryable(exc):
                raise
            last_error = exc
            if attempt >= attempts:
                break
            delay = backoff_base * (2 ** (attempt - 1))
            if on_retry is not None:
                custom = on_retry(attempt, exc)
                if custom is not None:
                    delay = custom
            time.sleep(min(delay, backoff_max))

    assert last_error is not None
    raise last_error
