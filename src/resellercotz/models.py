"""Pydantic models for reseller.co.tz API responses."""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator


class ResellerModel(BaseModel):
    model_config = ConfigDict(populate_by_name=True, str_strip_whitespace=True, extra="allow")


def _to_decimal(value: Any) -> Decimal | None:
    if value is None or value == "":
        return None
    try:
        return Decimal(str(value))
    except Exception:
        return None


def _to_date(value: Any) -> date | None:
    if not value:
        return None
    if isinstance(value, date) and not isinstance(value, datetime):
        return value
    if isinstance(value, datetime):
        return value.date()
    try:
        return date.fromisoformat(str(value).strip()[:10])
    except Exception:
        return None


def _to_datetime(value: Any) -> datetime | None:
    if not value:
        return None
    if isinstance(value, datetime):
        return value
    try:
        text = str(value).strip().replace("Z", "+00:00")
        return datetime.fromisoformat(text)
    except Exception:
        return None


class DomainCheck(ResellerModel):
    """Availability result for one domain (``POST /domains/check``)."""

    domain: str = Field(default="", alias="domain_name")
    available: bool = False
    bookable: bool = False
    reserved: bool = False
    premium: bool = False
    price_registration: Decimal | None = Field(default=None, alias="registration")
    price_renewal: Decimal | None = Field(default=None, alias="renewal")
    price_transfer: Decimal | None = Field(default=None, alias="transfer")
    premium_registration: Decimal | None = None
    premium_sellable: bool = False
    currency: str = "TZS"

    @field_validator("price_registration", "price_renewal", "price_transfer", "premium_registration", mode="before")
    @classmethod
    def _parse_price(cls, v: Any) -> Decimal | None:
        return _to_decimal(v)

    @classmethod
    def from_api(cls, domain: str, payload: dict[str, Any], currency: str = "TZS") -> DomainCheck:
        """Build from a ``check`` data envelope (nested ``price`` object)."""
        payload = dict(payload or {})
        price = payload.get("price") or {}
        if not isinstance(price, dict):
            price = {}
        return cls.model_validate(
            {
                "domain_name": payload.get("domain_name") or domain,
                "available": bool(payload.get("available", False)),
                "bookable": bool(payload.get("bookable", False)),
                "reserved": bool(payload.get("reserved", False)),
                "premium": bool(payload.get("premium", False)),
                "registration": price.get("registration"),
                "renewal": price.get("renewal"),
                "transfer": price.get("transfer"),
                "premium_registration": price.get("premium_registration"),
                "premium_sellable": bool(price.get("premium_sellable", False)),
                "currency": currency,
            }
        )

    # -- spaceship-shaped compat --
    @property
    def result(self) -> str:
        return "available" if self.available else "unavailable"

    @property
    def price(self) -> Decimal | None:
        """Best register price (premium leg wins when sellable)."""
        if self.premium and self.premium_sellable and self.premium_registration is not None:
            return self.premium_registration
        return self.price_registration

    @property
    def register_price(self) -> Decimal | None:
        return self.price

    @property
    def renew_price(self) -> Decimal | None:
        return self.price_renewal


class Domain(ResellerModel):
    """An owned domain (``GET /domains/{domain}`` shape)."""

    id: int | None = None
    name: str = Field(default="", alias="domain_name")
    status: str = ""
    registry_status: str = Field(default="", alias="registry_status")
    redemption_state: str = ""
    in_redemption: bool = False
    renewal_price: Decimal | None = None
    redemption_price: Decimal | None = None
    registration_date: date | None = None
    expiry_date: date | None = None
    lock_status: bool = False
    privacy_status: bool = False
    last_synced_at: datetime | None = None

    @field_validator("renewal_price", "redemption_price", mode="before")
    @classmethod
    def _parse_price(cls, v: Any) -> Decimal | None:
        return _to_decimal(v)

    @field_validator("registration_date", "expiry_date", mode="before")
    @classmethod
    def _parse_date(cls, v: Any) -> date | None:
        return _to_date(v)

    @field_validator("last_synced_at", mode="before")
    @classmethod
    def _parse_dt(cls, v: Any) -> datetime | None:
        return _to_datetime(v)

    # -- spaceship-shaped compat --
    @property
    def expiration_date(self) -> datetime | None:
        if self.expiry_date is None:
            return None
        return datetime(self.expiry_date.year, self.expiry_date.month, self.expiry_date.day)


class Contact(ResellerModel):
    """A whois contact (``GET /domains/{domain}/whois`` fields)."""

    name: str = ""
    organization: str | None = None
    email: str = ""
    address1: str = ""
    city: str = ""
    state: str | None = None
    postcode: str | None = None
    country: str = ""
    phone: str = ""

    def api_fields(self) -> dict[str, Any]:
        """Field payload for whois update (no empties)."""
        data = self.model_dump(exclude_none=True)
        return {k: v for k, v in data.items() if v not in ("", None)}

    @classmethod
    def from_api(cls, data: dict[str, Any]) -> Contact:
        return cls.model_validate(dict(data or {}))

    @classmethod
    def from_profile(
        cls,
        *,
        firstname: str = "",
        lastname: str = "",
        email: str = "",
        address1: str = "",
        city: str = "",
        state: str = "",
        postcode: str = "",
        country: str = "",
        phone: str = "",
        organization: str | None = None,
    ) -> Contact:
        """Build from split fikashop profile facts (``name`` = first + last)."""
        full = f"{firstname.strip()} {lastname.strip()}".strip()
        return cls(
            name=full,
            organization=organization or None,
            email=email.strip(),
            address1=address1.strip(),
            city=city.strip(),
            state=state.strip() or None,
            postcode=postcode.strip() or None,
            country=country.strip().upper(),
            phone=phone.strip(),
        )

    def split_name(self) -> tuple[str, str]:
        parts = (self.name or "").strip().split()
        if not parts:
            return "", ""
        if len(parts) == 1:
            return parts[0], ""
        return " ".join(parts[:-1]), parts[-1]


class DNSService(ResellerModel):
    """DNS management addon state for a zone."""

    id: int | None = None
    status: str = ""
    zone: str = ""

    @property
    def active(self) -> bool:
        return self.status.strip().lower() == "active"


class DNSRecord(ResellerModel):
    """A DNS resource record (API form: ``@`` apex, otherwise relative names)."""

    line: int | None = None
    type: str = ""
    name: str = "@"
    value: str | None = Field(default=None, alias="value")
    ttl: int | None = None
    priority: int | None = None
    replace_existing: bool | None = None

    @field_validator("type", mode="before")
    @classmethod
    def _upper(cls, v: Any) -> Any:
        return str(v).upper() if v else v

    @field_validator("priority", mode="before")
    @classmethod
    def _parse_priority(cls, v: Any) -> int | None:
        if v in (None, ""):
            return None
        try:
            return int(v)
        except Exception:
            return None

    @classmethod
    def from_api(cls, data: dict[str, Any]) -> DNSRecord:
        data = dict(data or {})
        # Accept spaceship-style ``address`` as an alias for ``value``.
        if data.get("value") in (None, "") and data.get("address") not in (None, ""):
            data["value"] = data.pop("address")
        for key in ("prio", "priority_value", "mx_priority"):
            if data.get("priority") in (None, "") and data.get(key) not in (None, ""):
                data["priority"] = data.pop(key)
        return cls.model_validate(data)

    # -- spaceship-shaped compat (``address`` instead of ``value``) --
    @property
    def address(self) -> str | None:
        return self.value

    @address.setter
    def address(self, val: str | None) -> None:
        self.value = val

    def fqdn(self, zone: str) -> str:
        """Fully qualified name of this record inside ``zone``."""
        z = zone.strip().rstrip(".").lower()
        n = (self.name or "").strip().rstrip(".")
        if not n or n == "@" or n.lower() == z:
            return z
        if n.lower().endswith("." + z):
            return n.lower()
        return f"{n}.{z}".lower()

    def to_api(self, *, include_replace_existing: bool = False) -> dict[str, Any]:
        """Record payload for create/update (no empties)."""
        data: dict[str, Any] = {"type": self.type.upper(), "name": self.name or "@"}
        if self.value not in (None, ""):
            data["value"] = self.value
        if self.ttl is not None:
            data["ttl"] = self.ttl
        if self.priority is not None:
            data["priority"] = self.priority
        if include_replace_existing and self.replace_existing is not None:
            data["replace_existing"] = self.replace_existing
        return data
