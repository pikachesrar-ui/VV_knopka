from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .settings import Settings
from .youtube_metadata_backfill import (
    _append_missing_hashtags,
    _desired_discovery_metadata,
    _merge_tags_preserving_existing,
    _read_json,
    _receipt_path,
)
from .youtube_uploader import ready_metadata


def _metadata_version(value: Any) -> int:
    try:
        return max(int(value), 0)
    except (TypeError, ValueError):
        return 0


def _merge_hashtag_fields(current: Any, desired: list[str]) -> list[str]:
    values = list(current) if isinstance(current, (list, tuple)) else []
    result: list[str] = []
    seen: set[str] = set()
    for raw in [*values, *desired]:
        value = str(raw or "").strip()
        key = value.casefold()
        if value and key not in seen:
            seen.add(key)
            result.append(value)
    return result


def pending_metadata_targets(settings: Settings, slots: set[int] | None) -> list[dict[str, Any]]:
    """Return ready metadata sidecars that have not yet received a YouTube receipt."""
    targets: list[dict[str, Any]] = []
    for metadata_path in ready_metadata(settings):
        metadata = _read_json(metadata_path)
        slot = int(metadata.get("slot") or 0)
        if slot <= 0 or (slots is not None and slot not in slots):
            continue
        if _receipt_path(metadata_path).exists():
            continue
        targets.append(
            {
                "slot": slot,
                "pipeline": str(metadata.get("pipeline") or "").strip(),
                "language": str(metadata.get("language") or "en").strip().lower(),
                "metadata_path": metadata_path,
                "metadata": metadata,
            }
        )
    return sorted(targets, key=lambda item: int(item["slot"]))


def upgrade_pending_metadata(
    settings: Settings,
    *,
    slots: set[int] | None = None,
    apply: bool = False,
) -> list[dict[str, Any]]:
    """Upgrade only unpublished ready sidecars with discovery metadata; never touch MP4 bytes."""
    targets = pending_metadata_targets(settings, slots)
    results: list[dict[str, Any]] = []

    for target in targets:
        metadata_path = Path(target["metadata_path"])
        metadata = dict(target["metadata"])
        hashtags, desired_tags = _desired_discovery_metadata(settings, target)

        current_tags = list(metadata.get("youtube_tags") or [])
        merged_tags, added_tags = _merge_tags_preserving_existing(current_tags, desired_tags)
        current_description = str(metadata.get("youtube_description") or "")
        new_description, added_hashtags = _append_missing_hashtags(current_description, hashtags)
        merged_hashtags = _merge_hashtag_fields(metadata.get("youtube_hashtags"), hashtags)
        target_version = max(_metadata_version(metadata.get("metadata_version")), 2)

        changed = bool(
            added_tags
            or added_hashtags
            or merged_hashtags != list(metadata.get("youtube_hashtags") or [])
            or target_version != _metadata_version(metadata.get("metadata_version"))
        )
        result: dict[str, Any] = {
            "slot": int(target["slot"]),
            "pipeline": str(target["pipeline"]),
            "language": str(target["language"]),
            "metadata_path": metadata_path,
            "added_tags": added_tags,
            "added_hashtags": added_hashtags,
            "changed": changed,
            "applied": False,
        }

        if apply and changed:
            backup_dir = settings.runtime_dir / "youtube" / "pending-metadata-backups"
            backup_dir.mkdir(parents=True, exist_ok=True)
            backup_path = backup_dir / f"{metadata_path.name}.before-v2.json"
            if not backup_path.exists():
                backup_path.write_text(metadata_path.read_text(encoding="utf-8"), encoding="utf-8")

            updated = dict(metadata)
            updated["youtube_description"] = new_description
            updated["youtube_hashtags"] = merged_hashtags
            updated["youtube_tags"] = merged_tags
            updated["metadata_version"] = target_version
            metadata_path.write_text(json.dumps(updated, ensure_ascii=False, indent=2), encoding="utf-8")
            result["applied"] = True
            result["backup_path"] = backup_path

        results.append(result)

    audit_path = settings.runtime_dir / "youtube" / "pending-metadata-upgrade-latest.json"
    audit_path.parent.mkdir(parents=True, exist_ok=True)
    audit_path.write_text(
        json.dumps(
            {
                "created_at": datetime.now(timezone.utc).isoformat(),
                "apply": bool(apply),
                "slots": sorted(slots) if slots is not None else None,
                "results": [
                    {
                        key: str(value) if isinstance(value, Path) else value
                        for key, value in item.items()
                    }
                    for item in results
                ],
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    return results
