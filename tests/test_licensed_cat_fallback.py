import json
from pathlib import Path

import pytest

import vv_knopka.licensed_cat_fallback as fallback


class DummySettings:
    def __init__(self, root: Path):
        self.root = root
        self.runtime_dir = root / "runtime"
        self.raw = {
            "pilot": {"runtime_dir": "runtime", "openai_budget_usd": 10.0},
            "animal": {
                "clip_seconds": 5.0,
                "material_count": 6,
                "min_unique_materials": 5,
                "min_source_mean_volume_db": -55.0,
                "source_aspect_tolerance": 0.08,
            },
            "materials": {"vision_batch_size": 8, "vision_min_confidence": 0.72},
            "source_fallback": {
                "local_library_enabled": True,
                "local_library_manifest": "runtime/licensed_sources/cats/manifest.json",
                "wikimedia_enabled": True,
            },
            "long_run": {"cat_source_cooldown_episodes": 5},
        }


def test_license_allowlist_rejects_share_alike_and_noncommercial():
    assert fallback._license_policy("CC0 1.0")["attribution_required"] is False
    assert fallback._license_policy("CC BY 4.0")["attribution_required"] is True
    assert fallback._license_policy("Public domain")["canonical"] == "Public Domain"
    assert fallback._license_policy("CC BY-SA 4.0") is None
    assert fallback._license_policy("CC BY-NC 4.0") is None
    assert fallback._license_policy("Creative Commons Attribution-NonCommercial 4.0") is None


def test_local_library_requires_explicit_approval_and_writes_attribution(monkeypatch, tmp_path):
    settings = DummySettings(tmp_path)
    library = settings.runtime_dir / "licensed_sources" / "cats"
    library.mkdir(parents=True)
    media = library / "cat.mp4"
    media.write_bytes(b"video")
    (library / "manifest.json").write_text(
        json.dumps(
            {
                "clips": [
                    {
                        "id": "approved-cat",
                        "file": "cat.mp4",
                        "title": "Cat reaching with a paw",
                        "creator": "Creator",
                        "source_url": "https://example.test/cat",
                        "license": "CC BY 4.0",
                        "license_url": "https://creativecommons.org/licenses/by/4.0/",
                        "commercial_use_allowed": True,
                        "human_approved": True,
                    }
                ]
            }
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(fallback._base, "video_dimensions", lambda path: (1080, 1920))
    monkeypatch.setattr(fallback._base, "has_audible_audio", lambda path, minimum_mean_db: (True, -18.0))
    monkeypatch.setattr(fallback, "_ffprobe_duration", lambda path: 12.0)
    monkeypatch.setattr(fallback, "_sha256", lambda path: "a" * 64)
    monkeypatch.setattr(fallback, "blocked_cat_source_identities", lambda *args, **kwargs: set())

    source_manifest = settings.runtime_dir / "slots" / "40" / "sources.json"
    audit = fallback.seed_local_library(settings, slot=40, source_manifest=source_manifest)
    raw = json.loads(source_manifest.read_text(encoding="utf-8"))

    assert audit["accepted"] == 1
    assert raw["clips"][0]["provider"] == "local_licensed"
    assert raw["clips"][0]["provider_id"] == "a" * 64
    assert raw["clips"][0]["attribution_required"] is True
    assert "Changes:" in raw["clips"][0]["attribution_text"]


class FakeResponse:
    def json(self):
        return {
            "query": {
                "pages": [
                    {
                        "pageid": 123,
                        "title": "File:Vertical cat.webm",
                        "imageinfo": [
                            {
                                "mime": "video/webm",
                                "mediatype": "VIDEO",
                                "width": 1080,
                                "height": 1920,
                                "size": 1024,
                                "url": "https://upload.wikimedia.org/cat.webm",
                                "thumburl": "https://upload.wikimedia.org/cat.jpg",
                                "descriptionurl": "https://commons.wikimedia.org/wiki/File:Vertical_cat.webm",
                                "extmetadata": {
                                    "LicenseShortName": {"value": "CC BY 4.0"},
                                    "LicenseUrl": {"value": "https://creativecommons.org/licenses/by/4.0/"},
                                    "Artist": {"value": "<b>Alice</b>"},
                                },
                            }
                        ],
                    }
                ]
            }
        }


def test_wikimedia_discovery_filters_and_preserves_license(monkeypatch, tmp_path):
    settings = DummySettings(tmp_path)
    monkeypatch.setattr(fallback, "get_stock", lambda *args, **kwargs: FakeResponse())
    found, stats = fallback.discover_wikimedia_candidates(
        settings,
        protected=set(),
        client=object(),
    )
    assert found[0]["provider"] == "wikimedia"
    assert found[0]["license"] == "CC BY 4.0"
    assert found[0]["creator"] == "Alice"
    assert found[0]["attribution_required"] is True
    assert stats["eligible_candidates"] >= 1


def test_exhausted_safe_sources_create_queue_but_still_fail_closed(monkeypatch, tmp_path):
    settings = DummySettings(tmp_path)
    slot_dir = settings.runtime_dir / "slots" / "50"
    source_manifest = slot_dir / "sources.json"
    queue = slot_dir / "source-candidate-queue.json"

    monkeypatch.setattr(fallback, "seed_local_library", lambda *args, **kwargs: {"accepted": 0})
    monkeypatch.setattr(
        fallback._v6,
        "ensure_audio_animal_sources",
        lambda *args, **kwargs: (_ for _ in ()).throw(RuntimeError("Vertical audible-source gate found only 2/5")),
    )
    monkeypatch.setattr(
        fallback,
        "try_wikimedia_fallback",
        lambda *args, **kwargs: (None, {"status": "insufficient_after_validation"}),
    )

    def fake_queue(*args, **kwargs):
        queue.parent.mkdir(parents=True, exist_ok=True)
        queue.write_text(json.dumps({"status": "ready_for_manual_review", "candidates": [{"video_id": "x"}]}))
        return queue

    monkeypatch.setattr(fallback, "ensure_candidate_queue", fake_queue)
    with pytest.raises(RuntimeError, match="Manual-review YouTube candidate queue"):
        fallback.ensure_audio_animal_sources(
            settings,
            {"search_terms": ["cat"]},
            slot=50,
            slot_dir=slot_dir,
            source_manifest=source_manifest,
            ledger=object(),
        )
    audit = json.loads((slot_dir / "cat_source_fallback.json").read_text(encoding="utf-8"))
    assert audit["youtube_queue"]["candidate_count"] == 1
    assert audit["youtube_queue"]["auto_publish"] is False
