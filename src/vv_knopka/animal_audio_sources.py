from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
from pathlib import Path
from typing import Any

import httpx

from .budget import BudgetLedger
from .pexels_curator import (
    _collect_pixabay_candidates,
    _material_from_candidate,
    _review_until_enough,
    choose_pexels_file,
    infer_visual_anchor,
    pexels_page_matches_anchor,
)
from .settings import Settings


_PROVIDER_LICENSES = {
    "pexels": "Pexels License",
    "pixabay": "Pixabay Content License",
}
_TARGET_SHORT_ASPECT = 9.0 / 16.0


def _ffprobe_binary() -> str:
    return shutil.which("ffprobe") or "ffprobe"


def _ffmpeg_binary() -> str:
    return os.getenv("IMAGEIO_FFMPEG_EXE", "").strip() or shutil.which("ffmpeg") or "ffmpeg"


def has_audio_stream(path_or_url: str | Path, *, timeout: float = 25.0) -> bool | None:
    """Return True/False when ffprobe can inspect the source, None on probe failure."""
    try:
        completed = subprocess.run(
            [
                _ffprobe_binary(),
                "-v",
                "error",
                "-select_streams",
                "a:0",
                "-show_entries",
                "stream=codec_type",
                "-of",
                "csv=p=0",
                str(path_or_url),
            ],
            capture_output=True,
            text=True,
            check=False,
            timeout=timeout,
        )
    except (OSError, subprocess.TimeoutExpired):
        return None
    if completed.returncode != 0:
        return None
    return bool(completed.stdout.strip())


def video_dimensions(path_or_url: str | Path, *, timeout: float = 25.0) -> tuple[int, int] | None:
    """Return the first video stream width/height, or None when it cannot be trusted."""
    try:
        completed = subprocess.run(
            [
                _ffprobe_binary(),
                "-v",
                "error",
                "-select_streams",
                "v:0",
                "-show_entries",
                "stream=width,height",
                "-of",
                "csv=p=0:s=x",
                str(path_or_url),
            ],
            capture_output=True,
            text=True,
            check=False,
            timeout=timeout,
        )
    except (OSError, subprocess.TimeoutExpired):
        return None
    if completed.returncode != 0:
        return None
    match = re.search(r"(\d+)x(\d+)", completed.stdout.strip())
    if not match:
        return None
    width, height = int(match.group(1)), int(match.group(2))
    if width <= 0 or height <= 0:
        return None
    return width, height


def is_short_portrait(width: int, height: int, *, tolerance: float = 0.11) -> bool:
    """Accept portrait footage close enough to 9:16 for a small full-frame crop.

    9:16 is 0.5625 in width/height terms. The default tolerance also accepts
    common 3:5 and 2:3 portrait phone footage, while rejecting 4:5/square and
    every landscape source. This avoids the visibly-horizontal blur-fill look.
    """
    width = int(width or 0)
    height = int(height or 0)
    if width <= 0 or height <= 0 or width >= height:
        return False
    return abs((width / height) - _TARGET_SHORT_ASPECT) <= max(float(tolerance), 0.0)


def _file_info_is_short_portrait(file_info: dict[str, Any], *, tolerance: float) -> bool:
    return is_short_portrait(
        int(file_info.get("width") or 0),
        int(file_info.get("height") or 0),
        tolerance=tolerance,
    )


def mean_audio_volume_db(path: Path, *, seconds: float = 8.0) -> float | None:
    """Measure actual signal level so a technically-present silent track is rejected."""
    try:
        completed = subprocess.run(
            [
                _ffmpeg_binary(),
                "-hide_banner",
                "-nostats",
                "-i",
                str(path),
                "-map",
                "0:a:0",
                "-t",
                f"{seconds:.2f}",
                "-af",
                "volumedetect",
                "-f",
                "null",
                "-",
            ],
            capture_output=True,
            text=True,
            check=False,
            timeout=40,
        )
    except (OSError, subprocess.TimeoutExpired):
        return None
    text = f"{completed.stdout}\n{completed.stderr}"
    if "mean_volume: -inf dB" in text:
        return float("-inf")
    match = re.search(r"mean_volume:\s*(-?\d+(?:\.\d+)?)\s*dB", text)
    if not match:
        return None
    return float(match.group(1))


def has_audible_audio(path: Path, *, minimum_mean_db: float = -55.0) -> tuple[bool, float | None]:
    stream = has_audio_stream(path)
    if stream is not True:
        return False, None
    mean_db = mean_audio_volume_db(path)
    if mean_db is None:
        # A real stream is still preferable to a guaranteed-silent stock file.
        return True, None
    return mean_db > minimum_mean_db, mean_db


def _collect_pexels_audio_candidates(
    *,
    client: httpx.Client,
    api_key: str,
    queries: list[str],
    per_page: int,
    max_candidates: int,
    clip_seconds: int,
    anchor: str,
    aspect_tolerance: float,
) -> list[dict[str, Any]]:
    """Search Pexels for audible candidates while refusing horizontal footage."""
    candidates: list[dict[str, Any]] = []
    seen_ids: set[int] = set()
    for query in queries:
        response = client.get(
            "https://api.pexels.com/videos/search",
            headers={"Authorization": api_key},
            params={"query": query, "orientation": "portrait", "per_page": per_page},
        )
        response.raise_for_status()
        for video in (response.json()).get("videos") or []:
            video_id = int(video.get("id") or 0)
            if not video_id or video_id in seen_ids:
                continue
            duration = float(video.get("duration") or 0)
            if duration < clip_seconds:
                continue
            file_info = choose_pexels_file(video)
            thumbnail_url = str(video.get("image") or "").strip()
            if (
                not file_info
                or not thumbnail_url
                or not _file_info_is_short_portrait(file_info, tolerance=aspect_tolerance)
            ):
                continue
            page_url = str(video.get("url") or "")
            creator = video.get("user") or {}
            candidates.append(
                {
                    "provider": "pexels",
                    "id": video_id,
                    "query": query,
                    "page_url": page_url,
                    "thumbnail_url": thumbnail_url,
                    "duration": duration,
                    "creator": creator.get("name"),
                    "creator_url": creator.get("url"),
                    "file_info": file_info,
                    "metadata_mentions_anchor": pexels_page_matches_anchor(page_url, anchor),
                }
            )
            seen_ids.add(video_id)
            if len(candidates) >= max_candidates:
                return candidates
    return candidates


def _clip_identity(item: dict[str, Any]) -> tuple[str, str]:
    provider = str(item.get("provider") or "").strip().lower()
    provider_id = item.get("provider_id")
    if provider_id not in (None, ""):
        return provider, str(provider_id)
    return provider, str(item.get("source_url") or item.get("file") or "")


def _clip_from_cached_info(local_dir: Path, info: dict[str, Any]) -> dict[str, Any] | None:
    provider = str(info.get("provider") or "").strip().lower()
    filename = str(info.get("local_file") or "").strip()
    page_url = str(info.get("page_url") or "").strip()
    license_name = _PROVIDER_LICENSES.get(provider)
    if not provider or not filename or not page_url or not license_name:
        return None
    file_path = local_dir / filename
    if not file_path.exists() or file_path.stat().st_size <= 0:
        return None
    return {
        "file": str(file_path.resolve()),
        "source_url": page_url,
        "license": license_name,
        "commercial_use_allowed": True,
        "creator": str(info.get("creator") or ""),
        "provider": provider,
        "provider_id": info.get(f"{provider}_id"),
        "duration": float(info.get("duration") or 0.0),
        "vision_confidence": info.get("vision_confidence"),
        "vision_reason": info.get("vision_reason"),
        "source_width": int(info.get("width") or 0),
        "source_height": int(info.get("height") or 0),
    }


def _existing_audio_clips(
    source_manifest: Path,
    audit_path: Path,
    *,
    local_dir: Path,
    minimum_mean_db: float,
    aspect_tolerance: float,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    candidates: list[dict[str, Any]] = []
    rejected: list[dict[str, Any]] = []

    if source_manifest.exists():
        try:
            raw = json.loads(source_manifest.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            raw = {}
        for item in raw.get("clips", []):
            if isinstance(item, dict):
                candidates.append(dict(item))

    if audit_path.exists():
        try:
            audit = json.loads(audit_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            audit = {}
        for info in audit.get("materials", []):
            if not isinstance(info, dict):
                continue
            converted = _clip_from_cached_info(local_dir, info)
            if converted:
                candidates.append(converted)

    accepted: list[dict[str, Any]] = []
    seen: set[tuple[str, str]] = set()
    for item in candidates:
        identity = _clip_identity(item)
        if not identity[0] or not identity[1] or identity in seen:
            continue
        seen.add(identity)
        path = Path(str(item.get("file") or ""))
        if not path.is_absolute():
            path = (source_manifest.parent / path).resolve()
        if not path.exists():
            continue

        dimensions = video_dimensions(path)
        if dimensions is None or not is_short_portrait(*dimensions, tolerance=aspect_tolerance):
            rejected.append(
                {
                    "provider": item.get("provider"),
                    "provider_id": item.get("provider_id"),
                    "file": str(path),
                    "reason": "source is not vertical 9:16-ish footage",
                    "dimensions": list(dimensions) if dimensions else None,
                }
            )
            continue

        audible, mean_db = has_audible_audio(path, minimum_mean_db=minimum_mean_db)
        if not audible:
            rejected.append(
                {
                    "provider": item.get("provider"),
                    "provider_id": item.get("provider_id"),
                    "file": str(path),
                    "reason": "missing or effectively silent audio",
                    "mean_volume_db": mean_db,
                }
            )
            continue
        width, height = dimensions
        item["file"] = str(path)
        item["has_audio"] = True
        item["mean_volume_db"] = mean_db
        item["source_width"] = width
        item["source_height"] = height
        item["source_aspect_ratio"] = round(width / height, 6)
        accepted.append(item)
    return accepted, rejected


def _candidate_to_audio_clip(
    *,
    candidate: dict[str, Any],
    slot: int,
    anchor: str,
    local_dir: Path,
    client: httpx.Client,
    minimum_mean_db: float,
    aspect_tolerance: float,
) -> tuple[dict[str, Any] | None, dict[str, Any]]:
    file_info = candidate.get("file_info") or {}
    if not _file_info_is_short_portrait(file_info, tolerance=aspect_tolerance):
        return None, {
            "provider": candidate.get("provider"),
            "provider_id": candidate.get("id"),
            "reason": "candidate metadata is not vertical 9:16-ish footage",
            "dimensions": [int(file_info.get("width") or 0), int(file_info.get("height") or 0)],
        }

    remote_probe = has_audio_stream(str(file_info["link"]))
    if remote_probe is False:
        return None, {
            "provider": candidate.get("provider"),
            "provider_id": candidate.get("id"),
            "reason": "remote file has no audio stream",
        }

    material, source = _material_from_candidate(
        candidate=candidate,
        slot=slot,
        anchor=anchor,
        local_videos_dir=local_dir,
        download_client=client,
    )
    path = local_dir / str(material["url"])

    dimensions = video_dimensions(path)
    if dimensions is None or not is_short_portrait(*dimensions, tolerance=aspect_tolerance):
        return None, {
            "provider": candidate.get("provider"),
            "provider_id": candidate.get("id"),
            "file": str(path),
            "reason": "downloaded file is not vertical 9:16-ish footage",
            "dimensions": list(dimensions) if dimensions else None,
        }

    audible, mean_db = has_audible_audio(path, minimum_mean_db=minimum_mean_db)
    if not audible:
        return None, {
            "provider": candidate.get("provider"),
            "provider_id": candidate.get("id"),
            "file": str(path),
            "reason": "downloaded file is missing audible audio",
            "mean_volume_db": mean_db,
        }

    width, height = dimensions
    provider = str(candidate["provider"]).lower()
    clip = {
        "file": str(path.resolve()),
        "source_url": str(source.get("page_url") or ""),
        "license": _PROVIDER_LICENSES[provider],
        "commercial_use_allowed": True,
        "creator": str(source.get("creator") or ""),
        "provider": provider,
        "provider_id": source.get(f"{provider}_id"),
        "duration": float(source.get("duration") or candidate.get("duration") or 0.0),
        "vision_confidence": source.get("vision_confidence"),
        "vision_reason": source.get("vision_reason"),
        "has_audio": True,
        "mean_volume_db": mean_db,
        "source_width": width,
        "source_height": height,
        "source_aspect_ratio": round(width / height, 6),
    }
    return clip, {
        "provider": provider,
        "provider_id": clip["provider_id"],
        "file": str(path),
        "reason": "accepted audible vertical source",
        "mean_volume_db": mean_db,
        "dimensions": [width, height],
    }


def ensure_audio_animal_sources(
    settings: Settings,
    plan: dict[str, Any],
    *,
    slot: int,
    slot_dir: Path,
    source_manifest: Path,
    ledger: BudgetLedger,
) -> Path:
    """Ensure cat sources are licensed, visually relevant, audible and vertical."""
    animal_cfg = settings.raw.get("animal", {})
    materials_cfg = settings.raw.get("materials", {})
    target_count = int(animal_cfg.get("material_count", 6))
    min_unique = int(animal_cfg.get("min_unique_materials", 5))
    clip_seconds = int(float(animal_cfg.get("clip_seconds", 5)))
    minimum_mean_db = float(animal_cfg.get("min_source_mean_volume_db", -55.0))
    aspect_tolerance = float(animal_cfg.get("source_aspect_tolerance", 0.11))
    max_pexels = int(animal_cfg.get("audio_pexels_candidates", 60))
    max_pixabay = int(animal_cfg.get("audio_pixabay_candidates", 80))
    pexels_per_page = int(materials_cfg.get("pexels_per_page", 40))
    pixabay_per_page = int(materials_cfg.get("pixabay_per_page", 100))
    batch_size = max(1, int(materials_cfg.get("vision_batch_size", 10)))
    min_confidence = float(materials_cfg.get("vision_min_confidence", 0.72))
    anchor = infer_visual_anchor(plan)

    local_dir = Path(
        os.getenv(
            "MPT_LOCAL_VIDEOS_DIR",
            str(settings.root / "MoneyPrinterTurbo" / "storage" / "local_videos"),
        )
    ).resolve()
    local_dir.mkdir(parents=True, exist_ok=True)
    slot_dir.mkdir(parents=True, exist_ok=True)

    old_audit = slot_dir / "ai_materials.json"
    accepted, rejected = _existing_audio_clips(
        source_manifest,
        old_audit,
        local_dir=local_dir,
        minimum_mean_db=minimum_mean_db,
        aspect_tolerance=aspect_tolerance,
    )
    accepted = accepted[:target_count]
    seen = {_clip_identity(item) for item in accepted}

    raw_queries = [str(term).strip() for term in plan.get("search_terms", []) if str(term).strip()]
    anchored = [term if anchor in term.lower() else f"{anchor} {term}" for term in raw_queries]
    audio_queries = [
        f"{anchor} meowing",
        f"{anchor} purring",
        f"{anchor} playing",
        f"{anchor} interacting",
        anchor,
    ]
    queries = list(dict.fromkeys(anchored + audio_queries))

    stats: dict[str, Any] = {
        "reused_audio_sources": len(accepted),
        "minimum_mean_volume_db": minimum_mean_db,
        "target_aspect": "9:16",
        "source_aspect_tolerance": aspect_tolerance,
        "pexels": {"candidates": 0, "vision_reviewed": 0, "vision_approved": 0, "audio_accepted": 0},
        "pixabay": {"candidates": 0, "vision_reviewed": 0, "vision_approved": 0, "audio_accepted": 0},
    }

    def consume(provider: str, candidates: list[dict[str, Any]]) -> None:
        nonlocal accepted, rejected, seen
        if len(accepted) >= target_count or not candidates:
            return
        candidates = [
            candidate
            for candidate in candidates
            if (provider, str(candidate.get("id") or "")) not in seen
            and _file_info_is_short_portrait(candidate.get("file_info") or {}, tolerance=aspect_tolerance)
        ]
        if not candidates:
            return
        approved, decisions = _review_until_enough(
            settings=settings,
            ledger=ledger,
            anchor=anchor,
            candidates=candidates,
            slot=slot,
            batch_size=batch_size,
            minimum_confidence=min_confidence,
            # Audio presence is only knowable after probing/downloading, so review
            # the available vertical pool instead of stopping after the first six visuals.
            needed=len(candidates) + 1,
        )
        stats[provider]["candidates"] = len(candidates)
        stats[provider]["vision_reviewed"] = len(decisions)
        stats[provider]["vision_approved"] = len(approved)
        with httpx.Client(timeout=120, follow_redirects=True) as download_client:
            for candidate in approved:
                if len(accepted) >= target_count:
                    break
                identity = (provider, str(candidate.get("id") or ""))
                if identity in seen:
                    continue
                clip, audit_row = _candidate_to_audio_clip(
                    candidate=candidate,
                    slot=slot,
                    anchor=anchor,
                    local_dir=local_dir,
                    client=download_client,
                    minimum_mean_db=minimum_mean_db,
                    aspect_tolerance=aspect_tolerance,
                )
                rejected.append(audit_row) if clip is None else None
                seen.add(identity)
                if clip is None:
                    continue
                accepted.append(clip)
                stats[provider]["audio_accepted"] += 1

    if len(accepted) < target_count:
        pexels_key = os.getenv("PEXELS_API_KEY", "").strip()
        if not pexels_key:
            raise RuntimeError("PEXELS_API_KEY is not set; cannot search audible vertical cat stock")
        with httpx.Client(timeout=60, follow_redirects=True) as client:
            pexels_candidates = _collect_pexels_audio_candidates(
                client=client,
                api_key=pexels_key,
                queries=queries,
                per_page=pexels_per_page,
                max_candidates=max_pexels,
                clip_seconds=clip_seconds,
                anchor=anchor,
                aspect_tolerance=aspect_tolerance,
            )
        consume("pexels", pexels_candidates)

    if len(accepted) < target_count:
        pixabay_key = os.getenv("PIXABAY_API_KEY", "").strip()
        if pixabay_key:
            with httpx.Client(timeout=60, follow_redirects=True) as client:
                pixabay_candidates = _collect_pixabay_candidates(
                    client=client,
                    api_key=pixabay_key,
                    queries=queries,
                    per_page=pixabay_per_page,
                    max_candidates=max_pixabay,
                    clip_seconds=clip_seconds,
                    anchor=anchor,
                )
            consume("pixabay", pixabay_candidates)

    audit_path = slot_dir / "animal_audio_sources.json"
    audit = {
        "version": 2,
        "slot": slot,
        "visual_anchor": anchor,
        "required_minimum": min_unique,
        "target": target_count,
        "selected": len(accepted),
        "queries": queries,
        "target_aspect": "9:16",
        "source_aspect_tolerance": aspect_tolerance,
        "stats": stats,
        "rejected_or_tested": rejected,
        "selected_sources": accepted,
    }
    audit_path.write_text(json.dumps(audit, ensure_ascii=False, indent=2), encoding="utf-8")

    if len(accepted) < min_unique:
        raise RuntimeError(
            f"Vertical audible-source gate found only {len(accepted)}/{min_unique} usable cat clips. "
            f"See {audit_path}. Refusing landscape/non-9:16-ish or effectively silent footage."
        )

    selected = accepted[:target_count]
    source_manifest.write_text(
        json.dumps(
            {
                "source_policy": "vision-approved licensed vertical stock with audible source audio",
                "require_audible_audio": True,
                "require_vertical_short_source": True,
                "target_aspect": "9:16",
                "source_aspect_tolerance": aspect_tolerance,
                "minimum_mean_volume_db": minimum_mean_db,
                "clips": selected,
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    return source_manifest
