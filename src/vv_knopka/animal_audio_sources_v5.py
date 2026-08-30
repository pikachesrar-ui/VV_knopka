from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .animal_audio_sources_v4 import ensure_audio_animal_sources as _ensure_audio_animal_sources
from .budget import BudgetLedger
from .settings import Settings
from .source_history import (
    blocked_cat_source_identities,
    cooled_down_rendered_cat_slots,
)


_MINIMUM_GATE_TEXT = "Vertical audible-source gate found only"


def _identity(item: dict[str, Any]) -> tuple[str, str] | None:
    provider = str(item.get("provider") or "").strip().lower()
    provider_id = str(item.get("provider_id") or "").strip()
    if provider and provider_id:
        return provider, provider_id
    return None


def _read_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return raw if isinstance(raw, dict) else {}


def _failed_minimum_audit(slot_dir: Path) -> bool:
    audit = _read_json(slot_dir / "animal_audio_sources.json")
    try:
        selected = int(audit.get("selected") or len(audit.get("selected_sources") or []))
        required = int(audit.get("required_minimum") or 0)
    except (TypeError, ValueError):
        return False
    return required > 0 and selected < required


def recover_failed_audit_sources(
    *,
    slot_dir: Path,
    source_manifest: Path,
    prior: set[tuple[str, str]],
) -> int:
    """Reuse stock already validated/downloaded by an earlier failed minimum-count attempt.

    `prior` is the active protected source window. Long-run sources that have aged
    out of the configured cooldown may therefore be recovered again, while recent
    repeats stay blocked.
    """
    audit_path = slot_dir / "animal_audio_sources.json"
    audit = _read_json(audit_path)
    if not audit:
        return 0

    selected = audit.get("selected_sources") or []
    if not isinstance(selected, list):
        return 0

    manifest = _read_json(source_manifest)
    existing = [item for item in (manifest.get("clips") or []) if isinstance(item, dict)]
    seen = {_identity(item) for item in existing}

    recovered: list[dict[str, Any]] = []
    for item in selected:
        if not isinstance(item, dict):
            continue
        provider = str(item.get("provider") or "").strip().lower()
        if provider not in {"pexels", "pixabay"}:
            continue
        identity = _identity(item)
        if identity is None or identity in prior or identity in seen:
            continue
        file_path = Path(str(item.get("file") or ""))
        if not file_path.exists() or file_path.stat().st_size <= 0:
            continue
        existing.append(dict(item))
        seen.add(identity)
        recovered.append(dict(item))

    if not recovered:
        return 0

    manifest["clips"] = existing
    manifest["recovered_from_failed_audio_audit"] = len(recovered)
    source_manifest.parent.mkdir(parents=True, exist_ok=True)
    source_manifest.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    return len(recovered)


def seed_cooled_history_sources(
    settings: Settings,
    *,
    slot: int,
    source_manifest: Path,
    protected: set[tuple[str, str]],
    max_sources: int,
) -> list[dict[str, Any]]:
    """Seed local, cooled-down stock from older rendered episodes as last-resort input.

    This does not trust the old files blindly: the base audio-source pipeline will
    re-run current geometry and audible-audio checks on every seeded local file.
    Only Pexels/Pixabay entries with an existing non-empty local file are copied.
    """
    if max_sources <= 0:
        return []

    manifest = _read_json(source_manifest)
    existing = [item for item in (manifest.get("clips") or []) if isinstance(item, dict)]
    seen = {_identity(item) for item in existing}
    seeded: list[dict[str, Any]] = []

    for history_slot in cooled_down_rendered_cat_slots(settings, before_slot=slot):
        history_path = settings.runtime_dir / "slots" / f"{history_slot:02d}" / "sources.json"
        history = _read_json(history_path)
        for item in history.get("clips") or []:
            if len(seeded) >= int(max_sources):
                break
            if not isinstance(item, dict):
                continue
            provider = str(item.get("provider") or "").strip().lower()
            if provider not in {"pexels", "pixabay"}:
                continue
            identity = _identity(item)
            if identity is None or identity in protected or identity in seen:
                continue
            file_path = Path(str(item.get("file") or ""))
            if not file_path.exists() or file_path.stat().st_size <= 0:
                continue
            copied = dict(item)
            copied["cooled_down_reuse"] = True
            copied["reused_from_slot"] = int(history_slot)
            existing.append(copied)
            seen.add(identity)
            seeded.append(copied)
        if len(seeded) >= int(max_sources):
            break

    if seeded:
        manifest["clips"] = existing
        manifest["cooled_history_seeded"] = len(seeded)
        source_manifest.parent.mkdir(parents=True, exist_ok=True)
        source_manifest.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    return seeded


def _record_recovery(slot_dir: Path, recovered: int) -> None:
    if recovered <= 0:
        return
    audit_path = slot_dir / "animal_audio_sources.json"
    audit = _read_json(audit_path)
    if not audit:
        return
    audit["resume_from_failed_attempt"] = {
        "enabled": True,
        "recovered_sources": int(recovered),
        "policy": "reuse already validated local stock when it is outside the active protected source window",
    }
    audit_path.write_text(json.dumps(audit, ensure_ascii=False, indent=2), encoding="utf-8")


def _record_cooled_fallback(slot_dir: Path, seeded: list[dict[str, Any]]) -> None:
    if not seeded:
        return
    audit_path = slot_dir / "animal_audio_sources.json"
    audit = _read_json(audit_path)
    if not audit:
        return
    source_slots = sorted({int(item.get("reused_from_slot") or 0) for item in seeded if item.get("reused_from_slot")})
    audit["cooled_history_local_fallback"] = {
        "enabled": True,
        "seeded_sources": len(seeded),
        "source_slots": source_slots,
        "policy": (
            "fresh stock was exhausted first; older Pexels/Pixabay files outside the cat-episode cooldown "
            "were then seeded locally and revalidated by current geometry/audio gates"
        ),
    }
    audit_path.write_text(json.dumps(audit, ensure_ascii=False, indent=2), encoding="utf-8")


def ensure_audio_animal_sources(
    settings: Settings,
    plan: dict[str, Any],
    *,
    slot: int,
    slot_dir: Path,
    source_manifest: Path,
    ledger: BudgetLedger,
) -> Path:
    protected = blocked_cat_source_identities(settings, before_slot=slot)
    had_failed_minimum_audit = _failed_minimum_audit(slot_dir)
    recovered = recover_failed_audit_sources(
        slot_dir=slot_dir,
        source_manifest=source_manifest,
        prior=protected,
    )

    target_count = max(int(settings.raw.get("animal", {}).get("material_count", 6)), 1)
    seeded: list[dict[str, Any]] = []

    # On a retry after a completed fresh-source minimum-count failure, do not pay
    # to repeat the same remote discovery pass. Resume the accepted local files and
    # immediately add cooled historical local stock as fallback.
    if had_failed_minimum_audit:
        seeded = seed_cooled_history_sources(
            settings,
            slot=slot,
            source_manifest=source_manifest,
            protected=protected,
            max_sources=target_count * 2,
        )

    try:
        result = _ensure_audio_animal_sources(
            settings,
            plan,
            slot=slot,
            slot_dir=slot_dir,
            source_manifest=source_manifest,
            ledger=ledger,
        )
    except RuntimeError as exc:
        if _MINIMUM_GATE_TEXT not in str(exc):
            raise

        # First-attempt behavior: only after a full fresh search has genuinely
        # failed do we promote its accepted files plus cooled local history, then
        # run the same base validators again. Other RuntimeErrors remain fail-closed.
        recovered += recover_failed_audit_sources(
            slot_dir=slot_dir,
            source_manifest=source_manifest,
            prior=protected,
        )
        if not seeded:
            seeded = seed_cooled_history_sources(
                settings,
                slot=slot,
                source_manifest=source_manifest,
                protected=protected,
                max_sources=target_count * 2,
            )
        if not seeded:
            raise
        result = _ensure_audio_animal_sources(
            settings,
            plan,
            slot=slot,
            slot_dir=slot_dir,
            source_manifest=source_manifest,
            ledger=ledger,
        )

    _record_recovery(slot_dir, recovered)
    _record_cooled_fallback(slot_dir, seeded)
    return result
