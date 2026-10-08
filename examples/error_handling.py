"""Error shapes (offline). Run: python examples/error_handling.py"""

from __future__ import annotations

from resellercotz import NotSupportedError, ResellerCoTzError


def main() -> None:
    err = ResellerCoTzError.from_response(
        422, {"success": False, "message": "Registry failed.", "errors": {"registry": ["x"]}}
    )
    print(err)
    try:
        raise NotSupportedError("suggest() has no endpoint.", alternative="Fan check() out instead.")
    except NotSupportedError as e:
        print(e)


if __name__ == "__main__":
    main()
