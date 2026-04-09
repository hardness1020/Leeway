"""API error types for Leeway."""

from __future__ import annotations


class LeewayApiError(RuntimeError):
    """Base class for upstream API failures."""


class AuthenticationFailure(LeewayApiError):
    """Raised when the upstream service rejects the provided credentials."""


class RateLimitFailure(LeewayApiError):
    """Raised when the upstream service rejects the request due to rate limits."""


class RequestFailure(LeewayApiError):
    """Raised for generic request or transport failures."""
