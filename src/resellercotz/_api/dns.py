"""DNS record management (``/domains/{domain}/dns``).

DNS management is a per-domain addon: it must be provisioned before records
can be edited. ``ensure()``/auto-provision helpers below call
``POST .../dns/provision`` on demand.
"""

from __future__ import annotations

from typing import Any

from ..idn import to_punycode
from ..models import DNSRecord, DNSService
from .base import BaseAPI

#: Page size kept for spaceship signature compat (API returns full zone).
PAGE_SIZE = 100


class DnsAPI(BaseAPI):
    """DNS resource records for domains with the DNS management addon."""

    @staticmethod
    def _zone(zone: str) -> str:
        return to_punycode(zone)

    @staticmethod
    def _short_name(name: str, zone: str) -> str:
        n = (name or "").strip().rstrip(".").lower()
        z = zone.strip().rstrip(".").lower()
        if not n or n == "@" or n == z:
            return "@"
        if n.endswith("." + z):
            return n[: -(len(z) + 1)]
        return n

    # -- addon lifecycle --
    def get_status(self, zone: str) -> DNSService:
        data = self._request("GET", f"/domains/{self._zone(zone)}/dns")
        payload = (data or {}).get("dns_service", {}) if isinstance(data, dict) else {}
        service = DNSService.model_validate(payload if isinstance(payload, dict) else {})
        if not service.zone:
            service.zone = self._zone(zone)
        return service

    def provision(self, zone: str) -> DNSService:
        data = self._request("POST", f"/domains/{self._zone(zone)}/dns/provision")
        payload = (data or {}).get("dns_service", data) if isinstance(data, dict) else {}
        service = DNSService.model_validate(payload if isinstance(payload, dict) else {})
        if not service.zone:
            service.zone = self._zone(zone)
        return service

    def cancel(self, zone: str) -> DNSService:
        data = self._request("DELETE", f"/domains/{self._zone(zone)}/dns")
        payload = (data or {}).get("dns_service", data) if isinstance(data, dict) else {}
        service = DNSService.model_validate(payload if isinstance(payload, dict) else {})
        if not service.zone:
            service.zone = self._zone(zone)
        return service

    def ensure(self, zone: str) -> DNSService:
        """Return active addon state, provisioning it when inactive."""
        service = self.get_status(zone)
        if service.active:
            return service
        return self.provision(zone)

    # -- records --
    def _parse_records(self, data: Any) -> list[DNSRecord]:
        rows = (data or {}).get("records", []) if isinstance(data, dict) else []
        return [DNSRecord.from_api(r) for r in rows if isinstance(r, dict)]

    def get(self, zone: str, *, page: int = 1, page_size: int = PAGE_SIZE) -> list[DNSRecord]:  # noqa: ARG002
        """Records for a zone (full zone; page args kept for compat)."""
        data = self._request("GET", f"/domains/{self._zone(zone)}/dns")
        return self._parse_records(data)

    def list(self, zone: str) -> list[DNSRecord]:
        """All records for a zone."""
        return self.get(zone)

    def set(self, zone: str, records: list[DNSRecord | dict[str, Any]], *, force: bool = True) -> list[DNSRecord]:  # noqa: ARG002
        """Replace the whole zone (delete-all + create loop; no native endpoint)."""
        z = self._zone(zone)
        self.ensure(z)
        existing = self.list(z)
        for rec in existing:
            if rec.line is not None:
                self.delete_by_line(z, rec.line)
        out: list[DNSRecord] = []
        for item in records:
            rec = item if isinstance(item, DNSRecord) else DNSRecord.from_api(dict(item))
            out.append(
                self.create_record(
                    z,
                    rec.name,
                    rec.type,
                    rec.value or "",
                    ttl=rec.ttl,
                    prio=rec.priority or 0,
                    replace_existing=True,
                )
            )
        return out

    def add(self, zone: str, record: DNSRecord | dict[str, Any]) -> DNSRecord:
        """Append one record; returns the created record."""
        rec = record if isinstance(record, DNSRecord) else DNSRecord.from_api(dict(record))
        return self.create_record(
            zone,
            rec.name,
            rec.type,
            rec.value or "",
            ttl=rec.ttl,
            prio=rec.priority or 0,
            replace_existing=bool(rec.replace_existing),
        )

    def create_record(
        self,
        zone: str,
        name: str,
        record_type: str,
        content: str,
        ttl: int | None = None,
        *,
        prio: int = 0,
        priority: int | None = None,
        port: Any = None,  # noqa: ARG002 - accepted for spaceship signature compat
        weight: Any = None,  # noqa: ARG002 - accepted for spaceship signature compat
        replace_existing: bool = False,
    ) -> DNSRecord:
        """Create one record; returns it in API form."""
        z = self._zone(zone)
        body: dict[str, Any] = {
            "type": record_type.upper(),
            "name": self._short_name(name, z),
            "value": content,
        }
        if ttl is not None:
            body["ttl"] = int(ttl)
        effective_prio = int(priority) if priority is not None else int(prio)
        if effective_prio:
            body["priority"] = effective_prio
        if replace_existing:
            body["replace_existing"] = True
        data = self._request("POST", f"/domains/{z}/dns/records", json=body)
        rows = self._parse_records(data)
        if rows:
            return rows[0]
        return DNSRecord(
            type=record_type.upper(),
            name=self._short_name(name, z),
            value=content,
            ttl=ttl,
            priority=effective_prio or None,
        )

    def update_record(
        self,
        zone: str,
        record_id: str | int,
        *,
        content: str | None = None,
        value: str | None = None,
        ttl: int | None = None,
        prio: int | None = None,
        priority: int | None = None,
        record_type: str | None = None,
        name: str | None = None,
        port: Any = None,  # noqa: ARG002 - accepted for compat
        weight: Any = None,  # noqa: ARG002 - accepted for compat
    ) -> DNSRecord:
        """Update a record by line/ID; returns the updated record."""
        z = self._zone(zone)
        current: DNSRecord | None = None
        if name is not None or record_type is not None:
            for row in self.list(z):
                if str(row.line) == str(record_id):
                    current = row
                    break
        body: dict[str, Any] = {}
        body["type"] = (record_type or (current.type if current else "A")).upper()
        body["name"] = name if name is not None else (current.name if current else "@")
        new_value = content if content is not None else value
        if new_value is None and current is not None:
            new_value = current.value or ""
        body["value"] = new_value or ""
        new_ttl = ttl if ttl is not None else (current.ttl if current else None)
        if new_ttl is not None:
            body["ttl"] = int(new_ttl)
        new_prio = priority if priority is not None else prio
        if new_prio is None and current is not None:
            new_prio = current.priority
        if new_prio:
            body["priority"] = int(new_prio)
        data = self._request("PUT", f"/domains/{z}/dns/records/{record_id}", json=body)
        rows = self._parse_records(data)
        if rows:
            return rows[0]
        return DNSRecord.from_api({**body, "line": record_id})

    def delete_by_line(self, zone: str, record_id: str | int) -> None:
        self._request("DELETE", f"/domains/{self._zone(zone)}/dns/records/{record_id}")

    def delete(
        self,
        zone: str,
        *,
        name: str | None = None,
        record_type: str | None = None,
        value: str | None = None,
        content: str | None = None,
    ) -> int:
        """Delete matching records; returns deleted count."""
        z = self._zone(zone)
        want_value = value if value is not None else content
        short = self._short_name(name, z) if name else None
        rows = self.list(z)
        doomed = [
            r
            for r in rows
            if (short is None or r.name.lower() == short)
            and (record_type is None or r.type.upper() == record_type.upper())
            and (want_value is None or (r.value or "") == want_value)
        ]
        if short is None and record_type is None and want_value is None:
            return 0
        for rec in doomed:
            if rec.line is not None:
                self.delete_by_line(z, rec.line)
        return len(doomed)

    def delete_exact(self, zone: str, records: list[DNSRecord | dict[str, Any]]) -> None:
        """Delete exact records by line where known, else by match."""
        z = self._zone(zone)
        for item in records:
            rec = item if isinstance(item, DNSRecord) else DNSRecord.from_api(dict(item))
            if rec.line is not None:
                self.delete_by_line(z, rec.line)
            else:
                self.delete(z, name=rec.name, record_type=rec.type, value=rec.value)

    def delete_records_by_type(self, zone: str, record_type: str, name: str | None = None) -> int:
        return self.delete(zone, name=name, record_type=record_type)

    def delete_record(self, zone: str, record_id: str | int) -> None:
        self.delete_by_line(zone, record_id)

    # -- fikashop-style record conveniences --
    def set_a_records(
        self,
        zone: str,
        domain: str,
        ip: str,
        include_www: bool = True,
        include_wildcard: bool = False,
        ttl: int | None = None,
    ) -> list[DNSRecord]:
        """Replace A records for ``domain`` (+www/wildcard) with ``ip``."""
        z = self._zone(zone)
        self.ensure(z)
        names = {self._short_name(domain, z)}
        if include_www:
            names.add(self._short_name(f"www.{domain.rstrip('.')}", z))
        if include_wildcard:
            names.add(self._short_name(f"*.{domain.rstrip('.')}", z))
        for short in names:
            self.delete(z, name=short, record_type="A")
        for short in sorted(names):
            body: dict[str, Any] = {"type": "A", "name": short, "value": ip, "replace_existing": True}
            if ttl is not None:
                body["ttl"] = int(ttl)
            self._request("POST", f"/domains/{z}/dns/records", json=body)
        return self.list(z)
