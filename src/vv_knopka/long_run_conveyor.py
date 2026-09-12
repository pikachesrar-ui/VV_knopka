from __future__ import annotations

import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from . import pilot_conveyor as _base
from .manifest import Slot, longrun_enabled, longrun_slot, longrun_start_slot
from .settings import Settings


def _run_current_cli(config_path: Path, *args: str) -> None:
    command = [sys.executable, "-m", "vv_knopka.cli_v2", "--config", str(config_path), *args]
    completed = subprocess.run(command, cwd=str(config_path.parent.parent), check=False)
    if completed.returncode != 0:
        raise RuntimeError(f"child command failed ({completed.returncode}): {' '.join(args)}")


def _state_path(settings: Settings) -> Path:
    return settings.runtime_dir / "long_run" / "state.json"


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


def pending_longrun_slots(settings: Settings, *, count: int) -> list[Slot]:
    """Return the first N missing deterministic long-run slots in strict sequence order."""
    if not longrun_enabled(settings):
        raise RuntimeError("Long-run generation is disabled in config")
    wanted = max(int(count), 0)
    if wanted == 0:
        return []

    result: list[Slot] = []
    number = longrun_start_slot(settings)
    while len(result) < wanted:
        slot = longrun_slot(settings, number)
        if not _base.is_rendered(settings, slot):
            result.append(slot)
        number += 1
    return result


def run_longrun_batch(
    settings: Settings,
    *,
    config_path: Path,
    count: int,
    dry_run: bool = False,
) -> list[Path]:
    """Render N missing post-pilot slots, preserving review-first safety and resumability."""
    _base._validate_conveyor_lock(settings)
    todo = pending_longrun_slots(settings, count=count)
    if dry_run:
        for slot in todo:
            print(
                f"slot {slot.slot:02d}: {slot.pipeline} / {slot.language} "
                f"-> {_base.expected_output(settings, slot)}"
            )
        return []
    if not todo:
        print("Long-run conveyor: count is zero; nothing to render.")
        return []

    state = _load_state(settings)
    outputs: list[Path] = []
    mpt = _base.MPTProcessManager(settings)
    original_run_cli = _base._run_cli
    _base._run_cli = _run_current_cli
    try:
        for slot in todo:
            _base._validate_conveyor_lock(settings)
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
                output = _base._render_one(settings, config_path, slot, mpt)
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
        _base._run_cli = original_run_cli
        mpt.close()
    return outputs
