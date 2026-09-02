from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from .manifest import Slot, animal_episode_number_for_slot, longrun_start_slot
from .settings import Settings


_CAT_DESCRIPTIONS_EN = (
    "A short collection of cute and funny cats.",
    "A quick dose of playful, curious and dramatic cats.",
    "A few cats being charming, chaotic and completely themselves.",
    "Cute cat moments, tiny surprises and a little feline chaos.",
    "A short mix of playful cats and unexpectedly funny reactions.",
    "Thirty-something seconds of cats doing what cats do best.",
)

_CAT_DESCRIPTIONS_RU = (
    "Небольшая подборка милых и смешных котиков.",
    "Короткая подборка любопытных, игривых и немного хаотичных котиков.",
    "Несколько милых кошачьих моментов и неожиданных реакций.",
    "Котики, немного хаоса и несколько забавных моментов.",
    "Короткий микс игривых котиков и смешных кошачьих реакций.",
    "Полминуты котиков, которые просто делают свои кошачьи дела.",
)

_CAT_CTA_EN = (
    "Which cat was your favorite? 😹",
    "Which one made you laugh the most? 😹",
    "Rate the last cat from 1 to 10. 😹",
    "Which cat would you adopt? 😹",
)
_CAT_CTA_RU = (
    "Какой котик понравился больше всего? 😹",
    "Какой момент оказался самым смешным? 😹",
    "Оцени последнего котика от 1 до 10. 😹",
    "Какого котика ты бы забрал домой? 😹",
)

_CAT_HASHTAGS_EN = ("#cats", "#funnycats", "#catshorts", "#shorts")
_CAT_HASHTAGS_RU = ("#котики", "#смешныекотики", "#cats", "#shorts")


def _with_shorts(title: str) -> str:
    value = " ".join(str(title or "").split()).strip()
    if not value:
        value = "Animal Curiosity"
    if "#shorts" not in value.casefold():
        value = f"{value} #shorts"
    return value[:100]


def _cat_episode_number(settings: Settings, slot: int) -> int:
    return animal_episode_number_for_slot(settings, slot)


def _cat_description(settings: Settings, *, slot: Slot, episode: int) -> str:
    if slot.slot < longrun_start_slot(settings):
        return (
            "Небольшая подборка милых и смешных котиков."
            if slot.language == "ru"
            else "A short collection of cute and funny cats."
        )
    variants = _CAT_DESCRIPTIONS_RU if slot.language == "ru" else _CAT_DESCRIPTIONS_EN
    return variants[(max(int(episode), 1) - 1) % len(variants)]


def _cat_cta(slot: Slot, episode: int) -> str:
    variants = _CAT_CTA_RU if slot.language == "ru" else _CAT_CTA_EN
    return variants[(max(int(episode), 1) - 1) % len(variants)]


def _normalize_hashtag(value: Any) -> str:
    text = "".join(str(value or "").split()).strip()
    if not text:
        return ""
    if not text.startswith("#"):
        text = "#" + text
    body = re.sub(r"[^\w]", "", text[1:], flags=re.UNICODE)
    return f"#{body}" if body else ""


def _dedupe(values: list[str] | tuple[str, ...]) -> list[str]:
    result: list[str] = []
    seen: set[str] = set()
    for raw in values:
        value = str(raw or "").strip()
        key = value.casefold()
        if value and key not in seen:
            seen.add(key)
            result.append(value)
    return result


def _hashtags(values: list[Any] | tuple[Any, ...], *, fallback: tuple[str, ...] = ()) -> list[str]:
    normalized = [_normalize_hashtag(value) for value in values]
    result = _dedupe([value for value in normalized if value])
    if not result:
        result = list(fallback)
    if "#shorts" not in {value.casefold() for value in result}:
        result.append("#shorts")
    return result[:5]


def _youtube_tags(hashtags: list[str], *extra: str) -> list[str]:
    values = [tag.lstrip("#") for tag in hashtags]
    values.extend(extra)
    return _dedupe(values)[:12]


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


def _music_disclosure(slot_dir: Path) -> bool:
    path = slot_dir / "music.json"
    if not path.exists():
        return False
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return False
    return bool(raw.get("ai_generated") and raw.get("applied_to_video"))


def build_upload_metadata(
    settings: Settings,
    *,
    slot: Slot,
    output: Path,
    slot_dir: Path,
) -> dict[str, Any]:
    """Build deterministic upload metadata while preserving frozen-pilot bytes."""
    longrun = slot.slot >= longrun_start_slot(settings)
    plan: dict[str, Any] = {}

    if slot.pipeline == "animal_compilation":
        episode = _cat_episode_number(settings, slot.slot)
        if slot.language == "ru":
            title = f"Котики, которые сделали мой день 😹 #{episode:03d} #shorts"
        else:
            title = f"Cats That Made My Day 😹 #{episode:03d} #shorts"
        description = _cat_description(settings, slot=slot, episode=episode)
        attributions = _required_attributions(slot_dir)
        if longrun:
            hashtags = _hashtags(
                _CAT_HASHTAGS_RU if slot.language == "ru" else _CAT_HASHTAGS_EN
            )
            cta = _cat_cta(slot, episode)
            tags = _youtube_tags(
                hashtags,
                "cats",
                "funny cats",
                "cat compilation",
                "animals",
            )
        else:
            hashtags, tags, cta = [], [], ""
    else:
        plan_path = slot_dir / "plan.json"
        if not plan_path.exists():
            raise FileNotFoundError(f"missing {plan_path}")
        plan = json.loads(plan_path.read_text(encoding="utf-8"))
        title = _with_shorts(str(plan.get("title") or ""))
        description = str(plan.get("hook") or plan.get("summary") or "").strip()
        attributions = []
        if longrun:
            hashtags = _hashtags(list(plan.get("hashtags") or []), fallback=("#animals", "#shorts"))
            anchor = str(plan.get("visual_anchor") or "").strip()
            tags = _youtube_tags(
                hashtags,
                anchor,
                "animal facts",
                "nature facts",
                "animals",
            )
            cta = "What animal should we cover next?"
        else:
            hashtags, tags, cta = [], [], ""

    description_lines = [description] if description else []
    if longrun and cta:
        description_lines.extend(["", cta])
    if longrun and hashtags:
        description_lines.extend(["", " ".join(hashtags)])
    if attributions:
        description_lines.append("")
        description_lines.append("Sources / Creative Commons attribution:")
        description_lines.extend(f"- {text}" for text in attributions)

    if longrun:
        auto_publish = bool(settings.youtube_auto_publish)
        review_required = not auto_publish
        publication_allowed = auto_publish
    else:
        # Frozen pilot metadata is historical and must remain review-first.
        auto_publish = False
        review_required = True
        publication_allowed = False

    result = {
        "slot": slot.slot,
        "pipeline": slot.pipeline,
        "language": slot.language,
        "video_file": str(output.resolve()),
        "youtube_title": title,
        "youtube_description": "\n".join(description_lines).strip(),
        "attributions": attributions,
        "review_required": review_required,
        "auto_publish": auto_publish,
        "publication_allowed_by_conveyor": publication_allowed,
    }

    if longrun:
        result["youtube_hashtags"] = hashtags
        result["youtube_tags"] = tags
        result["contains_synthetic_media"] = bool(
            plan.get("ai_disclosure_recommended", False) or _music_disclosure(slot_dir)
        )
        result["metadata_version"] = 2
    return result


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
