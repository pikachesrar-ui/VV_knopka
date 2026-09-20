"""Bounded retries for idempotent stock-media GET requests only."""

from __future__ import annotations

import time
from typing import Any

import httpx


RETRYABLE_STOCK_ERRORS = (httpx.ConnectError, httpx.ConnectTimeout, httpx.ReadError, httpx.ReadTimeout)
RETRY_DELAYS_SECONDS = (2, 6)


def get_stock(client: httpx.Client, url: str, **kwargs: Any) -> httpx.Response:
    for attempt in range(3):
        try:
            return client.get(url, **kwargs)
        except RETRYABLE_STOCK_ERRORS:
            if attempt == 2:
                raise
            time.sleep(RETRY_DELAYS_SECONDS[attempt])
    raise AssertionError("unreachable")
