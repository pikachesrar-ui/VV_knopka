from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from .settings import Settings


_READY_ANIMAL_RE = re.compile(r"^slot-(\d+)-(?:en|ru)-animals\.mp4$", re.IGNORECASE)


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


def _rendered_cat_slots(settings: Settings, *, before_slot: int) -> list[int]:
    """Discover rendered cat slots from artifacts instead of the finite pilot manifest."""
    ready_dir = settings.runtime_dir / "ready_for_review"
    if not ready_dir.exists():
        return []
    result: set[int] = set()
    for path in ready_dir.glob("slot-*-*-animals.mp4"):
        match = _READY_ANIMAL_RE.match(path.name)
        if not match or path.stat().st_size <= 0:
            continue
        slot = int(match.group(1))
        if slot < int(before_slot):
            result.add(slot)
    return sorted(result)


def _identities_for_slots(settings: Settings, slots: list[int]) -> set[tuple[str, str]]:
    used: set[tuple[str, str]] = set()
    for slot in slots:
        used |= _manifest_identities(settings.runtime_dir / "slots" / f"{slot:02d}" / "sources.json")
    return used


def prior_rendered_cat_identities(settings: Settings, *, before_slot: int) -> set[tuple[str, str]]:
    """Return every source identity used by an earlier rendered cat episode."""
    return _identities_for_slots(
        settings,
        _rendered_cat_slots(settings, before_slot=before_slot),
    )


def cat_source_cooldown_episodes(settings: Settings) -> int:
    """Number of immediately preceding rendered cat episodes whose sources stay blocked in long-run."""
    return max(int(settings.raw.get("long_run", {}).get("cat_source_cooldown_episodes", 5)), 0)


def cat_cooled_reuse_max_sources(settings: Settings) -> int:
    """Maximum cooled-down source clips allowed in one new long-run cat Short."""
    return max(int(settings.raw.get("long_run", {}).get("cat_cooled_reuse_max_sources", 2)), 0)


def cat_cooled_reuse_max_per_history_episode(settings: Settings) -> int:
    """Maximum clips reused from any one older cat episode in a new Short."""
    return max(
        int(settings.raw.get("long_run", {}).get("cat_cooled_reuse_max_per_history_episode", 1)),
        0,
    )


def blocked_rendered_cat_slots(settings: Settings, *, before_slot: int) -> list[int]:
    """Return the rendered cat slots protected by the active source-reuse policy.

    The immutable pilot keeps the original all-history behavior. Post-pilot long-run
    uses a rolling episode cooldown so the finite licensed stock pool can rotate
    indefinitely without allowing recent clips to recur.
    """
    rendered = _rendered_cat_slots(settings, before_slot=before_slot)
    pilot_total = int(settings.raw.get("pilot", {}).get("total_shorts", 15))
    if int(before_slot) <= pilot_total:
        return rendered
    cooldown = cat_source_cooldown_episodes(settings)
    if cooldown <= 0:
        return []
    return rendered[-cooldown:]


def cooled_down_rendered_cat_slots(settings: Settings, *, before_slot: int) -> list[int]:
    """Return older rendered cat slots that are eligible again in long-run.

    The returned list is chronological. Consumers may deliberately reverse it when
    they want the most recently cooled episode first. Pilot slots never expose
    cooled-down history because the frozen pilot keeps all-history protection.
    """
    pilot_total = int(settings.raw.get("pilot", {}).get("total_shorts", 15))
    if int(before_slot) <= pilot_total:
        return []
    rendered = _rendered_cat_slots(settings, before_slot=before_slot)
    blocked = set(blocked_rendered_cat_slots(settings, before_slot=before_slot))
    return [slot for slot in rendered if slot not in blocked]


def blocked_cat_source_identities(settings: Settings, *, before_slot: int) -> set[tuple[str, str]]:
    """Return identities that may not be selected for this cat episode."""
    return _identities_for_slots(
        settings,
        blocked_rendered_cat_slots(settings, before_slot=before_slot),
    )


def _latest_history_slot_by_identity(
    settings: Settings,
    *,
    slots: list[int],
) -> dict[tuple[str, str], int]:
    latest: dict[tuple[str, str], int] = {}
    for history_slot in slots:
        for identity in _manifest_identities(
            settings.runtime_dir / "slots" / f"{history_slot:02d}" / "sources.json"
        ):
            latest[identity] = int(history_slot)
    return latest


def audit_cat_source_reuse(
    settings: Settings,
    *,
    slot: int,
    source_manifest: Path,
    max_reused_sources: int = 1,
) -> Path:
    """Enforce recent-reuse and cooled-history concentration limits.

    The frozen pilot protects all prior cat sources. Long-run protects the configured
    recent episode window, then permits only a small bounded amount of cooled history.
    This prevents a fallback from reconstructing a new episode mostly out of one old
    compilation even when those sources are technically outside the cooldown window.
    """
    current = _manifest_identities(source_manifest)
    all_prior = prior_rendered_cat_identities(settings, before_slot=slot)
    blocked_prior_slots = blocked_rendered_cat_slots(settings, before_slot=slot)
    blocked_prior = _identities_for_slots(settings, blocked_prior_slots)
    recent_overlap = sorted(current & blocked_prior)
    cooled_overlap = sorted(current & (all_prior - blocked_prior))
    pilot_total = int(settings.raw.get("pilot", {}).get("total_shorts", 15))
    is_long_run = int(slot) > pilot_total
    cooldown = cat_source_cooldown_episodes(settings) if is_long_run else None

    cooled_slots = cooled_down_rendered_cat_slots(settings, before_slot=slot) if is_long_run else []
    latest_slot = _latest_history_slot_by_identity(settings, slots=cooled_slots)
    cooled_by_slot: dict[int, int] = {}
    for identity in cooled_overlap:
        history_slot = latest_slot.get(identity)
        if history_slot is not None:
            cooled_by_slot[history_slot] = cooled_by_slot.get(history_slot, 0) + 1

    max_cooled = cat_cooled_reuse_max_sources(settings) if is_long_run else 0
    max_per_history = cat_cooled_reuse_max_per_history_episode(settings) if is_long_run else 0
    recent_passed = len(recent_overlap) <= int(max_reused_sources)
    cooled_total_passed = not is_long_run or len(cooled_overlap) <= max_cooled
    cooled_episode_passed = not is_long_run or all(
        count <= max_per_history for count in cooled_by_slot.values()
    )
    passed = recent_passed and cooled_total_passed and cooled_episode_passed

    audit = {
        "slot": int(slot),
        "history_policy": "rolling_cat_episode_cooldown" if is_long_run else "pilot_all_history",
        "cooldown_cat_episodes": cooldown,
        "blocked_prior_slots": blocked_prior_slots,
        "current_unique_sources": len(current),
        "prior_unique_sources": len(all_prior),
        "blocked_prior_unique_sources": len(blocked_prior),
        "reused_sources": [
            {"provider": provider, "provider_id": provider_id}
            for provider, provider_id in recent_overlap
        ],
        "reused_cooled_down_sources": [
            {"provider": provider, "provider_id": provider_id}
            for provider, provider_id in cooled_overlap
        ],
        "cooled_reuse_by_history_slot": {
            str(history_slot): count for history_slot, count in sorted(cooled_by_slot.items())
        },
        "max_reused_sources": int(max_reused_sources),
        "max_cooled_reuse_sources": max_cooled if is_long_run else None,
        "max_cooled_reuse_per_history_episode": max_per_history if is_long_run else None,
        "recent_reuse_passed": recent_passed,
        "cooled_reuse_passed": cooled_total_passed and cooled_episode_passed,
        "passed": passed,
    }
    path = source_manifest.parent / "source_reuse_audit.json"
    path.write_text(json.dumps(audit, ensure_ascii=False, indent=2), encoding="utf-8")
    if not passed:
        if not recent_passed:
            preview = ", ".join(f"{provider}:{provider_id}" for provider, provider_id in recent_overlap[:5])
            raise RuntimeError(
                f"cat source reuse gate: {len(recent_overlap)} sources were used inside the protected history window "
                f"(allowed {max_reused_sources}); examples: {preview}. Refresh the slot source pool before rendering."
            )
        concentration = ", ".join(
            f"slot {history_slot}: {count}" for history_slot, count in sorted(cooled_by_slot.items())
        ) or "no source-slot mapping"
        raise RuntimeError(
            "cat cooled-source reuse gate: "
            f"{len(cooled_overlap)} cooled sources were reused (allowed total {max_cooled}, "
            f"max {max_per_history} per history episode); {concentration}. "
            "Refresh fresh stock instead of rebuilding the Short from old episodes."
        )
    return path
