from pathlib import Path

from vv_knopka.music_library import (
    available_tracks,
    music_library_dir,
    select_background_track,
    write_music_audit,
)
from vv_knopka.settings import Settings


def _settings(tmp_path: Path, *, enabled: bool = True) -> Settings:
    return Settings(
        raw={
            "pilot": {"runtime_dir": "runtime", "openai_budget_usd": 10.0, "auto_publish": False},
            "music": {
                "enabled": enabled,
                "library_dir": "runtime/assets/music",
                "cooldown_shorts": 2,
                "ai_generated": True,
                "generator": "ACE-Step",
                "ai_volume": 0.10,
                "cat_volume": 0.07,
                "ducking": True,
            },
        },
        root=tmp_path,
    )


def _track(root: Path, name: str) -> Path:
    root.mkdir(parents=True, exist_ok=True)
    path = root / name
    path.write_bytes(name.encode("utf-8"))
    return path


def test_music_library_is_local_runtime_asset(tmp_path):
    settings = _settings(tmp_path)
    assert music_library_dir(settings) == (tmp_path / "runtime" / "assets" / "music").resolve()


def test_disabled_music_never_selects_track(tmp_path):
    settings = _settings(tmp_path, enabled=False)
    _track(music_library_dir(settings), "curious-01.wav")
    assert select_background_track(settings, slot=17, pipeline="ai_short") is None


def test_candidate_subdirectory_is_not_part_of_production_rotation(tmp_path):
    settings = _settings(tmp_path)
    root = music_library_dir(settings)
    _track(root / "candidates", "curious_01.wav")
    assert available_tracks(settings) == []
    assert select_background_track(settings, slot=17, pipeline="ai_short") is None


def test_pipeline_prefers_matching_track_category(tmp_path):
    settings = _settings(tmp_path)
    root = music_library_dir(settings)
    _track(root, "cute-01.wav")
    _track(root, "curious-01.wav")
    _track(root, "calm-01.wav")

    assert [p.name for p in available_tracks(settings, pipeline="ai_short")][0] == "curious-01.wav"
    assert [p.name for p in available_tracks(settings, pipeline="animal_compilation")][0] == "cute-01.wav"


def test_recent_track_is_avoided_by_cooldown(tmp_path):
    settings = _settings(tmp_path)
    root = music_library_dir(settings)
    first = _track(root, "curious-01.wav")
    second = _track(root, "curious-02.wav")

    slot16 = settings.runtime_dir / "slots" / "16"
    write_music_audit(
        settings,
        slot=16,
        pipeline="ai_short",
        track=first,
        slot_dir=slot16,
        applied_to_video=True,
    )

    selected = select_background_track(settings, slot=17, pipeline="ai_short")
    assert selected == second.resolve()


def test_music_audit_records_ai_generation_and_hash(tmp_path):
    settings = _settings(tmp_path)
    track = _track(music_library_dir(settings), "playful-01.wav")
    audit = write_music_audit(
        settings,
        slot=18,
        pipeline="animal_compilation",
        track=track,
        slot_dir=settings.runtime_dir / "slots" / "18",
        applied_to_video=False,
    )
    text = audit.read_text(encoding="utf-8")
    assert '"ai_generated": true' in text
    assert '"generator": "ACE-Step"' in text
    assert '"applied_to_video": false' in text
    assert '"sha256":' in text
