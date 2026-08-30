from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Callable

from . import animal_audio_sources as _base
from .animal_audio_sources_v2 import (
    _normalize_source_policy,
    sanitize_unapproved_youtube_sources,
)
from .budget import BudgetLedger
from .settings import Settings
from .source_history import prior_rendered_cat_identities


def _identity_from_clip(item: dict[str, Any]) -> tuple[str, str] | None:
    provider = str(item.get("provider") or "").strip().lower()
    provider_id = str(item.get("provider_id") or "").strip()
    if provider and provider_id:
        return provider, provider_id
    return None


def _identity_from_cached_material(item: dict[str, Any]) -> tuple[str, str] | None:
    provider = str(item.get("provider") or "").strip().lower()
    if not provider:
        return None
    provider_id = str(item.get(f"{provider}_id") or item.get("provider_id") or "").strip()
    if provider_id:
        return provider, provider_id
    return None


def _remove_prior_from_manifest(
    source_manifest: Path,
    prior: set[tuple[str, str]],
) -> list[dict[str, Any]]:
    if not source_manifest.exists() or not prior:
        return []
    try:
        raw = json.loads(source_manifest.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return []

    clips = raw.get("clips") or []
    if not isinstance(clips, list):
        return []

    kept: list[dict[str, Any]] = []
    removed: list[dict[str, Any]] = []
    for item in clips:
        if not isinstance(item, dict):
            continue
        identity = _identity_from_clip(item)
        if identity and identity in prior:
            removed.append(
                {
                    "provider": identity[0],
                    "provider_id": identity[1],
                    "file": item.get("file"),
                    "source_url": item.get("source_url"),
                    "reason": "excluded before sourcing because this clip was used in an earlier rendered cat episode",
                }
            )
            continue
        kept.append(item)

    if removed:
        raw["clips"] = kept
        source_manifest.write_text(json.dumps(raw, ensure_ascii=False, indent=2), encoding="utf-8")
    return removed


def _remove_prior_from_cached_materials(
    audit_path: Path,
    prior: set[tuple[str, str]],
) -> list[dict[str, Any]]:
    """Prevent a slot-local legacy material cache from reintroducing old episode clips."""
    if not audit_path.exists() or not prior:
        return []
    try:
        raw = json.loads(audit_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return []

    materials = raw.get("materials") or []
    if not isinstance(materials, list):
        return []

    kept: list[dict[str, Any]] = []
    removed: list[dict[str, Any]] = []
    for item in materials:
        if not isinstance(item, dict):
            continue
        identity = _identity_from_cached_material(item)
        if identity and identity in prior:
            removed.append(
                {
                    "provider": identity[0],
                    "provider_id": identity[1],
                    "file": item.get("local_file"),
                    "source_url": item.get("page_url"),
                    "reason": "excluded from cached material pool because this clip was used in an earlier rendered cat episode",
                }
            )
            continue
        kept.append(item)

    if removed:
        raw["materials"] = kept
        raw["cross_episode_cache_filter_removed"] = len(removed)
        audit_path.write_text(json.dumps(raw, ensure_ascii=False, indent=2), encoding="utf-8")
    return removed


def _filtered_collector(
    original: Callable[..., list[dict[str, Any]]],
    *,
    provider: str,
    prior: set[tuple[str, str]],
) -> Callable[..., list[dict[str, Any]]]:
    def collect(**kwargs: Any) -> list[dict[str, Any]]:
        candidates = original(**kwargs)
        return [
            item
            for item in candidates
            if (provider, str(item.get("id") or "")) not in prior
        ]

    return collect


def _append_history_audit(
    slot_dir: Path,
    *,
    prior_count: int,
    removed: list[dict[str, Any]],
) -> None:
    audit_path = slot_dir / "animal_audio_sources.json"
    if not audit_path.exists():
        return
    try:
        raw = json.loads(audit_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return

    rejected = raw.setdefault("rejected_or_tested", [])
    if isinstance(rejected, list) and removed:
        rejected[:0] = removed
    raw["cross_episode_source_filter"] = {
        "enabled": True,
        "prior_source_ids": int(prior_count),
        "removed_cached_or_manifest_sources": len(removed),
        "policy": "previously rendered cat source IDs are excluded before new sourcing; final reuse audit remains fail-closed",
    }
    audit_path.write_text(json.dumps(raw, ensure_ascii=False, indent=2), encoding="utf-8")


def ensure_audio_animal_sources(
    settings: Settings,
    plan: dict[str, Any],
    *,
    slot: int,
    slot_dir: Path,
    source_manifest: Path,
    ledger: BudgetLedger,
) -> Path:
    """Source cats while automatically excluding clips used by earlier rendered episodes."""
    prior = prior_rendered_cat_identities(settings, before_slot=slot)

    removed: list[dict[str, Any]] = []
    removed.extend(sanitize_unapproved_youtube_sources(source_manifest))
    removed.extend(_remove_prior_from_manifest(source_manifest, prior))
    removed.extend(_remove_prior_from_cached_materials(slot_dir / "ai_materials.json", prior))

    original_pexels = _base._collect_pexels_audio_candidates
    original_pixabay = _base._collect_pixabay_candidates
    _base._collect_pexels_audio_candidates = _filtered_collector(
        original_pexels,
        provider="pexels",
        prior=prior,
    )
    _base._collect_pixabay_candidates = _filtered_collector(
        original_pixabay,
        provider="pixabay",
        prior=prior,
    )

    try:
        result = _base.ensure_audio_animal_sources(
            settings,
            plan,
            slot=slot,
            slot_dir=slot_dir,
            source_manifest=source_manifest,
            ledger=ledger,
        )
    finally:
        _base._collect_pexels_audio_candidates = original_pexels
        _base._collect_pixabay_candidates = original_pixabay

    _append_history_audit(slot_dir, prior_count=len(prior), removed=removed)
    _normalize_source_policy(result)
    return result
