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


def collect_statistics(settings: Settings) -> dict[str, Any]:
    receipts = _load_receipts(settings)
    collected_at = datetime.now(timezone.utc).isoformat()
    if not receipts:
        snapshot = {"collected_at": collected_at, "videos": []}
        path = settings.runtime_dir / "youtube" / "statistics.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(snapshot, ensure_ascii=False, indent=2), encoding="utf-8")
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
        _, payload = by_id[video_id]
        item = found.get(video_id, {})
        stats = dict(item.get("statistics") or {})
        status = dict(item.get("status") or {})
        snippet = dict(item.get("snippet") or {})
        entry = {
            "slot": int(payload.get("slot") or 0),
            "video_id": video_id,
            "youtube_url": payload.get("youtube_url"),
            "pipeline": payload.get("pipeline"),
            "language": payload.get("language"),
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
    path = settings.runtime_dir / "youtube" / "statistics.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(snapshot, ensure_ascii=False, indent=2), encoding="utf-8")
    return snapshot
