from __future__ import annotations

from dataclasses import dataclass
import os
import re
from typing import Any

import httpx


_SECRET_RE = re.compile(r"sk-[A-Za-z0-9_-]{8,}")


@dataclass(frozen=True)
class OpenAIAuthCheck:
    ok: bool
    status_code: int | None
    code: str | None
    message: str


def describe_openai_key() -> str:
    """Describe whether a key is loaded without exposing any key characters."""
    key = os.getenv("OPENAI_API_KEY", "").strip()
    if not key:
        return "missing"

    if key.startswith("sk-proj-"):
        kind = "project key"
    elif key.startswith("sk-svcacct-"):
        kind = "service-account key"
    elif key.startswith("sk-"):
        kind = "secret key"
    else:
        kind = "unexpected format"
    return f"loaded ({len(key)} chars, {kind})"


def safe_openai_error(response: httpx.Response) -> str:
    """Return useful OpenAI API error context while redacting possible secrets."""
    code: str | None = None
    message = ""
    try:
        body: Any = response.json()
        if isinstance(body, dict):
            error = body.get("error")
            if isinstance(error, dict):
                raw_code = error.get("code") or error.get("type")
                if raw_code is not None:
                    code = str(raw_code)
                raw_message = error.get("message")
                if raw_message is not None:
                    message = str(raw_message)
    except Exception:
        pass

    message = _SECRET_RE.sub("[REDACTED_API_KEY]", message).strip()
    if len(message) > 500:
        message = message[:500] + "..."

    suffix = f", code={code}" if code else ""
    if response.status_code == 401:
        return (
            f"OpenAI authentication failed (401{suffix}). The OPENAI_API_KEY loaded from .env was rejected. "
            "Create/verify a secret key in the OpenAI API Platform, replace OPENAI_API_KEY in .env, then run `vv doctor`."
        )
    if response.status_code == 403:
        return (
            f"OpenAI permission denied (403{suffix}). Check the key/project permissions for the requested API endpoint/model."
        )
    if response.status_code == 429:
        return (
            f"OpenAI request rejected (429{suffix}). Check API billing/credits and rate limits."
        )

    detail = f" {message}" if message else ""
    return f"OpenAI API request failed ({response.status_code}{suffix}).{detail}"


def check_openai_auth(timeout: float = 20.0) -> OpenAIAuthCheck:
    """Validate the configured API key against OpenAI's account-info endpoint without spending tokens."""
    key = os.getenv("OPENAI_API_KEY", "").strip()
    if not key:
        return OpenAIAuthCheck(False, None, None, "OPENAI_API_KEY is not set in the environment/.env.")

    try:
        with httpx.Client(timeout=timeout) as client:
            response = client.get(
                "https://api.openai.com/v1/me",
                headers={"Authorization": f"Bearer {key}"},
            )
    except httpx.RequestError as exc:
        return OpenAIAuthCheck(False, None, None, f"Could not reach OpenAI API: {type(exc).__name__}")

    if response.status_code == 200:
        return OpenAIAuthCheck(True, 200, None, "OpenAI authentication: PASS")

    code: str | None = None
    try:
        body = response.json()
        if isinstance(body, dict) and isinstance(body.get("error"), dict):
            raw_code = body["error"].get("code") or body["error"].get("type")
            if raw_code is not None:
                code = str(raw_code)
    except Exception:
        pass
    return OpenAIAuthCheck(False, response.status_code, code, safe_openai_error(response))
