"""Typed exceptions for the Voice Interview Assistant API."""

from __future__ import annotations


class AppError(Exception):
    """Base application error with a machine-readable code."""

    def __init__(self, message: str, *, code: str = "APP_ERROR") -> None:
        self.message = message
        self.code = code
        super().__init__(message)


class BadRequestError(AppError):
    """Client sent an invalid or malformed request."""

    def __init__(self, message: str, *, code: str = "BAD_REQUEST") -> None:
        super().__init__(message, code=code)


class SessionError(AppError):
    """WebSocket interview session failed."""

    def __init__(self, message: str, *, code: str = "SESSION_ERROR") -> None:
        super().__init__(message, code=code)


class SessionTimeoutError(SessionError):
    """Session timed out waiting for client input."""

    def __init__(self, message: str, *, code: str = "SESSION_TIMEOUT") -> None:
        super().__init__(message, code=code)
