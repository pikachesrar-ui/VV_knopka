from pathlib import Path

from vv_knopka.manifest import build_manifest
from vv_knopka.settings import load_settings


def settings():
    return load_settings(Path(__file__).parents[1] / "config" / "pilot.toml")


def test_pilot_split_and_languages():
    slots = build_manifest(settings())
    assert len(slots) == 15
    assert sum(s.pipeline == "ai_short" for s in slots) == 8
    assert sum(s.pipeline == "animal_compilation" for s in slots) == 7
    assert sum(s.language == "ru" for s in slots) == 2
    assert sum(s.language == "ru" and s.pipeline == "ai_short" for s in slots) == 1
    assert sum(s.language == "ru" and s.pipeline == "animal_compilation" for s in slots) == 1
