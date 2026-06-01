"""Signup stubs — no auth required."""

from __future__ import annotations

from fastapi import APIRouter
from pydantic import BaseModel, EmailStr, Field

router = APIRouter(tags=["signup"])


class SignupRequest(BaseModel):
    email: str = Field(..., description="Email address to register.")


class SignupResponse(BaseModel):
    message: str
    email: str


@router.get("/signup", summary="Signup page (stub)")
def signup_page() -> dict:
    return {
        "message": "Lexara alpha access",
        "instructions": "POST /signup with {\"email\": \"you@example.com\"} to request an API key.",
    }


@router.post("/signup", response_model=SignupResponse, summary="Request alpha access")
def signup(payload: SignupRequest) -> SignupResponse:
    return SignupResponse(
        message="Thanks! We'll send your API key to this address shortly.",
        email=payload.email,
    )
