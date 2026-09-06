from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .manifest import animal_episode_number_for_slot
from .settings import Settings
from .editorial import PROFILE, enabled_for_slot


_FORBIDDEN_SERIES_PHRASES = (
    "daily dose of cats",
    "your daily dose of cats",
)


def animal_episode_number(settings: Settings, slot: int) -> int:
    """Return stable 1-based cat episode numbering across pilot and long-run."""
    return animal_episode_number_for_slot(settings, slot)


def scheduled_animal_language(settings: Settings, episode_number: int) -> str:
    """Return the configured long-run EN/RU cadence for cat episodes."""
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
        "version": 3,
        "episode_number": episode,
        "language": language,
        "production_language_cadence": "long-run cat cycle is config-driven; no duplicate translations",
        "display_title": display_title,
        "transition_cards": cards,
        "end_text": "Спасибо за просмотр" if language == "ru" else "Thanks for watching",
        "forbidden_series_phrases": list(_FORBIDDEN_SERIES_PHRASES),
    }
    if enabled_for_slot(settings, slot) and highlights.get("editorial_profile") == PROFILE:
        first = selections[order[0]]
        caption = " ".join(str(first.get("caption") or "").split())[:70]
        if not caption:
            raise ValueError("Editorial cat cut needs a caption describing the opening moment")
        payload.update({
            "editorial_profile": PROFILE,
            "youtube_title": ("Котики: " if language == "ru" else "Cats: ") + caption,
            "youtube_description": " ".join(str(selections[i].get("description") or "").strip() for i in order),
            "transition_cards": [],
            "end_text": "",
        })
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return output
