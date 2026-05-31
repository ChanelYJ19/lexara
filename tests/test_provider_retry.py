"""Tests for vendor-agnostic provider retry helper."""

from __future__ import annotations

import pytest

from lexara.rewriting.providers.errors import ProviderError
from lexara.rewriting.providers.retry import call_with_retries


def test_call_with_retries_succeeds_first_try():
    assert call_with_retries(
        lambda: "ok",
        max_retries=2,
        is_retryable=lambda _: True,
    ) == "ok"


def test_call_with_retries_eventually_succeeds():
    state = {"n": 0}

    def fn():
        state["n"] += 1
        if state["n"] < 3:
            raise ConnectionError("down")
        return "ok"

    assert call_with_retries(
        fn,
        max_retries=3,
        is_retryable=lambda exc: isinstance(exc, ConnectionError),
        backoff_base=0.0,
        backoff_max=0.0,
    ) == "ok"


def test_call_with_retries_raises_non_retryable():
    with pytest.raises(ValueError):
        call_with_retries(
            lambda: (_ for _ in ()).throw(ValueError("nope")),
            max_retries=2,
            is_retryable=lambda exc: isinstance(exc, ConnectionError),
        )


def test_call_with_retries_respects_provider_retryable_flag():
    with pytest.raises(ProviderError):
        call_with_retries(
            lambda: (_ for _ in ()).throw(
                ProviderError("bad request", code="provider_error", retryable=False)
            ),
            max_retries=2,
            is_retryable=lambda exc: isinstance(exc, ProviderError) and exc.retryable,
        )
