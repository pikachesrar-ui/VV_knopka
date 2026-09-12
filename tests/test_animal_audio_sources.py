import json
from pathlib import Path

import vv_knopka.animal_audio_sources as audio_sources


def test_short_portrait_accepts_916_and_rejects_landscape_or_45():
    assert audio_sources.is_short_portrait(1080, 1920, tolerance=0.08)
    assert audio_sources.is_short_portrait(720, 1280, tolerance=0.08)
    assert not audio_sources.is_short_portrait(1920, 1080, tolerance=0.08)
    assert not audio_sources.is_short_portrait(1080, 1350, tolerance=0.08)


def test_existing_audio_clips_rejects_silent_and_keeps_audible(tmp_path, monkeypatch):
    source_manifest = tmp_path / "sources.json"
    audible = tmp_path / "audible.mp4"
    silent = tmp_path / "silent.mp4"
    audible.write_bytes(b"audible")
    silent.write_bytes(b"silent")
    source_manifest.write_text(
        json.dumps(
            {
                "clips": [
                    {
                        "file": str(audible),
                        "source_url": "https://example.test/a",
                        "license": "Pexels License",
                        "commercial_use_allowed": True,
                        "provider": "pexels",
                        "provider_id": 1,
                    },
                    {
                        "file": str(silent),
                        "source_url": "https://example.test/b",
                        "license": "Pixabay Content License",
                        "commercial_use_allowed": True,
                        "provider": "pixabay",
                        "provider_id": 2,
                    },
                ]
            }
        ),
        encoding="utf-8",
    )
    audit = tmp_path / "ai_materials.json"
    audit.write_text(json.dumps({"materials": []}), encoding="utf-8")

    def fake_probe(path: Path, *, minimum_mean_db: float):
        assert minimum_mean_db == -55.0
        return (path.name == "audible.mp4", -18.0 if path.name == "audible.mp4" else None)

    monkeypatch.setattr(audio_sources, "video_dimensions", lambda path: (720, 1280))
    monkeypatch.setattr(audio_sources, "has_audible_audio", fake_probe)
    accepted, rejected = audio_sources._existing_audio_clips(
        source_manifest,
        audit,
        local_dir=tmp_path,
        minimum_mean_db=-55.0,
        aspect_tolerance=0.08,
    )

    assert len(accepted) == 1
    assert accepted[0]["provider_id"] == 1
    assert accepted[0]["has_audio"] is True
    assert accepted[0]["mean_volume_db"] == -18.0
    assert accepted[0]["source_width"] == 720
    assert accepted[0]["source_height"] == 1280
    assert len(rejected) == 1
    assert rejected[0]["provider_id"] == 2


def test_existing_audio_clips_rejects_landscape_even_when_audio_is_good(tmp_path, monkeypatch):
    source_manifest = tmp_path / "sources.json"
    landscape = tmp_path / "landscape.mp4"
    landscape.write_bytes(b"landscape")
    source_manifest.write_text(
        json.dumps(
            {
                "clips": [
                    {
                        "file": str(landscape),
                        "source_url": "https://example.test/landscape",
                        "license": "Pixabay Content License",
                        "commercial_use_allowed": True,
                        "provider": "pixabay",
                        "provider_id": 9,
                    }
                ]
            }
        ),
        encoding="utf-8",
    )
    audit = tmp_path / "ai_materials.json"
    audit.write_text(json.dumps({"materials": []}), encoding="utf-8")

    monkeypatch.setattr(audio_sources, "video_dimensions", lambda path: (1920, 1080))
    monkeypatch.setattr(
        audio_sources,
        "has_audible_audio",
        lambda path, *, minimum_mean_db: (True, -12.0),
    )

    accepted, rejected = audio_sources._existing_audio_clips(
        source_manifest,
        audit,
        local_dir=tmp_path,
        minimum_mean_db=-55.0,
        aspect_tolerance=0.08,
    )

    assert accepted == []
    assert len(rejected) == 1
    assert rejected[0]["provider_id"] == 9
    assert "not vertical" in rejected[0]["reason"]
    assert rejected[0]["dimensions"] == [1920, 1080]


def test_cached_material_can_be_promoted_to_audio_source(tmp_path, monkeypatch):
    local_dir = tmp_path / "local"
    local_dir.mkdir()
    file_path = local_dir / "cat.mp4"
    file_path.write_bytes(b"cat")
    source_manifest = tmp_path / "sources.json"
    source_manifest.write_text(json.dumps({"clips": []}), encoding="utf-8")
    audit = tmp_path / "ai_materials.json"
    audit.write_text(
        json.dumps(
            {
                "materials": [
                    {
                        "provider": "pexels",
                        "pexels_id": 123,
                        "page_url": "https://www.pexels.com/video/cat-123/",
                        "creator": "Tester",
                        "duration": 9,
                        "vision_confidence": 0.95,
                        "vision_reason": "cat visible",
                        "width": 720,
                        "height": 1280,
                        "local_file": "cat.mp4",
                    }
                ]
            }
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(audio_sources, "video_dimensions", lambda path: (720, 1280))
    monkeypatch.setattr(
        audio_sources,
        "has_audible_audio",
        lambda path, *, minimum_mean_db: (True, -22.5),
    )

    accepted, rejected = audio_sources._existing_audio_clips(
        source_manifest,
        audit,
        local_dir=local_dir,
        minimum_mean_db=-55.0,
        aspect_tolerance=0.08,
    )
    assert not rejected
    assert len(accepted) == 1
    assert accepted[0]["provider"] == "pexels"
    assert accepted[0]["provider_id"] == 123
    assert Path(accepted[0]["file"]) == file_path
