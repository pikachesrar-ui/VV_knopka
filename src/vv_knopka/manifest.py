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


def build_manifest(settings: Settings) -> list[Slot]:
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
