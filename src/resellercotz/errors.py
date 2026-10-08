"""reseller.co.tz API error handling."""

from __future__ import annotations

from typing import Any


class ResellerCoTzError(Exception):
    """Base exception for all reseller.co.tz API errors."""

    def __init__(
        self,
        message: str,
        status_code: int = 0,
        code: str | None = None,
        details: Any | None = None,
    ) -> None:
        self.message = message
        self.status_code = status_code
        self.code = code or ""
        self.details = details
        # Aliases matching the sibling SDKs' error shapes.
        self.response_text = message
        super().__init__(str(self))

    def __str__(self) -> str:
        prefix = f"reseller.co.tz API error {self.status_code}" if self.status_code else "reseller.co.tz API error"
        if self.code:
            return f"{prefix} [{self.code}]: {self.message}"
        return f"{prefix}: {self.message}"

    @classmethod
    def from_response(cls, status_code: int, data: Any) -> ResellerCoTzError:
        """Build an error from the ``{success,message,errors}`` envelope."""
        if isinstance(data, dict):
            message = data.get("message") or data.get("detail") or data.get("title") or f"HTTP {status_code}"
            errors = data.get("errors")
            code = ""
            if isinstance(errors, dict):
                keys = sorted(errors.keys())
                code = keys[0] if keys else ""
            return cls(str(message), status_code, code or None, data)
        return cls(str(data) if data else f"HTTP {status_code}", status_code, None, data)


class ConfigurationError(Exception):
    """Raised when client configuration is invalid."""

    pass


class NotSupportedError(Exception):
    """Raised when an operation has no reseller.co.tz endpoint.

    Carries an ``alternative`` hint pointing at the supported way to
    achieve the same result.
    """

    def __init__(self, message: str, alternative: str = "") -> None:
        self.alternative = alternative
        super().__init__(f"{message} Alternative: {alternative}" if alternative else message)
