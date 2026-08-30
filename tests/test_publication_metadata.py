import json

from vv_knopka.manifest import Slot
from vv_knopka.publication_metadata import build_upload_metadata
from vv_knopka.settings import Settings


def _settings(tmp_path):
    return Settings(
        raw={
            "pilot": {
                "total_shorts": 15,
                "runtime_dir": "runtime",
                "auto_publish": False,
                "openai_budget_usd": 10.0,
            },
            "content": {
                "default_language": "en",
                "animal_slots": [2, 4, 6, 8, 10, 12, 14],
            },
            "long_run": {
                "enabled": True,
                "pipeline_cycle": ["animal_compilation", "ai_short"],
                "ai_language": "en",
            },
            "animal": {"language_cycle": ["en", "en", "en", "en", "ru"]},
        },
        root=tmp_path,
    )


def test_cat_upload_title_uses_episode_number_and_cc_attribution(tmp_path):
    settings = _settings(tmp_path)
    slot_dir = tmp_path / "runtime" / "slots" / "04"
    slot_dir.mkdir(parents=True)
    (slot_dir / "sources.json").write_text(
        json.dumps(
            {
                "clips": [
                    {
                        "attribution_required": True,
                        "attribution_text": '"Cat" by Creator — https://example.test — CC BY',
                    }
                ]
            }
        ),
        encoding="utf-8",
    )
    output = tmp_path / "runtime" / "ready_for_review" / "slot-04-en-animals.mp4"
    metadata = build_upload_metadata(
        settings,
        slot=Slot(4, "animal_compilation", "en"),
        output=output,
        slot_dir=slot_dir,
    )
    assert metadata["youtube_title"] == "Cats That Made My Day 😹 #002 #shorts"
    assert metadata["youtube_description"].startswith("A short collection of cute and funny cats.")
    assert "Creator" in metadata["youtube_description"]
    assert metadata["review_required"] is True
    assert metadata["auto_publish"] is False
    assert metadata["publication_allowed_by_conveyor"] is False


def test_ai_upload_title_comes_from_specific_plan(tmp_path):
    settings = _settings(tmp_path)
    slot_dir = tmp_path / "runtime" / "slots" / "03"
    slot_dir.mkdir(parents=True)
    (slot_dir / "plan.json").write_text(
        json.dumps({"title": "Why Owls Fly So Quietly", "hook": "Their feathers hide a clever trick."}),
        encoding="utf-8",
    )
    output = tmp_path / "runtime" / "ready_for_review" / "slot-03-en-ai.mp4"
    metadata = build_upload_metadata(
        settings,
        slot=Slot(3, "ai_short", "en"),
        output=output,
        slot_dir=slot_dir,
    )
    assert metadata["youtube_title"] == "Why Owls Fly So Quietly #shorts"
    assert metadata["youtube_description"] == "Their feathers hide a clever trick."


def test_longrun_cat_metadata_continues_numbering_and_varies_description(tmp_path):
    settings = _settings(tmp_path)
    slot16_dir = tmp_path / "runtime" / "slots" / "16"
    slot18_dir = tmp_path / "runtime" / "slots" / "18"
    slot16_dir.mkdir(parents=True)
    slot18_dir.mkdir(parents=True)

    first = build_upload_metadata(
        settings,
        slot=Slot(16, "animal_compilation", "en"),
        output=tmp_path / "runtime" / "ready_for_review" / "slot-16-en-animals.mp4",
        slot_dir=slot16_dir,
    )
    second = build_upload_metadata(
        settings,
        slot=Slot(18, "animal_compilation", "en"),
        output=tmp_path / "runtime" / "ready_for_review" / "slot-18-en-animals.mp4",
        slot_dir=slot18_dir,
    )

    assert first["youtube_title"] == "Cats That Made My Day 😹 #008 #shorts"
    assert second["youtube_title"] == "Cats That Made My Day 😹 #009 #shorts"
    assert first["youtube_description"] != second["youtube_description"]
