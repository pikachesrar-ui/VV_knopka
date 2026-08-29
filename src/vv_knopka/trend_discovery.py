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
from yt_dlp import YoutubeDL
from yt_dlp.utils import DownloadError

from .settings import load_settings


YOUTUBE_SEARCH_URL = "https://www.googleapis.com/youtube/v3/search"
YOUTUBE_VIDEOS_URL = "https://www.googleapis.com/youtube/v3/videos"
PETS_TOPIC_ID = "/m/068hy"


def _parse_youtube_duration(value: str) -> float:
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


def _is_creative_commons(license_name: str) -> bool:
    text = str(license_name or "").casefold()
    return "creative commons" in text or "cc by" in text


def _entry_published_at(entry: dict[str, Any]) -> str:
    timestamp = entry.get("timestamp")
    if timestamp not in (None, ""):
        try:
            return datetime.fromtimestamp(float(timestamp), tz=timezone.utc).isoformat()
        except (TypeError, ValueError, OSError):
            pass
    upload_date = str(entry.get("upload_date") or "").strip()
    if re.fullmatch(r"\d{8}", upload_date):
        return datetime.strptime(upload_date, "%Y%m%d").replace(tzinfo=timezone.utc).isoformat()
    return ""


def _candidate_from_ytdlp_entry(
    entry: dict[str, Any],
    *,
    now: datetime,
    cutoff: datetime,
    min_seconds: float = 5.0,
    max_seconds: float = 180.0,
) -> dict[str, Any] | None:
    video_id = str(entry.get("id") or "").strip()
    if not video_id:
        return None
    try:
        duration = float(entry.get("duration") or 0.0)
    except (TypeError, ValueError):
        duration = 0.0
    if duration < min_seconds or duration > max_seconds:
        return None

    published_at = _entry_published_at(entry)
    if not published_at:
        return None
    published = _parse_utc(published_at)
    if published < cutoff or published > now + timedelta(hours=12):
        return None

    view_count = int(entry.get("view_count") or 0)
    like_count = int(entry.get("like_count") or 0)
    license_name = str(entry.get("license") or "").strip()
    cc = _is_creative_commons(license_name)
    webpage_url = str(entry.get("webpage_url") or "").strip()
    if not webpage_url:
        webpage_url = f"https://www.youtube.com/watch?v={video_id}"

    return {
        "provider": "youtube",
        "video_id": video_id,
        "url": webpage_url,
        "title": str(entry.get("title") or ""),
        "channel_title": str(entry.get("channel") or entry.get("uploader") or ""),
        "published_at": published_at,
        "view_count": view_count,
        "like_count": like_count,
        "views_per_day": round(_views_per_day(view_count, published_at, now=now), 1),
        "duration_seconds": duration,
        "license": license_name or "unverified",
        "rights_status": "creative_commons_attribution_required" if cc else "license_unverified",
        "attribution_required": bool(cc),
        "import_status": (
            "manual_review_required" if cc else "trend_reference_only_until_rights_verified"
        ),
        "auto_download": False,
        "discovery_backend": "yt_dlp_no_key",
    }


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
        "topicId": PETS_TOPIC_ID,
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
    query: str = "cat|kitten",
    days: int = 30,
    limit: int = 30,
    now: datetime | None = None,
) -> list[dict[str, Any]]:
    current = (now or datetime.now(timezone.utc)).astimezone(timezone.utc)
    params = youtube_search_params(api_key=api_key, query=query, days=days, limit=limit, now=current)
    with httpx.Client(timeout=45, follow_redirects=True) as client:
        search_response = client.get(YOUTUBE_SEARCH_URL, params=params)
        search_response.raise_for_status()
        ids = [
            str((item.get("id") or {}).get("videoId") or "").strip()
            for item in search_response.json().get("items", [])
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
        candidates.append(
            {
                "provider": "youtube",
                "video_id": video_id,
                "url": f"https://www.youtube.com/watch?v={video_id}",
                "title": str(snippet.get("title") or ""),
                "channel_title": str(snippet.get("channelTitle") or ""),
                "published_at": published_at,
                "view_count": view_count,
                "like_count": int(stats.get("likeCount") or 0),
                "views_per_day": round(_views_per_day(view_count, published_at, now=current), 1),
                "duration_seconds": _parse_youtube_duration(str(content_details.get("duration") or "")),
                "license": "YouTube Creative Commons Attribution",
                "rights_status": "creative_commons_attribution_required",
                "attribution_required": True,
                "import_status": "manual_review_required",
                "auto_download": False,
                "discovery_backend": "youtube_data_api",
            }
        )
    return _rank_candidates(candidates, limit)


def discover_ytdlp_cats(
    *,
    query: str = "cat kitten shorts",
    days: int = 30,
    limit: int = 30,
    now: datetime | None = None,
) -> list[dict[str, Any]]:
    """No-key YouTube trend discovery through yt-dlp search metadata; does not download media."""
    current = (now or datetime.now(timezone.utc)).astimezone(timezone.utc)
    cutoff = current - timedelta(days=max(int(days), 1))
    scan_count = max(50, min(max(int(limit), 1) * 3, 100))
    options = {
        "quiet": True,
        "no_warnings": True,
        "skip_download": True,
        "extract_flat": "in_playlist",
        "socket_timeout": 30,
    }
    try:
        with YoutubeDL(options) as ydl:
            result = ydl.extract_info(f"ytsearchdate{scan_count}:{query}", download=False)
    except DownloadError as exc:
        raise RuntimeError(
            "No-key YouTube search failed. Update the project environment and retry; "
            "do not log a personal YouTube account into yt-dlp for this workflow."
        ) from exc

    candidates: list[dict[str, Any]] = []
    for raw in (result or {}).get("entries", []) or []:
        if not isinstance(raw, dict):
            continue
        candidate = _candidate_from_ytdlp_entry(raw, now=current, cutoff=cutoff)
        if candidate:
            candidates.append(candidate)
    return _rank_candidates(candidates, limit)


def _rank_candidates(candidates: list[dict[str, Any]], limit: int) -> list[dict[str, Any]]:
    candidates.sort(
        key=lambda item: (
            -float(item.get("views_per_day") or 0),
            -int(item.get("view_count") or 0),
            str(item.get("published_at") or ""),
        )
    )
    ranked = candidates[: max(1, int(limit))]
    for rank, item in enumerate(ranked, 1):
        item["trend_rank"] = rank
    return ranked


def write_discovery_report(
    output: Path,
    *,
    query: str,
    days: int,
    candidates: list[dict[str, Any]],
    backend: str,
) -> Path:
    output.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "version": 3,
        "source": "youtube_trend_discovery",
        "backend": backend,
        "query": query,
        "lookback_days": int(days),
        "discovered_at": datetime.now(timezone.utc).isoformat(),
        "candidate_count": len(candidates),
        "policy": {
            "purpose": "trend discovery only",
            "auto_download": False,
            "human_review_required": True,
            "note": (
                "The no-key yt-dlp backend is best-effort. License metadata may be absent; "
                "unverified candidates are trend references only until rights are verified. "
                "Creative Commons rights do not remove YouTube reused-content risk."
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
    parser.add_argument("--query", default="cat kitten shorts")
    parser.add_argument("--backend", choices=("auto", "ytdlp", "api"), default="auto")
    args = parser.parse_args()

    settings = load_settings(args.config)
    api_key = os.getenv("YOUTUBE_API_KEY", "").strip()
    backend = args.backend
    if backend == "auto":
        backend = "api" if api_key else "ytdlp"

    if backend == "api":
        if not api_key:
            raise SystemExit(
                "--backend api requires YOUTUBE_API_KEY. Use the default/--backend ytdlp for no-key discovery."
            )
        candidates = discover_youtube_cc_cats(
            api_key=api_key,
            query=args.query,
            days=max(args.days, 1),
            limit=max(args.limit, 1),
        )
        backend_label = "youtube_data_api"
        print("Trend backend: YouTube Data API (exact Creative Commons filter)")
    else:
        candidates = discover_ytdlp_cats(
            query=args.query,
            days=max(args.days, 1),
            limit=max(args.limit, 1),
        )
        backend_label = "yt_dlp_no_key"
        print("Trend backend: yt-dlp (no Google Cloud, no API key, no account login)")

    output = settings.runtime_dir / "trends" / "youtube-cat-cc.json"
    write_discovery_report(
        output,
        query=args.query,
        days=max(args.days, 1),
        candidates=candidates,
        backend=backend_label,
    )
    cc_count = sum(
        1 for item in candidates if item.get("rights_status") == "creative_commons_attribution_required"
    )
    print(f"YouTube cat trend candidates: {len(candidates)} (CC already identified: {cc_count})")
    print(output)
    if candidates:
        print("Top current candidates:")
        for candidate in candidates[:10]:
            rights = "CC" if candidate.get("rights_status") == "creative_commons_attribution_required" else "rights?"
            print(
                f"[{int(candidate['trend_rank']):02d}] [{rights}] "
                f"{float(candidate['views_per_day']):,.0f} views/day | "
                f"{int(candidate['view_count']):,} views | "
                f"{candidate['title']} | {candidate['url']}"
            )
        print(
            "Candidates marked rights? are discovery references only. vv-cat-import re-checks "
            "YouTube license metadata and refuses an unverified/non-CC source."
        )


if __name__ == "__main__":
    main()
