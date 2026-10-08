"""Bulk availability checks. Run: python examples/check_availability.py example.co.tz example.com"""

from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from resellercotz import ResellerCoTz  # noqa: E402


def main() -> None:
    domains = sys.argv[1:] or ["example.co.tz", "example.com"]
    rc = ResellerCoTz()
    for row in rc.domains.check(*domains):
        flag = "premium" if row.premium else "standard"
        print(f"{row.domain}: {'available' if row.available else 'taken'} ({flag}) price={row.price} {row.currency}")


if __name__ == "__main__":
    main()
