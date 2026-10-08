"""Base transport for all reseller.co.tz endpoint groups."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

import httpx

from ..errors import ResellerCoTzError
from ..logging import get_logger

if TYPE_CHECKING:
    from ..client import ResellerCoTz

logger = get_logger("api")


class BaseAPI:
    """Shared request handling: auth headers, envelope unwrap, error mapping."""

    def __init__(self, client: ResellerCoTz) -> None:
        self._client = client

    @property
    def _http(self) -> httpx.Client:
        return self._client._http

    def _url(self, path: str) -> str:
        base = self._client.config.base_url.rstrip("/")
        return f"{base}/{path.lstrip('/')}"

    def _headers(self, extra: dict[str, str] | None = None) -> dict[str, str]:
        headers = {
            "X-API-KEY": self._client.config.api_key,
            "Accept": "application/json",
        }
        if extra:
            headers.update(extra)
        return headers

    def _raise_for_envelope(self, response: httpx.Response, payload: Any) -> Any:
        if isinstance(payload, dict) and "success" in payload:
            if payload.get("success") is True:
                return payload.get("data")
            raise ResellerCoTzError.from_response(response.status_code, payload)
        if response.status_code >= 400:
            raise ResellerCoTzError.from_response(response.status_code, payload)
        return payload

    def _request(
        self,
        method: str,
        path: str,
        *,
        params: dict[str, Any] | None = None,
        json: Any | None = None,
    ) -> Any:
        """Send a request and return the unwrapped ``data`` payload."""
        try:
            response = self._http.request(
                method,
                self._url(path),
                params=params,
                json=json,
                headers=self._headers({"Content-Type": "application/json"} if json is not None else None),
            )
        except ResellerCoTzError:
            raise
        except Exception as e:
            raise ResellerCoTzError(f"Request failed: {e}") from e
        if response.status_code == 204 or not response.content:
            if response.status_code >= 400:
                raise ResellerCoTzError.from_response(response.status_code, None)
            return None
        try:
            payload = response.json()
        except Exception as e:
            raise ResellerCoTzError(f"Invalid JSON response: {e}", response.status_code) from e
        return self._raise_for_envelope(response, payload)
