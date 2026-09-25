from __future__ import annotations

import html
import json
import os
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import unquote, urlparse

import httpx

from . import animal_audio_sources as _base
from . import animal_audio_sources_v6 as _v6
from .budget import BudgetLedger
from .cat_source_candidates import ensure_candidate_queue
from .pexels_curator import _download, _review_until_enough, infer_visual_anchor
from .settings import Settings
from .source_history import blocked_cat_source_identities
from .stock_network import get_stock
from .trend_import import _ffprobe_duration, _sha256, write_attribution_report


_MINIMUM_GATE_TEXT = "Vertical audible-source gate found only"
_WIKIMEDIA_API = "https://commons.wikimedia.org/w/api.php"
_VIDEO_SUFFIXES = {".mp4", ".webm", ".ogv", ".ogg", ".mov", ".m4v"}


def _read_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return raw if isinstance(raw, dict) else {}


def _plain(value: Any) -> str:
    text = html.unescape(str(value or ""))
    text = re.sub(r"<[^>]+>", " ", text)
    return " ".join(text.split()).strip()


def _ext_value(metadata: dict[str, Any], key: str) -> str:
    item = metadata.get(key) or {}
    if isinstance(item, dict):
        return _plain(item.get("value"))
    return _plain(item)


def _license_policy(name: str, url: str = "") -> dict[str, Any] | None:
    text = f"{name} {url}".casefold().replace("_", " ")
    if "public domain" in text or "publicdomain" in text:
        return {"canonical": "Public Domain", "attribution_required": False}
    if "cc0" in text or "creativecommons.org/publicdomain/zero" in text:
        return {"canonical": "CC0 1.0", "attribution_required": False}
    if any(
        marker in text
        for marker in (
            "noncommercial",
            "non-commercial",
            "no derivatives",
            "no-derivatives",
            "by-nc",
            "by-nd",
            "/by-nc/",
            "/by-nd/",
        )
    ):
        return None
    if "by-sa" in text or "share alike" in text or "/by-sa/" in text:
        return None
    if "cc by 4.0" in text or "attribution 4.0" in text or "/by/4.0" in text:
        return {"canonical": "CC BY 4.0", "attribution_required": True}
    if "cc by 3.0" in text or "attribution 3.0" in text or "/by/3.0" in text:
        return {"canonical": "CC BY 3.0", "attribution_required": True}
    return None


def _attribution_text(
    *,
    title: str,
    creator: str,
    source_url: str,
    license_name: str,
    license_url: str,
) -> str:
    author = creator or "Wikimedia Commons contributor"
    parts = [f'"{title or "Untitled source"}" by {author}', source_url, license_name]
    if license_url:
        parts.append(license_url)
    parts.append("Changes: excerpted, captioned, and audio-mixed for this Short")
    return " — ".join(part for part in parts if part)


def _library_manifest_path(settings: Settings) -> Path:
    configured = str(
        settings.raw.get("source_fallback", {}).get(
            "local_library_manifest",
            "runtime/licensed_sources/cats/manifest.json",
        )
    ).strip()
    path = Path(configured)
    return path if path.is_absolute() else (settings.root / path).resolve()


def _merge_clips(source_manifest: Path, clips: list[dict[str, Any]]) -> None:
    raw = _read_json(source_manifest)
    existing = [item for item in (raw.get("clips") or []) if isinstance(item, dict)]
    seen = {_base._clip_identity(item) for item in existing}
    hashes = {str(item.get("source_sha256") or "") for item in existing if item.get("source_sha256")}
    for clip in clips:
        identity = _base._clip_identity(clip)
        digest = str(clip.get("source_sha256") or "")
        if identity in seen or (digest and digest in hashes):
            continue
        existing.append(dict(clip))
        seen.add(identity)
        if digest:
            hashes.add(digest)
    raw.update(
        {
            "source_policy": "licensed stock plus verified local/Wikimedia fallbacks",
            "require_audible_audio": True,
            "require_vertical_short_source": True,
            "clips": existing,
        }
    )
    source_manifest.parent.mkdir(parents=True, exist_ok=True)
    source_manifest.write_text(json.dumps(raw, ensure_ascii=False, indent=2), encoding="utf-8")


def seed_local_library(
    settings: Settings,
    *,
    slot: int,
    source_manifest: Path,
) -> dict[str, Any]:
    cfg = settings.raw.get("source_fallback", {})
    manifest_path = _library_manifest_path(settings)
    result: dict[str, Any] = {
        "enabled": bool(cfg.get("local_library_enabled", True)),
        "manifest": str(manifest_path),
        "seen": 0,
        "accepted": 0,
        "rejected": [],
    }
    if not result["enabled"] or not manifest_path.exists():
        result["status"] = "disabled" if not result["enabled"] else "manifest_not_found"
        return result

    raw = _read_json(manifest_path)
    entries = raw.get("clips") or []
    if not isinstance(entries, list):
        result["status"] = "invalid_manifest"
        return result

    animal_cfg = settings.raw.get("animal", {})
    minimum_mean_db = float(animal_cfg.get("min_source_mean_volume_db", -55.0))
    aspect_tolerance = float(animal_cfg.get("source_aspect_tolerance", 0.08))
    minimum_seconds = float(animal_cfg.get("clip_seconds", 5.0))
    max_sources = max(int(cfg.get("local_library_max_sources", 6)), 0)
    protected = blocked_cat_source_identities(settings, before_slot=slot)
    accepted: list[dict[str, Any]] = []

    for index, item in enumerate(entries, 1):
        if len(accepted) >= max_sources:
            break
        if not isinstance(item, dict):
            continue
        result["seen"] += 1
        entry_id = str(item.get("id") or f"entry-{index}").strip()
        rejection: dict[str, Any] = {"id": entry_id}
        file_value = str(item.get("file") or "").strip()
        path = Path(file_value)
        if not path.is_absolute():
            path = (manifest_path.parent / path).resolve()
        license_name = str(item.get("license") or "").strip()
        license_url = str(item.get("license_url") or "").strip()
        policy = _license_policy(license_name, license_url)
        if item.get("commercial_use_allowed") is not True or item.get("human_approved") is not True:
            rejection["reason"] = "commercial_use_allowed=true and human_approved=true are required"
        elif policy is None:
            rejection["reason"] = "license is not in the Public Domain/CC0/CC BY 3.0/4.0 allowlist"
        elif not path.exists() or not path.is_file() or path.stat().st_size <= 0:
            rejection["reason"] = "local media file is missing or empty"
        else:
            dimensions = _base.video_dimensions(path)
            audible, mean_db = _base.has_audible_audio(path, minimum_mean_db=minimum_mean_db)
            duration = _ffprobe_duration(path)
            creator = str(item.get("creator") or "").strip()
            source_url = str(item.get("source_url") or "").strip()
            if dimensions is None or not _base.is_short_portrait(*dimensions, tolerance=aspect_tolerance):
                rejection["reason"] = "source is not vertical 9:16-ish footage"
            elif not audible:
                rejection["reason"] = "source has no audible audio"
            elif duration < minimum_seconds:
                rejection["reason"] = f"source is shorter than {minimum_seconds:.1f}s"
            elif policy["attribution_required"] and (not creator or not source_url):
                rejection["reason"] = "CC BY sources require creator and source_url"
            else:
                digest = _sha256(path)
                # The content hash is the durable identity. A user-editable label
                # must not let the same bytes bypass cross-episode cooldown/reuse.
                provider_id = digest
                identity = ("local_licensed", provider_id)
                if identity in protected:
                    rejection["reason"] = "source is inside the active cat-episode cooldown"
                else:
                    width, height = dimensions
                    canonical = str(policy["canonical"])
                    title = str(item.get("title") or path.stem).strip()
                    accepted.append(
                        {
                            "file": str(path.resolve()),
                            "source_url": source_url,
                            "source_title": title,
                            "license": canonical,
                            "license_url": license_url,
                            "commercial_use_allowed": True,
                            "creator": creator,
                            "creator_url": str(item.get("creator_url") or "").strip(),
                            "provider": "local_licensed",
                            "provider_id": provider_id,
                            "library_id": entry_id,
                            "duration": duration,
                            "has_audio": True,
                            "mean_volume_db": mean_db,
                            "source_width": width,
                            "source_height": height,
                            "source_aspect_ratio": round(width / height, 6),
                            "source_sha256": digest,
                            "rights_status": "allowlisted_license_and_human_approved",
                            "human_approved": True,
                            "attribution_required": bool(policy["attribution_required"]),
                            "attribution_text": _attribution_text(
                                title=title,
                                creator=creator,
                                source_url=source_url,
                                license_name=canonical,
                                license_url=license_url,
                            ),
                        }
                    )
        if rejection.get("reason"):
            result["rejected"].append(rejection)

    if accepted:
        _merge_clips(source_manifest, accepted)
    result["accepted"] = len(accepted)
    result["status"] = "loaded"
    return result


def _wikimedia_queries(settings: Settings) -> list[str]:
    raw = settings.raw.get("source_fallback", {}).get(
        "wikimedia_queries",
        ["cat", "kitten", "domestic cat", "cat playing"],
    )
    values = [str(value).strip() for value in raw if str(value).strip()]
    return list(dict.fromkeys(values))


def discover_wikimedia_candidates(
    settings: Settings,
    *,
    protected: set[tuple[str, str]],
    client: httpx.Client,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    cfg = settings.raw.get("source_fallback", {})
    animal_cfg = settings.raw.get("animal", {})
    per_query = max(1, min(int(cfg.get("wikimedia_per_query", 25)), 50))
    max_candidates = max(1, min(int(cfg.get("wikimedia_max_candidates", 16)), 40))
    max_bytes = max(int(cfg.get("wikimedia_max_file_mb", 80)), 1) * 1024 * 1024
    tolerance = float(animal_cfg.get("source_aspect_tolerance", 0.08))
    found: list[dict[str, Any]] = []
    seen: set[int] = set()
    stats: dict[str, Any] = {"queries": {}, "license_rejected": 0, "format_rejected": 0}

    for query in _wikimedia_queries(settings):
        response = get_stock(
            client,
            _WIKIMEDIA_API,
            params={
                "action": "query",
                "generator": "search",
                "gsrsearch": f"{query} filetype:video",
                "gsrnamespace": 6,
                "gsrlimit": per_query,
                "prop": "imageinfo",
                "iiprop": "url|mime|size|mediatype|extmetadata",
                "iiurlwidth": 360,
                "format": "json",
                "formatversion": 2,
                "origin": "*",
            },
            headers={"User-Agent": "VV-Knopka/0.1 (licensed cat video discovery)"},
        )
        pages = list((response.json().get("query") or {}).get("pages") or [])
        accepted_for_query = 0
        for page in pages:
            page_id = int(page.get("pageid") or 0)
            if not page_id or page_id in seen or ("wikimedia", str(page_id)) in protected:
                continue
            seen.add(page_id)
            info = ((page.get("imageinfo") or [{}])[0]) or {}
            mime = str(info.get("mime") or "").lower()
            media_type = str(info.get("mediatype") or "").upper()
            if not (mime.startswith("video/") or media_type == "VIDEO"):
                continue
            width, height = int(info.get("width") or 0), int(info.get("height") or 0)
            size = int(info.get("size") or 0)
            thumb = str(info.get("thumburl") or "").strip()
            source_file = str(info.get("url") or "").strip()
            if (
                not source_file
                or not thumb
                or size <= 0
                or size > max_bytes
                or not _base.is_short_portrait(width, height, tolerance=tolerance)
            ):
                stats["format_rejected"] += 1
                continue
            metadata = info.get("extmetadata") or {}
            license_name = _ext_value(metadata, "LicenseShortName") or _ext_value(metadata, "UsageTerms")
            license_url = _ext_value(metadata, "LicenseUrl")
            policy = _license_policy(license_name, license_url)
            if policy is None:
                stats["license_rejected"] += 1
                continue
            title = str(page.get("title") or "").removeprefix("File:")
            creator = _ext_value(metadata, "Artist") or _ext_value(metadata, "Credit")
            page_url = str(info.get("descriptionurl") or "").strip()
            if policy["attribution_required"] and (not creator or not page_url or not license_url):
                stats["license_rejected"] += 1
                continue
            found.append(
                {
                    "provider": "wikimedia",
                    "id": page_id,
                    "query": query,
                    "page_url": page_url,
                    "file_url": source_file,
                    "thumbnail_url": thumb,
                    "title": title,
                    "creator": creator,
                    "license": str(policy["canonical"]),
                    "license_url": license_url,
                    "attribution_required": bool(policy["attribution_required"]),
                    "size_bytes": size,
                    "width": width,
                    "height": height,
                    "metadata_mentions_anchor": "cat" in title.casefold() or "kitten" in title.casefold(),
                }
            )
            accepted_for_query += 1
            if len(found) >= max_candidates:
                break
        stats["queries"][query] = {"returned": len(pages), "eligible": accepted_for_query}
        if len(found) >= max_candidates:
            break
    stats["eligible_candidates"] = len(found)
    return found, stats


def _source_suffix(url: str) -> str:
    suffix = Path(unquote(urlparse(url).path)).suffix.lower()
    return suffix if suffix in _VIDEO_SUFFIXES else ".webm"


def _download_wikimedia_clip(
    settings: Settings,
    *,
    candidate: dict[str, Any],
    client: httpx.Client,
) -> tuple[dict[str, Any] | None, dict[str, Any]]:
    animal_cfg = settings.raw.get("animal", {})
    minimum_mean_db = float(animal_cfg.get("min_source_mean_volume_db", -55.0))
    minimum_seconds = float(animal_cfg.get("clip_seconds", 5.0))
    tolerance = float(animal_cfg.get("source_aspect_tolerance", 0.08))
    cache = settings.runtime_dir / "licensed_sources" / "cache" / "wikimedia"
    cache.mkdir(parents=True, exist_ok=True)
    destination = cache / f"wikimedia-{int(candidate['id'])}{_source_suffix(str(candidate['file_url']))}"
    _download(client, str(candidate["file_url"]), destination)

    dimensions = _base.video_dimensions(destination)
    audible, mean_db = _base.has_audible_audio(destination, minimum_mean_db=minimum_mean_db)
    duration = _ffprobe_duration(destination)
    audit = {
        "provider_id": str(candidate["id"]),
        "file": str(destination),
        "dimensions": list(dimensions) if dimensions else None,
        "mean_volume_db": mean_db,
        "duration": duration,
    }
    if dimensions is None or not _base.is_short_portrait(*dimensions, tolerance=tolerance):
        audit["reason"] = "downloaded Wikimedia file is not vertical 9:16-ish footage"
        return None, audit
    if not audible:
        audit["reason"] = "downloaded Wikimedia file has no audible source audio"
        return None, audit
    if duration < minimum_seconds:
        audit["reason"] = f"downloaded Wikimedia file is shorter than {minimum_seconds:.1f}s"
        return None, audit

    width, height = dimensions
    title = str(candidate.get("title") or "Wikimedia source")
    creator = str(candidate.get("creator") or "")
    source_url = str(candidate.get("page_url") or "")
    license_name = str(candidate.get("license") or "")
    license_url = str(candidate.get("license_url") or "")
    clip = {
        "file": str(destination.resolve()),
        "source_url": source_url,
        "source_title": title,
        "license": license_name,
        "license_url": license_url,
        "commercial_use_allowed": True,
        "creator": creator,
        "provider": "wikimedia",
        "provider_id": str(candidate["id"]),
        "duration": duration,
        "vision_confidence": candidate.get("vision_confidence"),
        "vision_reason": candidate.get("vision_reason"),
        "has_audio": True,
        "mean_volume_db": mean_db,
        "source_width": width,
        "source_height": height,
        "source_aspect_ratio": round(width / height, 6),
        "source_sha256": _sha256(destination),
        "rights_status": "wikimedia_allowlisted_license",
        "attribution_required": bool(candidate.get("attribution_required")),
        "attribution_text": _attribution_text(
            title=title,
            creator=creator,
            source_url=source_url,
            license_name=license_name,
            license_url=license_url,
        ),
    }
    audit["reason"] = "accepted licensed audible vertical Wikimedia source"
    return clip, audit


def _validated_manifest_clips(
    settings: Settings,
    *,
    slot_dir: Path,
    source_manifest: Path,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    animal_cfg = settings.raw.get("animal", {})
    local_dir = Path(
        os.getenv(
            "MPT_LOCAL_VIDEOS_DIR",
            str(settings.root / "MoneyPrinterTurbo" / "storage" / "local_videos"),
        )
    ).resolve()
    return _base._existing_audio_clips(
        source_manifest,
        slot_dir / "ai_materials.json",
        local_dir=local_dir,
        minimum_mean_db=float(animal_cfg.get("min_source_mean_volume_db", -55.0)),
        aspect_tolerance=float(animal_cfg.get("source_aspect_tolerance", 0.08)),
    )


def try_wikimedia_fallback(
    settings: Settings,
    plan: dict[str, Any],
    *,
    slot: int,
    slot_dir: Path,
    source_manifest: Path,
    ledger: BudgetLedger,
) -> tuple[Path | None, dict[str, Any]]:
    cfg = settings.raw.get("source_fallback", {})
    result: dict[str, Any] = {
        "enabled": bool(cfg.get("wikimedia_enabled", True)),
        "selected": 0,
        "downloaded": [],
    }
    if not result["enabled"]:
        result["status"] = "disabled"
        return None, result

    animal_cfg = settings.raw.get("animal", {})
    materials_cfg = settings.raw.get("materials", {})
    target_count = max(int(animal_cfg.get("material_count", 6)), 1)
    minimum_unique = max(int(animal_cfg.get("min_unique_materials", 5)), 1)
    existing, existing_rejected = _validated_manifest_clips(
        settings,
        slot_dir=slot_dir,
        source_manifest=source_manifest,
    )
    result["existing_accepted"] = len(existing)
    result["existing_rejected"] = existing_rejected
    if len(existing) >= minimum_unique:
        selected = existing[:target_count]
        _merge_clips(source_manifest, selected)
        result["status"] = "already_sufficient"
        result["selected"] = len(selected)
        return source_manifest, result

    protected = blocked_cat_source_identities(settings, before_slot=slot)
    with httpx.Client(timeout=60, follow_redirects=True) as client:
        candidates, discovery = discover_wikimedia_candidates(
            settings,
            protected=protected,
            client=client,
        )
    result["discovery"] = discovery
    if not candidates:
        result["status"] = "no_eligible_candidates"
        return None, result

    needed = max(minimum_unique - len(existing), 1)
    approved, decisions = _review_until_enough(
        settings=settings,
        ledger=ledger,
        anchor=infer_visual_anchor(plan),
        candidates=candidates,
        slot=slot,
        batch_size=max(1, int(cfg.get("wikimedia_vision_batch_size", materials_cfg.get("vision_batch_size", 10)))),
        minimum_confidence=float(materials_cfg.get("vision_min_confidence", 0.72)),
        # Audio can be measured only after download, so review the bounded pool.
        needed=len(candidates) + 1,
    )
    result["vision_reviewed"] = len(decisions)
    result["vision_approved"] = len(approved)
    new_clips: list[dict[str, Any]] = []
    with httpx.Client(timeout=180, follow_redirects=True) as client:
        for candidate in approved:
            if len(new_clips) >= needed:
                break
            clip, audit = _download_wikimedia_clip(settings, candidate=candidate, client=client)
            result["downloaded"].append(audit)
            if clip is not None:
                new_clips.append(clip)

    if new_clips:
        _merge_clips(source_manifest, new_clips)
    accepted, rejected = _validated_manifest_clips(
        settings,
        slot_dir=slot_dir,
        source_manifest=source_manifest,
    )
    result["post_validation_rejected"] = rejected
    result["selected"] = len(accepted)
    if len(accepted) < minimum_unique:
        result["status"] = "insufficient_after_validation"
        return None, result

    selected = accepted[:target_count]
    source_manifest.write_text(
        json.dumps(
            {
                "source_policy": "licensed stock plus verified local/Wikimedia fallbacks",
                "require_audible_audio": True,
                "require_vertical_short_source": True,
                "target_aspect": "9:16",
                "source_aspect_tolerance": float(animal_cfg.get("source_aspect_tolerance", 0.08)),
                "minimum_mean_volume_db": float(animal_cfg.get("min_source_mean_volume_db", -55.0)),
                "clips": selected,
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    write_attribution_report(slot_dir, source_manifest)
    result["status"] = "sufficient"
    result["selected"] = len(selected)
    return source_manifest, result


def _write_fallback_audit(slot_dir: Path, payload: dict[str, Any]) -> Path:
    output = slot_dir / "cat_source_fallback.json"
    existing = _read_json(output)
    existing.update(payload)
    existing["version"] = 1
    existing["updated_at"] = datetime.now(timezone.utc).isoformat()
    output.write_text(json.dumps(existing, ensure_ascii=False, indent=2), encoding="utf-8")
    return output


def _finalize_provenance(source_manifest: Path) -> None:
    if not source_manifest.exists():
        return
    raw = _read_json(source_manifest)
    providers = {
        str(item.get("provider") or "").strip().lower()
        for item in (raw.get("clips") or [])
        if isinstance(item, dict)
    }
    if providers & {"local_licensed", "wikimedia"}:
        raw["source_policy"] = "licensed stock plus verified local/Wikimedia fallbacks"
        raw["require_license_provenance"] = True
        source_manifest.write_text(json.dumps(raw, ensure_ascii=False, indent=2), encoding="utf-8")
    write_attribution_report(source_manifest.parent, source_manifest)


def ensure_audio_animal_sources(
    settings: Settings,
    plan: dict[str, Any],
    *,
    slot: int,
    slot_dir: Path,
    source_manifest: Path,
    ledger: BudgetLedger,
) -> Path:
    """v6 stock policy plus local/Wikimedia sources and a no-download YouTube queue."""
    local_audit = seed_local_library(
        settings,
        slot=slot,
        source_manifest=source_manifest,
    )
    try:
        result = _v6.ensure_audio_animal_sources(
            settings,
            plan,
            slot=slot,
            slot_dir=slot_dir,
            source_manifest=source_manifest,
            ledger=ledger,
        )
        _write_fallback_audit(
            slot_dir,
            {
                "slot": int(slot),
                "local_library": local_audit,
                "wikimedia": {"status": "not_needed"},
                "youtube_queue": {"status": "not_needed"},
            },
        )
        _finalize_provenance(result)
        return result
    except RuntimeError as exc:
        if _MINIMUM_GATE_TEXT not in str(exc):
            raise
        stock_error = str(exc)

    wikimedia_result, wikimedia_audit = try_wikimedia_fallback(
        settings,
        plan,
        slot=slot,
        slot_dir=slot_dir,
        source_manifest=source_manifest,
        ledger=ledger,
    )
    if wikimedia_result is not None:
        _write_fallback_audit(
            slot_dir,
            {
                "slot": int(slot),
                "local_library": local_audit,
                "wikimedia": wikimedia_audit,
                "youtube_queue": {"status": "not_needed"},
            },
        )
        _finalize_provenance(wikimedia_result)
        return wikimedia_result

    queue_path = ensure_candidate_queue(
        settings,
        slot=slot,
        reason=stock_error,
    )
    queue = _read_json(queue_path)
    audit_path = _write_fallback_audit(
        slot_dir,
        {
            "slot": int(slot),
            "local_library": local_audit,
            "wikimedia": wikimedia_audit,
            "youtube_queue": {
                "status": queue.get("status"),
                "path": str(queue_path),
                "candidate_count": len(queue.get("candidates") or []),
                "auto_download": False,
                "auto_publish": False,
            },
        },
    )
    raise RuntimeError(
        f"{stock_error} Local licensed library and Wikimedia fallback were insufficient. "
        f"Manual-review YouTube candidate queue: {queue_path}. Fallback audit: {audit_path}."
    )
