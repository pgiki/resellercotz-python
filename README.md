# resellercotz-python

A friendly Python SDK for the [reseller.co.tz API](https://reseller.co.tz/api-docs) (domains, DNS).

Mirrors the `spaceship-python` surface where possible so it plugs into
fikashop as an additional registrar/DNS provider.

```python
from resellercotz import ResellerCoTz

rc = ResellerCoTz()  # reads RESELLER_API_KEY from env
checks = rc.domains.check("example.co.tz")
print(checks[0].available, checks[0].price)
```

## Install

```bash
pip install resellercotz-python
```

Requires Python ≥ 3.12. Dependencies: `httpx`, `pydantic`, `python-dotenv`.

## Authentication

Create a reseller account at [reseller.co.tz](https://reseller.co.tz/register),
then copy the reseller API key:

```bash
RESELLER_API_KEY=...
RESELLER_BASE_URL=https://reseller.co.tz/api/v1  # optional override
```

```python
rc = ResellerCoTz(api_key="...")
rc = ResellerCoTz.from_env_file(".env.prod")
```

Domain endpoints use `X-API-KEY`. (SMS endpoints use a separate bearer
token and are out of scope for this SDK.)

## Examples

Runnable end-to-end scripts in `examples/` (run from the repo root, e.g.
`python examples/quickstart.py`). ⚠️ marks scripts that can spend money or
mutate live state — those require explicit confirmation:

| Script | What it shows |
|---|---|
| `quickstart.py` | Availability check (free). |
| `check_availability.py` | Bulk checks, premium vs standard pricing. |
| `domain_lifecycle.py` ⚠️ | `register/renew/transfer` (charged) + `info`/`sync`; whois + nameservers + lock. |
| `contacts.py` | Whois read/update. |
| `dns_manage.py` ⚠️ | Provision/add/update/delete; dry-run by default, `--apply` + YES to write. |
| `error_handling.py` | Error shapes, unsupported endpoints (offline). |

## Endpoint coverage (v1)

Domains: `check`, `list`, `info`, `register`, `renew`, `transfer`,
`whois` (get/update), `nameservers` (get/set), `lock` (get/set),
`privacy` (get/set), `epp-code` (request/set), `sync`.

DNS: `status`, `provision`, `cancel`, record `list/create/update/delete`,
plus `set_a_records` convenience.

Not wrapped (parity with `NotSupportedError`): SMS send/logs,
child-nameservers/glue, `register-cancelled` re-register, TLD catalog,
`suggest()`.

## Testing

Fully offline (mock transport, no network, no spend):

```bash
pytest
ruff check src/ tests/
```
