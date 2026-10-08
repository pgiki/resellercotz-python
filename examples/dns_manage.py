"""DNS management (mutating). Run: python examples/dns_manage.py example.co.tz --apply"""

from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from resellercotz import ResellerCoTz  # noqa: E402


def main() -> None:
    zone = sys.argv[1] if len(sys.argv) > 1 else "example.co.tz"
    apply = "--apply" in sys.argv
    rc = ResellerCoTz()
    print(rc.dns.get_status(zone))
    for rec in rc.dns.list(zone):
        print(rec.line, rec.type, rec.name, rec.value)
    if not apply:
        print("dry-run: pass --apply to write.")
        return
    if input("Type YES to modify DNS: ") != "YES":
        print("aborted.")
        return
    print(rc.dns.set_a_records(zone, zone, "192.0.2.10"))


if __name__ == "__main__":
    main()
