from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from dotenv import load_dotenv

from .content_strategy import ALL_CATEGORIES
from .settings import Settings, load_settings
from .youtube_uploader import _require_bound_service


DEFAULT_QUERIES = {
    "cats": "cat shorts",
    "animals": "animal facts shorts",
    "anime": "anime facts shorts",
    "movies": "movie facts shorts",
    "theories": "film anime theories shorts",
    "other_facts": "interesting facts shorts",
}


def _duration_seconds(value: str) -> float:
    match = re.fullmatch(r"PT(?:(\d+)H)?(?:(\d+)M)?(?:(\d+(?:\.\d+)?)S)?", str(value or ""))
    if not match:
        return 0.0
    return int(match.group(1) or 0) * 3600 + int(match.group(2) or 0) * 60 + float(match.group(3) or 0)


def _parse_time(value: str) -> datetime:
    text = str(value or "").replace("Z", "+00:00")
    parsed = datetime.fromisoformat(text)
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _paths(settings: Settings) -> tuple[Path, Path, Path]:
    root = settings.runtime_dir / "research"
    root.mkdir(parents=True, exist_ok=True)
    return root / "outliers-latest.json", root / "outliers-history.jsonl", root / "outliers-attempt.json"


def collect_outliers(
    settings: Settings,
    *,
    categories: list[str] | None = None,
    max_queries: int | None = None,
    if_due_hours: float = 0,
    service: Any | None = None,
    now: datetime | None = None,
) -> dict[str, Any]:
    """Collect public metadata only; never download or copy other creators' media."""
    current = (now or datetime.now(timezone.utc)).astimezone(timezone.utc)
    latest_path, history_path, attempt_path = _paths(settings)
    if if_due_hours > 0 and latest_path.exists():
        age = current.timestamp() - latest_path.stat().st_mtime
        if age < if_due_hours * 3600:
            return {"status": "not_due", "output_file": str(latest_path), "age_hours": round(age / 3600, 2)}
    failure_retry_hours = max(float(settings.raw.get("research", {}).get("failure_retry_hours", 24)), 1.0)
    latest_mtime = latest_path.stat().st_mtime if latest_path.exists() else 0.0
    if if_due_hours > 0 and attempt_path.exists() and attempt_path.stat().st_mtime > latest_mtime:
        age = current.timestamp() - attempt_path.stat().st_mtime
        if age < failure_retry_hours * 3600:
            return {"status": "not_due", "output_file": str(latest_path), "age_hours": round(age / 3600, 2)}

    cfg = settings.raw.get("research", {})
    explicit_categories = categories is not None
    enabled = categories or [str(value) for value in cfg.get("categories", ALL_CATEGORIES)]
    enabled = [value for value in enabled if value in ALL_CATEGORIES]
    query_limit = max(1, int(max_queries or cfg.get("max_queries_per_run", 2)))
    if enabled and not explicit_categories:
        # Rotate the small weekly quota window so every configured category is
        # researched over time instead of permanently favoring the first two.
        offset = ((current.isocalendar().week - 1) * query_limit) % len(enabled)
        enabled = (enabled[offset:] + enabled[:offset])[:query_limit]
    else:
        enabled = enabled[:query_limit]
    days = max(7, int(cfg.get("lookback_days", 90)))
    per_query = max(5, min(int(cfg.get("results_per_query", 25)), 50))
    attempt_path.write_text(
        json.dumps({"status": "started", "started_at": current.isoformat()}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    youtube = service or _require_bound_service(settings)[0]
    published_after = (current - timedelta(days=days)).isoformat().replace("+00:00", "Z")

    candidates: list[dict[str, Any]] = []
    for category in enabled:
        query = str((cfg.get("queries") or {}).get(category) or DEFAULT_QUERIES[category])
        response = youtube.search().list(
            part="snippet",
            type="video",
            q=query,
            order="viewCount",
            publishedAfter=published_after,
            videoDuration="short",
            safeSearch="strict",
            maxResults=per_query,
        ).execute()
        ids = [str((item.get("id") or {}).get("videoId") or "") for item in response.get("items") or []]
        ids = [value for value in ids if value]
        if not ids:
            continue
        details = youtube.videos().list(part="snippet,statistics,contentDetails,status", id=",".join(ids)).execute()
        for item in details.get("items") or []:
            snippet = item.get("snippet") or {}
            stats = item.get("statistics") or {}
            status = item.get("status") or {}
            published_at = str(snippet.get("publishedAt") or "")
            if not published_at:
                continue
            age_days = max((current - _parse_time(published_at)).total_seconds() / 86400.0, 0.5)
            views = max(int(stats.get("viewCount") or 0), 0)
            likes = max(int(stats.get("likeCount") or 0), 0)
            candidates.append({
                "category": category,
                "video_id": str(item.get("id") or ""),
                "url": f"https://www.youtube.com/watch?v={item.get('id')}",
                "title": str(snippet.get("title") or ""),
                "channel_title": str(snippet.get("channelTitle") or ""),
                "published_at": published_at,
                "duration_seconds": _duration_seconds(str((item.get("contentDetails") or {}).get("duration") or "")),
                "views": views,
                "likes": likes,
                "views_per_day": round(views / age_days, 2),
                "likes_per_1000_views": round(likes * 1000 / views, 2) if views else 0.0,
                "license": str(status.get("license") or "youtube"),
                "analysis_scope": "metadata_only",
                "auto_download": False,
                "publication_allowed": False,
            })

    candidates.sort(key=lambda item: (float(item["views_per_day"]), int(item["views"])), reverse=True)
    payload = {
        "schema_version": 1,
        "status": "ok",
        "collected_at": current.isoformat(),
        "queries_used": len(enabled),
        "estimated_youtube_quota_units": len(enabled) * 101,
        "candidates": candidates,
        "limitations": [
            "Titles are hook proxies; first seconds, pacing and payoff need manual annotation.",
            "No media is downloaded or reused.",
        ],
    }
    latest_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    with history_path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(payload, ensure_ascii=False, separators=(",", ":")) + "\n")
    attempt_path.write_text(
        json.dumps({"status": "ok", "finished_at": current.isoformat()}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    payload["output_file"] = str(latest_path)
    return payload


def summarize_outliers(settings: Settings, *, limit: int = 10) -> dict[str, Any]:
    latest_path, _, _ = _paths(settings)
    if not latest_path.exists():
        return {"status": "missing", "candidates": [], "output_file": str(latest_path)}
    payload = json.loads(latest_path.read_text(encoding="utf-8"))
    rows = list(payload.get("candidates") or [])[: max(int(limit), 0)]
    return {"status": "ok", "collected_at": payload.get("collected_at"), "candidates": rows, "output_file": str(latest_path)}


def main() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        try:
            sys.stdout.reconfigure(errors="backslashreplace")
        except (OSError, ValueError):
            pass
    load_dotenv()
    parser = argparse.ArgumentParser(prog="vv-research")
    parser.add_argument("--config", default="config/pilot.toml")
    sub = parser.add_subparsers(dest="command", required=True)
    collect = sub.add_parser("collect")
    collect.add_argument("--categories", default=None, help="Comma-separated category list")
    collect.add_argument("--max-queries", type=int, default=None)
    collect.add_argument("--if-due-hours", type=float, default=0)
    report = sub.add_parser("report")
    report.add_argument("--limit", type=int, default=10)
    args = parser.parse_args()
    settings = load_settings(Path(args.config).resolve())
    if args.command == "collect":
        categories = [part.strip() for part in args.categories.split(",")] if args.categories else None
        result = collect_outliers(settings, categories=categories, max_queries=args.max_queries, if_due_hours=args.if_due_hours)
        if result["status"] == "not_due":
            print(f"outlier research: NOT DUE | age={result['age_hours']}h | {result['output_file']}")
        else:
            print(f"outlier research: OK | queries={result['queries_used']} | candidates={len(result['candidates'])}")
            print(result["output_file"])
        return
    result = summarize_outliers(settings, limit=args.limit)
    print(f"outlier research: {result['status'].upper()} | {result['output_file']}")
    for row in result.get("candidates") or []:
        print(f"{row['category']}: {row['views_per_day']:.0f}/day | {row['duration_seconds']:.0f}s | {row['title']}")


if __name__ == "__main__":
    main()
