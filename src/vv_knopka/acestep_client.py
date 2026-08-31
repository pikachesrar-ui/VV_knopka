from __future__ import annotations

import json
import os
import shutil
import subprocess
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from urllib.parse import urljoin

import httpx

from .settings import Settings


@dataclass(frozen=True)
class GeneratedTrack:
    task_id: str
    file: Path
    prompt: str
    seed_value: str
    lm_model: str
    dit_model: str


def acestep_base_url(settings: Settings) -> str:
    return os.getenv("ACESTEP_BASE_URL", "http://127.0.0.1:8001").rstrip("/")


def acestep_root(settings: Settings) -> Path:
    return (settings.root / "ACE-Step-1.5").resolve()


def _headers() -> dict[str, str]:
    key = os.getenv("ACESTEP_API_KEY", "").strip()
    return {"Authorization": f"Bearer {key}"} if key else {}


def api_available(settings: Settings, *, timeout_seconds: float = 2.0) -> bool:
    try:
        with httpx.Client(timeout=timeout_seconds) as client:
            response = client.get(f"{acestep_base_url(settings)}/health", headers=_headers())
        return response.status_code < 500
    except httpx.RequestError:
        return False


def _uv_executable(settings: Settings) -> str | None:
    local = settings.root / ".venv" / "Scripts" / "uv.exe"
    if local.exists():
        return str(local)
    return shutil.which("uv")


def _api_command(settings: Settings) -> tuple[list[str], Path]:
    root = acestep_root(settings)
    if not root.exists():
        raise RuntimeError(
            f"ACE-Step checkout not found at {root}. Run scripts/setup-acestep-windows.ps1 first."
        )

    windows_entry = root / ".venv" / "Scripts" / "acestep-api.exe"
    if windows_entry.exists():
        return [str(windows_entry)], root

    posix_entry = root / ".venv" / "bin" / "acestep-api"
    if posix_entry.exists():
        return [str(posix_entry)], root

    uv = _uv_executable(settings)
    if uv:
        return [uv, "run", "acestep-api"], root

    raise RuntimeError(
        "ACE-Step is installed but its API executable/uv could not be found. "
        "Run scripts/setup-acestep-windows.ps1 again."
    )


class ACEStepProcessManager:
    """Start the local ACE-Step API only when needed and stop only what we started."""

    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.process: subprocess.Popen[Any] | None = None
        self.log_handle: Any | None = None

    def ensure_running(self, *, timeout_seconds: float = 600.0) -> None:
        if api_available(self.settings):
            return

        command, cwd = _api_command(self.settings)
        log_path = self.settings.runtime_dir / "music" / "acestep-api.log"
        log_path.parent.mkdir(parents=True, exist_ok=True)
        self.log_handle = log_path.open("a", encoding="utf-8")
        self.log_handle.write(f"\nstarting ACE-Step API: {command!r}\n")
        self.log_handle.flush()

        creationflags = 0
        if os.name == "nt" and hasattr(subprocess, "CREATE_NEW_PROCESS_GROUP"):
            creationflags = subprocess.CREATE_NEW_PROCESS_GROUP
        self.process = subprocess.Popen(
            command,
            cwd=str(cwd),
            stdout=self.log_handle,
            stderr=subprocess.STDOUT,
            creationflags=creationflags,
        )

        deadline = time.monotonic() + timeout_seconds
        while time.monotonic() < deadline:
            if api_available(self.settings, timeout_seconds=3.0):
                return
            if self.process.poll() is not None:
                raise RuntimeError(
                    f"ACE-Step API exited during startup with code {self.process.returncode}. See {log_path}."
                )
            time.sleep(2.0)
        raise RuntimeError(
            f"ACE-Step API did not become ready within {timeout_seconds:.0f}s. "
            f"First launch may download models; see {log_path}."
        )

    def close(self) -> None:
        if self.process is not None and self.process.poll() is None:
            self.process.terminate()
            try:
                self.process.wait(timeout=15)
            except subprocess.TimeoutExpired:
                self.process.kill()
                self.process.wait(timeout=5)
        self.process = None
        if self.log_handle is not None:
            self.log_handle.close()
            self.log_handle = None

    def __enter__(self) -> "ACEStepProcessManager":
        self.ensure_running()
        return self

    def __exit__(self, *_args: Any) -> None:
        self.close()


class ACEStepClient:
    """Thin client for ACE-Step 1.5's documented asynchronous REST API."""

    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.base_url = acestep_base_url(settings)

    def _unwrap(self, response: httpx.Response) -> Any:
        response.raise_for_status()
        body = response.json()
        if isinstance(body, dict) and body.get("error"):
            raise RuntimeError(f"ACE-Step API error: {body['error']}")
        return body.get("data") if isinstance(body, dict) and "data" in body else body

    def release_instrumental(
        self,
        *,
        prompt: str,
        duration_seconds: float = 45.0,
        bpm: int | None = None,
    ) -> str:
        payload: dict[str, Any] = {
            "prompt": str(prompt).strip(),
            "lyrics": "[Instrumental]",
            "instrumental": True,
            "thinking": True,
            "audio_duration": max(10.0, min(float(duration_seconds), 600.0)),
            "audio_format": "wav",
            "batch_size": 1,
            "inference_steps": 8,
            "use_random_seed": True,
        }
        if bpm is not None:
            payload["bpm"] = max(30, min(int(bpm), 300))

        with httpx.Client(timeout=60) as client:
            data = self._unwrap(
                client.post(
                    f"{self.base_url}/release_task",
                    headers={"Content-Type": "application/json", **_headers()},
                    json=payload,
                )
            )
        task_id = str((data or {}).get("task_id") or "")
        if not task_id:
            raise RuntimeError(f"ACE-Step release_task did not return task_id: {data!r}")
        return task_id

    def wait(self, task_id: str, *, timeout_seconds: float = 1800.0, poll_seconds: float = 3.0) -> dict[str, Any]:
        deadline = time.monotonic() + timeout_seconds
        while time.monotonic() < deadline:
            try:
                with httpx.Client(timeout=60) as client:
                    data = self._unwrap(
                        client.post(
                            f"{self.base_url}/query_result",
                            headers={"Content-Type": "application/json", **_headers()},
                            json={"task_id_list": [task_id]},
                        )
                    )
            except httpx.ReadTimeout:
                # First-run model loading can keep /query_result busy for longer than
                # one HTTP read timeout. The API is asynchronous, so a read timeout
                # while polling is not a task failure; keep polling until the overall
                # task deadline expires.
                time.sleep(poll_seconds)
                continue

            rows = data if isinstance(data, list) else []
            row = next((item for item in rows if str(item.get("task_id")) == task_id), None)
            if row is None:
                time.sleep(poll_seconds)
                continue
            status = int(row.get("status") or 0)
            if status == 2:
                raise RuntimeError(f"ACE-Step task {task_id} failed: {row!r}")
            if status == 1:
                raw_result = row.get("result") or "[]"
                try:
                    result = json.loads(raw_result) if isinstance(raw_result, str) else raw_result
                except json.JSONDecodeError as exc:
                    raise RuntimeError(f"ACE-Step returned invalid task result JSON: {raw_result!r}") from exc
                items = result if isinstance(result, list) else []
                if not items:
                    raise RuntimeError(f"ACE-Step task {task_id} succeeded without audio result")
                return dict(items[0])
            time.sleep(poll_seconds)
        raise TimeoutError(f"ACE-Step task {task_id} timed out after {timeout_seconds:.0f}s")

    def download(self, result: dict[str, Any], output: Path) -> Path:
        file_url = str(result.get("file") or result.get("url") or "").strip()
        if not file_url:
            raise RuntimeError(f"ACE-Step result has no downloadable file URL: {result!r}")
        url = file_url if file_url.startswith(("http://", "https://")) else urljoin(self.base_url + "/", file_url.lstrip("/"))
        output.parent.mkdir(parents=True, exist_ok=True)
        with httpx.Client(timeout=300, follow_redirects=True) as client:
            response = client.get(url, headers=_headers())
            response.raise_for_status()
            output.write_bytes(response.content)
        if output.stat().st_size <= 0:
            raise RuntimeError(f"ACE-Step downloaded an empty file: {output}")
        return output

    def generate_instrumental(
        self,
        *,
        prompt: str,
        output: Path,
        duration_seconds: float = 45.0,
        bpm: int | None = None,
    ) -> GeneratedTrack:
        task_id = self.release_instrumental(prompt=prompt, duration_seconds=duration_seconds, bpm=bpm)
        result = self.wait(task_id)
        file = self.download(result, output)
        return GeneratedTrack(
            task_id=task_id,
            file=file,
            prompt=prompt,
            seed_value=str(result.get("seed_value") or ""),
            lm_model=str(result.get("lm_model") or ""),
            dit_model=str(result.get("dit_model") or ""),
        )
