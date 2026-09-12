import json
from pathlib import Path

from vv_knopka.settings import Settings
from vv_knopka.youtube_pending_metadata import pending_metadata_targets, upgrade_pending_metadata


def _settings(tmp_path: Path) -> Settings:
    return Settings(
        raw={
            "pilot": {"runtime_dir": "runtime", "openai_budget_usd": 10.0, "auto_publish": False},
            "youtube": {"enabled": True, "auto_publish": True, "privacy_status": "public", "category_id": "15"},
        },
        root=tmp_path,
    )


def _pending(settings: Settings, *, slot: int, pipeline: str, language: str) -> tuple[Path, Path]:
    ready = settings.runtime_dir / "ready_for_review"
    ready.mkdir(parents=True, exist_ok=True)
    kind = "animals" if pipeline == "animal_compilation" else "ai"
    video = ready / f"slot-{slot:02d}-{language}-{kind}.mp4"
    video.write_bytes(b"immutable-video-bytes")
    metadata = ready / f"slot-{slot:02d}-{language}-{kind}.upload.json"
    metadata.write_text(
        json.dumps(
            {
                "slot": slot,
                "pipeline": pipeline,
                "language": language,
                "video_file": str(video),
                "youtube_title": f"Slot {slot} #shorts",
                "youtube_description": "legacy description",
                "review_required": True,
                "auto_publish": False,
                "publication_allowed_by_conveyor": False,
            }
        ),
        encoding="utf-8",
    )
    return video, metadata


def test_upgrade_pending_metadata_updates_only_sidecar_and_is_idempotent(tmp_path):
    settings = _settings(tmp_path)
    video, metadata = _pending(settings, slot=12, pipeline="animal_compilation", language="en")
    before_video = video.read_bytes()

    preview = upgrade_pending_metadata(settings, slots={12}, apply=False)
    assert len(preview) == 1
    assert preview[0]["changed"] is True
    assert preview[0]["applied"] is False
    assert json.loads(metadata.read_text(encoding="utf-8")).get("youtube_tags") is None

    applied = upgrade_pending_metadata(settings, slots={12}, apply=True)
    assert applied[0]["applied"] is True
    updated = json.loads(metadata.read_text(encoding="utf-8"))
    assert updated["youtube_tags"]
    assert "cats" in [tag.casefold() for tag in updated["youtube_tags"]]
    assert "#cats" in updated["youtube_description"].casefold()
    assert updated["metadata_version"] == 2
    assert updated["review_required"] is True
    assert updated["auto_publish"] is False
    assert updated["publication_allowed_by_conveyor"] is False
    assert video.read_bytes() == before_video

    backup = settings.runtime_dir / "youtube" / "pending-metadata-backups" / f"{metadata.name}.before-v2.json"
    assert backup.exists()
    original = json.loads(backup.read_text(encoding="utf-8"))
    assert original.get("youtube_tags") is None

    again = upgrade_pending_metadata(settings, slots={12}, apply=False)
    assert again[0]["changed"] is False


def test_upgrade_pending_metadata_skips_slots_that_already_have_receipts(tmp_path):
    settings = _settings(tmp_path)
    _, metadata = _pending(settings, slot=13, pipeline="ai_short", language="en")
    metadata.with_suffix(".youtube.json").write_text(
        json.dumps({"slot": 13, "video_id": "already-published"}),
        encoding="utf-8",
    )

    assert pending_metadata_targets(settings, {13}) == []
    assert upgrade_pending_metadata(settings, slots={13}, apply=True) == []
