from __future__ import annotations

import argparse
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from dotenv import load_dotenv

from .settings import Settings, load_settings
from .trend_discovery import _parse_youtube_duration, _views_per_day
from .youtube_uploader import _require_bound_service


_DEFAULT_CC_QUERY = "cat kitten shorts"
_DEFAULT_GENERAL_QUERY = "funny cat shorts"


def candidate_queue_path(settings: Settings, slot: int) -> Path:
    return settings.runtime_dir / "slots" / f"{int(slot):02d}" / "source-candidate-queue.json"


def _search_ids(
    service: Any,
    *,
    query: str,
    days: int,
    limit: int,
    creative_commons_only: bool,
    now: datetime,
) -> list[str]:
    kwargs: dict[str, Any] = {
        "part": "snippet",
        "type": "video",
        "q": query,
        "order": "viewCount",
        "publishedAfter": (now - timedelta(days=max(int(days), 1))).isoformat().replace("+00:00", "Z"),
        "maxResults": max(1, min(int(limit), 50)),
        "videoDuration": "short",
        "videoEmbeddable": "true",
        "safeSearch": "strict",
    }
    if creative_commons_only:
        kwargs["videoLicense"] = "creativeCommon"
    response = service.search().list(**kwargs).execute()
    result: list[str] = []
    for item in response.get("items") or []:
        video_id = str((item.get("id") or {}).get("videoId") or "").strip()
        if video_id and video_id not in result:
            result.append(video_id)
    return result


def _details(service: Any, ids: list[str]) -> list[dict[str, Any]]:
    if not ids:
        return []
    response = service.videos().list(
        part="snippet,statistics,status,contentDetails",
        id=",".join(ids[:50]),
    ).execute()
    return [item for item in (response.get("items") or []) if isinstance(item, dict)]


def _candidate(item: dict[str, Any], *, now: datetime) -> dict[str, Any] | None:
    video_id = str(item.get("id") or "").strip()
    snippet = item.get("snippet") or {}
    status = item.get("status") or {}
    stats = item.get("statistics") or {}
    details = item.get("contentDetails") or {}
    published_at = str(snippet.get("publishedAt") or "").strip()
    if not video_id or not published_at:
        return None
    license_code = str(status.get("license") or "").strip()
    creative_commons = license_code == "creativeCommon"
    views = int(stats.get("viewCount") or 0)
    return {
        "provider": "youtube",
        "video_id": video_id,
        "url": f"https://www.youtube.com/watch?v={video_id}",
        "title": str(snippet.get("title") or ""),
        "channel_title": str(snippet.get("channelTitle") or ""),
        "published_at": published_at,
        "duration_seconds": _parse_youtube_duration(str(details.get("duration") or "")),
        "view_count": views,
        "like_count": int(stats.get("likeCount") or 0),
        "views_per_day": round(_views_per_day(views, published_at, now=now), 1),
        "api_status_license": license_code,
        "license": (
            "YouTube Creative Commons Attribution"
            if creative_commons
            else "Standard YouTube License / permission not verified"
        ),
        "rights_status": (
            "creative_commons_attribution_required"
            if creative_commons
            else "permission_required_before_use"
        ),
        "attribution_required": creative_commons,
        "manual_review_required": True,
        "auto_download": False,
        "publication_allowed": False,
        "discovery_backend": "youtube_data_api_oauth",
    }


def discover_youtube_candidates(
    settings: Settings,
    *,
    days: int,
    limit: int,
    cc_query: str = _DEFAULT_CC_QUERY,
    general_query: str = _DEFAULT_GENERAL_QUERY,
    include_standard: bool = True,
    service: Any | None = None,
    now: datetime | None = None,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Search public metadata only; never download or approve media for publication."""
    current = (now or datetime.now(timezone.utc)).astimezone(timezone.utc)
    channel_binding_checked = service is None
    if service is None:
        service, channel = _require_bound_service(settings)
    else:
        channel = {"channel_id": None, "channel_title": None}

    cc_ids = _search_ids(
        service,
        query=cc_query,
        days=days,
        limit=limit,
        creative_commons_only=True,
        now=current,
    )
    general_ids = (
        _search_ids(
            service,
            query=general_query,
            days=days,
            limit=limit,
            creative_commons_only=False,
            now=current,
        )
        if include_standard
        else []
    )
    ordered_ids = list(dict.fromkeys(cc_ids + general_ids))
    by_id: dict[str, dict[str, Any]] = {}
    for item in _details(service, ordered_ids):
        converted = _candidate(item, now=current)
        if converted:
            by_id[str(converted["video_id"])] = converted

    candidates = [by_id[video_id] for video_id in ordered_ids if video_id in by_id]
    candidates.sort(
        key=lambda item: (
            item.get("rights_status") != "creative_commons_attribution_required",
            -float(item.get("views_per_day") or 0.0),
            -int(item.get("view_count") or 0),
        )
    )
    for rank, item in enumerate(candidates, 1):
        item["candidate_rank"] = rank
    diagnostics = {
        "backend": "youtube_data_api_oauth",
        "channel_binding_checked": channel_binding_checked,
        "authorized_channel_id": channel.get("channel_id"),
        "cc_query": cc_query,
        "general_query": general_query,
        "cc_search_ids": len(cc_ids),
        "general_search_ids": len(general_ids),
        "unique_candidates": len(candidates),
        "quota_note": (
            "two search.list calls plus one videos.list call; cached per slot"
            if include_standard
            else "one search.list call plus one videos.list call; cached per slot"
        ),
    }
    return candidates, diagnostics


def ensure_candidate_queue(
    settings: Settings,
    *,
    slot: int,
    reason: str,
    refresh: bool = False,
) -> Path:
    """Create a cached manual-review queue after every licensed automatic source failed."""
    output = candidate_queue_path(settings, slot)
    if output.exists() and not refresh:
        return output

    cfg = settings.raw.get("source_fallback", {})
    days = max(int(cfg.get("youtube_queue_days", 3650)), 1)
    limit = max(1, min(int(cfg.get("youtube_queue_limit", 10)), 25))
    enabled = bool(cfg.get("youtube_queue_enabled", True))
    candidates: list[dict[str, Any]] = []
    diagnostics: dict[str, Any] = {"backend": "disabled"}
    status = "disabled"
    error: str | None = None

    if enabled:
        try:
            candidates, diagnostics = discover_youtube_candidates(
                settings,
                days=days,
                limit=limit,
                cc_query=str(cfg.get("youtube_cc_query", _DEFAULT_CC_QUERY)),
                general_query=str(cfg.get("youtube_general_query", _DEFAULT_GENERAL_QUERY)),
                include_standard=bool(cfg.get("youtube_standard_queue_enabled", True)),
            )
            status = "ready_for_manual_review" if candidates else "empty"
        except Exception as exc:  # queue discovery is diagnostic and must not hide the source-gate result
            status = "unavailable"
            error = f"{type(exc).__name__}: {exc}"

    payload = {
        "version": 1,
        "slot": int(slot),
        "created_at": datetime.now(timezone.utc).isoformat(),
        "status": status,
        "trigger_reason": str(reason),
        "policy": {
            "auto_download": False,
            "auto_publish": False,
            "manual_review_required": True,
            "creative_commons_note": (
                "YouTube status.license=creativeCommon is recorded, but the clean-footage gate and human review "
                "are still required before import."
            ),
            "standard_license_note": (
                "Standard-license results are references only until direct permission or another valid right is documented."
            ),
        },
        "diagnostics": diagnostics,
        "error": error,
        "candidates": candidates,
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return output


def main() -> None:
    load_dotenv()
    parser = argparse.ArgumentParser(prog="vv-cat-sources")
    parser.add_argument("--config", default="config/pilot.toml")
    sub = parser.add_subparsers(dest="command", required=True)
    queue = sub.add_parser("youtube-queue", help="Create/inspect a no-download YouTube candidate queue")
    queue.add_argument("slot", type=int)
    queue.add_argument("--refresh", action="store_true")
    sub.add_parser("local-template", help="Create an empty manifest for user-approved licensed cat clips")
    args = parser.parse_args()
    settings = load_settings(args.config)

    if args.command == "youtube-queue":
        path = ensure_candidate_queue(
            settings,
            slot=args.slot,
            reason="manual queue refresh",
            refresh=bool(args.refresh),
        )
        raw = json.loads(path.read_text(encoding="utf-8"))
        print(f"YouTube source candidate queue: {raw.get('status')} | {path}")
        for item in (raw.get("candidates") or [])[:10]:
            rights = "CC BY" if item.get("rights_status") == "creative_commons_attribution_required" else "permission needed"
            print(
                f"[{int(item.get('candidate_rank') or 0):02d}] [{rights}] "
                f"{int(item.get('view_count') or 0):,} views | {item.get('title')} | {item.get('url')}"
            )
        print("Nothing in this queue is downloaded or published automatically.")
        print(f"For a reviewed CC BY URL: `vv-cat-youtube cc {args.slot} --url \"https://...\"`")
        return

    if args.command == "local-template":
        configured = str(
            settings.raw.get("source_fallback", {}).get(
                "local_library_manifest",
                "runtime/licensed_sources/cats/manifest.json",
            )
        )
        path = Path(configured)
        path = path if path.is_absolute() else (settings.root / path).resolve()
        path.parent.mkdir(parents=True, exist_ok=True)
        if not path.exists():
            path.write_text(json.dumps({"version": 1, "clips": []}, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"Local licensed cat library manifest: {path}")
        print("Add media files beside it and document license/source/human approval in the manifest.")


if __name__ == "__main__":
    main()
