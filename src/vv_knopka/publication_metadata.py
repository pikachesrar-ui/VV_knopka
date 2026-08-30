from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .manifest import Slot
from .settings import Settings


def _with_shorts(title: str) -> str:
    value = " ".join(str(title or "").split()).strip()
    if not value:
        value = "Animal Curiosity"
    if "#shorts" not in value.casefold():
        value = f"{value} #shorts"
    return value[:100]


def _cat_episode_number(settings: Settings, slot: int) -> int:
    animal_slots = [int(value) for value in settings.raw["content"]["animal_slots"]]
    return animal_slots.index(int(slot)) + 1


def _required_attributions(slot_dir: Path) -> list[str]:
    path = slot_dir / "sources.json"
    if not path.exists():
        return []
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return []
    result: list[str] = []
    for item in raw.get("clips") or []:
        if not isinstance(item, dict) or item.get("attribution_required") is not True:
            continue
        text = str(item.get("attribution_text") or "").strip()
        if text and text not in result:
            result.append(text)
    return result


def build_upload_metadata(
    settings: Settings,
    *,
    slot: Slot,
    output: Path,
    slot_dir: Path,
) -> dict[str, Any]:
    """Build deterministic review-only upload metadata without publishing anything."""
    if slot.pipeline == "animal_compilation":
        episode = _cat_episode_number(settings, slot.slot)
        if slot.language == "ru":
            title = f"Котики, которые сделали мой день 😹 #{episode:03d} #shorts"
            description = "Небольшая подборка милых и смешных котиков."
        else:
            title = f"Cats That Made My Day 😹 #{episode:03d} #shorts"
            description = "A short collection of cute and funny cats."
        attributions = _required_attributions(slot_dir)
    else:
        plan_path = slot_dir / "plan.json"
        if not plan_path.exists():
            raise FileNotFoundError(f"missing {plan_path}")
        plan = json.loads(plan_path.read_text(encoding="utf-8"))
        title = _with_shorts(str(plan.get("title") or ""))
        description = str(plan.get("hook") or plan.get("summary") or "").strip()
        attributions = []

    description_lines = [description] if description else []
    if attributions:
        description_lines.append("")
        description_lines.append("Sources / Creative Commons attribution:")
        description_lines.extend(f"- {text}" for text in attributions)

    return {
        "slot": slot.slot,
        "pipeline": slot.pipeline,
        "language": slot.language,
        "video_file": str(output.resolve()),
        "youtube_title": title,
        "youtube_description": "\n".join(description_lines).strip(),
        "attributions": attributions,
        "review_required": True,
        "auto_publish": False,
        "publication_allowed_by_conveyor": False,
    }


def write_upload_metadata(
    settings: Settings,
    *,
    slot: Slot,
    output: Path,
    slot_dir: Path,
) -> Path:
    metadata = build_upload_metadata(settings, slot=slot, output=output, slot_dir=slot_dir)
    path = output.with_suffix(".upload.json")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(metadata, ensure_ascii=False, indent=2), encoding="utf-8")
    return path
