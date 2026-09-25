from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .animal_audio_sources import ensure_audio_animal_sources as _ensure_audio_animal_sources
from .budget import BudgetLedger
from .settings import Settings


def sanitize_unapproved_youtube_sources(source_manifest: Path) -> list[dict[str, Any]]:
    """Remove YouTube clips that have not passed the clean-footage vision gate.

    This deliberately treats pre-gate legacy imports as unapproved. They can be
    reviewed with `vv-cat-youtube cc-clean SLOT` and re-added only after passing.
    """
    if not source_manifest.exists():
        return []
    try:
        raw = json.loads(source_manifest.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return []

    clips = raw.get("clips") or []
    if not isinstance(clips, list):
        return []

    kept: list[dict[str, Any]] = []
    rejected: list[dict[str, Any]] = []
    for item in clips:
        if not isinstance(item, dict):
            continue
        provider = str(item.get("provider") or "").strip().lower()
        if provider == "youtube" and item.get("clean_footage_approved") is not True:
            rejected.append(
                {
                    "provider": "youtube",
                    "provider_id": item.get("provider_id"),
                    "file": item.get("file"),
                    "source_url": item.get("source_url"),
                    "reason": "YouTube source has no clean_footage_approved=true review",
                }
            )
            continue
        kept.append(item)

    if rejected:
        raw["clips"] = kept
        raw["require_clean_youtube_footage"] = True
        source_manifest.write_text(json.dumps(raw, ensure_ascii=False, indent=2), encoding="utf-8")
    return rejected


def _append_clean_rejections(slot_dir: Path, rows: list[dict[str, Any]]) -> None:
    if not rows:
        return
    audit_path = slot_dir / "animal_audio_sources.json"
    if not audit_path.exists():
        return
    try:
        audit = json.loads(audit_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return
    rejected = audit.setdefault("rejected_or_tested", [])
    if isinstance(rejected, list):
        rejected[:0] = rows
    audit["youtube_clean_gate"] = {
        "required": True,
        "legacy_or_unapproved_removed": len(rows),
    }
    audit_path.write_text(json.dumps(audit, ensure_ascii=False, indent=2), encoding="utf-8")


def _normalize_source_policy(source_manifest: Path) -> None:
    if not source_manifest.exists():
        return
    try:
        raw = json.loads(source_manifest.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return
    clips = raw.get("clips") or []
    has_youtube = any(
        isinstance(item, dict) and str(item.get("provider") or "").strip().lower() == "youtube"
        for item in clips
    )
    raw["require_clean_youtube_footage"] = True
    raw["source_policy"] = (
        "clean-reviewed YouTube Creative Commons plus vision-approved licensed vertical stock with audible source audio"
        if has_youtube
        else "vision-approved licensed vertical stock with audible source audio"
    )
    source_manifest.write_text(json.dumps(raw, ensure_ascii=False, indent=2), encoding="utf-8")


def ensure_audio_animal_sources(
    settings: Settings,
    plan: dict[str, Any],
    *,
    slot: int,
    slot_dir: Path,
    source_manifest: Path,
    ledger: BudgetLedger,
) -> Path:
    removed = sanitize_unapproved_youtube_sources(source_manifest)
    try:
        result = _ensure_audio_animal_sources(
            settings,
            plan,
            slot=slot,
            slot_dir=slot_dir,
            source_manifest=source_manifest,
            ledger=ledger,
        )
    except RuntimeError:
        _append_clean_rejections(slot_dir, removed)
        raise
    _append_clean_rejections(slot_dir, removed)
    _normalize_source_policy(result)
    return result
