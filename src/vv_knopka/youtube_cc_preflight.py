from __future__ import annotations

import json
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from yt_dlp import YoutubeDL
from yt_dlp.utils import DownloadError

from .animal_audio_sources import is_short_portrait, video_dimensions
from .budget import BudgetLedger
from .settings import Settings
from .trend_import import _ffprobe_duration
from .youtube_clean_footage import clean_review_clip_metadata, review_clean_youtube_footage


_VIDEO_SUFFIXES = {".mp4", ".mkv", ".webm", ".mov", ".m4v"}


def known_preflight_rejected_video_ids(runtime_dir: Path) -> set[str]:
    """Read durable deterministic preflight rejects such as wrong aspect ratio."""
    rejected: set[str] = set()
    for path in runtime_dir.glob("slots/*/youtube_preflight_rejects/*.json"):
        try:
            raw = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        video_id = str(raw.get("video_id") or "").strip()
        if video_id and raw.get("durable_reject") is True:
            rejected.add(video_id)
    return rejected


def known_rejected_video_ids(runtime_dir: Path) -> set[str]:
    """Read fail-closed clean reviews plus deterministic preflight rejects."""
    rejected = known_preflight_rejected_video_ids(runtime_dir)
    for path in runtime_dir.glob("slots/*/youtube_clean_reviews/*.json"):
        try:
            raw = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        video_id = str(raw.get("video_id") or "").strip()
        if video_id and raw.get("clean_footage_approved") is False:
            rejected.add(video_id)
    return rejected


def filter_known_rejections(candidates: list[dict[str, Any]], runtime_dir: Path) -> tuple[list[dict[str, Any]], list[str]]:
    rejected = known_rejected_video_ids(runtime_dir)
    kept: list[dict[str, Any]] = []
    removed: list[str] = []
    for item in candidates:
        video_id = str(item.get("video_id") or "").strip()
        if video_id and video_id in rejected:
            removed.append(video_id)
            continue
        kept.append(item)
    return kept, removed


def download_low_res_preview(url: str, *, destination_dir: Path, video_id: str) -> Path:
    """Download a small preview for format/visual screening before production-quality media."""
    destination_dir.mkdir(parents=True, exist_ok=True)
    template = str(destination_dir / "youtube-cc-preview-%(id)s.%(ext)s")
    options = {
        # Prefer one small muxed stream. If YouTube does not expose one, allow
        # a small video-only stream because the preflight only needs frames.
        "format": "b[height<=360]/bv*[height<=360]/worstvideo",
        "outtmpl": template,
        "noplaylist": True,
        "socket_timeout": 30,
        "windowsfilenames": True,
        "quiet": True,
        "no_warnings": False,
    }
    try:
        with YoutubeDL(options) as ydl:
            ydl.extract_info(url, download=True)
    except DownloadError as exc:
        raise RuntimeError("yt-dlp could not download the low-resolution CC preview") from exc

    matches = [
        path
        for path in destination_dir.glob(f"youtube-cc-preview-{video_id}.*")
        if path.is_file() and path.suffix.lower() in _VIDEO_SUFFIXES and path.stat().st_size > 0
    ]
    if not matches:
        raise RuntimeError("CC preview download completed but no preview video file was found")
    matches.sort(key=lambda path: (path.suffix.lower() != ".mp4", path.stat().st_size, path.name))
    return matches[0].resolve()


def _write_preflight_reject(
    settings: Settings,
    *,
    slot: int,
    video_id: str,
    url: str,
    reason: str,
    details: dict[str, Any] | None = None,
    durable_reject: bool,
) -> Path:
    reject_dir = settings.runtime_dir / "slots" / f"{int(slot):02d}" / "youtube_preflight_rejects"
    reject_dir.mkdir(parents=True, exist_ok=True)
    safe_id = "".join(ch for ch in str(video_id) if ch.isalnum() or ch in "-_") or "unknown"
    output = reject_dir / f"{safe_id}.json"
    payload = {
        "version": 1,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "video_id": str(video_id),
        "source_url": str(url),
        "stage": "low_res_format_preflight",
        "durable_reject": bool(durable_reject),
        "reason": str(reason),
        "details": details or {},
    }
    output.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return output


def _validate_preview_format(settings: Settings, preview: Path) -> dict[str, Any]:
    """Run deterministic geometry/duration gates before spending on Luna."""
    animal_cfg = settings.raw.get("animal", {})
    tolerance = float(animal_cfg.get("source_aspect_tolerance", 0.08))
    min_seconds = float(animal_cfg.get("clip_seconds", 5.0))

    dimensions = video_dimensions(preview)
    if dimensions is None:
        raise RuntimeError("Could not read low-resolution preview dimensions")
    width, height = dimensions
    aspect_ratio = width / height if height else 0.0
    if not is_short_portrait(width, height, tolerance=tolerance):
        raise ValueError(
            f"preview is {width}x{height} (aspect {aspect_ratio:.4f}); source must already be near 9:16 portrait"
        )

    duration = _ffprobe_duration(preview)
    if duration < min_seconds:
        raise ValueError(f"preview duration is {duration:.2f}s; need at least {min_seconds:.2f}s")

    return {
        "preview_width": width,
        "preview_height": height,
        "preview_aspect_ratio": round(aspect_ratio, 6),
        "preview_duration_seconds": round(float(duration), 3),
    }


def clean_preflight_candidate(
    settings: Settings,
    *,
    slot: int,
    video_id: str,
    url: str,
    title: str = "",
    creator: str = "",
) -> tuple[Path, dict[str, Any], dict[str, Any]]:
    """Screen low-res format and temporal samples before downloading the production asset."""
    preview_dir = settings.runtime_dir / "previews" / "youtube-cc"
    preview = download_low_res_preview(url, destination_dir=preview_dir, video_id=video_id)

    try:
        format_metadata = _validate_preview_format(settings, preview)
    except ValueError as exc:
        dimensions = video_dimensions(preview)
        duration = _ffprobe_duration(preview)
        details: dict[str, Any] = {"duration_seconds": round(float(duration), 3)}
        if dimensions is not None:
            width, height = dimensions
            details.update(
                {
                    "width": width,
                    "height": height,
                    "aspect_ratio": round(width / height, 6) if height else 0.0,
                }
            )
        reject_path = _write_preflight_reject(
            settings,
            slot=slot,
            video_id=video_id,
            url=url,
            reason=str(exc),
            details=details,
            durable_reject=True,
        )
        raise ValueError(
            "YouTube CC candidate failed low-resolution format preflight before Luna/full download: "
            f"{exc}. Reject audit: {reject_path}"
        ) from None
    except RuntimeError as exc:
        # Decode/tool failures can be transient. Record them for debugging but
        # do not poison reject memory permanently.
        reject_path = _write_preflight_reject(
            settings,
            slot=slot,
            video_id=video_id,
            url=url,
            reason=str(exc),
            durable_reject=False,
        )
        raise RuntimeError(f"YouTube CC preview format preflight could not run: {exc}. Audit: {reject_path}") from exc

    ledger = BudgetLedger(settings)
    review = review_clean_youtube_footage(
        settings,
        ledger,
        video=preview,
        slot=slot,
        video_id=video_id,
        title=title,
        creator=creator,
    )
    metadata = format_metadata | clean_review_clip_metadata(review)
    if metadata.get("clean_footage_approved") is not True:
        reason = str(metadata.get("clean_footage_reason") or "clean preview rejected")
        raise ValueError(
            "YouTube CC candidate failed low-resolution temporal clean preflight before full download: "
            f"{reason}"
        )
    return preview, review, metadata


def remove_preview(path: Path) -> None:
    """Best-effort cleanup for previews that passed and are no longer needed."""
    try:
        if path.exists():
            path.unlink()
    except OSError:
        pass
