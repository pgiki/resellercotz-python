"""Offline tests for resellercotz-python (no network)."""

from __future__ import annotations

import os
from datetime import date
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from resellercotz import (
    ConfigurationError,
    Contact,
    Domain,
    DomainCheck,
    NotSupportedError,
    ResellerCoTz,
    ResellerCoTzError,
)
from resellercotz.idn import from_punycode, to_punycode


def _client(**overrides):
    os.environ.update({"RESELLER_API_KEY": "key"})
    kwargs = {"api_key": "key"}
    kwargs.update(overrides)
    return ResellerCoTz(**kwargs)


def _response(status=200, payload=None):
    import json as jsonlib

    return SimpleNamespace(
        status_code=status,
        headers={},
        content=jsonlib.dumps(payload).encode() if payload is not None else b"",
        json=(lambda: payload),
    )


def _ok_data(data, message="OK"):
    return _response(200, {"success": True, "message": message, "data": data})


def test_config_missing_raises():
    os.environ.pop("RESELLER_API_KEY", None)
    with pytest.raises(ConfigurationError):
        ResellerCoTz()
    os.environ.update({"RESELLER_API_KEY": "k"})


def test_config_invalid_log_level():
    with pytest.raises(ConfigurationError):
        ResellerCoTz(api_key="k", log_level="VERBOSE")


def test_client_context_manager():
    rc = _client()
    rc._http = MagicMock()
    with rc as ctx:
        assert ctx is rc
    rc._http.close.assert_called_once()


def test_auth_headers():
    rc = _client(api_key="K")
    captured = {}

    def fake_request(method, url, **kwargs):
        captured.update(kwargs.get("headers") or {})
        return _ok_data({})

    rc._http = MagicMock()
    rc._http.request.side_effect = fake_request
    from resellercotz._api.base import BaseAPI

    BaseAPI(rc)._request("GET", "/domains")
    assert captured["X-API-KEY"] == "K"
    assert captured["Accept"] == "application/json"


def test_error_envelope_registry():
    rc = _client()
    rc._http = MagicMock()
    rc._http.request.return_value = _response(
        422,
        {"success": False, "message": "Registry failed.", "errors": {"registry": ["Registry failed."]}},
    )
    from resellercotz._api.base import BaseAPI

    with pytest.raises(ResellerCoTzError) as exc_info:
        BaseAPI(rc)._request("GET", "/domains/x")
    assert exc_info.value.status_code == 422
    assert exc_info.value.code == "registry"


def test_error_non_json_body():
    rc = _client()
    bad = SimpleNamespace(status_code=500, headers={}, content=b"oops", text="oops")
    bad.json = MagicMock(side_effect=ValueError("no json"))
    rc._http = MagicMock()
    rc._http.request.return_value = bad
    from resellercotz._api.base import BaseAPI

    with pytest.raises(ResellerCoTzError):
        BaseAPI(rc)._request("GET", "/x")


def test_not_supported_error_hint():
    err = NotSupportedError("No endpoint.", alternative="Use X instead.")
    assert "Use X instead." in str(err)


def test_idn_roundtrip():
    assert to_punycode("Example.CO.TZ.") == "example.co.tz"
    assert from_punycode("example.co.tz") == "example.co.tz"


def _transport(*responses):
    rc = _client()
    rc._http = MagicMock()
    rc._http.request.side_effect = list(responses)
    return rc


def _check_data(name="example.co.tz", available=True, registration=20000):
    return {
        "domain_name": name,
        "available": available,
        "bookable": available,
        "reserved": False,
        "premium": False,
        "price": {
            "registration": registration,
            "renewal": 20000,
            "transfer": 0,
            "premium_registration": None,
            "premium_sellable": False,
        },
    }


def _domain_data(name="example.co.tz"):
    return {
        "domain": {
            "id": 123,
            "domain_name": name,
            "status": "active",
            "registry_status": "active",
            "redemption_state": "grace",
            "in_redemption": False,
            "renewal_price": 20000,
            "redemption_price": None,
            "registration_date": "2026-05-28",
            "expiry_date": "2027-05-28",
            "lock_status": False,
            "privacy_status": False,
            "last_synced_at": "2026-05-28T12:00:00.000000Z",
        }
    }


def test_check_parses_pricing():
    rc = _transport(_ok_data(_check_data("cool.co.tz", True, 35000)))
    (row,) = rc.domains.check("cool.co.tz")
    assert isinstance(row, DomainCheck)
    assert row.available is True
    assert row.result == "available"
    assert str(row.price) == "35000"
    assert row.currency == "TZS"
    body = rc._http.request.call_args[1]["json"]
    assert body == {"domain_name": "cool.co.tz"}


def test_check_unavailable():
    rc = _transport(_ok_data(_check_data("taken.co.tz", False)))
    (row,) = rc.domains.check("taken.co.tz")
    assert row.available is False
    assert row.result == "unavailable"


def test_get_info_parses():
    rc = _transport(_ok_data(_domain_data()))
    d = rc.domains.get_info("Example.CO.TZ")
    assert isinstance(d, Domain)
    assert d.name == "example.co.tz"
    assert d.expiry_date is not None
    assert d.expiration_date is not None
    assert d.lock_status is False


@pytest.mark.parametrize(
    ("raw", "want"),
    [
        ("2027-05-28", date(2027, 5, 28)),
        ("10/15/2027", date(2027, 10, 15)),
        ("15/10/2027", date(2027, 10, 15)),
        ("not-a-date", None),
    ],
)
def test_domain_expiry_date_tolerates_wire_formats(raw, want):
    d = Domain(**{**_domain_data()["domain"], "expiry_date": raw})
    assert d.expiry_date == want
    assert (d.expiration_date.date() if d.expiration_date else None) == want


def test_list_parses():
    rc = _transport(
        _ok_data(
            {
                "domains": [_domain_data()["domain"]],
                "pagination": {"current_page": 1, "per_page": 25, "total": 1, "last_page": 1},
            }
        )
    )
    rows = rc.domains.list(q="example", page=1, page_size=25)
    assert len(rows) == 1
    assert rows[0].name == "example.co.tz"


def _contact_fields():
    return {
        "name": "Jane Doe",
        "organization": "Jane Doe Ltd",
        "address1": "123 Registry Road",
        "city": "Dar es Salaam",
        "state": "Dar es Salaam",
        "postcode": "11101",
        "country": "TZ",
        "phone": "+255.754123456",
        "email": "jane@example.co.tz",
    }


def test_register_body():
    rc = _transport(_response(201, {"success": True, "message": "Registered.", "data": _domain_data()}))
    out = rc.domains.register(
        "example.co.tz", contact=_contact_fields(), years=1, nameservers=["ns1.example.co.tz", "ns2.example.co.tz"]
    )
    assert isinstance(out, Domain)
    body = rc._http.request.call_args[1]["json"]
    assert body["domain_name"] == "example.co.tz"
    assert body["period"] == 1
    assert body["nameservers"] == ["ns1.example.co.tz", "ns2.example.co.tz"]
    assert body["registrant"]["name"] == "Jane Doe"
    assert body["same_contact"] is True


def test_renew_body():
    rc = _transport(_ok_data(_domain_data(), message="Domain renewed successfully."))
    out = rc.domains.renew("example.co.tz", years=2)
    assert isinstance(out, Domain)
    body = rc._http.request.call_args[1]["json"]
    assert body == {"period": 2}


def test_transfer_body():
    rc = _transport(_ok_data(_domain_data(), message="Transfer submitted."))
    out = rc.domains.transfer("example.co.tz", contact=_contact_fields(), auth_code="secret123")
    assert isinstance(out, Domain)
    body = rc._http.request.call_args[1]["json"]
    assert body["auth_code"] == "secret123"


def test_whois_and_nameservers_lock_privacy_epp():
    rc = _transport(
        _ok_data({"registrant": _contact_fields(), "admin": _contact_fields()}),
        _ok_data({"registrant": _contact_fields(), "admin": _contact_fields()}),
        _ok_data({"nameservers": ["ns1.example.co.tz", "ns2.example.co.tz"]}),
        _ok_data({"nameservers": ["ns1.example.co.tz", "ns2.example.co.tz"]}),
        _ok_data({"locked": True}),
        _ok_data({"locked": False}),
        _ok_data({"enabled": True}),
        _ok_data({"epp_code": "secret123"}),
    )
    assert "registrant" in rc.domains.get_whois("example.co.tz")
    rc.domains.update_whois("example.co.tz", _contact_fields(), same_contact=True)
    assert rc.domains.get_nameservers("example.co.tz") == ["ns1.example.co.tz", "ns2.example.co.tz"]
    assert rc.domains.set_nameservers("example.co.tz", ["ns1.example.co.tz"]) is not None
    assert rc.domains.lock("example.co.tz") is True
    assert rc.domains.unlock("example.co.tz") is False
    assert rc.domains.set_privacy("example.co.tz", True) is True
    assert rc.domains.request_epp_code("example.co.tz") == "secret123"


def test_contact_model_helpers():
    c = Contact.from_profile(
        firstname="Jane", lastname="Doe", email="j@x.test", address1="x", city="Dar", country="tz", phone="+255.1"
    )
    assert c.name == "Jane Doe"
    assert c.country == "TZ"
    assert c.split_name() == ("Jane", "Doe")
    fields = c.api_fields()
    assert fields["name"] == "Jane Doe"


def test_unsupported_endpoints_raise():
    rc = _client()
    with pytest.raises(NotSupportedError):
        rc.domains.get_tld_list()
    with pytest.raises(NotSupportedError):
        rc.domains.suggest("example.co.tz")


def _dns_list_data():
    return {
        "dns_service": {"id": 10, "status": "active", "zone": "example.co.tz"},
        "records": [
            {"line": 24, "type": "A", "name": "@", "value": "192.0.2.10", "ttl": 14400},
            {"line": 25, "type": "CNAME", "name": "www", "value": "example.co.tz", "ttl": 14400},
        ],
    }


def test_dns_list_and_name_translation():
    from resellercotz import DNSRecord

    rc = _transport(_ok_data(_dns_list_data()))
    rows = rc.dns.list("Example.CO.TZ.")
    assert [r.fqdn("example.co.tz") for r in rows] == ["example.co.tz", "www.example.co.tz"]
    assert rows[0].to_api() == {"type": "A", "name": "@", "value": "192.0.2.10", "ttl": 14400}
    assert DNSRecord(type="a", name="@", value="x").fqdn("example.co.tz") == "example.co.tz"


def test_dns_create_update_delete():
    rc = _transport(
        _ok_data({"records": [{"line": 26, "type": "A", "name": "shop", "value": "5.6.7.8", "ttl": 300}]}),
        _ok_data({"records": [{"line": 26, "type": "A", "name": "shop", "value": "5.6.7.9", "ttl": 300}]}),
        _ok_data({"records": []}),
    )
    created = rc.dns.create_record("example.co.tz", "shop", "A", "5.6.7.8", ttl=300)
    assert created.value == "5.6.7.8"
    updated = rc.dns.update_record("example.co.tz", 26, content="5.6.7.9")
    assert updated.value == "5.6.7.9"
    rc.dns.delete_record("example.co.tz", 26)
    assert rc._http.request.call_count == 3


def test_dns_set_a_records_provisions():
    rc = _transport(
        _ok_data({"dns_service": {"id": 10, "status": "active", "zone": "example.co.tz"}}),
        _ok_data(_dns_list_data()),
        _ok_data(_dns_list_data()),
        _ok_data(_dns_list_data()),
        _ok_data({"records": []}),
        _response(201, {"success": True, "message": "Created.", "data": {"records": []}}),
        _response(201, {"success": True, "message": "Created.", "data": {"records": []}}),
        _ok_data(_dns_list_data()),
    )
    out = rc.dns.set_a_records("example.co.tz", "example.co.tz", "9.9.9.9")
    assert isinstance(out, list)
