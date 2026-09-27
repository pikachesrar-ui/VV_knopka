import json
from pathlib import Path

from vv_knopka.settings import Settings
from vv_knopka.youtube_uploader import _normalize_tags, ready_metadata, upload_one, upload_ready


def _settings(tmp_path: Path) -> Settings:
    return Settings(
        raw={
            "pilot": {"runtime_dir": "runtime", "openai_budget_usd": 10.0, "auto_publish": False},
            "youtube": {"enabled": True, "auto_publish": True, "privacy_status": "public", "category_id": "15"},
        },
        root=tmp_path,
    )


def _ready(settings: Settings, slot: int, kind: str = "ai") -> Path:
    ready = settings.runtime_dir / "ready_for_review"
    ready.mkdir(parents=True, exist_ok=True)
    video = ready / f"slot-{slot:02d}-en-{kind}.mp4"
    video.write_bytes(b"video")
    metadata = ready / f"slot-{slot:02d}-en-{kind}.upload.json"
    metadata.write_text(
        json.dumps(
            {
                "slot": slot,
                "pipeline": "ai_short" if kind == "ai" else "animal_compilation",
                "language": "en",
                "video_file": str(video),
                "youtube_title": f"Slot {slot} #shorts",
                "youtube_description": "description",
                "youtube_tags": ["#cats", "funny cats", "#cats"],
                "contains_synthetic_media": True,
            }
        ),
        encoding="utf-8",
    )
    return metadata


def test_ready_metadata_is_sorted_by_numeric_slot(tmp_path):
    settings = _settings(tmp_path)
    _ready(settings, 16, "animals")
    _ready(settings, 2, "animals")
    _ready(settings, 11, "ai")
    assert [int(path.name.split("-")[1]) for path in ready_metadata(settings)] == [2, 11, 16]


def test_upload_ready_dry_run_can_pick_newest_without_google_auth(tmp_path):
    settings = _settings(tmp_path)
    _ready(settings, 16, "animals")
    _ready(settings, 17, "ai")
    results = upload_ready(settings, limit=1, newest=True, dry_run=True)
    assert len(results) == 1
    assert results[0]["dry_run"] is True
    assert results[0]["slot"] == 17
    assert results[0]["requested_privacy"] == "public"
    assert results[0]["tags"] == ["cats", "funny cats"]
    assert results[0]["contains_synthetic_media"] is True


def test_existing_youtube_receipt_makes_upload_idempotent(tmp_path):
    settings = _settings(tmp_path)
    metadata = _ready(settings, 16, "animals")
    receipt = metadata.with_suffix(".youtube.json")
    receipt.write_text(json.dumps({"slot": 16, "video_id": "abc123"}), encoding="utf-8")

    result = upload_one(settings, metadata, dry_run=False)
    assert result["skipped"] is True
    assert result["video_id"] == "abc123"

    pending = upload_ready(settings, dry_run=True)
    assert pending == []


def test_normalize_tags_deduplicates_and_removes_hashtag_prefix():
    assert _normalize_tags(["#Cats", "cats", " funny cats ", "", None]) == ["Cats", "funny cats"]
