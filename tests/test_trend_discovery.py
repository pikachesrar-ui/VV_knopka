from datetime import datetime, timezone

from vv_knopka.trend_discovery import (
    _parse_youtube_duration,
    _views_per_day,
    youtube_search_params,
)


def test_youtube_duration_parser_handles_short_videos():
    assert _parse_youtube_duration("PT42S") == 42
    assert _parse_youtube_duration("PT2M5S") == 125
    assert _parse_youtube_duration("PT1H2M3S") == 3723


def test_youtube_cat_search_is_recent_short_and_creative_commons():
    now = datetime(2026, 8, 29, 20, 0, tzinfo=timezone.utc)
    params = youtube_search_params(
        api_key="test-key",
        query="funny cat kitten",
        days=30,
        limit=80,
        now=now,
    )
    assert params["type"] == "video"
    assert params["videoLicense"] == "creativeCommon"
    assert params["videoDuration"] == "short"
    assert params["order"] == "viewCount"
    assert params["maxResults"] == 50
    assert params["publishedAfter"] == "2026-07-30T20:00:00Z"


def test_views_per_day_favors_fast_recent_growth():
    now = datetime(2026, 8, 29, 20, 0, tzinfo=timezone.utc)
    fast = _views_per_day(500_000, "2026-08-27T20:00:00Z", now=now)
    older = _views_per_day(700_000, "2026-07-30T20:00:00Z", now=now)
    assert fast > older
