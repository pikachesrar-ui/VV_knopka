import json
from pathlib import Path

import pytest

import vv_knopka.youtube_cc_preflight as preflight


class DummySettings:
    def __init__(self, root: Path):
        self.runtime_dir = root / "runtime"
        self.raw = {
            "pilot": {"openai_budget_usd": 10.0},
            "animal": {
                "source_aspect_tolerance": 0.08,
                "clip_seconds": 5.0,
            },
        }


def test_known_rejected_video_ids_reads_failed_clean_reviews(tmp_path):
    review_dir = tmp_path / "runtime" / "slots" / "02" / "youtube_clean_reviews"
    review_dir.mkdir(parents=True)
    (review_dir / "bad.json").write_text(
        json.dumps({"video_id": "bad1", "clean_footage_approved": False}),
        encoding="utf-8",
    )
    (review_dir / "good.json").write_text(
        json.dumps({"video_id": "good1", "clean_footage_approved": True}),
        encoding="utf-8",
    )
    assert preflight.known_rejected_video_ids(tmp_path / "runtime") == {"bad1"}


def test_known_rejected_video_ids_reads_durable_format_rejects(tmp_path):
    reject_dir = tmp_path / "runtime" / "slots" / "02" / "youtube_preflight_rejects"
    reject_dir.mkdir(parents=True)
    (reject_dir / "wide.json").write_text(
        json.dumps({"video_id": "wide1", "durable_reject": True}),
        encoding="utf-8",
    )
    (reject_dir / "transient.json").write_text(
        json.dumps({"video_id": "retry1", "durable_reject": False}),
        encoding="utf-8",
    )
    assert preflight.known_preflight_rejected_video_ids(tmp_path / "runtime") == {"wide1"}
    assert preflight.known_rejected_video_ids(tmp_path / "runtime") == {"wide1"}


def test_filter_known_rejections_removes_previous_failures(tmp_path):
    review_dir = tmp_path / "runtime" / "slots" / "02" / "youtube_clean_reviews"
    review_dir.mkdir(parents=True)
    (review_dir / "bad.json").write_text(
        json.dumps({"video_id": "bad1", "clean_footage_approved": False}),
        encoding="utf-8",
    )
    candidates = [{"video_id": "bad1"}, {"video_id": "good1"}]
    kept, removed = preflight.filter_known_rejections(candidates, tmp_path / "runtime")
    assert kept == [{"video_id": "good1"}]
    assert removed == ["bad1"]


def test_preview_format_rejects_wide_portrait_before_luna(monkeypatch, tmp_path):
    settings = DummySettings(tmp_path)
    preview = tmp_path / "preview.mp4"
    preview.write_bytes(b"preview")
    monkeypatch.setattr(preflight, "download_low_res_preview", lambda *args, **kwargs: preview)
    monkeypatch.setattr(preflight, "video_dimensions", lambda path: (502, 720))
    monkeypatch.setattr(preflight, "_ffprobe_duration", lambda path: 12.0)

    called = {"vision": False}

    def should_not_run(*args, **kwargs):
        called["vision"] = True
        raise AssertionError("vision must not run for deterministic format reject")

    monkeypatch.setattr(preflight, "review_clean_youtube_footage", should_not_run)

    with pytest.raises(ValueError, match="failed low-resolution format preflight before Luna/full download"):
        preflight.clean_preflight_candidate(
            settings,
            slot=2,
            video_id="wide1",
            url="https://www.youtube.com/watch?v=wide1",
        )

    assert called["vision"] is False
    reject = json.loads(
        (settings.runtime_dir / "slots" / "02" / "youtube_preflight_rejects" / "wide1.json").read_text(
            encoding="utf-8"
        )
    )
    assert reject["durable_reject"] is True
    assert reject["details"]["width"] == 502
    assert reject["details"]["height"] == 720
    assert preflight.known_preflight_rejected_video_ids(settings.runtime_dir) == {"wide1"}


def test_clean_preflight_rejects_before_full_download(monkeypatch, tmp_path):
    settings = DummySettings(tmp_path)
    preview = tmp_path / "preview.mp4"
    preview.write_bytes(b"preview")
    monkeypatch.setattr(preflight, "download_low_res_preview", lambda *args, **kwargs: preview)
    monkeypatch.setattr(
        preflight,
        "_validate_preview_format",
        lambda *args, **kwargs: {
            "preview_width": 360,
            "preview_height": 640,
            "preview_aspect_ratio": 0.5625,
            "preview_duration_seconds": 10.0,
        },
    )
    monkeypatch.setattr(
        preflight,
        "review_clean_youtube_footage",
        lambda *args, **kwargs: {
            "clean_footage_approved": False,
            "decision": {
                "confidence": 0.99,
                "reason": "livestream chat UI and large caption",
                "creator_branding": True,
                "social_ui": True,
                "large_added_caption": True,
                "compilation_or_repost_style": True,
            },
        },
    )
    with pytest.raises(ValueError, match="failed low-resolution temporal clean preflight"):
        preflight.clean_preflight_candidate(
            settings,
            slot=2,
            video_id="bad1",
            url="https://www.youtube.com/watch?v=bad1",
        )


def test_clean_preflight_pass_returns_preview_and_metadata(monkeypatch, tmp_path):
    settings = DummySettings(tmp_path)
    preview = tmp_path / "preview.mp4"
    preview.write_bytes(b"preview")
    monkeypatch.setattr(preflight, "download_low_res_preview", lambda *args, **kwargs: preview)
    monkeypatch.setattr(
        preflight,
        "_validate_preview_format",
        lambda *args, **kwargs: {
            "preview_width": 360,
            "preview_height": 640,
            "preview_aspect_ratio": 0.5625,
            "preview_duration_seconds": 10.0,
        },
    )
    monkeypatch.setattr(
        preflight,
        "review_clean_youtube_footage",
        lambda *args, **kwargs: {
            "clean_footage_approved": True,
            "decision": {
                "confidence": 0.93,
                "reason": "clean raw cat footage",
                "creator_branding": False,
                "social_ui": False,
                "large_added_caption": False,
                "compilation_or_repost_style": False,
            },
        },
    )
    path, _, metadata = preflight.clean_preflight_candidate(
        settings,
        slot=2,
        video_id="good1",
        url="https://www.youtube.com/watch?v=good1",
    )
    assert path == preview
    assert metadata["clean_footage_approved"] is True
    assert metadata["clean_footage_confidence"] == pytest.approx(0.93)
    assert metadata["preview_aspect_ratio"] == pytest.approx(0.5625)
