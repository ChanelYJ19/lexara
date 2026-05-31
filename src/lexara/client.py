"""Lexara Python SDK — score and rewrite in one developer-friendly workflow."""

from __future__ import annotations

from typing import Any

import httpx

from lexara.models.rewrite import RewriteResponse, Tone
from lexara.models.scoring import ScoreResponse

DEFAULT_BASE_URL = "http://localhost:8000"


class LexaraError(Exception):
    def __init__(self, status_code: int, code: str, message: str) -> None:
        self.status_code = status_code
        self.code = code
        self.message = message
        super().__init__(f"[{status_code} {code}] {message}")


class _Readability:
    """Readability workflow: multi-framework scoring and grade-targeted rewrite."""

    def __init__(self, client: "LexaraClient") -> None:
        self._client = client

    def adjust(
        self,
        text: str,
        target_grade: float,
        *,
        preserve_meaning: bool = True,
        tone: Tone | str = Tone.neutral,
        max_passes: int = 3,
        frameworks: list[str] | None = None,
        tolerance: float = 1.0,
    ) -> RewriteResponse:
        """Core Lexara workflow: score → rewrite → rescore until target grade.

        Returns a before/after response with multi-framework scores at each step.
        """
        return self.rewrite(
            text,
            target_grade,
            preserve_meaning=preserve_meaning,
            tone=tone,
            max_passes=max_passes,
            frameworks=frameworks,
            tolerance=tolerance,
        )

    def rewrite(
        self,
        text: str,
        target_grade: float,
        *,
        preserve_meaning: bool = True,
        tone: Tone | str = Tone.neutral,
        max_passes: int = 3,
        frameworks: list[str] | None = None,
        tolerance: float = 1.0,
    ) -> RewriteResponse:
        payload = {
            "text": text,
            "target_grade": target_grade,
            "preserve_meaning": preserve_meaning,
            "tone": tone.value if isinstance(tone, Tone) else tone,
            "max_passes": max_passes,
            "frameworks": frameworks,
            "tolerance": tolerance,
        }
        data = self._client._post("/v1/readability/rewrite", payload)
        return RewriteResponse.model_validate(data)

    def score(
        self, text: str, frameworks: list[str] | None = None
    ) -> ScoreResponse:
        """Multi-framework score only (no rewrite). Use ``adjust()`` for the full workflow."""
        data = self._client._post(
            "/v1/readability/score", {"text": text, "frameworks": frameworks}
        )
        return ScoreResponse.model_validate(data)


class LexaraClient:
    def __init__(
        self,
        api_key: str,
        base_url: str = DEFAULT_BASE_URL,
        *,
        timeout: float = 60.0,
        transport: httpx.BaseTransport | None = None,
    ) -> None:
        self._http = httpx.Client(
            base_url=base_url.rstrip("/"),
            timeout=timeout,
            headers={"Authorization": f"Bearer {api_key}"},
            transport=transport,
        )
        self.readability = _Readability(self)

    def health(self) -> dict[str, Any]:
        resp = self._http.get("/health")
        resp.raise_for_status()
        return resp.json()

    def _post(self, path: str, json: dict[str, Any]) -> dict[str, Any]:
        resp = self._http.post(path, json=json)
        if resp.status_code >= 400:
            self._raise(resp)
        return resp.json()

    @staticmethod
    def _raise(resp: httpx.Response) -> None:
        try:
            body = resp.json().get("error", {})
        except Exception:  # noqa: BLE001
            body = {}
        raise LexaraError(
            resp.status_code,
            body.get("code", "error"),
            body.get("message", resp.text),
        )

    def close(self) -> None:
        self._http.close()

    def __enter__(self) -> "LexaraClient":
        return self

    def __exit__(self, *exc: object) -> None:
        self.close()
