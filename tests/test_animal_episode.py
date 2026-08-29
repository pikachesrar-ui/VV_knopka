import json
import wave

from vv_knopka.animal_episode import (
    animal_episode_number,
    build_episode_metadata,
    scheduled_animal_language,
)
from vv_knopka.animal_v3 import _generate_quick_meow
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


def test_episode_metadata_numbers_title_and_blocks_daily_dose_phrase(tmp_path):
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
    assert data["intro_voice"] == "Коты снова что-то задумали."
    assert [item["text"] for item in data["transition_cards"]] == ["Лазер победил", "Почти поймал"]


def test_quick_meow_is_short_and_non_silent(tmp_path):
    path = _generate_quick_meow(tmp_path / "quick.wav")
    with wave.open(str(path), "rb") as handle:
        duration = handle.getnframes() / handle.getframerate()
        raw = handle.readframes(handle.getnframes())
    values = memoryview(raw).cast("h")
    assert 0.28 <= duration <= 0.31
    assert max(abs(int(value)) for value in values) > 100
