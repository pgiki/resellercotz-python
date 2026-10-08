"""resellercotz-python — a friendly Python SDK for the reseller.co.tz API.

Example:
    >>> from resellercotz import ResellerCoTz
    >>> rc = ResellerCoTz()  # auto-loads RESELLER_API_KEY from environment
    >>> checks = rc.domains.check("example.co.tz")
    >>> [(c.domain, c.available, c.price) for c in checks]
"""

from __future__ import annotations

from .client import ResellerCoTz
from .config import Config
from .errors import (
    ConfigurationError,
    NotSupportedError,
    ResellerCoTzError,
)
from .models import (
    Contact,
    DNSRecord,
    DNSService,
    Domain,
    DomainCheck,
)

__version__ = "0.1.0"
__all__ = [
    "Config",
    "ConfigurationError",
    "Contact",
    "DNSRecord",
    "DNSService",
    "Domain",
    "DomainCheck",
    "NotSupportedError",
    "ResellerCoTz",
    "ResellerCoTzError",
]
