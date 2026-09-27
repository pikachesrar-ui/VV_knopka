import json
from datetime import datetime, timezone
from pathlib import Path

import vv_knopka.cat_source_candidates as candidates


class DummySettings:
    def __init__(self, root: Path):
        self.root = root
        self.runtime_dir = root / "runtime"
        self.raw = {"source_fallback": {"youtube_queue_enabled": True}}


class Request:
    def __init__(self, payload):
        self.payload = payload

    def execute(self):
        return self.payload


class SearchResource:
    def list(self, **kwargs):
        video_id = "cc1" if kwargs.get("videoLicense") == "creativeCommon" else "std1"
        return Request({"items": [{"id": {"videoId": video_id}}]})


class VideoResource:
    def list(self, **kwargs):
        items = []
        for video_id in kwargs["id"].split(","):
            items.append(
                {
                    "id": video_id,
                    "snippet": {
                        "title": f"title-{video_id}",
                        "channelTitle": "creator",
                        "publishedAt": "2026-09-01T00:00:00Z",
                    },
                    "statistics": {"viewCount": "100", "likeCount": "5"},
                    "status": {"license": "creativeCommon" if video_id == "cc1" else "youtube"},
                    "contentDetails": {"duration": "PT20S"},
                }
            )
        return Request({"items": items})


class Service:
    def search(self):
        return SearchResource()

    def videos(self):
        return VideoResource()


def test_discovery_keeps_cc_first_and_standard_manual_only(tmp_path):
    found, diagnostics = candidates.discover_youtube_candidates(
        DummySettings(tmp_path),
        days=3650,
        limit=5,
        service=Service(),
        now=datetime(2026, 9, 25, tzinfo=timezone.utc),
    )

    assert [item["video_id"] for item in found] == ["cc1", "std1"]
    assert found[0]["rights_status"] == "creative_commons_attribution_required"
    assert found[1]["rights_status"] == "permission_required_before_use"
    assert all(item["auto_download"] is False for item in found)
    assert all(item["publication_allowed"] is False for item in found)
    assert diagnostics["cc_search_ids"] == 1
    assert diagnostics["general_search_ids"] == 1


def test_queue_is_cached_per_slot(monkeypatch, tmp_path):
    settings = DummySettings(tmp_path)
    calls = {"count": 0}

    def fake_discover(*args, **kwargs):
        calls["count"] += 1
        return ([{"video_id": "one", "candidate_rank": 1}], {"backend": "fake"})

    monkeypatch.setattr(candidates, "discover_youtube_candidates", fake_discover)
    first = candidates.ensure_candidate_queue(settings, slot=42, reason="stock exhausted")
    second = candidates.ensure_candidate_queue(settings, slot=42, reason="retry")

    assert first == second
    assert calls["count"] == 1
    raw = json.loads(first.read_text(encoding="utf-8"))
    assert raw["status"] == "ready_for_manual_review"
    assert raw["policy"]["auto_publish"] is False


def test_queue_failure_is_recorded_without_approving_any_media(monkeypatch, tmp_path):
    settings = DummySettings(tmp_path)
    monkeypatch.setattr(
        candidates,
        "discover_youtube_candidates",
        lambda *args, **kwargs: (_ for _ in ()).throw(RuntimeError("quota unavailable")),
    )
    path = candidates.ensure_candidate_queue(settings, slot=44, reason="stock exhausted")
    raw = json.loads(path.read_text(encoding="utf-8"))
    assert raw["status"] == "unavailable"
    assert raw["candidates"] == []
    assert "quota unavailable" in raw["error"]

