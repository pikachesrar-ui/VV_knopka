import json

from vv_knopka.manifest import Slot
from vv_knopka.publication_metadata import build_upload_metadata
from vv_knopka.settings import Settings


def _settings(tmp_path):
    return Settings(
        raw={
            "pilot": {"runtime_dir": "runtime", "auto_publish": False, "openai_budget_usd": 10.0},
            "content": {"animal_slots": [2, 4, 6, 8, 10, 12, 14]},
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
