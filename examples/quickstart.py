"""Availability check (free). Run: python examples/quickstart.py example.co.tz"""

from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from resellercotz import ResellerCoTz  # noqa: E402


def main() -> None:
    domain = sys.argv[1] if len(sys.argv) > 1 else "example.co.tz"
    rc = ResellerCoTz()
    (row,) = rc.domains.check(domain)
    print(f"{row.domain}: {'available' if row.available else 'unavailable'} price={row.price} {row.currency}")


if __name__ == "__main__":
    main()
