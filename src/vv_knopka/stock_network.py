"""Bounded retries for idempotent stock-media GET requests only."""

from __future__ import annotations

import time
from typing import Any
from urllib.parse import urlsplit, urlunsplit

import httpx


RETRYABLE_STOCK_ERRORS = (httpx.ConnectError, httpx.ConnectTimeout, httpx.ReadError, httpx.ReadTimeout)
RETRYABLE_STATUS_CODES = {429, 500, 502, 503, 504}
RETRY_DELAYS_SECONDS = (2, 6)


def _safe_url(url: str) -> str:
    """Return a log-safe provider URL without credentials or query values."""
    parts = urlsplit(str(url))
    return urlunsplit((parts.scheme, parts.netloc, parts.path, "", ""))


def get_stock(client: httpx.Client, url: str, **kwargs: Any) -> httpx.Response:
    for attempt in range(3):
        try:
            response = client.get(url, **kwargs)
            response.raise_for_status()
            return response
        except httpx.HTTPStatusError as exc:
            status = int(exc.response.status_code)
            if status not in RETRYABLE_STATUS_CODES or attempt == 2:
                raise RuntimeError(
                    f"stock provider returned HTTP {status} for {_safe_url(url)}"
                ) from None
        except RETRYABLE_STOCK_ERRORS as exc:
            if attempt == 2:
                raise RuntimeError(
                    f"stock provider request failed for {_safe_url(url)} ({type(exc).__name__})"
                ) from None
        if attempt < 2:
            time.sleep(RETRY_DELAYS_SECONDS[attempt])
    raise AssertionError("unreachable")
