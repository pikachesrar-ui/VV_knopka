from __future__ import annotations

import os
import subprocess
import time
from pathlib import Path

import httpx

from .settings import Settings


def _probe_mpt(settings: Settings, *, timeout_seconds: float = 3.0) -> tuple[bool, int | None, str | None]:
    base_url = str(settings.mpt_base_url).rstrip("/")
    try:
        with httpx.Client(timeout=timeout_seconds, follow_redirects=True) as client:
            response = client.get(f"{base_url}/docs")
    except httpx.RequestError as exc:
        return False, None, str(exc)
    return response.status_code < 500, int(response.status_code), None


def require_mpt_available(settings: Settings, *, timeout_seconds: float = 3.0) -> None:
    """Fail early with an actionable message when the local MPT API is offline."""
    base_url = str(settings.mpt_base_url).rstrip("/")
    reachable, status_code, error = _probe_mpt(settings, timeout_seconds=timeout_seconds)
    if reachable:
        return
    if status_code is not None:
        raise RuntimeError(
            f"MoneyPrinterTurbo API is reachable at {base_url} but returned HTTP "
            f"{status_code} from /docs. Check the MPT process before rendering."
        )
    raise RuntimeError(
        "MoneyPrinterTurbo API is not reachable at "
        f"{base_url}. Start MoneyPrinterTurbo in another terminal from its project root "
        "with `uv run python main.py` (or `python main.py` in its active environment), "
        f"then retry `vv render-ai SLOT`. Detail: {error or 'connection failed'}"
    )


def _mpt_root(settings: Settings) -> Path:
    return (settings.root / "MoneyPrinterTurbo").resolve()


def _mpt_python(settings: Settings) -> Path:
    root = _mpt_root(settings)
    candidates = (
        root / ".venv" / "Scripts" / "python.exe",
        root / ".venv" / "bin" / "python",
    )
    for candidate in candidates:
        if candidate.exists() and candidate.is_file():
            return candidate
    raise RuntimeError(
        f"MoneyPrinterTurbo environment is missing under {root}. "
        "Run `powershell -ExecutionPolicy Bypass -File .\\scripts\\setup-mpt-windows.ps1` once first."
    )


def _tail(path: Path, *, limit: int = 3000) -> str:
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return ""
    return text[-limit:].strip()


def start_mpt_background(settings: Settings) -> subprocess.Popen:
    """Start the local MPT API detached enough for scheduled, windowless operation."""
    root = _mpt_root(settings)
    if not (root / "main.py").exists():
        raise RuntimeError(
            f"MoneyPrinterTurbo source is missing at {root}. "
            "Run `powershell -ExecutionPolicy Bypass -File .\\scripts\\setup-mpt-windows.ps1` once first."
        )
    python = _mpt_python(settings)
    runtime = settings.runtime_dir / "mpt"
    runtime.mkdir(parents=True, exist_ok=True)
    log_path = runtime / "mpt-api.log"
    log_handle = log_path.open("ab")

    kwargs: dict[str, object] = {
        "cwd": str(root),
        "stdin": subprocess.DEVNULL,
        "stdout": log_handle,
        "stderr": subprocess.STDOUT,
        "close_fds": True,
    }
    if os.name == "nt":
        kwargs["creationflags"] = (
            getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0)
            | getattr(subprocess, "DETACHED_PROCESS", 0)
        )
    else:
        kwargs["start_new_session"] = True

    try:
        process = subprocess.Popen([str(python), "main.py"], **kwargs)
    finally:
        # Popen owns a duplicated OS handle after process creation; the parent does
        # not need to keep this Python file object open for the life of the server.
        log_handle.close()
    return process


def ensure_mpt_available(
    settings: Settings,
    *,
    timeout_seconds: float = 3.0,
    startup_timeout_seconds: float = 90.0,
    poll_seconds: float = 1.5,
) -> None:
    """Use an existing MPT API or start the configured local checkout automatically."""
    reachable, status_code, _ = _probe_mpt(settings, timeout_seconds=timeout_seconds)
    if reachable:
        return
    if status_code is not None:
        # An HTTP 5xx proves a server already owns the endpoint. Starting a second
        # process would hide the original failure or collide on the port.
        require_mpt_available(settings, timeout_seconds=timeout_seconds)
        return

    process = start_mpt_background(settings)
    deadline = time.monotonic() + max(float(startup_timeout_seconds), 1.0)
    while time.monotonic() < deadline:
        if process.poll() is not None:
            log_path = settings.runtime_dir / "mpt" / "mpt-api.log"
            detail = _tail(log_path)
            raise RuntimeError(
                f"MoneyPrinterTurbo auto-start exited with code {process.returncode}. "
                f"See {log_path}." + (f" Last log output: {detail}" if detail else "")
            )
        reachable, status_code, _ = _probe_mpt(settings, timeout_seconds=timeout_seconds)
        if reachable:
            return
        if status_code is not None:
            require_mpt_available(settings, timeout_seconds=timeout_seconds)
        time.sleep(max(float(poll_seconds), 0.1))

    log_path = settings.runtime_dir / "mpt" / "mpt-api.log"
    detail = _tail(log_path)
    raise RuntimeError(
        f"MoneyPrinterTurbo did not become ready within {startup_timeout_seconds:.0f}s after auto-start. "
        f"See {log_path}." + (f" Last log output: {detail}" if detail else "")
    )
