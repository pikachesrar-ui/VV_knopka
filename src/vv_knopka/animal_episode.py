from __future__ import annotations

import json
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
    """Return the long-run 80/20 EN/RU cadence for future cat episodes."""
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
    # Renderer wraps title cards safely; keep more of the actual generated title.
    if len(title) > 52:
        title = title[:49].rsplit(" ", 1)[0].rstrip(" -—:|,.!?") + "…"
    return f"#{episode_number:03d} — {title}"


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
    display_title = _clean_title(
        str(plan.get("title") or ""),
        episode_number=episode,
        language=language,
    )

    # Product decision: every inter-clip black card repeats the episode title.
    cards = [
        {
            "sequence": sequence,
            "clip_index": clip_index,
            "text": display_title,
        }
        for sequence, clip_index in enumerate(order, start=1)
    ]

    payload = {
        "version": 2,
        "episode_number": episode,
        "pilot_language": language,
        "production_language_cadence": "80% en / 20% ru; no duplicate translations",
        "scheduled_language_after_pilot": scheduled_animal_language(settings, episode),
        "display_title": display_title,
        "transition_cards": cards,
        "end_text": "Спасибо за просмотр" if language == "ru" else "Thanks for watching",
        "forbidden_series_phrases": list(_FORBIDDEN_SERIES_PHRASES),
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return output
