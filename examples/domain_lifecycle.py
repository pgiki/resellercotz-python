"""Domain lifecycle (charged). Run: python examples/domain_lifecycle.py example.co.tz --apply"""

from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from resellercotz import ResellerCoTz  # noqa: E402

CONTACT = {
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


def main() -> None:
    domain = sys.argv[1] if len(sys.argv) > 1 else "example.co.tz"
    apply = "--apply" in sys.argv
    rc = ResellerCoTz()
    info = rc.domains.get_info(domain)
    print(info)
    if not apply:
        print("dry-run: pass --apply to register/renew.")
        return
    if input("Type YES to spend money: ") != "YES":
        print("aborted.")
        return
    print(rc.domains.register(domain, contact=CONTACT, years=1, nameservers=["ns1.example.co.tz", "ns2.example.co.tz"]))
    print(rc.domains.renew(domain, years=1))


if __name__ == "__main__":
    main()
