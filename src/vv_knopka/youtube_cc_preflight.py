from __future__ import annotations

import json
import shutil
from pathlib import Path
from typing import Any

from yt_dlp import YoutubeDL
from yt_dlp.utils import DownloadError

from .budget import BudgetLedger
from .settings import Settings
from .youtube_clean_footage import clean_review_clip_metadata, review_clean_youtube_footage


_VIDEO_SUFFIXES = {".mp4", ".mkv", ".webm", ".mov", ".m4v"}


def known_rejected_video_ids(runtime_dir: Path) -> set[str]:
    """Read fail-closed clean reviews so rejected videos are not offered again."""
    rejected: set[str] = set()
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
    """Download a small preview for visual screening before production-quality media."""
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


def clean_preflight_candidate(
    settings: Settings,
    *,
    slot: int,
    video_id: str,
    url: str,
    title: str = "",
    creator: str = "",
) -> tuple[Path, dict[str, Any], dict[str, Any]]:
    """Screen low-res temporal samples before downloading the production asset."""
    preview_dir = settings.runtime_dir / "previews" / "youtube-cc"
    preview = download_low_res_preview(url, destination_dir=preview_dir, video_id=video_id)
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
    metadata = clean_review_clip_metadata(review)
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
