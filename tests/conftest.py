from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from lexara.api.app import create_app
from lexara.config import Settings

API_KEY = "test-key"


@pytest.fixture
def settings() -> Settings:
    return Settings(api_keys=[API_KEY], llm_provider="mock", log_level="WARNING")


@pytest.fixture
def app(settings: Settings):
    return create_app(settings)


@pytest.fixture
def client(app):
    return TestClient(app)


@pytest.fixture
def auth_headers() -> dict[str, str]:
    return {"Authorization": f"Bearer {API_KEY}"}
