from __future__ import annotations

import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from . import pilot_conveyor as _base
from .longrun_recovery import (
    archive_failed_plan,
    blocked_reason,
    recovery_state,
    reserve_recovery_budget,
    terminal_ai_failure,
    terminal_animal_failure,
    write_recovery,
)
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
            blocked = blocked_reason(settings, number)
            if blocked:
                print(f"RECOVERY: slot {number} blocked ({blocked}); continuing with next slot")
            else:
                result.append(slot)
        number += 1
    return result


def _recover_ai_slot(
    settings: Settings,
    config_path: Path,
    slot: Slot,
    mpt: Any,
    original_error: Exception,
    attempt_started_at: str,
) -> Path:
    started = datetime.fromisoformat(attempt_started_at).timestamp()
    issue = terminal_ai_failure(settings, slot.slot, original_error, not_before=started)
    if issue is None:
        raise original_error
    reason, anchor = issue
    state = recovery_state(settings, slot.slot)
    maximum = int(settings.raw.get("recovery", {}).get("max_replans_per_slot", 1))
    if int(state.get("replans_used") or 0) >= maximum:
        state.update(status="blocked", reason=reason, failed_anchor=anchor)
        write_recovery(settings, slot.slot, state)
        raise RuntimeError(f"slot {slot.slot} BLOCKED after {maximum} alternative plan(s): {reason}") from original_error

    try:
        reserved = reserve_recovery_budget(settings)
    except RuntimeError as exc:
        state.update(status="blocked", reason=f"recovery budget guard: {exc}", failed_anchor=anchor)
        write_recovery(settings, slot.slot, state)
        raise RuntimeError(f"slot {slot.slot} BLOCKED: {state['reason']}") from exc

    archive = archive_failed_plan(settings, slot.slot)
    state.update(
        status="replanning",
        replans_used=int(state.get("replans_used") or 0) + 1,
        reason=reason,
        failed_anchor=anchor,
        reserved_usd=round(reserved, 4),
        archive=str(archive),
    )
    write_recovery(settings, slot.slot, state)
    print(f"RECOVERY: slot {slot.slot}: {reason}; replanning once without {anchor} (reserve ${reserved:.2f})")
    (settings.runtime_dir / "slots" / f"{slot.slot:02d}" / "plan.json").unlink(missing_ok=True)
    try:
        _base._run_cli(config_path, "plan", str(slot.slot), "--avoid-anchor", anchor)
        state["status"] = "replanned"
        write_recovery(settings, slot.slot, state)
        output = _base._render_one(settings, config_path, slot, mpt)
    except Exception as exc:
        second = terminal_ai_failure(settings, slot.slot, exc, not_before=started)
        if second is not None:
            state["reason"], state["failed_anchor"] = second
            state["status"] = "blocked"
        elif state.get("status") == "replanning":
            # An HTTP or process failure is not proof the subject is invalid.
            # Preserve the reserved budget and try the same replacement once
            # more on the next invocation; do not skip this slot.
            state["reason"] = f"replacement plan interrupted: {exc}"
            state["status"] = "retry_replacement"
        write_recovery(settings, slot.slot, state)
        raise
    state.update(status="recovered", reason="new subject passed existing gates")
    write_recovery(settings, slot.slot, state)
    return output


def run_longrun_batch(
    settings: Settings,
    *,
    config_path: Path,
    count: int,
    dry_run: bool = False,
) -> list[Path]:
    """Render N missing post-pilot slots, preserving review-first safety and resumability."""
    _base._validate_conveyor_lock(settings)
    wanted = max(int(count), 0)
    if dry_run:
        todo = pending_longrun_slots(settings, count=wanted)
        for slot in todo:
            print(
                f"slot {slot.slot:02d}: {slot.pipeline} / {slot.language} "
                f"-> {_base.expected_output(settings, slot)}"
            )
        return []
    if wanted == 0:
        print("Long-run conveyor: count is zero; nothing to render.")
        return []

    state = _load_state(settings)
    outputs: list[Path] = []
    blocked_skips = 0
    # One newly proven terminal AI or cat slot may be skipped within this
    # invocation, so a publication cycle can still use its upload opportunity.
    # Bound this per invocation because later slots can incur paid review calls.
    max_blocked_skips = max(0, int(settings.raw.get("recovery", {}).get("max_blocked_skips_per_run", 1)))
    mpt = _base.MPTProcessManager(settings)
    original_run_cli = _base._run_cli
    _base._run_cli = _run_current_cli
    try:
        while len(outputs) < wanted:
            slot = pending_longrun_slots(settings, count=1)[0]
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
                recovery = recovery_state(settings, slot.slot)
                if recovery.get("status") in {"replanning", "retry_replacement"}:
                    if recovery.get("status") == "replanning":
                        recovery.update(status="retry_replacement", reason="interrupted during replanning")
                        write_recovery(settings, slot.slot, recovery)
                    failed_anchor = str(recovery.get("failed_anchor") or "")
                    if not failed_anchor:
                        raise RuntimeError(f"slot {slot.slot} recovery has no original anchor")
                    current = settings.runtime_dir / "slots" / f"{slot.slot:02d}" / "plan.json"
                    if current.exists():
                        try:
                            anchor = str(json.loads(current.read_text(encoding="utf-8")).get("visual_anchor") or "")
                        except (OSError, ValueError, TypeError):
                            anchor = ""
                        if anchor.casefold() == failed_anchor.casefold():
                            current.unlink()
                    if not current.exists():
                        _base._run_cli(config_path, "plan", str(slot.slot), "--avoid-anchor", failed_anchor)
                    recovery["status"] = "replanned"
                    write_recovery(settings, slot.slot, recovery)
                output = _base._render_one(settings, config_path, slot, mpt)
                if recovery.get("status") == "replanned":
                    recovery.update(status="recovered", reason="new subject passed existing gates")
                    write_recovery(settings, slot.slot, recovery)
            except Exception as exc:
                try:
                    if slot.pipeline != "ai_short" or not settings.raw.get("recovery", {}).get("enabled", False):
                        raise exc
                    output = _recover_ai_slot(settings, config_path, slot, mpt, exc, attempt["started_at"])
                except Exception as final_error:
                    if (
                        slot.pipeline == "animal_compilation"
                        and settings.raw.get("recovery", {}).get("enabled", False)
                    ):
                        started = datetime.fromisoformat(attempt["started_at"]).timestamp()
                        reason = terminal_animal_failure(
                            settings, slot.slot, final_error, not_before=started
                        )
                        if reason is not None:
                            write_recovery(
                                settings,
                                slot.slot,
                                {
                                    "status": "blocked",
                                    "reason": reason,
                                    "pipeline": slot.pipeline,
                                },
                            )
                    attempt["status"] = "failed"
                    attempt["error"] = f"{type(final_error).__name__}: {final_error}"
                    attempt["finished_at"] = datetime.now(timezone.utc).isoformat()
                    _write_state(settings, state)
                    latest = recovery_state(settings, slot.slot)
                    # A temporary HTTP failure remains retryable on this same
                    # slot. A budget guard also must not trigger new planning.
                    if (
                        latest.get("status") == "blocked"
                        and not str(latest.get("reason") or "").startswith("recovery budget guard:")
                        and blocked_skips < max_blocked_skips
                    ):
                        blocked_skips += 1
                        print(f"RECOVERY: slot {slot.slot} blocked; continuing with next missing slot in this run")
                        continue
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
