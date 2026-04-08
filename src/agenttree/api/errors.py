"""API error types for AgentTree."""

from __future__ import annotations


class AgentTreeApiError(RuntimeError):
    """Base class for upstream API failures."""


class AuthenticationFailure(AgentTreeApiError):
    """Raised when the upstream service rejects the provided credentials."""


class RateLimitFailure(AgentTreeApiError):
    """Raised when the upstream service rejects the request due to rate limits."""


class RequestFailure(AgentTreeApiError):
    """Raised for generic request or transport failures."""
