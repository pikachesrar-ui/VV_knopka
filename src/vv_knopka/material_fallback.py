from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .settings import Settings


class CuratedMaterialFallbackError(RuntimeError):
    pass


def load_duration_sufficient_materials(
    settings: Settings,
    *,
    slot_dir: Path,
    expected_anchor: str | None = None,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Reuse already vision-approved stock when unique-source count is low.

    Stock libraries can have only a handful of truly relevant videos for a narrow
    subject. MoneyPrinterTurbo's random concat mode can split a long approved
    source into multiple non-overlapping clips. Therefore quality is better
    expressed as: enough unique approved sources + enough reusable duration,
    rather than an arbitrary requirement for eight separate files.

    Cached material is valid only for the visual anchor it was reviewed against.
    A regenerated plan for the same slot must never inherit footage from the old
    animal/topic.
    """
    audit_path = slot_dir / "ai_materials.json"
    if not audit_path.exists():
        raise CuratedMaterialFallbackError(f"missing material audit: {audit_path}")

    try:
        audit = json.loads(audit_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise CuratedMaterialFallbackError(f"cannot read material audit: {audit_path}") from exc

    audit_anchor = str(audit.get("visual_anchor") or "").strip()
    normalized_expected = str(expected_anchor or "").strip()
    if normalized_expected and audit_anchor.casefold() != normalized_expected.casefold():
        raise CuratedMaterialFallbackError(
            f"Cached material audit anchor {audit_anchor!r} does not match current plan anchor "
            f"{normalized_expected!r}."
        )

    materials_cfg = settings.raw.get("materials", {})
    video_cfg = settings.raw["video"]
    min_unique = int(materials_cfg.get("min_unique_ai_materials", 3))
    clip_seconds = int(video_cfg.get("clip_seconds", 6))
    max_segments_per_source = int(materials_cfg.get("max_segments_per_source", 4))
    min_reusable_seconds = float(materials_cfg.get("min_reusable_stock_seconds", 36))
    min_confidence = float(materials_cfg.get("vision_min_confidence", 0.72))

    local_videos_dir = Path(
        settings.root / "MoneyPrinterTurbo" / "storage" / "local_videos"
    ).resolve()

    materials: list[dict[str, Any]] = []
    reusable_seconds = 0.0
    seen_files: set[str] = set()

    for info in audit.get("materials", []):
        if not isinstance(info, dict):
            continue
        filename = str(info.get("local_file") or "").strip()
        provider = str(info.get("provider") or "").strip()
        confidence = float(info.get("vision_confidence") or 0)
        duration = float(info.get("duration") or 0)
        if (
            not filename
            or filename in seen_files
            or not provider
            or confidence < min_confidence
            or duration <= 0
            or not (local_videos_dir / filename).exists()
        ):
            continue

        source_info = {key: value for key, value in info.items() if key != "local_file"}
        materials.append(
            {
                "provider": provider,
                "url": filename,
                "duration": int(duration),
                "source_info": source_info,
            }
        )
        seen_files.add(filename)
        reusable_seconds += min(duration, clip_seconds * max_segments_per_source)

    stats = {
        "unique_sources": len(materials),
        "reusable_seconds": round(reusable_seconds, 2),
        "min_unique_sources": min_unique,
        "min_reusable_seconds": min_reusable_seconds,
        "max_segments_per_source": max_segments_per_source,
        "visual_anchor": audit_anchor,
        "audit_path": str(audit_path),
    }

    if len(materials) < min_unique:
        raise CuratedMaterialFallbackError(
            f"Only {len(materials)} vision-approved unique sources are cached; need at least {min_unique}."
        )
    if reusable_seconds < min_reusable_seconds:
        raise CuratedMaterialFallbackError(
            f"Approved sources provide only {reusable_seconds:.1f}s reusable footage; "
            f"need at least {min_reusable_seconds:.1f}s."
        )

    return materials, stats
