"""Lexara — rewrite to target grade API + Python SDK."""

from lexara.client import LexaraClient, Readability
from lexara.exceptions import (
    AuthenticationError,
    LexaraAPIError,
    LexaraConnectionError,
    LexaraError,
    LexaraTimeoutError,
    ValidationError,
)
from lexara.models.rewrite import Tone
from lexara.options import RewriteOptions

__version__ = "0.1.0a1"
__all__ = [
    "LexaraClient",
    "Readability",
    "RewriteOptions",
    "Tone",
    "LexaraError",
    "AuthenticationError",
    "ValidationError",
    "LexaraAPIError",
    "LexaraTimeoutError",
    "LexaraConnectionError",
    "__version__",
]
