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
from .source_history import (
    blocked_cat_source_identities,
    cat_source_cooldown_episodes,
    prior_rendered_cat_identities,
)


_EXTRA_CAT_QUERIES = (
    "cat",
    "kitten",
    "cute cat",
    "funny cat",
    "cat playing",
    "kitten playing",
    "cat meowing",
    "cat purring",
    "cat eating",
    "cat grooming",
    "cat walking",
    "cat jumping",
    "cat at home",
    "kitten at home",
    "house cat",
    "indoor cat",
    "domestic cat",
    "pet cat",
)


def _expanded_queries(queries: list[str]) -> list[str]:
    values = [str(value).strip() for value in queries if str(value).strip()]
    values.extend(_EXTRA_CAT_QUERIES)
    return list(dict.fromkeys(values))


def _audio_probe_state(file_info: dict[str, Any]) -> bool | None:
    link = str(file_info.get("link") or "").strip()
    if not link:
        return False
    # This is intentionally before Luna. Confirmed-silent files must not consume
    # the finite visual-review pool. Probe failures remain eligible as unknown so
    # transient network/ffprobe issues do not become false permanent rejects.
    return _base.has_audio_stream(link, timeout=8.0)


def _finish_fresh_first(
    fresh_confirmed: list[dict[str, Any]],
    fresh_unknown: list[dict[str, Any]],
    cooled_confirmed: list[dict[str, Any]],
    cooled_unknown: list[dict[str, Any]],
    *,
    max_candidates: int,
) -> list[dict[str, Any]]:
    """Prefer never-used stock; only then use sources outside the cooldown window."""
    cap = max(int(max_candidates), 1)
    return (fresh_confirmed + fresh_unknown + cooled_confirmed + cooled_unknown)[:cap]


def _deep_pexels_collector(
    *,
    prior: set[tuple[str, str]],
    all_prior: set[tuple[str, str]] | None = None,
    pages_per_query: int = 4,
):
    blocked = set(prior)
    historical = set(all_prior) if all_prior is not None else set(prior)

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
        fresh_confirmed: list[dict[str, Any]] = []
        fresh_unknown: list[dict[str, Any]] = []
        cooled_confirmed: list[dict[str, Any]] = []
        cooled_unknown: list[dict[str, Any]] = []
        seen_ids: set[int] = set()
        page_size = max(1, min(int(per_page), 80))
        cap = max(int(max_candidates), 1)

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
                    if not video_id or video_id in seen_ids or identity in blocked:
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
                    audio_state = _audio_probe_state(file_info)
                    if audio_state is False:
                        continue
                    page_url = str(video.get("url") or "")
                    creator = video.get("user") or {}
                    candidate = {
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
                        "remote_audio_probe": "confirmed" if audio_state is True else "unknown",
                        "metadata_mentions_anchor": _base.pexels_page_matches_anchor(page_url, anchor),
                        "cooled_down_reuse": identity in historical,
                    }
                    if identity in historical:
                        (cooled_confirmed if audio_state is True else cooled_unknown).append(candidate)
                    else:
                        (fresh_confirmed if audio_state is True else fresh_unknown).append(candidate)
                    # A full cap of confirmed never-used sources is ideal; there is
                    # no reason to keep walking the remote catalog after that.
                    if len(fresh_confirmed) >= cap:
                        return fresh_confirmed[:cap]
        return _finish_fresh_first(
            fresh_confirmed,
            fresh_unknown,
            cooled_confirmed,
            cooled_unknown,
            max_candidates=cap,
        )

    return collect


def _deep_pixabay_collector(
    *,
    prior: set[tuple[str, str]],
    all_prior: set[tuple[str, str]] | None = None,
    pages_per_query: int = 4,
):
    blocked = set(prior)
    historical = set(all_prior) if all_prior is not None else set(prior)

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
        fresh_confirmed: list[dict[str, Any]] = []
        fresh_unknown: list[dict[str, Any]] = []
        cooled_confirmed: list[dict[str, Any]] = []
        cooled_unknown: list[dict[str, Any]] = []
        seen_ids: set[int] = set()
        page_size = max(3, min(int(per_page), 200))
        cap = max(int(max_candidates), 1)

        for query in _expanded_queries(queries):
            # "latest" exposes a different safe stock tail after several earlier
            # episodes have exhausted the same popular results.
            for order in ("popular", "latest"):
                for page in range(1, max(int(pages_per_query), 1) + 1):
                    response = client.get(
                        "https://pixabay.com/api/videos/",
                        params={
                            "key": api_key,
                            "q": query,
                            "category": "animals",
                            "safesearch": "true",
                            "order": order,
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
                        if not video_id or video_id in seen_ids or identity in blocked:
                            continue
                        seen_ids.add(video_id)
                        duration = float(video.get("duration") or 0)
                        if duration < clip_seconds:
                            continue
                        file_info = choose_pixabay_file(video)
                        thumbnail_url = str((file_info or {}).get("thumbnail") or "").strip()
                        if not file_info or not thumbnail_url:
                            continue
                        audio_state = _audio_probe_state(file_info)
                        if audio_state is False:
                            continue
                        user = str(video.get("user") or "").strip()
                        user_id = int(video.get("user_id") or 0)
                        creator_url = (
                            f"https://pixabay.com/users/{quote(user)}-{user_id}/"
                            if user and user_id
                            else None
                        )
                        tags = str(video.get("tags") or "")
                        candidate = {
                            "provider": "pixabay",
                            "id": video_id,
                            "query": query,
                            "search_page": page,
                            "search_order": order,
                            "page_url": str(video.get("pageURL") or ""),
                            "thumbnail_url": thumbnail_url,
                            "duration": duration,
                            "creator": user or None,
                            "creator_url": creator_url,
                            "tags": tags,
                            "file_info": file_info,
                            "remote_audio_probe": "confirmed" if audio_state is True else "unknown",
                            "metadata_mentions_anchor": _text_matches_anchor(tags, anchor),
                            "cooled_down_reuse": identity in historical,
                        }
                        if identity in historical:
                            (cooled_confirmed if audio_state is True else cooled_unknown).append(candidate)
                        else:
                            (fresh_confirmed if audio_state is True else fresh_unknown).append(candidate)
                        if len(fresh_confirmed) >= cap:
                            return fresh_confirmed[:cap]
        return _finish_fresh_first(
            fresh_confirmed,
            fresh_unknown,
            cooled_confirmed,
            cooled_unknown,
            max_candidates=cap,
        )

    return collect


def _append_deep_search_audit(
    slot_dir: Path,
    *,
    all_prior_count: int,
    protected_count: int,
    cooldown_episodes: int,
) -> None:
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
        "remote_audio_prefilter": True,
        "remote_audio_probe_timeout_seconds": 8.0,
        "pixabay_orders": ["popular", "latest"],
        "fresh_first": True,
        "all_prior_source_ids": int(all_prior_count),
        "protected_source_ids": int(protected_count),
        "long_run_cat_source_cooldown_episodes": int(cooldown_episodes),
        "policy": (
            "exclude source IDs inside the active protected cooldown window; scan for never-used stock first; "
            "only then use older cooled-down stock as fallback; skip confirmed-silent remote files before Luna/candidate cap"
        ),
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
    """History-aware cat sourcing with pagination, cooldown and pre-vision audio filtering."""
    all_prior = prior_rendered_cat_identities(settings, before_slot=slot)
    protected = blocked_cat_source_identities(settings, before_slot=slot)

    removed: list[dict[str, Any]] = []
    removed.extend(sanitize_unapproved_youtube_sources(source_manifest))
    removed.extend(_remove_prior_from_manifest(source_manifest, protected))
    removed.extend(_remove_prior_from_cached_materials(slot_dir / "ai_materials.json", protected))

    original_pexels = _base._collect_pexels_audio_candidates
    original_pixabay = _base._collect_pixabay_candidates
    _base._collect_pexels_audio_candidates = _deep_pexels_collector(
        prior=protected,
        all_prior=all_prior,
    )
    _base._collect_pixabay_candidates = _deep_pixabay_collector(
        prior=protected,
        all_prior=all_prior,
    )

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

    _append_history_audit(slot_dir, prior_count=len(protected), removed=removed)
    _append_deep_search_audit(
        slot_dir,
        all_prior_count=len(all_prior),
        protected_count=len(protected),
        cooldown_episodes=cat_source_cooldown_episodes(settings),
    )
    _normalize_source_policy(result)
    return result
