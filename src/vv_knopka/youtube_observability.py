from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

from .settings import Settings
from .youtube_uploader import _require_bound_service


def _receipt_paths(settings: Settings) -> list[Path]:
    ready = settings.runtime_dir / "ready_for_review"
    if not ready.exists():
        return []
    paths = sorted(ready.glob("slot-*.youtube.json"))

    def slot_number(path: Path) -> int:
        try:
            return int(path.name.split("-", 2)[1])
        except (ValueError, IndexError):
            return 10**9

    return sorted(paths, key=slot_number)


def _chunks(values: list[str], size: int = 50) -> Iterable[list[str]]:
    for index in range(0, len(values), size):
        yield values[index:index + size]


def _load_receipts(settings: Settings) -> list[tuple[Path, dict[str, Any]]]:
    result: list[tuple[Path, dict[str, Any]]] = []
    for path in _receipt_paths(settings):
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        video_id = str(payload.get("video_id") or "").strip()
        if video_id:
            result.append((path, payload))
    return result


def _receipt_identity(path: Path, payload: dict[str, Any]) -> tuple[str | None, str | None]:
    """Recover pipeline/language for old receipts that predate those receipt fields."""
    pipeline = str(payload.get("pipeline") or "").strip() or None
    language = str(payload.get("language") or "").strip() or None
    name = path.name.casefold()
    if pipeline is None:
        if "-animals." in name or "-animals-" in name:
            pipeline = "animal_compilation"
        elif "-ai." in name or "-ai-" in name:
            pipeline = "ai_short"
    if language is None:
        if "-ru-" in name:
            language = "ru"
        elif "-en-" in name:
            language = "en"
    return pipeline, language


def _publication_state(item: dict[str, Any]) -> tuple[str, dict[str, Any]]:
    status = dict(item.get("status") or {})
    processing = dict(item.get("processingDetails") or {})
    upload_status = str(status.get("uploadStatus") or "").strip().lower()
    privacy = str(status.get("privacyStatus") or "").strip().lower()
    processing_status = str(processing.get("processingStatus") or "").strip().lower()
    failure_reason = str(status.get("failureReason") or processing.get("processingFailureReason") or "").strip()
    rejection_reason = str(status.get("rejectionReason") or "").strip()

    failure_states = {"failed", "rejected", "deleted"}
    processing_failure_states = {"failed", "terminated"}

    if upload_status in failure_states or processing_status in processing_failure_states or failure_reason or rejection_reason:
        state = "FAILED"
    elif privacy == "public" and upload_status in {"processed", "uploaded"} and processing_status in {"", "succeeded"}:
        state = "VERIFIED_PUBLIC"
    elif privacy == "public" and processing_status == "succeeded":
        state = "VERIFIED_PUBLIC"
    else:
        state = "PROCESSING"

    detail = {
        "upload_status": upload_status or None,
        "processing_status": processing_status or None,
        "privacy_status": privacy or None,
        "failure_reason": failure_reason or None,
        "rejection_reason": rejection_reason or None,
    }
    return state, detail


def verify_receipts(settings: Settings) -> list[dict[str, Any]]:
    receipts = _load_receipts(settings)
    if not receipts:
        return []

    service, channel = _require_bound_service(settings)
    by_id = {str(payload["video_id"]): (path, payload) for path, payload in receipts}
    found: dict[str, dict[str, Any]] = {}
    ids = list(by_id)
    for chunk in _chunks(ids):
        response = service.videos().list(
            part="status,processingDetails",
            id=",".join(chunk),
        ).execute()
        for item in response.get("items") or []:
            video_id = str(item.get("id") or "").strip()
            if video_id:
                found[video_id] = item

    checked_at = datetime.now(timezone.utc).isoformat()
    results: list[dict[str, Any]] = []
    for video_id in ids:
        path, payload = by_id[video_id]
        item = found.get(video_id)
        if item is None:
            state = "MISSING"
            detail = {
                "upload_status": None,
                "processing_status": None,
                "privacy_status": None,
                "failure_reason": "Video was not returned by videos.list for the bound channel.",
                "rejection_reason": None,
            }
        else:
            state, detail = _publication_state(item)

        verification = {
            **detail,
            "checked_at": checked_at,
            "channel_id": channel["channel_id"],
            "channel_title": channel["channel_title"],
        }
        payload["publication_state"] = state
        payload["verification"] = verification
        path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        results.append({
            "slot": int(payload.get("slot") or 0),
            "video_id": video_id,
            "youtube_url": payload.get("youtube_url"),
            "publication_state": state,
            **detail,
        })
    return results


def failed_publications(settings: Settings) -> list[dict[str, Any]]:
    result: list[dict[str, Any]] = []
    for _, payload in _load_receipts(settings):
        state = str(payload.get("publication_state") or "")
        if state in {"FAILED", "MISSING"}:
            result.append(payload)
    return result


def _statistics_dir(settings: Settings) -> Path:
    path = settings.runtime_dir / "youtube"
    path.mkdir(parents=True, exist_ok=True)
    return path


def _save_statistics_snapshot(settings: Settings, snapshot: dict[str, Any]) -> None:
    root = _statistics_dir(settings)
    (root / "statistics.json").write_text(
        json.dumps(snapshot, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    with (root / "statistics-history.jsonl").open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(snapshot, ensure_ascii=False, separators=(",", ":")) + "\n")


def collect_statistics(settings: Settings) -> dict[str, Any]:
    receipts = _load_receipts(settings)
    collected_at = datetime.now(timezone.utc).isoformat()
    if not receipts:
        snapshot = {"collected_at": collected_at, "videos": []}
        _save_statistics_snapshot(settings, snapshot)
        return snapshot

    service, channel = _require_bound_service(settings)
    by_id = {str(payload["video_id"]): (path, payload) for path, payload in receipts}
    found: dict[str, dict[str, Any]] = {}
    ids = list(by_id)
    for chunk in _chunks(ids):
        response = service.videos().list(
            part="statistics,status,snippet",
            id=",".join(chunk),
        ).execute()
        for item in response.get("items") or []:
            video_id = str(item.get("id") or "").strip()
            if video_id:
                found[video_id] = item

    videos: list[dict[str, Any]] = []
    for video_id in ids:
        receipt_path, payload = by_id[video_id]
        item = found.get(video_id, {})
        stats = dict(item.get("statistics") or {})
        status = dict(item.get("status") or {})
        snippet = dict(item.get("snippet") or {})
        pipeline, language = _receipt_identity(receipt_path, payload)
        entry = {
            "slot": int(payload.get("slot") or 0),
            "video_id": video_id,
            "youtube_url": payload.get("youtube_url"),
            "pipeline": pipeline,
            "language": language,
            "title": snippet.get("title") or payload.get("title"),
            "published_at": snippet.get("publishedAt") or payload.get("uploaded_at"),
            "privacy_status": status.get("privacyStatus") or payload.get("actual_privacy"),
            "views": int(stats.get("viewCount") or 0),
            "likes": int(stats.get("likeCount") or 0),
            "comments": int(stats.get("commentCount") or 0),
        }
        videos.append(entry)

    videos.sort(key=lambda item: int(item.get("slot") or 0))
    snapshot = {
        "collected_at": collected_at,
        "channel_id": channel["channel_id"],
        "channel_title": channel["channel_title"],
        "videos": videos,
    }
    _save_statistics_snapshot(settings, snapshot)
    return snapshot


def _parse_datetime(value: Any) -> datetime | None:
    text = str(value or "").strip()
    if not text:
        return None
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    try:
        parsed = datetime.fromisoformat(text)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _mean(values: list[float]) -> float:
    return sum(values) / len(values) if values else 0.0


def build_performance_report(settings: Settings) -> dict[str, Any]:
    """Build an age-aware report from the latest local YouTube statistics snapshot."""
    stats_path = _statistics_dir(settings) / "statistics.json"
    if not stats_path.exists():
        return {"generated_at": datetime.now(timezone.utc).isoformat(), "videos": [], "pipelines": {}}
    try:
        snapshot = json.loads(stats_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {"generated_at": datetime.now(timezone.utc).isoformat(), "videos": [], "pipelines": {}}

    collected_at = _parse_datetime(snapshot.get("collected_at")) or datetime.now(timezone.utc)
    enriched: list[dict[str, Any]] = []
    for raw in snapshot.get("videos") or []:
        if not isinstance(raw, dict):
            continue
        item = dict(raw)
        views = max(int(item.get("views") or 0), 0)
        likes = max(int(item.get("likes") or 0), 0)
        comments = max(int(item.get("comments") or 0), 0)
        published_at = _parse_datetime(item.get("published_at"))
        age_hours = max((collected_at - published_at).total_seconds() / 3600.0, 0.0) if published_at else 0.0
        # Avoid exploding very-fresh rates while still making age normalization useful.
        denominator_hours = max(age_hours, 1.0)
        item["age_hours"] = round(age_hours, 2)
        item["views_per_hour"] = round(views / denominator_hours, 2)
        item["likes_per_1000_views"] = round(likes * 1000.0 / views, 2) if views else 0.0
        item["comments_per_1000_views"] = round(comments * 1000.0 / views, 2) if views else 0.0
        enriched.append(item)

    pipelines: dict[str, dict[str, Any]] = {}
    names = sorted({str(item.get("pipeline") or "unknown") for item in enriched})
    for name in names:
        group = [item for item in enriched if str(item.get("pipeline") or "unknown") == name]
        pipelines[name] = {
            "videos": len(group),
            "total_views": sum(int(item.get("views") or 0) for item in group),
            "average_views": round(_mean([float(item.get("views") or 0) for item in group]), 2),
            "average_views_per_hour": round(_mean([float(item.get("views_per_hour") or 0) for item in group]), 2),
            "average_likes_per_1000_views": round(_mean([float(item.get("likes_per_1000_views") or 0) for item in group]), 2),
            "average_comments_per_1000_views": round(_mean([float(item.get("comments_per_1000_views") or 0) for item in group]), 2),
        }

    ranked = sorted(
        enriched,
        key=lambda item: (float(item.get("views_per_hour") or 0), int(item.get("views") or 0)),
        reverse=True,
    )
    report = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "statistics_collected_at": snapshot.get("collected_at"),
        "channel_id": snapshot.get("channel_id"),
        "channel_title": snapshot.get("channel_title"),
        "videos": ranked,
        "pipelines": pipelines,
    }
    (_statistics_dir(settings) / "performance-report.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return report
