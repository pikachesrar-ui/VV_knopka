from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .settings import Settings


def _identity(item: dict[str, Any]) -> tuple[str, str] | None:
    provider = str(item.get("provider") or "").strip().lower()
    provider_id = str(item.get("provider_id") or "").strip()
    if provider and provider_id:
        return provider, provider_id
    source_url = str(item.get("source_url") or "").strip()
    if provider and source_url:
        return provider, source_url
    return None


def _manifest_identities(path: Path) -> set[tuple[str, str]]:
    if not path.exists():
        return set()
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return set()
    result: set[tuple[str, str]] = set()
    for item in raw.get("clips") or []:
        if isinstance(item, dict):
            identity = _identity(item)
            if identity:
                result.add(identity)
    return result


def prior_rendered_cat_identities(settings: Settings, *, before_slot: int) -> set[tuple[str, str]]:
    used: set[tuple[str, str]] = set()
    animal_slots = {int(value) for value in settings.raw["content"]["animal_slots"]}
    for slot in sorted(value for value in animal_slots if value < int(before_slot)):
        ready = settings.runtime_dir / "ready_for_review" / f"slot-{slot:02d}-*-animals.mp4"
        if not any(settings.runtime_dir.glob(str(ready.relative_to(settings.runtime_dir)))):
            continue
        used |= _manifest_identities(settings.runtime_dir / "slots" / f"{slot:02d}" / "sources.json")
    return used


def audit_cat_source_reuse(
    settings: Settings,
    *,
    slot: int,
    source_manifest: Path,
    max_reused_sources: int = 1,
) -> Path:
    """Stop heavily recycled cat episodes while allowing one incidental repeat."""
    current = _manifest_identities(source_manifest)
    prior = prior_rendered_cat_identities(settings, before_slot=slot)
    overlap = sorted(current & prior)
    audit = {
        "slot": int(slot),
        "current_unique_sources": len(current),
        "prior_unique_sources": len(prior),
        "reused_sources": [{"provider": provider, "provider_id": provider_id} for provider, provider_id in overlap],
        "max_reused_sources": int(max_reused_sources),
        "passed": len(overlap) <= int(max_reused_sources),
    }
    path = source_manifest.parent / "source_reuse_audit.json"
    path.write_text(json.dumps(audit, ensure_ascii=False, indent=2), encoding="utf-8")
    if not audit["passed"]:
        preview = ", ".join(f"{provider}:{provider_id}" for provider, provider_id in overlap[:5])
        raise RuntimeError(
            f"cat source reuse gate: {len(overlap)} sources were already used in earlier rendered cat episodes "
            f"(allowed {max_reused_sources}); examples: {preview}. Refresh the slot source pool before rendering."
        )
    return path
