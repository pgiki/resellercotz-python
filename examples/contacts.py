"""Whois contacts. Run: python examples/contacts.py example.co.tz"""

from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from resellercotz import ResellerCoTz  # noqa: E402


def main() -> None:
    domain = sys.argv[1] if len(sys.argv) > 1 else "example.co.tz"
    rc = ResellerCoTz()
    print(rc.domains.get_whois(domain))


if __name__ == "__main__":
    main()
