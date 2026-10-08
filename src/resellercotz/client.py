"""Main reseller.co.tz client."""

from __future__ import annotations

from functools import cached_property
from typing import Self

import httpx
from dotenv import load_dotenv

from ._api.dns import DnsAPI
from ._api.domains import DomainsAPI
from .config import Config
from .errors import ConfigurationError
from .logging import set_log_level


class ResellerCoTz:
    """
    The main reseller.co.tz client.

    Examples:
        >>> rc = ResellerCoTz()  # Loads RESELLER_API_KEY from environment
        >>> rc = ResellerCoTz(api_key="...")  # Explicit
        >>> rc = ResellerCoTz.from_env_file(".env.prod")  # From specific env file

        >>> # Check domain availability (free endpoint)
        >>> rc.domains.check("example.co.tz")

        >>> # Use as context manager
        >>> with ResellerCoTz() as rc:
        ...     rc.domains.get_info("example.co.tz")
    """

    def __init__(
        self,
        *,
        api_key: str | None = None,
        base_url: str | None = None,
        timeout: float | None = None,
        log_level: str | None = None,
    ) -> None:
        """
        Initialize the client with smart defaults.

        Args:
            api_key: Reseller API key (or set RESELLER_API_KEY env var)
            base_url: API base URL (default: https://reseller.co.tz/api/v1)
            timeout: Request timeout in seconds (default: 30.0)
            log_level: Logging level (default: INFO)

        Raises:
            ConfigurationError: If required configuration is missing
        """
        try:
            self.config = Config.from_env(
                api_key=api_key,
                base_url=base_url,
                timeout=timeout,
                log_level=log_level,
            )
            set_log_level(self.config.log_level)
        except Exception as e:
            raise ConfigurationError(
                "Failed to load configuration. Ensure you have set:\n"
                "- RESELLER_API_KEY\n"
                "Or pass it as a parameter to the client."
            ) from e

        self._http = httpx.Client(timeout=self.config.timeout)

    @classmethod
    def from_env_file(cls, path: str = ".env") -> Self:
        """Create a client from a specific env file."""
        load_dotenv(path)
        return cls()

    @cached_property
    def domains(self) -> DomainsAPI:
        """Domain availability, registration, renewal and transfer."""
        return DomainsAPI(self)

    @cached_property
    def dns(self) -> DnsAPI:
        """DNS record management (per-domain addon, auto-provisioned)."""
        return DnsAPI(self)

    def close(self) -> None:
        """Close the underlying HTTP client."""
        self._http.close()

    def __enter__(self) -> Self:
        return self

    def __exit__(self, *args: object) -> None:
        self.close()

    def __repr__(self) -> str:
        return f"<ResellerCoTz(base_url={self.config.base_url!r})>"
