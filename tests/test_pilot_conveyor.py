from pathlib import Path

from vv_knopka.pilot_conveyor import expected_output, pending_slots, run_batch
from vv_knopka.settings import Settings


def _settings(tmp_path):
    raw = {
        "pilot": {
            "total_shorts": 15,
            "openai_budget_usd": 10.0,
            "auto_publish": False,
            "review_required": True,
            "runtime_dir": "runtime",
        },
        "content": {
            "niche": "animals_nature_curiosities",
            "ai_slots": [1, 3, 5, 7, 9, 11, 13, 15],
            "animal_slots": [2, 4, 6, 8, 10, 12, 14],
            "russian_slots": [1, 2],
        },
        "audio": {"transition_sfx": "none"},
    }
    return Settings(raw=raw, root=tmp_path)


def test_pending_slots_skip_existing_review_outputs(tmp_path):
    settings = _settings(tmp_path)
    ready = settings.runtime_dir / "ready_for_review"
    ready.mkdir(parents=True)
    for name in (
        "slot-01-ru-ai.mp4",
        "slot-02-ru-animals.mp4",
        "slot-03-en-ai.mp4",
        "slot-04-en-animals.mp4",
    ):
        (ready / name).write_bytes(b"video")

    pending = pending_slots(settings)
    assert pending[0].slot == 5
    assert pending[0].pipeline == "ai_short"
    assert expected_output(settings, pending[0]).name == "slot-05-en-ai.mp4"


def test_dry_run_does_not_render(tmp_path, capsys):
    settings = _settings(tmp_path)
    outputs = run_batch(
        settings,
        config_path=Path(tmp_path / "config" / "pilot.toml"),
        count=2,
        dry_run=True,
    )
    assert outputs == []
    text = capsys.readouterr().out
    assert "slot 01: ai_short / ru" in text
    assert "slot 02: animal_compilation / ru" in text
    assert not (settings.runtime_dir / "conveyor" / "state.json").exists()
