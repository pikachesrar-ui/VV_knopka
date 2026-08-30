from __future__ import annotations

import json
from pathlib import Path
from typing import Any
from urllib.parse import quote

import httpx

from . import animal_audio_sources as _base
from .animal_audio_sources_v2 import _normalize_source_policy, sanitize_unapproved_youtube_sources
from .animal_audio_sources_v3 import (
    _append_history_audit,
    _remove_prior_from_cached_materials,
    _remove_prior_from_manifest,
)
from .budget import BudgetLedger
from .pexels_curator import _text_matches_anchor, choose_pixabay_file
from .settings import Settings
from .source_history import prior_rendered_cat_identities


_EXTRA_CAT_QUERIES = (
    "cat",
    "kitten",
    "cute cat",
    "funny cat",
    "cat playing",
    "kitten playing",
    "cat meowing",
    "cat purring",
    "house cat",
    "pet cat",
)


def _expanded_queries(queries: list[str]) -> list[str]:
    values = [str(value).strip() for value in queries if str(value).strip()]
    values.extend(_EXTRA_CAT_QUERIES)
    return list(dict.fromkeys(values))


def _deep_pexels_collector(
    *,
    prior: set[tuple[str, str]],
    pages_per_query: int = 4,
):
    def collect(
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
        candidates: list[dict[str, Any]] = []
        seen_ids: set[int] = set()
        page_size = max(1, min(int(per_page), 80))

        for query in _expanded_queries(queries):
            for page in range(1, max(int(pages_per_query), 1) + 1):
                response = client.get(
                    "https://api.pexels.com/videos/search",
                    headers={"Authorization": api_key},
                    params={
                        "query": query,
                        "orientation": "portrait",
                        "per_page": page_size,
                        "page": page,
                    },
                )
                response.raise_for_status()
                videos = list((response.json()).get("videos") or [])
                if not videos:
                    break

                for video in videos:
                    video_id = int(video.get("id") or 0)
                    identity = ("pexels", str(video_id))
                    if not video_id or video_id in seen_ids or identity in prior:
                        continue
                    seen_ids.add(video_id)
                    duration = float(video.get("duration") or 0)
                    if duration < clip_seconds:
                        continue
                    file_info = _base.choose_pexels_file(video)
                    thumbnail_url = str(video.get("image") or "").strip()
                    if (
                        not file_info
                        or not thumbnail_url
                        or not _base._file_info_is_short_portrait(
                            file_info,
                            tolerance=aspect_tolerance,
                        )
                    ):
                        continue
                    page_url = str(video.get("url") or "")
                    creator = video.get("user") or {}
                    candidates.append(
                        {
                            "provider": "pexels",
                            "id": video_id,
                            "query": query,
                            "search_page": page,
                            "page_url": page_url,
                            "thumbnail_url": thumbnail_url,
                            "duration": duration,
                            "creator": creator.get("name"),
                            "creator_url": creator.get("url"),
                            "file_info": file_info,
                            "metadata_mentions_anchor": _base.pexels_page_matches_anchor(page_url, anchor),
                        }
                    )
                    if len(candidates) >= max(int(max_candidates), 1):
                        return candidates
        return candidates

    return collect


def _deep_pixabay_collector(
    *,
    prior: set[tuple[str, str]],
    pages_per_query: int = 4,
):
    def collect(
        *,
        client: httpx.Client,
        api_key: str,
        queries: list[str],
        per_page: int,
        max_candidates: int,
        clip_seconds: int,
        anchor: str,
    ) -> list[dict[str, Any]]:
        candidates: list[dict[str, Any]] = []
        seen_ids: set[int] = set()
        page_size = max(3, min(int(per_page), 200))

        for query in _expanded_queries(queries):
            for page in range(1, max(int(pages_per_query), 1) + 1):
                response = client.get(
                    "https://pixabay.com/api/videos/",
                    params={
                        "key": api_key,
                        "q": query,
                        "category": "animals",
                        "safesearch": "true",
                        "order": "popular",
                        "per_page": page_size,
                        "page": page,
                    },
                )
                response.raise_for_status()
                videos = list((response.json()).get("hits") or [])
                if not videos:
                    break

                for video in videos:
                    video_id = int(video.get("id") or 0)
                    identity = ("pixabay", str(video_id))
                    if not video_id or video_id in seen_ids or identity in prior:
                        continue
                    seen_ids.add(video_id)
                    duration = float(video.get("duration") or 0)
                    if duration < clip_seconds:
                        continue
                    # Pixabay helpers live in pexels_curator; the base animal
                    # module intentionally imports only the shared collector.
                    file_info = choose_pixabay_file(video)
                    thumbnail_url = str((file_info or {}).get("thumbnail") or "").strip()
                    if not file_info or not thumbnail_url:
                        continue
                    user = str(video.get("user") or "").strip()
                    user_id = int(video.get("user_id") or 0)
                    creator_url = (
                        f"https://pixabay.com/users/{quote(user)}-{user_id}/"
                        if user and user_id
                        else None
                    )
                    tags = str(video.get("tags") or "")
                    candidates.append(
                        {
                            "provider": "pixabay",
                            "id": video_id,
                            "query": query,
                            "search_page": page,
                            "page_url": str(video.get("pageURL") or ""),
                            "thumbnail_url": thumbnail_url,
                            "duration": duration,
                            "creator": user or None,
                            "creator_url": creator_url,
                            "tags": tags,
                            "file_info": file_info,
                            "metadata_mentions_anchor": _text_matches_anchor(tags, anchor),
                        }
                    )
                    if len(candidates) >= max(int(max_candidates), 1):
                        return candidates
        return candidates

    return collect


def _append_deep_search_audit(slot_dir: Path) -> None:
    audit_path = slot_dir / "animal_audio_sources.json"
    if not audit_path.exists():
        return
    try:
        raw = json.loads(audit_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return
    raw["deep_stock_search"] = {
        "enabled": True,
        "pages_per_query": 4,
        "extra_queries": list(_EXTRA_CAT_QUERIES),
        "policy": "exclude prior rendered source IDs while collecting, then paginate until the fresh candidate cap is filled",
    }
    audit_path.write_text(json.dumps(raw, ensure_ascii=False, indent=2), encoding="utf-8")


def ensure_audio_animal_sources(
    settings: Settings,
    plan: dict[str, Any],
    *,
    slot: int,
    slot_dir: Path,
    source_manifest: Path,
    ledger: BudgetLedger,
) -> Path:
    """History-aware cat sourcing with pagination beyond repeated popular stock results."""
    prior = prior_rendered_cat_identities(settings, before_slot=slot)

    removed: list[dict[str, Any]] = []
    removed.extend(sanitize_unapproved_youtube_sources(source_manifest))
    removed.extend(_remove_prior_from_manifest(source_manifest, prior))
    removed.extend(_remove_prior_from_cached_materials(slot_dir / "ai_materials.json", prior))

    original_pexels = _base._collect_pexels_audio_candidates
    original_pixabay = _base._collect_pixabay_candidates
    _base._collect_pexels_audio_candidates = _deep_pexels_collector(prior=prior)
    _base._collect_pixabay_candidates = _deep_pixabay_collector(prior=prior)

    try:
        result = _base.ensure_audio_animal_sources(
            settings,
            plan,
            slot=slot,
            slot_dir=slot_dir,
            source_manifest=source_manifest,
            ledger=ledger,
        )
    finally:
        _base._collect_pexels_audio_candidates = original_pexels
        _base._collect_pixabay_candidates = original_pixabay

    _append_history_audit(slot_dir, prior_count=len(prior), removed=removed)
    _append_deep_search_audit(slot_dir)
    _normalize_source_policy(result)
    return result
