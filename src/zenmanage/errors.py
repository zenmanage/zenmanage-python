"""Custom exceptions for the Zenmanage Python SDK."""

from typing import Optional


class ZenmanageError(Exception):
    """Base exception for all SDK errors."""


class ConfigurationError(ZenmanageError):
    """Raised when SDK configuration is invalid."""


class EvaluationError(ZenmanageError):
    """Raised when a flag cannot be evaluated."""


class FetchRulesError(ZenmanageError):
    """Raised when rules cannot be fetched from the API."""

    def __init__(self, message: str, status_code: Optional[int] = None) -> None:
        super().__init__(message)
        self.status_code = status_code


class InvalidRulesError(ZenmanageError):
    """Raised when rules payloads are malformed."""
