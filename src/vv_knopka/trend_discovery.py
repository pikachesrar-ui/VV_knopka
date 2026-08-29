from __future__ import annotations

import argparse
import json
import os
import re
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import httpx
from dotenv import load_dotenv

from .settings import load_settings


YOUTUBE_SEARCH_URL = "https://www.googleapis.com/youtube/v3/search"
YOUTUBE_VIDEOS_URL = "https://www.googleapis.com/youtube/v3/videos"


def _parse_youtube_duration(value: str) -> float:
    """Parse the common PT#H#M#S subset used by YouTube contentDetails.duration."""
    match = re.fullmatch(
        r"PT(?:(?P<hours>\d+)H)?(?:(?P<minutes>\d+)M)?(?:(?P<seconds>\d+(?:\.\d+)?)S)?",
        str(value or "").strip(),
    )
    if not match:
        return 0.0
    return (
        int(match.group("hours") or 0) * 3600
        + int(match.group("minutes") or 0) * 60
        + float(match.group("seconds") or 0)
    )


def _parse_utc(value: str) -> datetime:
    text = str(value or "").strip().replace("Z", "+00:00")
    parsed = datetime.fromisoformat(text)
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _views_per_day(view_count: int, published_at: str, *, now: datetime) -> float:
    published = _parse_utc(published_at)
    age_days = max((now - published).total_seconds() / 86400.0, 0.5)
    return float(view_count) / age_days


def youtube_search_params(
    *,
    api_key: str,
    query: str,
    days: int,
    limit: int,
    now: datetime,
) -> dict[str, Any]:
    published_after = now - timedelta(days=max(int(days), 1))
    return {
        "key": api_key,
        "part": "snippet",
        "type": "video",
        "q": query,
        "order": "viewCount",
        "publishedAfter": published_after.isoformat().replace("+00:00", "Z"),
        "maxResults": max(1, min(int(limit), 50)),
        "videoLicense": "creativeCommon",
        "videoDuration": "short",
        "videoEmbeddable": "true",
        "safeSearch": "strict",
    }


def discover_youtube_cc_cats(
    *,
    api_key: str,
    query: str = "funny cat kitten",
    days: int = 30,
    limit: int = 30,
    now: datetime | None = None,
) -> list[dict[str, Any]]:
    """Discover recent popular Creative Commons cat videos without downloading them.

    This is a trend-discovery layer only. Media import remains a separate human-reviewed
    step because YouTube reused-content rules and source rights are independent concerns.
    """
    current = (now or datetime.now(timezone.utc)).astimezone(timezone.utc)
    params = youtube_search_params(
        api_key=api_key,
        query=query,
        days=days,
        limit=limit,
        now=current,
    )
    with httpx.Client(timeout=45, follow_redirects=True) as client:
        search_response = client.get(YOUTUBE_SEARCH_URL, params=params)
        search_response.raise_for_status()
        search_data = search_response.json()

        ids = [
            str((item.get("id") or {}).get("videoId") or "").strip()
            for item in search_data.get("items", [])
        ]
        ids = [video_id for video_id in ids if video_id]
        if not ids:
            return []

        details_response = client.get(
            YOUTUBE_VIDEOS_URL,
            params={
                "key": api_key,
                "part": "snippet,statistics,status,contentDetails",
                "id": ",".join(ids),
            },
        )
        details_response.raise_for_status()
        details = details_response.json()

    candidates: list[dict[str, Any]] = []
    for item in details.get("items", []):
        status = item.get("status") or {}
        if str(status.get("license") or "") != "creativeCommon":
            continue
        snippet = item.get("snippet") or {}
        stats = item.get("statistics") or {}
        content_details = item.get("contentDetails") or {}
        video_id = str(item.get("id") or "").strip()
        published_at = str(snippet.get("publishedAt") or "").strip()
        if not video_id or not published_at:
            continue
        view_count = int(stats.get("viewCount") or 0)
        like_count = int(stats.get("likeCount") or 0)
        duration_seconds = _parse_youtube_duration(str(content_details.get("duration") or ""))
        velocity = _views_per_day(view_count, published_at, now=current)
        candidates.append(
            {
                "provider": "youtube",
                "video_id": video_id,
                "url": f"https://www.youtube.com/watch?v={video_id}",
                "title": str(snippet.get("title") or ""),
                "channel_title": str(snippet.get("channelTitle") or ""),
                "published_at": published_at,
                "view_count": view_count,
                "like_count": like_count,
                "views_per_day": round(velocity, 1),
                "duration_seconds": duration_seconds,
                "license": "YouTube Creative Commons",
                "rights_status": "creative_commons_attribution_required",
                "attribution_required": True,
                "import_status": "manual_review_required",
                "auto_download": False,
            }
        )

    candidates.sort(
        key=lambda item: (
            -float(item.get("views_per_day") or 0),
            -int(item.get("view_count") or 0),
            str(item.get("published_at") or ""),
        )
    )
    return candidates[: max(1, int(limit))]


def write_discovery_report(
    output: Path,
    *,
    query: str,
    days: int,
    candidates: list[dict[str, Any]],
) -> Path:
    output.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "version": 1,
        "source": "youtube_creative_commons",
        "query": query,
        "lookback_days": int(days),
        "candidate_count": len(candidates),
        "policy": {
            "purpose": "trend discovery only",
            "auto_download": False,
            "human_review_required": True,
            "note": (
                "Creative Commons licensing helps with source rights, but YouTube reused-content "
                "monetization rules still require substantive original editing/value."
            ),
        },
        "candidates": candidates,
    }
    output.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return output


def main() -> None:
    load_dotenv()
    parser = argparse.ArgumentParser(prog="vv-cat-trends")
    parser.add_argument("--config", default="config/pilot.toml")
    parser.add_argument("--days", type=int, default=30)
    parser.add_argument("--limit", type=int, default=30)
    parser.add_argument("--query", default="funny cat kitten")
    args = parser.parse_args()

    settings = load_settings(args.config)
    api_key = os.getenv("YOUTUBE_API_KEY", "").strip()
    if not api_key:
        raise SystemExit(
            "YOUTUBE_API_KEY is not set. Add a YouTube Data API v3 key to .env before running trend discovery."
        )

    candidates = discover_youtube_cc_cats(
        api_key=api_key,
        query=args.query,
        days=max(args.days, 1),
        limit=max(args.limit, 1),
    )
    output = settings.runtime_dir / "trends" / "youtube-cat-cc.json"
    write_discovery_report(
        output,
        query=args.query,
        days=max(args.days, 1),
        candidates=candidates,
    )
    print(f"YouTube CC cat candidates: {len(candidates)}")
    print(output)
    if candidates:
        top = candidates[0]
        print(
            "Top candidate: "
            f"{top['title']} | {top['view_count']} views | {top['views_per_day']:.0f} views/day | {top['url']}"
        )


if __name__ == "__main__":
    main()
