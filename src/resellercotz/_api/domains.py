"""Domain management: check, list, info, register, renew, transfer, whois, nameservers, lock, privacy, EPP."""

from __future__ import annotations

from typing import Any

from ..errors import NotSupportedError
from ..idn import to_punycode
from ..models import Contact, Domain, DomainCheck
from .base import BaseAPI


def _contact_payload(contact: Contact | dict[str, Any]) -> dict[str, Any]:
    if isinstance(contact, Contact):
        return contact.api_fields()
    return {k: v for k, v in dict(contact or {}).items() if v not in ("", None)}


class DomainsAPI(BaseAPI):
    """Domain availability, registration, renewal, transfer and settings."""

    # -- availability --
    def check(self, *domains: str, include_pricing: bool = True) -> list[DomainCheck]:  # noqa: ARG002
        """Check availability; catalog pricing included in every response.

        Unlike spaceship, reseller.co.tz returns register/renew/transfer
        prices on the check itself, so ``DomainCheck.price`` is set for
        standard domains too (never priceless).
        """
        out: list[DomainCheck] = []
        for raw in domains:
            name = to_punycode(raw)
            if not name:
                continue
            data = self._request("POST", "/domains/check", json={"domain_name": name})
            payload = data if isinstance(data, dict) else {}
            out.append(DomainCheck.from_api(name, payload))
        return out

    def check_single(self, domain: str) -> DomainCheck:
        """Check a single domain."""
        rows = self.check(domain)
        if not rows:
            raise ValueError(f"No availability result for {domain!r}.")
        return rows[0]

    # -- listing / info --
    def list(
        self,
        *,
        q: str | None = None,
        status: str | None = None,
        page: int = 1,
        page_size: int = 25,
        per_page: int | None = None,
    ) -> list[Domain]:
        """List owned domains with search, status filter and pagination."""
        size = max(1, min(int(per_page if per_page is not None else page_size), 100))
        params: dict[str, Any] = {"page": max(page, 1), "per_page": size}
        if q:
            params["q"] = q
        if status:
            params["status"] = status
        data = self._request("GET", "/domains", params=params)
        rows = (data or {}).get("domains", []) if isinstance(data, dict) else []
        return [Domain.model_validate(r) for r in rows if isinstance(r, dict)]

    def get_info(self, domain: str) -> Domain:
        """Detailed info about an owned domain (status, dates, lock, privacy)."""
        data = self._request("GET", f"/domains/{to_punycode(domain)}")
        payload = (data or {}).get("domain", data) if isinstance(data, dict) else {}
        return Domain.model_validate(payload if isinstance(payload, dict) else {"domain_name": domain})

    get = get_info

    def sync(self, domain: str) -> Domain:
        """Refresh local status/expiry from the registry (never billable)."""
        data = self._request("POST", f"/domains/{to_punycode(domain)}/sync")
        payload = (data or {}).get("domain", data) if isinstance(data, dict) else {}
        return Domain.model_validate(payload if isinstance(payload, dict) else {"domain_name": domain})

    def whois(self, domain: str) -> dict[str, Any]:
        """WHMCS-shaped availability equivalent derived from ``check()``."""
        rows = self.check(domain)
        row = rows[0] if rows else None
        return {"status": "available" if row is not None and row.available else "unavailable"}

    # -- contacts (whois) --
    def get_whois(self, domain: str) -> dict[str, Any]:
        """Registrant + admin contacts currently held at the registry."""
        data = self._request("GET", f"/domains/{to_punycode(domain)}/whois")
        return data if isinstance(data, dict) else {}

    get_contacts = get_whois

    def update_whois(
        self,
        domain: str,
        registrant: Contact | dict[str, Any],
        admin: Contact | dict[str, Any] | None = None,
        *,
        same_contact: bool = False,
    ) -> dict[str, Any]:
        """Replace registrant/admin contacts at the registry."""
        body: dict[str, Any] = {"registrant": _contact_payload(registrant)}
        if same_contact:
            body["same_contact"] = True
        elif admin is not None:
            body["admin"] = _contact_payload(admin)
        else:
            body["same_contact"] = True
        data = self._request("POST", f"/domains/{to_punycode(domain)}/whois", json=body)
        return data if isinstance(data, dict) else {}

    set_contacts = update_whois

    # -- registration / renewal / transfer --
    def register(
        self,
        domain: str,
        *,
        contact: Contact | dict[str, Any],
        years: int = 1,
        period: int | None = None,
        nameservers: list[str] | None = None,
        admin: Contact | dict[str, Any] | None = None,
        same_contact: bool = True,
        provision_dns: bool = True,
        whois_protection: bool | None = None,  # noqa: ARG002 - accepted for spaceship signature compat
        auto_renew: bool | None = None,  # noqa: ARG002 - accepted for compat; registry default applies
        wait: bool = True,  # noqa: ARG002 - synchronous API; accepted for compat
        timeout: float = 30.0,  # noqa: ARG002 - accepted for compat
        poll_interval: float = 5.0,  # noqa: ARG002 - accepted for compat
    ) -> Domain:
        """Register a domain (charges the reseller balance on registry success)."""
        name = to_punycode(domain)
        body: dict[str, Any] = {
            "domain_name": name,
            "period": int(period if period is not None else years),
            "nameservers": [str(ns).strip().rstrip(".") for ns in (nameservers or []) if str(ns).strip()],
            "registrant": _contact_payload(contact),
            "same_contact": bool(same_contact and admin is None),
            "provision_dns": bool(provision_dns),
        }
        if admin is not None:
            body["admin"] = _contact_payload(admin)
        data = self._request("POST", "/domains/register", json=body)
        payload = (data or {}).get("domain", data) if isinstance(data, dict) else {}
        return Domain.model_validate(payload if isinstance(payload, dict) else {"domain_name": name})

    def renew(
        self,
        domain: str,
        *,
        years: int = 1,
        period: int | None = None,
        wait: bool = True,  # noqa: ARG002 - accepted for compat
        timeout: float = 30.0,  # noqa: ARG002 - accepted for compat
        poll_interval: float = 5.0,  # noqa: ARG002 - accepted for compat
    ) -> Domain:
        """Renew an owned domain (charged on registry success)."""
        name = to_punycode(domain)
        data = self._request(
            "POST",
            f"/domains/{name}/renew",
            json={"period": int(period if period is not None else years)},
        )
        payload = (data or {}).get("domain", data) if isinstance(data, dict) else {}
        return Domain.model_validate(payload if isinstance(payload, dict) else {"domain_name": name})

    def transfer(
        self,
        domain: str,
        *,
        contact: Contact | dict[str, Any] | None = None,
        auth_code: str | None = None,
        registrant: Contact | dict[str, Any] | None = None,
        admin: Contact | dict[str, Any] | None = None,
        wait: bool = True,  # noqa: ARG002 - accepted for compat
        timeout: float = 30.0,  # noqa: ARG002 - accepted for compat
        poll_interval: float = 5.0,  # noqa: ARG002 - accepted for compat
    ) -> Domain:
        """Submit a domain transfer (charged on registry success)."""
        name = to_punycode(domain)
        body: dict[str, Any] = {"auth_code": auth_code or ""}
        reg = registrant if registrant is not None else contact
        if reg is not None:
            body["registrant"] = _contact_payload(reg)
        if admin is not None:
            body["admin"] = _contact_payload(admin)
        data = self._request("POST", f"/domains/{name}/transfer", json=body)
        payload = (data or {}).get("domain", data) if isinstance(data, dict) else {}
        return Domain.model_validate(payload if isinstance(payload, dict) else {"domain_name": name})

    # -- nameservers --
    def get_nameservers(self, domain: str) -> list[str]:
        data = self._request("GET", f"/domains/{to_punycode(domain)}/nameservers")
        payload = data if isinstance(data, dict) else {}
        hosts = payload.get("nameservers", [])
        return [str(h) for h in hosts if str(h).strip()]

    def set_nameservers(self, domain: str, hosts: list[str] | None, *, provision_dns: bool = True) -> list[str]:
        data = self._request(
            "POST",
            f"/domains/{to_punycode(domain)}/nameservers",
            json={
                "nameservers": [str(h).strip().rstrip(".") for h in (hosts or []) if str(h).strip()],
                "provision_dns": bool(provision_dns),
            },
        )
        payload = data if isinstance(data, dict) else {}
        return [str(h) for h in payload.get("nameservers", []) if str(h).strip()]

    # -- lock / privacy / EPP --
    def get_lock(self, domain: str) -> bool:
        data = self._request("GET", f"/domains/{to_punycode(domain)}/lock")
        payload = data if isinstance(data, dict) else {}
        return bool(payload.get("locked", False))

    def set_lock(self, domain: str, locked: bool) -> bool:
        data = self._request("PUT", f"/domains/{to_punycode(domain)}/lock", json={"locked": bool(locked)})
        payload = data if isinstance(data, dict) else {}
        return bool(payload.get("locked", locked))

    def lock(self, domain: str) -> bool:
        return self.set_lock(domain, True)

    def unlock(self, domain: str) -> bool:
        return self.set_lock(domain, False)

    def get_privacy(self, domain: str) -> bool:
        data = self._request("GET", f"/domains/{to_punycode(domain)}/privacy")
        payload = data if isinstance(data, dict) else {}
        return bool(payload.get("enabled", False))

    def set_privacy(self, domain: str, enabled: bool) -> bool:
        data = self._request("PUT", f"/domains/{to_punycode(domain)}/privacy", json={"enabled": bool(enabled)})
        payload = data if isinstance(data, dict) else {}
        return bool(payload.get("enabled", enabled))

    def request_epp_code(self, domain: str) -> str:
        data = self._request("POST", f"/domains/{to_punycode(domain)}/epp-code")
        payload = data if isinstance(data, dict) else {}
        return str(payload.get("epp_code") or "")

    get_auth_code = request_epp_code

    def set_epp_code(self, domain: str, epp_code: str) -> None:
        self._request("PUT", f"/domains/{to_punycode(domain)}/epp-code", json={"epp_code": epp_code})

    def set_autorenew(self, domain: str, enabled: bool):  # noqa: ARG002
        raise NotSupportedError(
            "set_autorenew() has no reseller.co.tz endpoint.",
            alternative="Renew explicitly via renew().",
        )

    def get_tld_list(self) -> list:
        raise NotSupportedError(
            "get_tld_list() has no reseller.co.tz endpoint.",
            alternative="Derive supported TLDs from availability checks.",
        )

    def suggest(self, domain: str, **params: Any) -> list:
        raise NotSupportedError(
            f"suggest({domain}) has no reseller.co.tz endpoint.",
            alternative="Fan check() out over candidate FQDNs instead.",
        )
