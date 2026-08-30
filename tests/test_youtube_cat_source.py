import json
from pathlib import Path

import pytest

import vv_knopka.youtube_cat_source as youtube_source


class DummySettings:
    def __init__(self, root: Path):
        self.root = root
        self.runtime_dir = root / "runtime"
        self.raw = {
            "animal": {
                "clip_seconds": 5,
                "min_source_mean_volume_db": -55.0,
                "source_aspect_tolerance": 0.08,
            }
        }


def test_require_verified_cc_rejects_standard_license():
    with pytest.raises(ValueError, match="does not verify Creative Commons"):
        youtube_source.require_verified_cc({"license": "Standard YouTube License"})

    assert youtube_source.require_verified_cc(
        {"license": "Creative Commons Attribution license (reuse allowed)"}
    ).startswith("Creative Commons")


def test_test_only_import_is_isolated_and_locked(tmp_path, monkeypatch):
    settings = DummySettings(tmp_path)
    local_file = tmp_path / "cat.mp4"
    local_file.write_bytes(b"test-cat")

    monkeypatch.setattr(
        youtube_source,
        "fetch_youtube_metadata",
        lambda url: {
            "video_id": "abc123",
            "title": "Funny cat",
            "creator": "Tester",
            "source_url": url,
            "license": "Standard YouTube License",
        },
    )
    monkeypatch.setattr(
        youtube_source,
        "_validate_cat_media",
        lambda settings, path: {
            "duration": 12.0,
            "has_audio": True,
            "mean_volume_db": -20.0,
            "source_width": 720,
            "source_height": 1280,
            "source_aspect_ratio": 0.5625,
            "source_sha256": "f" * 64,
        },
    )

    manifest, clip = youtube_source.add_test_only_file(
        settings,
        slot=2,
        url="https://www.youtube.com/watch?v=abc123",
        local_file=local_file,
        confirm_match=True,
    )

    assert "test_only" in manifest.parts
    assert not (settings.runtime_dir / "slots" / "02" / "sources.json").exists()
    raw = json.loads(manifest.read_text(encoding="utf-8"))
    assert raw["do_not_publish"] is True
    assert raw["publication_allowed"] is False
    assert clip["commercial_use_allowed"] is False
    assert clip["rights_verified"] is False
    assert clip["do_not_publish"] is True
    assert clip["publication_allowed"] is False
    assert Path(clip["file"]).exists()


def test_test_only_render_requires_publication_lock(tmp_path):
    settings = DummySettings(tmp_path)
    test_dir = settings.runtime_dir / "test_only" / "slot-02"
    test_dir.mkdir(parents=True)
    (test_dir / "sources.json").write_text(
        json.dumps(
            {
                "do_not_publish": False,
                "publication_allowed": False,
                "clips": [],
            }
        ),
        encoding="utf-8",
    )

    with pytest.raises(RuntimeError, match="publication lock is missing"):
        youtube_source.render_test_only(settings, slot=2)
