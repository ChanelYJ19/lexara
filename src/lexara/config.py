"""Application settings, loaded from environment / .env (prefix ``LEXARA_``)."""

from __future__ import annotations

from functools import lru_cache
from typing import Annotated

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="LEXARA_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # NoDecode: stop pydantic-settings from JSON-parsing the env value so our
    # comma-separated validator below can handle it.
    api_keys: Annotated[list[str], NoDecode] = Field(
        default_factory=lambda: ["dev-local-key"]
    )
    llm_provider: str = "mock"
    openai_api_key: str | None = None
    openai_model: str = "gpt-4o-mini"
    openai_timeout_seconds: float = 60.0
    openai_max_retries: int = 2
    openai_max_completion_tokens: int = 4096
    log_level: str = "INFO"
    max_rewrite_passes: int = 5

    @field_validator("api_keys", mode="before")
    @classmethod
    def _split_keys(cls, value: object) -> object:
        # Allow a comma-separated string in the env var.
        if isinstance(value, str):
            return [k.strip() for k in value.split(",") if k.strip()]
        return value


@lru_cache
def get_settings() -> Settings:
    return Settings()
