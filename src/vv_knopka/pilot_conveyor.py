from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .budget import BudgetLedger
from .gates import publication_gate
from .manifest import Slot, build_manifest
from .mpt_health import require_mpt_available
from .publication_metadata import write_upload_metadata
from .settings import Settings


def expected_output(settings: Settings, slot: Slot) -> Path:
    suffix = "ai" if slot.pipeline == "ai_short" else "animals"
    return settings.runtime_dir / "ready_for_review" / f"slot-{slot.slot:02d}-{slot.language}-{suffix}.mp4"


def is_rendered(settings: Settings, slot: Slot) -> bool:
    output = expected_output(settings, slot)
    return output.exists() and output.stat().st_size > 0


def pending_slots(settings: Settings) -> list[Slot]:
    return [slot for slot in build_manifest(settings) if not is_rendered(settings, slot)]


def _state_path(settings: Settings) -> Path:
    return settings.runtime_dir / "conveyor" / "state.json"


def _load_state(settings: Settings) -> dict[str, Any]:
    path = _state_path(settings)
    if not path.exists():
        return {"version": 1, "attempts": []}
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {"version": 1, "attempts": []}
    if not isinstance(raw, dict):
        return {"version": 1, "attempts": []}
    raw.setdefault("version", 1)
    raw.setdefault("attempts", [])
    return raw


def _write_state(settings: Settings, state: dict[str, Any]) -> Path:
    path = _state_path(settings)
    path.parent.mkdir(parents=True, exist_ok=True)
    state["updated_at"] = datetime.now(timezone.utc).isoformat()
    path.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")
    return path


def _backfill_upload_metadata(settings: Settings) -> list[Path]:
    written: list[Path] = []
    for slot in build_manifest(settings):
        output = expected_output(settings, slot)
        if not output.exists() or output.stat().st_size <= 0:
            continue
        sidecar = output.with_suffix(".upload.json")
        if sidecar.exists() and sidecar.stat().st_size > 0:
            continue
        slot_dir = settings.runtime_dir / "slots" / f"{slot.slot:02d}"
        try:
            written.append(write_upload_metadata(settings, slot=slot, output=output, slot_dir=slot_dir))
        except (FileNotFoundError, json.JSONDecodeError):
            # An old rendered artifact may predate the metadata inputs. Never
            # block the conveyor just because a legacy sidecar cannot be rebuilt.
            continue
    return written


def _run_cli(config_path: Path, *args: str) -> None:
    command = [sys.executable, "-m", "vv_knopka.cli", "--config", str(config_path), *args]
    completed = subprocess.run(command, cwd=str(config_path.parent.parent), check=False)
    if completed.returncode != 0:
        raise RuntimeError(f"child command failed ({completed.returncode}): {' '.join(args)}")


def _mpt_is_available(settings: Settings) -> bool:
    try:
        require_mpt_available(settings, timeout_seconds=1.0)
        return True
    except RuntimeError:
        return False


def _mpt_command(settings: Settings) -> tuple[list[str], Path]:
    root = (settings.root / "MoneyPrinterTurbo").resolve()
    main = root / "main.py"
    if not main.exists():
        raise RuntimeError(
            f"MoneyPrinterTurbo checkout not found at {root}. Start MPT manually at {settings.mpt_base_url}."
        )

    candidates = [
        root / ".venv" / "Scripts" / "python.exe",
        root / "venv" / "Scripts" / "python.exe",
        root / ".venv" / "bin" / "python",
        root / "venv" / "bin" / "python",
    ]
    for python in candidates:
        if python.exists():
            return [str(python), "main.py"], root

    uv = shutil.which("uv")
    if uv:
        return [uv, "run", "python", "main.py"], root

    raise RuntimeError(
        "MoneyPrinterTurbo is offline and no local MPT Python environment or `uv` executable was found. "
        f"Start MPT manually at {settings.mpt_base_url} before running the conveyor."
    )


class MPTProcessManager:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.process: subprocess.Popen[Any] | None = None
        self.log_handle: Any | None = None

    def ensure_running(self, *, timeout_seconds: float = 90.0) -> None:
        if _mpt_is_available(self.settings):
            return

        command, cwd = _mpt_command(self.settings)
        log_path = self.settings.runtime_dir / "conveyor" / "mpt.log"
        log_path.parent.mkdir(parents=True, exist_ok=True)
        self.log_handle = log_path.open("a", encoding="utf-8")
        self.log_handle.write(f"\n[{datetime.now(timezone.utc).isoformat()}] starting: {command!r}\n")
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
            if _mpt_is_available(self.settings):
                return
            if self.process.poll() is not None:
                raise RuntimeError(
                    f"MoneyPrinterTurbo exited during startup with code {self.process.returncode}. "
                    f"See {log_path}."
                )
            time.sleep(1.0)
        raise RuntimeError(f"MoneyPrinterTurbo did not become ready within {timeout_seconds:.0f}s. See {log_path}.")

    def close(self) -> None:
        if self.process is not None and self.process.poll() is None:
            self.process.terminate()
            try:
                self.process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                self.process.kill()
                self.process.wait(timeout=5)
        self.process = None
        if self.log_handle is not None:
            self.log_handle.close()
            self.log_handle = None


def _validate_conveyor_lock(settings: Settings) -> None:
    gate = publication_gate(settings)
    if not gate.passed or settings.auto_publish:
        reasons = "; ".join(gate.reasons) if gate.reasons else "auto_publish must remain false"
        raise RuntimeError(f"Conveyor safety lock failed: {reasons}")
    ledger = BudgetLedger(settings)
    if ledger.spent_usd() >= settings.budget_usd:
        raise RuntimeError(
            f"OpenAI pilot budget is already exhausted: ${ledger.spent_usd():.4f} / ${settings.budget_usd:.2f}"
        )


def _render_one(settings: Settings, config_path: Path, slot: Slot, mpt: MPTProcessManager) -> Path:
    slot_dir = settings.runtime_dir / "slots" / f"{slot.slot:02d}"
    if slot.pipeline == "ai_short":
        plan_path = slot_dir / "plan.json"
        if not plan_path.exists():
            _run_cli(config_path, "plan", str(slot.slot))
        mpt.ensure_running()
        _run_cli(config_path, "render-ai", str(slot.slot))
    else:
        _run_cli(config_path, "render-animal", str(slot.slot))

    output = expected_output(settings, slot)
    if not output.exists() or output.stat().st_size <= 0:
        raise RuntimeError(f"slot {slot.slot} finished without expected output {output}")
    write_upload_metadata(settings, slot=slot, output=output, slot_dir=slot_dir)
    return output


def run_batch(settings: Settings, *, config_path: Path, count: int, dry_run: bool = False) -> list[Path]:
    """Render up to count missing pilot slots, stopping immediately on the first failure."""
    _validate_conveyor_lock(settings)
    _backfill_upload_metadata(settings)
    todo = pending_slots(settings)[: max(int(count), 0)]
    if dry_run:
        for slot in todo:
            print(f"slot {slot.slot:02d}: {slot.pipeline} / {slot.language} -> {expected_output(settings, slot)}")
        return []
    if not todo:
        print("Pilot conveyor: no unrendered slots remain.")
        return []

    state = _load_state(settings)
    outputs: list[Path] = []
    mpt = MPTProcessManager(settings)
    try:
        for slot in todo:
            _validate_conveyor_lock(settings)
            attempt = {
                "slot": slot.slot,
                "pipeline": slot.pipeline,
                "language": slot.language,
                "started_at": datetime.now(timezone.utc).isoformat(),
                "status": "running",
            }
            state["attempts"].append(attempt)
            _write_state(settings, state)
            try:
                output = _render_one(settings, config_path, slot, mpt)
            except Exception as exc:
                attempt["status"] = "failed"
                attempt["error"] = f"{type(exc).__name__}: {exc}"
                attempt["finished_at"] = datetime.now(timezone.utc).isoformat()
                _write_state(settings, state)
                raise
            attempt["status"] = "ready_for_review"
            attempt["output"] = str(output.resolve())
            attempt["finished_at"] = datetime.now(timezone.utc).isoformat()
            _write_state(settings, state)
            outputs.append(output)
    finally:
        mpt.close()
    return outputs
