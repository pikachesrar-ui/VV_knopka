from datetime import datetime, timezone

from vv_knopka.outlier_research import collect_outliers
from vv_knopka.settings import Settings


class _Call:
    def __init__(self, payload):
        self.payload = payload

    def execute(self):
        return self.payload


class _Search:
    def __init__(self, service):
        self.service = service

    def list(self, **kwargs):
        self.service.search_calls.append(kwargs)
        return _Call({"items": [{"id": {"videoId": "abc"}}]})


class _Videos:
    def __init__(self, service):
        self.service = service

    def list(self, **kwargs):
        self.service.video_calls.append(kwargs)
        return _Call({"items": [{
            "id": "abc",
            "snippet": {"title": "Why cats do this", "channelTitle": "Channel", "publishedAt": "2026-01-09T00:00:00Z"},
            "statistics": {"viewCount": "1000", "likeCount": "50"},
            "contentDetails": {"duration": "PT25S"},
            "status": {"license": "youtube"},
        }]})


class _Service:
    def __init__(self):
        self.search_calls = []
        self.video_calls = []

    def search(self):
        return _Search(self)

    def videos(self):
        return _Videos(self)


def test_outlier_research_is_metadata_only_and_quota_bounded(tmp_path) -> None:
    settings = Settings(root=tmp_path, raw={
        "pilot": {"runtime_dir": "runtime"},
        "research": {"categories": ["cats", "animals"], "max_queries_per_run": 1, "lookback_days": 30},
    })
    service = _Service()
    result = collect_outliers(
        settings,
        categories=["cats"],
        service=service,
        now=datetime(2026, 1, 10, tzinfo=timezone.utc),
    )

    assert result["queries_used"] == 1
    assert result["estimated_youtube_quota_units"] == 101
    assert len(service.search_calls) == len(service.video_calls) == 1
    row = result["candidates"][0]
    assert row["duration_seconds"] == 25
    assert row["auto_download"] is False
    assert row["publication_allowed"] is False
    assert row["analysis_scope"] == "metadata_only"


def test_outlier_research_cache_respects_due_window(tmp_path) -> None:
    settings = Settings(root=tmp_path, raw={"pilot": {"runtime_dir": "runtime"}, "research": {}})
    service = _Service()
    first = collect_outliers(settings, categories=["cats"], service=service)
    second = collect_outliers(settings, categories=["cats"], service=service, if_due_hours=168)
    assert first["status"] == "ok"
    assert second["status"] == "not_due"
    assert len(service.search_calls) == 1
