"""Client configuration (explicit args, env vars, or env file)."""

from __future__ import annotations

import os

from pydantic import BaseModel, ConfigDict, Field, field_validator

DEFAULT_BASE_URL = "https://reseller.co.tz/api/v1"


class Config(BaseModel):
    """reseller.co.tz client configuration with validation."""

    api_key: str = Field(description="Reseller API key (X-API-KEY)")
    base_url: str = Field(
        default=DEFAULT_BASE_URL,
        description="reseller.co.tz API base URL",
    )
    timeout: float = Field(default=30.0, description="Request timeout in seconds")
    log_level: str = Field(default="INFO", description="Logging level")

    model_config = ConfigDict(str_strip_whitespace=True, validate_default=True)

    @field_validator("api_key")
    @classmethod
    def validate_required(cls, v: str) -> str:
        if not v:
            raise ValueError("must not be empty")
        return v

    @field_validator("log_level")
    @classmethod
    def validate_log_level(cls, v: str) -> str:
        valid = {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}
        if v.upper() not in valid:
            raise ValueError(f"Invalid log level: {v}. Must be one of {valid}")
        return v.upper()

    @classmethod
    def from_env(
        cls,
        api_key: str | None = None,
        base_url: str | None = None,
        timeout: float | None = None,
        log_level: str | None = None,
    ) -> Config:
        """Build config from explicit args with ``RESELLER_*`` env fallback."""
        return cls(
            api_key=api_key or os.environ.get("RESELLER_API_KEY", ""),
            base_url=base_url or os.environ.get("RESELLER_BASE_URL", "") or DEFAULT_BASE_URL,
            timeout=timeout if timeout is not None else float(os.environ.get("RESELLER_TIMEOUT", "30.0")),
            log_level=log_level or os.environ.get("RESELLER_LOG_LEVEL", "INFO"),
        )
