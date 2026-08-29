import json
import tomllib
import wave
from pathlib import Path

from vv_knopka.animal_episode import (
    animal_episode_number,
    build_episode_metadata,
    scheduled_animal_language,
)
from vv_knopka.animal_v3 import _generate_quick_meow, _wrap_card_text
from vv_knopka.settings import Settings


def _settings(tmp_path):
    return Settings(
        raw={
            "content": {"animal_slots": [2, 4, 6, 8, 10, 12, 14]},
            "animal": {"language_cycle": ["en", "en", "en", "en", "ru"]},
            "pilot": {"openai_budget_usd": 10.0, "runtime_dir": "runtime"},
        },
        root=tmp_path,
    )


def test_animal_episode_number_and_80_20_cycle(tmp_path):
    settings = _settings(tmp_path)
    assert animal_episode_number(settings, 2) == 1
    assert animal_episode_number(settings, 10) == 5
    assert [scheduled_animal_language(settings, i) for i in range(1, 11)] == [
        "en", "en", "en", "en", "ru",
        "en", "en", "en", "en", "ru",
    ]


def test_episode_metadata_repeats_title_on_transitions_and_has_localized_end(tmp_path):
    settings = _settings(tmp_path)
    highlights = tmp_path / "highlights.json"
    highlights.write_text(
        json.dumps(
            {
                "order": [2, 1],
                "selections": [
                    {"clip_index": 1, "caption": "Почти поймал"},
                    {"clip_index": 2, "caption": "Лазер победил"},
                ],
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    output = tmp_path / "episode.json"
    build_episode_metadata(
        settings,
        slot=2,
        language="ru",
        plan={"title": "Daily Dose of Cats", "hook": "Коты снова что-то задумали."},
        highlight_manifest=highlights,
        output=output,
    )
    data = json.loads(output.read_text(encoding="utf-8"))
    assert data["display_title"] == "#001 — Кото-хаос"
    assert "intro_voice" not in data
    assert data["end_text"] == "Спасибо за просмотр"
    assert [item["text"] for item in data["transition_cards"]] == [
        "#001 — Кото-хаос",
        "#001 — Кото-хаос",
    ]


def test_long_numbered_title_wraps_inside_phone_card():
    wrapped = _wrap_card_text("#001 — Кошки и их важные маленькие миссии", width=22)
    lines = wrapped.splitlines()
    assert lines[0] == "#001"
    assert 2 <= len(lines) <= 4
    assert max(len(line) for line in lines) <= 22
    assert "маленькие" in wrapped


def test_quick_meow_is_short_and_non_silent(tmp_path):
    path = _generate_quick_meow(tmp_path / "quick.wav")
    with wave.open(str(path), "rb") as handle:
        duration = handle.getnframes() / handle.getframerate()
        raw = handle.readframes(handle.getnframes())
    values = memoryview(raw).cast("h")
    assert 0.28 <= duration <= 0.31
    assert max(abs(int(value)) for value in values) > 100


def test_pilot_uses_canonical_edge_tts_voice_ids_for_mpt_ai_shorts():
    config_path = Path(__file__).resolve().parents[1] / "config" / "pilot.toml"
    with config_path.open("rb") as handle:
        config = tomllib.load(handle)
    assert config["audio"]["edge_voice_ru"] == "ru-RU-SvetlanaNeural"
    assert config["audio"]["edge_voice_en"] == "en-US-AriaNeural"
    assert config["animal"]["intro_card_seconds"] < config["animal"]["transition_card_seconds"] + 0.3
    assert config["animal"]["require_source_audio"] is True
    assert "bgm_volume" not in config["animal"]
