"""Structured error envelope returned by every non-2xx response."""

from __future__ import annotations

from pydantic import BaseModel, Field


class ErrorBody(BaseModel):
    code: str = Field(..., description="Stable, machine-readable error code.")
    message: str = Field(..., description="Human-readable explanation.")
    details: dict | None = Field(
        default=None, description="Optional structured context (e.g. validation)."
    )


class ErrorResponse(BaseModel):
    error: ErrorBody
    request_id: str | None = None
