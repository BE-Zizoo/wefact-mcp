"""Thin HTTP client for the WeFact API v2.

Transport facts (see docs/wefact-api-reference.md):
- Single endpoint, POST only, application/x-www-form-urlencoded.
- Nested params use PHP bracket notation: InvoiceLines[0][ProductCode]=P0001
- Auth is the POST field ``api_key``; routing via ``controller`` + ``action``.
- The JSON body carries ``status`` = "success" | "error" and ``errors`` [].
- Rate limit: 200/min, 3600/hour per IP. Breaching it gets the IP firewalled
  (HTTP 403), so we never retry on 403.
"""

from __future__ import annotations

import time
from typing import Any

import httpx

DEFAULT_BASE_URL = "https://api.mijnwefact.nl/v2/"
DEFAULT_PAGE_SIZE = 1000  # WeFact's own default/maximum page size

# HTTP statuses that are worth retrying. 403 is deliberately absent: WeFact
# uses it for "IP blocked", and hammering it only extends the block.
RETRYABLE_STATUS = {429, 500, 502, 503, 504}


class WeFactError(Exception):
    """Raised for any failed WeFact call: API-level error, HTTP error or
    exhausted retries. ``to_dict()`` gives a structured, LLM-friendly view."""

    def __init__(
        self,
        message: str,
        *,
        controller: str = "",
        action: str = "",
        errors: list[str] | None = None,
        http_status: int | None = None,
    ) -> None:
        super().__init__(message)
        self.controller = controller
        self.action = action
        self.errors = errors or []
        self.http_status = http_status

    def to_dict(self) -> dict[str, Any]:
        return {
            "status": "error",
            "controller": self.controller,
            "action": self.action,
            "message": str(self),
            "errors": self.errors,
            "http_status": self.http_status,
        }


def flatten_params(data: Any, prefix: str = "") -> list[tuple[str, str]]:
    """Flatten nested dicts/lists into PHP-style form fields.

    {"InvoiceLines": [{"ProductCode": "P1"}]} ->
    [("InvoiceLines[0][ProductCode]", "P1")]
    """
    out: list[tuple[str, str]] = []
    if isinstance(data, dict):
        for key, value in data.items():
            name = f"{prefix}[{key}]" if prefix else str(key)
            out.extend(flatten_params(value, name))
    elif isinstance(data, (list, tuple)):
        for index, value in enumerate(data):
            out.extend(flatten_params(value, f"{prefix}[{index}]"))
    elif isinstance(data, bool):
        out.append((prefix, "1" if data else "0"))
    elif data is None:
        out.append((prefix, ""))
    else:
        out.append((prefix, str(data)))
    return out


class WeFactClient:
    def __init__(
        self,
        api_key: str,
        *,
        base_url: str = DEFAULT_BASE_URL,
        timeout: float = 30.0,
        max_retries: int = 3,
        backoff_base: float = 0.5,
        transport: httpx.BaseTransport | None = None,
        sleep=time.sleep,
    ) -> None:
        if not api_key:
            raise ValueError("WeFact api_key is required")
        self.api_key = api_key
        self.base_url = base_url
        self.max_retries = max_retries
        self.backoff_base = backoff_base
        self._sleep = sleep
        self._http = httpx.Client(timeout=timeout, transport=transport)

    def close(self) -> None:
        self._http.close()

    # -- core -----------------------------------------------------------

    def request(self, controller: str, action: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
        """Perform one WeFact call and return the parsed JSON body.

        Raises WeFactError when the API reports status=error, on a
        non-retryable HTTP error, or when retries are exhausted.
        """
        body = {"api_key": self.api_key, "controller": controller, "action": action}
        form = dict(flatten_params(body) + flatten_params(params or {}))

        attempt = 0
        while True:
            try:
                response = self._http.post(self.base_url, data=form)
            except httpx.TransportError as exc:  # timeouts, connection errors
                if attempt >= self.max_retries:
                    raise WeFactError(
                        f"Network error after {attempt + 1} attempts: {exc}",
                        controller=controller, action=action,
                    ) from exc
                self._backoff(attempt)
                attempt += 1
                continue

            if response.status_code in RETRYABLE_STATUS and attempt < self.max_retries:
                self._backoff(attempt)
                attempt += 1
                continue

            if response.status_code >= 400:
                raise WeFactError(
                    f"HTTP {response.status_code} from WeFact: {response.text[:300]}",
                    controller=controller, action=action, http_status=response.status_code,
                )

            try:
                payload = response.json()
            except ValueError as exc:
                raise WeFactError(
                    f"WeFact returned non-JSON body: {response.text[:300]}",
                    controller=controller, action=action, http_status=response.status_code,
                ) from exc

            if payload.get("status") != "success":
                errors = payload.get("errors") or []
                raise WeFactError(
                    "; ".join(errors) or "WeFact returned status=error",
                    controller=controller, action=action, errors=list(errors),
                    http_status=response.status_code,
                )
            return payload

    def _backoff(self, attempt: int) -> None:
        self._sleep(self.backoff_base * (2 ** attempt))

    # -- pagination -----------------------------------------------------

    def list_all(
        self,
        controller: str,
        params: dict[str, Any] | None = None,
        *,
        result_key: str | None = None,
        page_size: int = DEFAULT_PAGE_SIZE,
        max_items: int | None = None,
    ) -> dict[str, Any]:
        """Iterate ``action=list`` over all pages and merge the results.

        Returns {"totalresults": N, "currentresults": len(items), "<key>": [...]}
        using the plural key WeFact uses (e.g. "debtors").
        """
        key = result_key or f"{controller}s"
        params = dict(params or {})
        items: list[Any] = []
        offset = int(params.pop("offset", 0) or 0)
        total: int | None = None

        while True:
            page = self.request(controller, "list", {**params, "offset": offset, "limit": page_size})
            batch = page.get(key) or []
            items.extend(batch)
            total = int(page.get("totalresults", len(items)))
            offset += len(batch)
            if not batch or offset >= total or (max_items and len(items) >= max_items):
                break

        if max_items:
            items = items[:max_items]
        return {"totalresults": total, "currentresults": len(items), key: items}
