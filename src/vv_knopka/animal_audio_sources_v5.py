from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .animal_audio_sources_v4 import ensure_audio_animal_sources as _ensure_audio_animal_sources
from .budget import BudgetLedger
from .settings import Settings
from .source_history import blocked_cat_source_identities


def _identity(item: dict[str, Any]) -> tuple[str, str] | None:
    provider = str(item.get("provider") or "").strip().lower()
    provider_id = str(item.get("provider_id") or "").strip()
    if provider and provider_id:
        return provider, provider_id
    return None


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
    if not audit_path.exists():
        return 0
    try:
        audit = json.loads(audit_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return 0

    selected = audit.get("selected_sources") or []
    if not isinstance(selected, list):
        return 0

    try:
        manifest = json.loads(source_manifest.read_text(encoding="utf-8")) if source_manifest.exists() else {}
    except (OSError, json.JSONDecodeError):
        manifest = {}
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


def _record_recovery(slot_dir: Path, recovered: int) -> None:
    if recovered <= 0:
        return
    audit_path = slot_dir / "animal_audio_sources.json"
    if not audit_path.exists():
        return
    try:
        audit = json.loads(audit_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return
    audit["resume_from_failed_attempt"] = {
        "enabled": True,
        "recovered_fresh_sources": int(recovered),
        "policy": "reuse already validated local stock when it is outside the active protected source window",
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
    prior = blocked_cat_source_identities(settings, before_slot=slot)
    recovered = recover_failed_audit_sources(
        slot_dir=slot_dir,
        source_manifest=source_manifest,
        prior=prior,
    )
    result = _ensure_audio_animal_sources(
        settings,
        plan,
        slot=slot,
        slot_dir=slot_dir,
        source_manifest=source_manifest,
        ledger=ledger,
    )
    _record_recovery(slot_dir, recovered)
    return result
