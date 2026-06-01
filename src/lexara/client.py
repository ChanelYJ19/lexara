"""Lexara Python SDK — rewrite to target grade with scored before/after proof."""

from __future__ import annotations

import time
import warnings
from typing import Any

import httpx

from lexara.exceptions import (
    LexaraConnectionError,
    LexaraError,
    LexaraTimeoutError,
    raise_for_response,
)
from lexara.models.rewrite import RewriteResponse, Tone
from lexara.models.scoring import ScoreResponse
from lexara.options import RewriteOptions

DEFAULT_BASE_URL = "http://localhost:8000"
DEFAULT_TIMEOUT = httpx.Timeout(10.0, read=120.0)
_RETRYABLE_STATUS = frozenset({429, 502, 503, 504})


class Readability:
    """Rewrite-to-target-grade workflow with multi-framework verification scoring.

    Access via ``LexaraClient.readability``.

    Primary method: ``rewrite()`` — score, rewrite, rescore, return input/output proof.
    Diagnostic helper: ``score()`` — multi-framework grade estimate without rewriting.
    """

    def __init__(self, client: "LexaraClient") -> None:
        self._client = client

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
        options: RewriteOptions | None = None,
    ) -> RewriteResponse:
        """Rewrite ``text`` toward ``target_grade`` and return before/after scored proof.

        Lexara scores your passage, rewrites it toward the target US grade level,
        and rescoring after each pass until the target is met or ``max_passes`` is
        exhausted.

        Returns a :class:`~lexara.models.rewrite.RewriteResponse` with:

        - ``input`` / ``output`` — original vs rewritten text and per-framework scores
        - ``outcome`` — ``hit_target``, grade moved from → to, ``frameworks_improved``, ``summary``
        - ``execution`` — passes used, provider, warnings

        Shortcut properties: ``rewritten_text``, ``hit_target``.

        Example::

            result = client.readability.rewrite(passage, target_grade=6, max_passes=5)
            if result.hit_target:
                publish(result.output.text)
            else:
                print(result.outcome.summary)
        """
        opts = options or RewriteOptions(
            preserve_meaning=preserve_meaning,
            tone=tone,
            max_passes=max_passes,
            frameworks=frameworks,
            tolerance=tolerance,
        )
        payload = {"text": text, "target_grade": target_grade, **opts.to_payload_fields()}
        data = self._client._post("/v1/readability/rewrite", payload)
        return RewriteResponse.model_validate(data)

    def adjust(
        self,
        text: str,
        target_grade: float,
        **kwargs: Any,
    ) -> RewriteResponse:
        """Deprecated alias for :meth:`rewrite`. Prefer ``rewrite()``."""
        warnings.warn(
            "readability.adjust() is deprecated; use readability.rewrite()",
            DeprecationWarning,
            stacklevel=2,
        )
        return self.rewrite(text, target_grade, **kwargs)

    def score(
        self,
        text: str,
        frameworks: list[str] | None = None,
    ) -> ScoreResponse:
        """Score-only diagnostics across readability frameworks (no rewrite).

        Use before :meth:`rewrite` when you only need a grade estimate, or to
        compare frameworks on the same passage.

        Example::

            scored = client.readability.score(text, frameworks=["flesch_kincaid", "lexile"])
            print(scored.aggregate.estimated_grade_level)
        """
        data = self._client._post(
            "/v1/readability/score", {"text": text, "frameworks": frameworks}
        )
        return ScoreResponse.model_validate(data)


class LexaraClient:
    """Lexara API client — optimized for rewrite-to-target-grade workflows."""

    def __init__(
        self,
        api_key: str,
        base_url: str = DEFAULT_BASE_URL,
        *,
        timeout: float | httpx.Timeout = DEFAULT_TIMEOUT,
        max_retries: int = 2,
        transport: httpx.BaseTransport | None = None,
    ) -> None:
        """Create a client.

        Args:
            api_key: Lexara API key (``Authorization: Bearer``).
            base_url: API base URL (default ``http://localhost:8000``).
            timeout: Total or granular httpx timeout. Default allows up to 120s read
                time for rewrite workflows.
            max_retries: Retries on transient HTTP/network errors (429, 502–504, timeouts).
            transport: Optional httpx transport (for testing).
        """
        if not api_key:
            raise ValueError("api_key is required")
        self._max_retries = max(0, max_retries)
        self._http = httpx.Client(
            base_url=base_url.rstrip("/"),
            timeout=timeout,
            headers={"Authorization": f"Bearer {api_key}"},
            transport=transport,
        )
        self.readability = Readability(self)

    def health(self) -> dict[str, Any]:
        """GET /health — liveness check (no API key required on server)."""
        try:
            resp = self._http.get("/health")
            resp.raise_for_status()
            return resp.json()
        except httpx.TimeoutException as exc:
            raise LexaraTimeoutError("Health check timed out.") from exc
        except httpx.TransportError as exc:
            raise LexaraConnectionError(str(exc)) from exc

    def _post(self, path: str, json: dict[str, Any]) -> dict[str, Any]:
        attempts = self._max_retries + 1
        last_transport_error: Exception | None = None

        for attempt in range(1, attempts + 1):
            try:
                resp = self._http.post(path, json=json)
            except httpx.TimeoutException as exc:
                last_transport_error = exc
                if attempt < attempts:
                    time.sleep(min(2 ** (attempt - 1), 8))
                    continue
                raise LexaraTimeoutError(
                    f"POST {path} timed out after {attempts} attempt(s)."
                ) from exc
            except httpx.TransportError as exc:
                last_transport_error = exc
                if attempt < attempts:
                    time.sleep(min(2 ** (attempt - 1), 8))
                    continue
                raise LexaraConnectionError(str(exc)) from exc

            if resp.status_code >= 400:
                if resp.status_code in _RETRYABLE_STATUS and attempt < attempts:
                    retry_after = resp.headers.get("Retry-After")
                    delay = 2 ** (attempt - 1)
                    if retry_after:
                        try:
                            delay = max(float(retry_after), delay)
                        except ValueError:
                            pass
                    time.sleep(min(delay, 30))
                    continue
                self._raise(resp)

            return resp.json()

        if last_transport_error is not None:
            raise LexaraConnectionError(str(last_transport_error)) from last_transport_error
        raise LexaraError("Request failed after retries.")

    @staticmethod
    def _raise(resp: httpx.Response) -> None:
        try:
            payload = resp.json()
        except Exception:  # noqa: BLE001
            payload = {}
        error_field = payload.get("error", {})
        if isinstance(error_field, dict):
            # Nested envelope: {"error": {"code": "...", "message": "..."}}
            code = error_field.get("code", "error")
            message = error_field.get("message", resp.text)
            details = error_field.get("details")
        else:
            # Flat 401 shape: {"error": "unauthorized", "message": "..."}
            code = str(error_field) if error_field else "error"
            message = payload.get("message", resp.text)
            details = None
        raise_for_response(resp.status_code, code, message, details)

    def close(self) -> None:
        self._http.close()

    def __enter__(self) -> "LexaraClient":
        return self

    def __exit__(self, *exc: object) -> None:
        self.close()
