"""Bounded recovery for permanently unfilmable long-run AI plans.

Only deterministic, audited terminal failures qualify. Unknown, transient, and
publication failures remain fail-closed and are retried by the existing runner.
"""

from __future__ import annotations

import json
import math
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .budget import BudgetLedger
from .material_fallback import CuratedMaterialFallbackError, load_duration_sufficient_materials
from .settings import Settings


def _read_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (FileNotFoundError, OSError, json.JSONDecodeError):
        return {}
    return value if isinstance(value, dict) else {}


def recovery_path(settings: Settings, slot: int) -> Path:
    return settings.runtime_dir / "slots" / f"{slot:02d}" / "auto-recovery.json"


def recovery_state(settings: Settings, slot: int) -> dict[str, Any]:
    path = recovery_path(settings, slot)
    if not path.exists():
        return {}
    value = _read_json(path)
    if value.get("schema_version") != 1 or value.get("slot") != slot:
        raise RuntimeError(f"Corrupt long-run recovery state: {path}")
    return value


def write_recovery(settings: Settings, slot: int, value: dict[str, Any]) -> None:
    path = recovery_path(settings, slot)
    path.parent.mkdir(parents=True, exist_ok=True)
    value.update(schema_version=1, slot=slot, updated_at=datetime.now(timezone.utc).isoformat())
    temporary = path.with_suffix(".json.tmp")
    temporary.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding="utf-8")
    temporary.replace(path)


def blocked_reason(settings: Settings, slot: int) -> str | None:
    value = recovery_state(settings, slot)
    return str(value.get("reason") or "manual review required") if value.get("status") == "blocked" else None


def terminal_ai_failure(
    settings: Settings, slot: int, error: Exception, *, not_before: float = 0.0
) -> tuple[str, str] | None:
    """Return (reason, anchor) only for proven fact-check or stock exhaustion."""
    message = str(error)
    slot_dir = settings.runtime_dir / "slots" / f"{slot:02d}"
    if f"plan {slot}" in message and "child command failed" in message:
        audit_path = slot_dir / "fact-check.json"
        # A network/HTTP failure during planning must not be classified using
        # the previous attempt's fact-check sidecar.
        if not audit_path.exists() or audit_path.stat().st_mtime < not_before:
            return None
        fact = _read_json(slot_dir / "fact-check.json")
        candidate = _read_json(slot_dir / "plan-candidate.json")
        anchor = str(candidate.get("visual_anchor") or "").strip().lower()
        if fact.get("passed") is False and anchor and fact.get("visual_anchor") == anchor:
            return ("fact-check rejected the plan", anchor)
    if f"render-ai {slot}" not in message or "child command failed" not in message:
        return None

    plan = _read_json(slot_dir / "plan.json")
    audit = _read_json(slot_dir / "ai_materials.json")
    anchor = str(plan.get("visual_anchor") or "").strip().lower()
    if not anchor or str(audit.get("visual_anchor") or "").strip().lower() != anchor:
        return None
    providers = audit.get("providers") or {}
    if not isinstance(providers, dict):
        return None
    pexels = providers.get("pexels") or {}
    pixabay = providers.get("pixabay") or {}
    try:
        reviewed_both = int(pexels.get("vision_reviewed") or 0) > 0 and int(pixabay.get("vision_reviewed") or 0) > 0
        selected = int(audit.get("selected") or len(audit.get("materials") or []))
    except (TypeError, ValueError, AttributeError):
        return None
    min_sources = int(settings.raw.get("materials", {}).get("min_unique_ai_materials", 3))
    if reviewed_both and selected < min_sources:
        return (f"only {selected}/{min_sources} approved sources for {anchor}", anchor)
    if reviewed_both:
        try:
            load_duration_sufficient_materials(settings, slot_dir=slot_dir, expected_anchor=anchor)
        except CuratedMaterialFallbackError as exc:
            return (f"insufficient approved footage for {anchor}: {exc}", anchor)
    return None


def terminal_animal_failure(
    settings: Settings, slot: int, error: Exception, *, not_before: float = 0.0
) -> str | None:
    """Return a reason only for a freshly completed, fully audited cat shortage.

    Network failures and old audit files deliberately remain retryable. Both
    stock providers must be configured; quality gates are never relaxed.
    """
    message = str(error)
    if f"render-animal {slot}" not in message or "child command failed" not in message:
        return None

    audit = _read_json(settings.runtime_dir / "slots" / f"{slot:02d}" / "animal_audio_sources.json")
    try:
        completed = datetime.fromisoformat(str(audit.get("search_completed_at") or "")).timestamp()
        required = int(audit.get("required_minimum") or 0)
        selected = int(audit.get("selected") or len(audit.get("selected_sources") or []))
    except (TypeError, ValueError, AttributeError):
        return None
    availability = audit.get("provider_availability") or {}
    if not isinstance(availability, dict):
        return None
    both_configured = bool(availability.get("pexels_api_key_present")) and bool(
        availability.get("pixabay_api_key_present")
    )
    if completed < not_before or not both_configured or required <= 0 or selected >= required:
        return None
    return f"audited cat stock exhausted: only {selected}/{required} usable clips"


def reserve_recovery_budget(settings: Settings) -> float:
    """Reserve for at most one planner, fact-check, and bounded vision search."""
    cfg = settings.raw.get("recovery", {})
    max_extra = float(cfg.get("max_estimated_extra_usd", 0.55))
    materials = settings.raw.get("materials", {})
    batch = max(1, int(materials.get("vision_batch_size", 10)))
    vision_calls = math.ceil(int(materials.get("vision_max_candidates", 30)) / batch)
    vision_calls += math.ceil(int(materials.get("pixabay_vision_max_candidates", 40)) / batch)
    estimate = float(settings.raw.get("openai", {}).get("max_estimated_cost_per_call_usd", 0.25))
    estimate += float(settings.raw.get("openai", {}).get("fact_check_max_estimated_cost_usd", 0.05))
    estimate += vision_calls * float(materials.get("vision_max_estimated_cost_per_call_usd", 0.03))
    if estimate > max_extra:
        raise RuntimeError(f"Recovery reserve ${estimate:.2f} exceeds per-slot limit ${max_extra:.2f}")
    BudgetLedger(settings).ensure_room(estimate)
    return estimate


def archive_failed_plan(settings: Settings, slot: int) -> Path:
    slot_dir = settings.runtime_dir / "slots" / f"{slot:02d}"
    folder = slot_dir / "auto-recovery" / "original-plan"
    folder.mkdir(parents=True, exist_ok=True)
    for name in ("plan.json", "plan-candidate.json", "fact-check.json", "ai_materials.json"):
        path = slot_dir / name
        if path.exists() and not (folder / name).exists():
            shutil.copy2(path, folder / name)
    return folder


def unblock_after_manual_replan(settings: Settings, slot: int) -> None:
    state = recovery_state(settings, slot)
    if state.get("status") != "blocked":
        raise RuntimeError(f"Slot {slot} is not blocked by automatic recovery")
    slot_dir = settings.runtime_dir / "slots" / f"{slot:02d}"
    plan = _read_json(slot_dir / "plan.json")
    fact = _read_json(slot_dir / "fact-check.json")
    anchor = str(plan.get("visual_anchor") or "").strip().lower()
    if not anchor or anchor == str(state.get("failed_anchor") or "").strip().lower():
        raise RuntimeError("First create a verified plan with a different visual anchor")
    if fact.get("passed") is not True or str(fact.get("visual_anchor") or "").strip().lower() != anchor:
        raise RuntimeError("The replacement plan must have a matching successful fact-check")
    state["status"] = "manual_resume"
    write_recovery(settings, slot, state)
