"""Unit tests for OpenAI provider (mocked SDK — no network)."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from lexara.rewriting.providers.base import RewriteInstruction
from lexara.rewriting.providers.errors import ProviderError, ProviderParseError, ProviderTimeoutError
from lexara.rewriting.providers.openai import OpenAIProvider
from lexara.rewriting.providers.parsing import parse_rewrite_text


def test_parse_rewrite_text_json():
    assert parse_rewrite_text('{"rewritten_text": "Hello world."}') == "Hello world."


def test_parse_rewrite_text_embedded_json():
    raw = 'Sure. {"rewritten_text": "Hello world."}'
    assert parse_rewrite_text(raw) == "Hello world."


def test_parse_rewrite_text_fenced_json():
    raw = '```json\n{"rewritten_text": "Hello world."}\n```'
    assert parse_rewrite_text(raw) == "Hello world."


def test_parse_rewrite_text_plain_fallback():
    assert parse_rewrite_text("Plain text.") == "Plain text."


def test_parse_rewrite_text_strict_raises():
    with pytest.raises(ProviderParseError):
        parse_rewrite_text("not json", strict_json=True)


@patch("lexara.rewriting.providers.openai.OpenAIProvider._get_client")
def test_openai_provider_parses_json(mock_client_fn):
    mock_response = MagicMock()
    mock_response.model = "gpt-4o-mini"
    mock_response.usage.prompt_tokens = 100
    mock_response.usage.completion_tokens = 50
    mock_response.usage.total_tokens = 150
    mock_response.choices = [
        MagicMock(
            message=MagicMock(content='{"rewritten_text": "Simple text."}'),
            finish_reason="stop",
        )
    ]

    mock_client = MagicMock()
    mock_client.chat.completions.create.return_value = mock_response
    mock_client_fn.return_value = mock_client

    provider = OpenAIProvider(api_key="sk-test", max_retries=0)
    result = provider.complete(
        RewriteInstruction(system_prompt="sys", user_prompt="user")
    )
    assert result.text == "Simple text."
    assert result.usage.total_tokens == 150
    assert result.usage.estimated_cost_usd is not None
    mock_client.chat.completions.create.assert_called_once()
    call_kwargs = mock_client.chat.completions.create.call_args.kwargs
    assert call_kwargs["response_format"] == {"type": "json_object"}
    assert call_kwargs["max_tokens"] == 4096


@patch("lexara.rewriting.providers.openai.OpenAIProvider._get_client")
def test_openai_provider_retries_transient(mock_client_fn):
    try:
        from openai import APIConnectionError
    except ImportError:
        pytest.skip("openai not installed")

    mock_client = MagicMock()
    mock_client.chat.completions.create.side_effect = [
        APIConnectionError(request=MagicMock()),
        MagicMock(
            model="gpt-4o-mini",
            usage=MagicMock(prompt_tokens=10, completion_tokens=5, total_tokens=15),
            choices=[
                MagicMock(
                    message=MagicMock(content='{"rewritten_text": "Done."}'),
                    finish_reason="stop",
                )
            ],
        ),
    ]
    mock_client_fn.return_value = mock_client

    provider = OpenAIProvider(api_key="sk-test", max_retries=1)
    result = provider.complete(
        RewriteInstruction(system_prompt="sys", user_prompt="user")
    )
    assert result.text == "Done."
    assert mock_client.chat.completions.create.call_count == 2


@patch("lexara.rewriting.providers.openai.OpenAIProvider._get_client")
def test_openai_provider_raises_after_retries_exhausted(mock_client_fn):
    try:
        from openai import APIConnectionError
    except ImportError:
        pytest.skip("openai not installed")

    mock_client = MagicMock()
    mock_client.chat.completions.create.side_effect = APIConnectionError(
        request=MagicMock()
    )
    mock_client_fn.return_value = mock_client

    provider = OpenAIProvider(api_key="sk-test", max_retries=1)
    with pytest.raises(ProviderError) as exc:
        provider.complete(RewriteInstruction(system_prompt="s", user_prompt="u"))
    assert exc.value.code == "provider_transient_error"


@patch("lexara.rewriting.providers.openai.OpenAIProvider._get_client")
def test_openai_provider_timeout_is_provider_timeout_error(mock_client_fn):
    try:
        from openai import APITimeoutError
    except ImportError:
        pytest.skip("openai not installed")

    mock_client = MagicMock()
    mock_client.chat.completions.create.side_effect = APITimeoutError(request=MagicMock())
    mock_client_fn.return_value = mock_client

    provider = OpenAIProvider(api_key="sk-test", max_retries=0)
    with pytest.raises(ProviderTimeoutError) as exc:
        provider.complete(RewriteInstruction(system_prompt="s", user_prompt="u"))
    assert exc.value.code == "provider_timeout"
    assert exc.value.retryable is True


@patch("lexara.rewriting.providers.openai.OpenAIProvider._get_client")
def test_openai_provider_rejects_truncated_response(mock_client_fn):
    mock_response = MagicMock(
        model="gpt-4o-mini",
        usage=MagicMock(prompt_tokens=10, completion_tokens=5, total_tokens=15),
        choices=[
            MagicMock(
                message=MagicMock(content='{"rewritten_text": "Partial'),
                finish_reason="length",
            )
        ],
    )
    mock_client = MagicMock()
    mock_client.chat.completions.create.return_value = mock_response
    mock_client_fn.return_value = mock_client

    provider = OpenAIProvider(api_key="sk-test", max_retries=0)
    with pytest.raises(ProviderParseError):
        provider.complete(RewriteInstruction(system_prompt="s", user_prompt="u"))


@patch("lexara.rewriting.providers.openai.OpenAIProvider._get_client")
def test_openai_provider_rejects_empty_choices(mock_client_fn):
    mock_response = MagicMock(
        model="gpt-4o-mini",
        usage=MagicMock(prompt_tokens=0, completion_tokens=0, total_tokens=0),
        choices=[],
    )
    mock_client = MagicMock()
    mock_client.chat.completions.create.return_value = mock_response
    mock_client_fn.return_value = mock_client

    provider = OpenAIProvider(api_key="sk-test", max_retries=0)
    with pytest.raises(ProviderParseError):
        provider.complete(RewriteInstruction(system_prompt="s", user_prompt="u"))


@patch("lexara.rewriting.providers.openai.OpenAIProvider._get_client")
def test_openai_provider_lenient_fallback_when_json_shape_wrong(mock_client_fn):
    mock_response = MagicMock(
        model="gpt-4o-mini",
        usage=MagicMock(prompt_tokens=10, completion_tokens=5, total_tokens=15),
        choices=[
            MagicMock(
                message=MagicMock(content="Plain rewritten passage."),
                finish_reason="stop",
            )
        ],
    )
    mock_client = MagicMock()
    mock_client.chat.completions.create.return_value = mock_response
    mock_client_fn.return_value = mock_client

    provider = OpenAIProvider(api_key="sk-test", max_retries=0)
    result = provider.complete(RewriteInstruction(system_prompt="s", user_prompt="u"))
    assert result.text == "Plain rewritten passage."
