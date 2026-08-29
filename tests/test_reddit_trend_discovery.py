from datetime import datetime, timezone

from vv_knopka.reddit_trend_discovery import (
    _feed_urls,
    _parse_atom_feed,
)


ATOM = """<?xml version="1.0" encoding="UTF-8"?>
<feed xmlns="http://www.w3.org/2005/Atom">
  <entry>
    <title>Cat attacks cardboard box</title>
    <link href="https://www.reddit.com/r/cats/comments/abc123/cat_attacks_cardboard_box/" />
    <updated>2026-08-29T18:00:00+00:00</updated>
    <author><name>u/catperson</name></author>
    <content type="html">&lt;a href=&quot;https://v.redd.it/example123&quot;&gt;video&lt;/a&gt;</content>
  </entry>
</feed>
"""


def test_reddit_top_week_url_is_public_rss():
    urls = _feed_urls("cats", "top_week")
    assert urls[0] == "https://www.reddit.com/r/cats/top/.rss?sort=top&t=week"
    assert urls[1].startswith("https://old.reddit.com/")


def test_reddit_atom_candidate_is_reference_only_and_detects_video():
    now = datetime(2026, 8, 30, 0, 0, tzinfo=timezone.utc)
    candidates = _parse_atom_feed(
        ATOM,
        subreddit="cats",
        feed_kind="top_week",
        now=now,
        max_age_days=30,
    )
    assert len(candidates) == 1
    candidate = candidates[0]
    assert candidate["provider"] == "reddit"
    assert candidate["media_hint"] == "video"
    assert candidate["rights_status"] == "author_permission_required"
    assert candidate["import_status"] == "trend_reference_only_until_author_permission"
    assert candidate["auto_download"] is False
    assert candidate["media_links"] == ["https://v.redd.it/example123"]


def test_reddit_atom_filters_old_entries():
    now = datetime(2026, 10, 1, 0, 0, tzinfo=timezone.utc)
    candidates = _parse_atom_feed(
        ATOM,
        subreddit="cats",
        feed_kind="top_week",
        now=now,
        max_age_days=30,
    )
    assert candidates == []
