import json
from pathlib import Path

from vv_knopka import music_cli
from vv_knopka.music_library import music_library_dir
from vv_knopka.settings import Settings


def _settings(tmp_path: Path) -> Settings:
    return Settings(
        raw={
            "pilot": {"runtime_dir": "runtime", "openai_budget_usd": 10.0, "auto_publish": False},
            "music": {"library_dir": "runtime/assets/music", "enabled": False},
        },
        root=tmp_path,
    )


def test_candidate_listing_ignores_generation_manifest(tmp_path):
    settings = _settings(tmp_path)
    root = music_library_dir(settings) / "candidates"
    root.mkdir(parents=True)
    (root / "cute_01.wav").write_bytes(b"audio")
    (root / "generation.json").write_text("[]", encoding="utf-8")

    assert [path.name for path in music_cli._candidate_files(settings)] == ["cute_01.wav"]


def test_mark_approved_updates_generation_manifest(tmp_path):
    settings = _settings(tmp_path)
    path = music_cli._manifest_path(settings)
    path.write_text(
        json.dumps([
            {"name": "cute_01.wav", "approved": False},
            {"name": "calm_01.wav", "approved": False},
        ]),
        encoding="utf-8",
    )

    music_cli._mark_approved(settings, {"cute_01.wav"})
    rows = json.loads(path.read_text(encoding="utf-8"))

    assert rows[0]["name"] == "calm_01.wav"
    assert rows[0]["approved"] is False
    assert rows[1]["name"] == "cute_01.wav"
    assert rows[1]["approved"] is True


def test_preset_names_are_stable_by_category():
    names = [music_cli._next_name(category, index) for index, (category, _bpm, _prompt) in enumerate(music_cli._PRESETS)]
    assert names == [
        "cute_01.wav",
        "cute_02.wav",
        "playful_01.wav",
        "playful_02.wav",
        "curious_01.wav",
        "curious_02.wav",
        "calm_01.wav",
        "calm_02.wav",
    ]


def test_approved_track_resolves_only_library_root(tmp_path):
    settings = _settings(tmp_path)
    root = music_library_dir(settings)
    root.mkdir(parents=True)
    approved = root / "cute_01.wav"
    approved.write_bytes(b"audio")
    candidates = root / "candidates"
    candidates.mkdir()
    (candidates / "cute_02.wav").write_bytes(b"candidate")

    assert music_cli._approved_track(settings, "cute_01.wav") == approved.resolve()


def test_preview_output_defaults_to_runtime_music_previews(tmp_path):
    settings = _settings(tmp_path)
    source = tmp_path / "finished.mp4"
    track = music_library_dir(settings) / "cute_01.wav"

    output = music_cli._preview_output(settings, source, track, "animal_compilation", None)

    assert output == settings.runtime_dir / "music" / "previews" / "finished.animal_compilation.cute_01.preview.mp4"


def test_preview_output_resolves_explicit_relative_path(tmp_path):
    settings = _settings(tmp_path)
    source = tmp_path / "finished.mp4"
    track = music_library_dir(settings) / "curious_01.wav"

    output = music_cli._preview_output(settings, source, track, "ai_short", "runtime/custom-preview.mp4")

    assert output == (tmp_path / "runtime" / "custom-preview.mp4").resolve()
