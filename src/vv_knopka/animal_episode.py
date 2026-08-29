from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from .settings import Settings


_FORBIDDEN_SERIES_PHRASES = (
    "daily dose of cats",
    "your daily dose of cats",
)


def animal_episode_number(settings: Settings, slot: int) -> int:
    """Return a stable 1-based episode number for animal-compilation slots."""
    slots = [int(value) for value in settings.raw["content"]["animal_slots"]]
    if slot not in slots:
        raise ValueError(f"slot {slot} is not an animal-compilation slot")
    return slots.index(slot) + 1


def scheduled_animal_language(settings: Settings, episode_number: int) -> str:
    """Return the long-run 80/20 EN/RU cadence for future cat episodes.

    The frozen 15-video pilot keeps its existing slot languages. This helper is
    the production cadence after the pilot: four English originals, then one
    Russian original. We never translate/repost the same episode into both.
    """
    cycle = list(settings.raw.get("animal", {}).get("language_cycle", ["en", "en", "en", "en", "ru"]))
    if not cycle:
        cycle = ["en", "en", "en", "en", "ru"]
    language = str(cycle[(max(int(episode_number), 1) - 1) % len(cycle)]).strip().lower()
    return language if language in {"en", "ru"} else "en"


def _clean_title(value: str, *, episode_number: int, language: str) -> str:
    title = " ".join(str(value or "").replace("\n", " ").split()).strip(" -—:|.!?")
    lowered = title.casefold()
    if not title or any(phrase in lowered for phrase in _FORBIDDEN_SERIES_PHRASES):
        title = "Кото-хаос" if language == "ru" else "Cat Chaos"
    # Keep the black title card readable on a phone. The unique episode number
    # guarantees the displayed title cannot duplicate even if a future phrase repeats.
    if len(title) > 38:
        title = title[:35].rstrip(" -—:|,.!?") + "…"
    return f"#{episode_number:03d} — {title}"


def _clean_intro(value: str, *, language: str) -> str:
    text = " ".join(str(value or "").replace("\n", " ").split())
    if not text:
        return "Смотрим, что сегодня устроили коты." if language == "ru" else "Let's see what the cats are up to."
    # Edge TTS intro should stay brief enough for the opening card.
    if len(text) > 105:
        text = text[:102].rsplit(" ", 1)[0].rstrip(" ,;:-") + "."
    return text


def build_episode_metadata(
    settings: Settings,
    *,
    slot: int,
    language: str,
    plan: dict[str, Any],
    highlight_manifest: Path,
    output: Path,
) -> Path:
    highlights = json.loads(highlight_manifest.read_text(encoding="utf-8"))
    selections = {
        int(item["clip_index"]): item
        for item in highlights.get("selections", [])
        if isinstance(item, dict) and item.get("clip_index") is not None
    }
    order = [int(value) for value in highlights.get("order", []) if int(value) in selections]
    episode = animal_episode_number(settings, slot)

    cards: list[dict[str, Any]] = []
    for sequence, clip_index in enumerate(order, start=1):
        caption = " ".join(str(selections[clip_index].get("caption") or "").split())
        if not caption:
            caption = "Следующий котик" if language == "ru" else "Next cat"
        cards.append(
            {
                "sequence": sequence,
                "clip_index": clip_index,
                "text": caption[:64],
            }
        )

    payload = {
        "version": 1,
        "episode_number": episode,
        "pilot_language": language,
        "production_language_cadence": "80% en / 20% ru; no duplicate translations",
        "scheduled_language_after_pilot": scheduled_animal_language(settings, episode),
        "display_title": _clean_title(str(plan.get("title") or ""), episode_number=episode, language=language),
        "intro_voice": _clean_intro(str(plan.get("hook") or ""), language=language),
        "transition_cards": cards,
        "forbidden_series_phrases": list(_FORBIDDEN_SERIES_PHRASES),
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return output
