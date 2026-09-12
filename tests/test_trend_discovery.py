from datetime import datetime, timedelta, timezone

from vv_knopka.trend_discovery import (
    _candidate_from_ytdlp_entry,
    _flat_search_target,
    _parse_youtube_duration,
    _views_per_day,
    _ytdlp_search_queries,
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


def test_no_key_candidate_keeps_unverified_rights_closed():
    now = datetime(2026, 8, 29, 20, 0, tzinfo=timezone.utc)
    candidate = _candidate_from_ytdlp_entry(
        {
            "id": "cat123",
            "title": "Cat discovers a box",
            "channel": "Cat Person",
            "timestamp": (now - timedelta(days=2)).timestamp(),
            "duration": 24,
            "view_count": 400_000,
        },
        now=now,
        cutoff=now - timedelta(days=30),
    )
    assert candidate is not None
    assert candidate["discovery_backend"] == "yt_dlp_no_key"
    assert candidate["rights_status"] == "license_unverified"
    assert candidate["attribution_required"] is False
    assert candidate["import_status"] == "trend_reference_only_until_rights_verified"


def test_no_key_candidate_recognizes_explicit_creative_commons_metadata():
    now = datetime(2026, 8, 29, 20, 0, tzinfo=timezone.utc)
    candidate = _candidate_from_ytdlp_entry(
        {
            "id": "cccat",
            "title": "CC cat",
            "uploader": "Creator",
            "upload_date": "20260828",
            "duration": 31,
            "view_count": 50_000,
            "license": "Creative Commons Attribution license (reuse allowed)",
        },
        now=now,
        cutoff=now - timedelta(days=30),
    )
    assert candidate is not None
    assert candidate["rights_status"] == "creative_commons_attribution_required"
    assert candidate["attribution_required"] is True


def test_no_key_default_search_uses_multiple_current_year_queries():
    now = datetime(2026, 8, 30, tzinfo=timezone.utc)
    queries = _ytdlp_search_queries("cat kitten shorts", now=now)
    assert len(queries) >= 4
    assert "cat shorts 2026" in queries
    assert "funny cat shorts 2026" in queries
    assert all("ytsearchdate" not in query for query in queries)


def test_flat_search_target_can_be_hydrated_from_video_id():
    identity, url = _flat_search_target({"id": "abc123", "url": "abc123"})
    assert identity == "abc123"
    assert url == "https://www.youtube.com/watch?v=abc123"
