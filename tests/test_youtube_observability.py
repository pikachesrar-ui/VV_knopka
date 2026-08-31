import json
from pathlib import Path

from vv_knopka import youtube_observability as yo
from vv_knopka.settings import Settings


class _Request:
    def __init__(self, response):
        self.response = response

    def execute(self):
        return self.response


class _Videos:
    def __init__(self, responses):
        self.responses = responses
        self.calls = []

    def list(self, **kwargs):
        self.calls.append(kwargs)
        return _Request(self.responses[kwargs["part"]])


class _Service:
    def __init__(self, responses):
        self._videos = _Videos(responses)

    def videos(self):
        return self._videos


def _settings(tmp_path: Path) -> Settings:
    return Settings(
        raw={
            "pilot": {"runtime_dir": "runtime", "openai_budget_usd": 10.0, "auto_publish": False},
            "youtube": {"enabled": True, "auto_publish": True},
        },
        root=tmp_path,
    )


def _receipt(settings: Settings, slot: int, video_id: str) -> Path:
    ready = settings.runtime_dir / "ready_for_review"
    ready.mkdir(parents=True, exist_ok=True)
    path = ready / f"slot-{slot:02d}-en-ai.upload.youtube.json"
    path.write_text(
        json.dumps(
            {
                "slot": slot,
                "pipeline": "ai_short",
                "language": "en",
                "video_id": video_id,
                "youtube_url": f"https://www.youtube.com/watch?v={video_id}",
                "actual_privacy": "public",
                "title": f"Slot {slot}",
                "uploaded_at": "2026-08-31T00:00:00+00:00",
            }
        ),
        encoding="utf-8",
    )
    return path


def test_verify_receipts_marks_processed_public_video(monkeypatch, tmp_path):
    settings = _settings(tmp_path)
    receipt = _receipt(settings, 1, "abc")
    service = _Service(
        {
            "status,processingDetails": {
                "items": [
                    {
                        "id": "abc",
                        "status": {"uploadStatus": "processed", "privacyStatus": "public"},
                        "processingDetails": {"processingStatus": "succeeded"},
                    }
                ]
            }
        }
    )
    monkeypatch.setattr(
        yo,
        "_require_bound_service",
        lambda _settings: (service, {"channel_id": "channel", "channel_title": "Knopka322"}),
    )

    results = yo.verify_receipts(settings)

    assert results[0]["publication_state"] == "VERIFIED_PUBLIC"
    saved = json.loads(receipt.read_text(encoding="utf-8"))
    assert saved["publication_state"] == "VERIFIED_PUBLIC"
    assert saved["verification"]["privacy_status"] == "public"


def test_verify_receipts_marks_rejected_video_failed(monkeypatch, tmp_path):
    settings = _settings(tmp_path)
    _receipt(settings, 2, "rejected")
    service = _Service(
        {
            "status,processingDetails": {
                "items": [
                    {
                        "id": "rejected",
                        "status": {
                            "uploadStatus": "rejected",
                            "privacyStatus": "private",
                            "rejectionReason": "duplicate",
                        },
                        "processingDetails": {"processingStatus": "failed"},
                    }
                ]
            }
        }
    )
    monkeypatch.setattr(
        yo,
        "_require_bound_service",
        lambda _settings: (service, {"channel_id": "channel", "channel_title": "Knopka322"}),
    )

    results = yo.verify_receipts(settings)
    assert results[0]["publication_state"] == "FAILED"
    assert results[0]["rejection_reason"] == "duplicate"


def test_collect_statistics_writes_channel_snapshot(monkeypatch, tmp_path):
    settings = _settings(tmp_path)
    _receipt(settings, 3, "stats")
    service = _Service(
        {
            "statistics,status,snippet": {
                "items": [
                    {
                        "id": "stats",
                        "statistics": {"viewCount": "5728", "likeCount": "491", "commentCount": "64"},
                        "status": {"privacyStatus": "public"},
                        "snippet": {"title": "Funny cats", "publishedAt": "2026-08-31T10:00:00Z"},
                    }
                ]
            }
        }
    )
    monkeypatch.setattr(
        yo,
        "_require_bound_service",
        lambda _settings: (service, {"channel_id": "channel", "channel_title": "Knopka322"}),
    )

    snapshot = yo.collect_statistics(settings)

    assert snapshot["videos"][0]["views"] == 5728
    assert snapshot["videos"][0]["likes"] == 491
    assert snapshot["videos"][0]["comments"] == 64
    saved = settings.runtime_dir / "youtube" / "statistics.json"
    assert saved.exists()
