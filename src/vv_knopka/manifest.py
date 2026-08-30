from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path
import json

from .settings import Settings


@dataclass(frozen=True)
class Slot:
    slot: int
    pipeline: str
    language: str
    status: str = "planned"


_ALLOWED_PIPELINES = {"ai_short", "animal_compilation"}
_ALLOWED_LANGUAGES = {"en", "ru"}


def build_manifest(settings: Settings) -> list[Slot]:
    """Return the immutable 15-slot pilot manifest."""
    content = settings.raw["content"]
    ai = set(content["ai_slots"])
    animals = set(content["animal_slots"])
    ru = set(content["russian_slots"])
    total = int(settings.raw["pilot"]["total_shorts"])

    if ai & animals or ai | animals != set(range(1, total + 1)):
        raise ValueError("ai_slots and animal_slots must partition all pilot slots")
    if len(ai) != 8 or len(animals) != 7:
        raise ValueError("pilot must contain exactly 8 AI and 7 animal-compilation slots")
    if len(ru & ai) != 1 or len(ru & animals) != 1:
        raise ValueError("pilot must contain one Russian slot per pipeline")

    return [
        Slot(i, "ai_short" if i in ai else "animal_compilation", "ru" if i in ru else "en")
        for i in range(1, total + 1)
    ]


def longrun_start_slot(settings: Settings) -> int:
    return int(settings.raw["pilot"]["total_shorts"]) + 1


def longrun_enabled(settings: Settings) -> bool:
    return bool(settings.raw.get("long_run", {}).get("enabled", False))


def _longrun_pipeline_cycle(settings: Settings) -> list[str]:
    raw = settings.raw.get("long_run", {}).get(
        "pipeline_cycle",
        ["animal_compilation", "ai_short"],
    )
    cycle = [str(value).strip() for value in raw if str(value).strip()]
    if not cycle or any(value not in _ALLOWED_PIPELINES for value in cycle):
        raise ValueError("long_run.pipeline_cycle must contain only ai_short/animal_compilation")
    return cycle


def _animal_language_cycle(settings: Settings) -> list[str]:
    raw = settings.raw.get("animal", {}).get("language_cycle", ["en", "en", "en", "en", "ru"])
    cycle = [str(value).strip().lower() for value in raw if str(value).strip()]
    if not cycle or any(value not in _ALLOWED_LANGUAGES for value in cycle):
        raise ValueError("animal.language_cycle must contain only en/ru")
    return cycle


def longrun_animal_ordinal(settings: Settings, slot: int) -> int:
    """Return the 1-based cat ordinal inside long-run only, or 0 for a non-cat/future-invalid slot."""
    start = longrun_start_slot(settings)
    number = int(slot)
    if number < start:
        return 0
    cycle = _longrun_pipeline_cycle(settings)
    ordinal = 0
    for current in range(start, number + 1):
        pipeline = cycle[(current - start) % len(cycle)]
        if pipeline == "animal_compilation":
            ordinal += 1
    if cycle[(number - start) % len(cycle)] != "animal_compilation":
        return 0
    return ordinal


def longrun_slot(settings: Settings, number: int) -> Slot:
    """Resolve one deterministic post-pilot slot without a finite manifest."""
    if not longrun_enabled(settings):
        raise ValueError("long-run generation is disabled")
    start = longrun_start_slot(settings)
    number = int(number)
    if number < start:
        raise ValueError(f"long-run slots start at {start}")

    cycle = _longrun_pipeline_cycle(settings)
    pipeline = cycle[(number - start) % len(cycle)]
    if pipeline == "animal_compilation":
        ordinal = longrun_animal_ordinal(settings, number)
        languages = _animal_language_cycle(settings)
        language = languages[(ordinal - 1) % len(languages)]
    else:
        language = str(
            settings.raw.get("long_run", {}).get(
                "ai_language",
                settings.raw.get("content", {}).get("default_language", "en"),
            )
        ).strip().lower()
        if language not in _ALLOWED_LANGUAGES:
            raise ValueError("long_run.ai_language must be en or ru")
    return Slot(number, pipeline, language)


def resolve_slot(settings: Settings, number: int) -> Slot:
    """Resolve a pilot slot or, after the pilot boundary, a deterministic long-run slot."""
    number = int(number)
    total = int(settings.raw["pilot"]["total_shorts"])
    if 1 <= number <= total:
        return build_manifest(settings)[number - 1]
    if number > total:
        return longrun_slot(settings, number)
    raise ValueError(f"slot must be >= 1 (got {number})")


def animal_episode_number_for_slot(settings: Settings, slot: int) -> int:
    """Stable cat-series numbering across the frozen pilot and unbounded long-run."""
    number = int(slot)
    pilot_animals = [int(value) for value in settings.raw["content"]["animal_slots"]]
    if number in pilot_animals:
        return pilot_animals.index(number) + 1
    ordinal = longrun_animal_ordinal(settings, number)
    if ordinal <= 0:
        raise ValueError(f"slot {number} is not an animal-compilation slot")
    return len(pilot_animals) + ordinal


def write_manifest(settings: Settings) -> Path:
    path = settings.runtime_dir / "pilot_manifest.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "niche": settings.raw["content"]["niche"],
        "auto_publish": settings.auto_publish,
        "slots": [asdict(slot) for slot in build_manifest(settings)],
    }
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return path
