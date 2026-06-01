"""Signup endpoints — no auth required."""

from __future__ import annotations

import secrets

from fastapi import APIRouter, Request
from pydantic import BaseModel, Field

from lexara.db.models import User

router = APIRouter(tags=["signup"])


class SignupRequest(BaseModel):
    email: str = Field(..., description="Email address to register.")


class SignupResponse(BaseModel):
    message: str
    email: str
    api_key: str


@router.get("/signup", summary="Signup page (stub)")
def signup_page() -> dict:
    return {
        "message": "Lexara alpha access",
        "instructions": 'POST /signup with {"email": "you@example.com"} to get an API key.',
    }


@router.post("/signup", response_model=SignupResponse, summary="Request alpha access")
def signup(payload: SignupRequest, request: Request) -> SignupResponse:
    db = request.app.state.db_session_factory()
    try:
        existing = db.query(User).filter(User.email == payload.email).first()
        if existing:
            return SignupResponse(
                message="Welcome back! Use your existing API key.",
                email=existing.email,
                api_key=existing.api_key,
            )
        user = User(
            email=payload.email,
            api_key=secrets.token_hex(32),
        )
        db.add(user)
        db.commit()
    finally:
        db.close()

    return SignupResponse(
        message="You're in! Use the api_key below in your Authorization header.",
        email=user.email,
        api_key=user.api_key,
    )
