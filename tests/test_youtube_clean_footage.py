import json
from pathlib import Path

import pytest

import vv_knopka.youtube_cat_source_v4 as youtube_v4
from vv_knopka.animal_audio_sources_v2 import sanitize_unapproved_youtube_sources
from vv_knopka.youtube_clean_footage import decision_passes_clean_gate


class DummySettings:
    def __init__(self, root: Path):
        self.root = root
        self.runtime_dir = root / "runtime"
        self.raw = {"materials": {}}
        self.budget_usd = 10.0


def clean_decision(**overrides):
    base = {
        "approved": True,
        "confidence": 0.95,
        "cat_visible": True,
        "creator_branding": False,
        "social_ui": False,
        "large_added_caption": False,
        "compilation_or_repost_style": False,
        "reason": "raw cat footage",
    }
    base.update(overrides)
    return base


def clean_review(*, approved=True, **decision_overrides):
    decision = clean_decision(**decision_overrides)
    if not approved:
        decision["approved"] = False
    return {
        "version": 1,
        "review_file": "review.json",
        "model": "gpt-5.6-luna",
        "source_sha256": "abc",
        "clean_footage_approved": decision_passes_clean_gate(decision),
        "decision": decision,
    }


def test_clean_gate_accepts_raw_cat_clip():
    assert decision_passes_clean_gate(clean_decision()) is True


def test_clean_gate_rejects_creator_branding_even_if_model_says_approved():
    assert decision_passes_clean_gate(clean_decision(creator_branding=True)) is False


def test_clean_gate_rejects_large_added_caption():
    assert decision_passes_clean_gate(clean_decision(large_added_caption=True)) is False


def test_clean_gate_rejects_low_confidence():
    assert decision_passes_clean_gate(clean_decision(confidence=0.5), minimum_confidence=0.78) is False


def test_render_sanitizer_drops_legacy_youtube_and_keeps_clean_reviewed(tmp_path):
    source_manifest = tmp_path / "sources.json"
    source_manifest.write_text(
        json.dumps(
            {
                "clips": [
                    {"provider": "pexels", "provider_id": 1, "file": "stock.mp4"},
                    {"provider": "youtube", "provider_id": "old", "file": "old.mp4"},
                    {
                        "provider": "youtube",
                        "provider_id": "clean",
                        "file": "clean.mp4",
                        "clean_footage_approved": True,
                    },
                ]
            }
        ),
        encoding="utf-8",
    )

    removed = sanitize_unapproved_youtube_sources(source_manifest)
    raw = json.loads(source_manifest.read_text(encoding="utf-8"))

    assert [item["provider_id"] for item in raw["clips"]] == [1, "clean"]
    assert [item["provider_id"] for item in removed] == ["old"]
    assert raw["require_clean_youtube_footage"] is True


def test_import_clean_gate_rolls_back_rejected_youtube_clip(tmp_path, monkeypatch):
    settings = DummySettings(tmp_path)
    source_manifest = tmp_path / "runtime" / "slots" / "02" / "sources.json"
    source_manifest.parent.mkdir(parents=True, exist_ok=True)
    video = tmp_path / "cat.mp4"
    video.write_bytes(b"video")
    clip = {
        "provider": "youtube",
        "provider_id": "bad",
        "file": str(video),
        "source_url": "https://www.youtube.com/watch?v=bad",
        "source_title": "packaged cat",
        "creator": "SomeChannel",
    }
    source_manifest.write_text(json.dumps({"clips": [clip]}), encoding="utf-8")

    monkeypatch.setattr(
        youtube_v4,
        "review_clean_youtube_footage",
        lambda *args, **kwargs: clean_review(creator_branding=True, reason="visible @handle"),
    )
    monkeypatch.setattr(youtube_v4, "write_attribution_report", lambda *args, **kwargs: tmp_path / "attr.json")

    with pytest.raises(ValueError, match="failed the clean-footage"):
        youtube_v4._clean_gate_imported_clip(
            settings,
            slot=2,
            source_manifest=source_manifest,
            clip=clip,
        )

    raw = json.loads(source_manifest.read_text(encoding="utf-8"))
    assert raw["clips"] == []


def test_import_clean_gate_persists_pass_metadata(tmp_path, monkeypatch):
    settings = DummySettings(tmp_path)
    source_manifest = tmp_path / "runtime" / "slots" / "02" / "sources.json"
    source_manifest.parent.mkdir(parents=True, exist_ok=True)
    video = tmp_path / "cat.mp4"
    video.write_bytes(b"video")
    clip = {
        "provider": "youtube",
        "provider_id": "good",
        "file": str(video),
        "source_url": "https://www.youtube.com/watch?v=good",
        "source_title": "raw cat",
        "creator": "Owner",
    }
    source_manifest.write_text(json.dumps({"clips": [clip]}), encoding="utf-8")

    monkeypatch.setattr(youtube_v4, "review_clean_youtube_footage", lambda *args, **kwargs: clean_review())
    monkeypatch.setattr(youtube_v4, "write_attribution_report", lambda *args, **kwargs: tmp_path / "attr.json")

    updated, _ = youtube_v4._clean_gate_imported_clip(
        settings,
        slot=2,
        source_manifest=source_manifest,
        clip=clip,
    )
    raw = json.loads(source_manifest.read_text(encoding="utf-8"))

    assert updated["clean_footage_approved"] is True
    assert raw["clips"][0]["clean_footage_approved"] is True
    assert raw["require_clean_youtube_footage"] is True
