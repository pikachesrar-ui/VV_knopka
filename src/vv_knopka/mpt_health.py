from __future__ import annotations

import httpx

from .settings import Settings


def require_mpt_available(settings: Settings, *, timeout_seconds: float = 3.0) -> None:
    """Fail early with an actionable message when the local MPT API is offline."""
    base_url = str(settings.mpt_base_url).rstrip("/")
    try:
        with httpx.Client(timeout=timeout_seconds, follow_redirects=True) as client:
            # /docs is part of MoneyPrinterTurbo's documented local API surface.
            # Any non-5xx HTTP response proves that the service is reachable; the
            # render request itself remains responsible for API-level validation.
            response = client.get(f"{base_url}/docs")
    except httpx.RequestError as exc:
        raise RuntimeError(
            "MoneyPrinterTurbo API is not reachable at "
            f"{base_url}. Start MoneyPrinterTurbo in another terminal from its project root "
            "with `uv run python main.py` (or `python main.py` in its active environment), "
            "then retry `vv render-ai SLOT`."
        ) from exc

    if response.status_code >= 500:
        raise RuntimeError(
            f"MoneyPrinterTurbo API is reachable at {base_url} but returned HTTP "
            f"{response.status_code} from /docs. Check the MPT terminal before rendering."
        )
