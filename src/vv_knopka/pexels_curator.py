from __future__ import annotations

import json
import math
import os
import re
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

import httpx

from .settings import Settings


_STOPWORDS = {
    "a", "an", "and", "animal", "aquarium", "close", "coral", "footage", "in",
    "macro", "nature", "of", "on", "reef", "sleeping", "the", "texture", "underwater",
    "video", "water", "wild", "wildlife", "with",
}


def infer_visual_anchor(plan: dict[str, Any]) -> str:
    explicit = str(plan.get("visual_anchor") or "").strip().lower()
    if explicit:
        return explicit

    terms = [str(term).lower() for term in plan.get("search_terms", []) if str(term).strip()]
    if not terms:
        raise RuntimeError("plan has no search_terms; cannot infer a visual anchor")

    token_sets: list[set[str]] = []
    for term in terms:
        tokens = {
            token
            for token in re.findall(r"[a-z][a-z-]{2,}", term)
            if token not in _STOPWORDS
        }
        if tokens:
            token_sets.append(tokens)

    common = set.intersection(*token_sets) if token_sets else set()
    if not common:
        raise RuntimeError(
            "Could not infer one stable visible subject from search_terms. "
            "Regenerate the plan with one shared English visual anchor in every search term."
        )
    return sorted(common, key=lambda item: (-len(item), item))[0]


def pexels_page_matches_anchor(page_url: str, anchor: str) -> bool:
    path = urlparse(page_url).path.lower()
    normalized = re.sub(r"[^a-z0-9]+", "-", path)
    anchor_normalized = re.sub(r"[^a-z0-9]+", "-", anchor.lower()).strip("-")
    return bool(anchor_normalized and anchor_normalized in normalized)


def choose_pexels_file(video: dict[str, Any]) -> dict[str, Any] | None:
    files = [
        item
        for item in video.get("video_files", [])
        if item.get("file_type") == "video/mp4"
        and item.get("link")
        and int(item.get("width") or 0) > 0
        and int(item.get("height") or 0) > 0
    ]
    if not files:
        return None

    portrait = [item for item in files if int(item["height"]) >= int(item["width"])]
    candidates = portrait or files

    # Prefer a reasonably sized portrait source near 720x1280. MPT will render
    # 1080x1920; downloading the largest original wastes bandwidth for the pilot.
    def score(item: dict[str, Any]) -> tuple[float, int]:
        width = int(item["width"])
        height = int(item["height"])
        ratio_penalty = abs((width / height) - (9 / 16))
        size_penalty = abs(height - 1280) / 1280
        low_res_penalty = 10.0 if height < 720 else 0.0
        return (ratio_penalty * 5 + size_penalty + low_res_penalty, -height)

    return min(candidates, key=score)


def _search_pexels(client: httpx.Client, api_key: str, query: str, per_page: int) -> list[dict[str, Any]]:
    response = client.get(
        "https://api.pexels.com/videos/search",
        headers={"Authorization": api_key},
        params={"query": query, "orientation": "portrait", "per_page": per_page},
    )
    response.raise_for_status()
    data = response.json()
    return list(data.get("videos") or [])


def _download(client: httpx.Client, url: str, destination: Path) -> None:
    if destination.exists() and destination.stat().st_size > 0:
        return
    temp = destination.with_suffix(destination.suffix + ".part")
    with client.stream("GET", url) as response:
        response.raise_for_status()
        with temp.open("wb") as fh:
            for chunk in response.iter_bytes():
                fh.write(chunk)
    temp.replace(destination)


def prepare_pexels_materials(
    settings: Settings,
    plan: dict[str, Any],
    *,
    slot: int,
    slot_dir: Path,
) -> list[dict[str, Any]]:
    api_key = os.getenv("PEXELS_API_KEY", "").strip()
    if not api_key:
        raise RuntimeError("PEXELS_API_KEY is not set in .env")

    video_cfg = settings.raw["video"]
    materials_cfg = settings.raw.get("materials", {})
    clip_seconds = int(video_cfg.get("clip_seconds", 6))
    target_seconds = int(video_cfg.get("target_max_seconds", 45))
    target_count = int(materials_cfg.get("ai_material_count", math.ceil(target_seconds / clip_seconds)))
    per_page = int(materials_cfg.get("pexels_per_page", 40))
    require_slug_anchor = bool(materials_cfg.get("require_anchor_in_pexels_slug", True))
    anchor = infer_visual_anchor(plan)

    local_videos_dir = Path(
        os.getenv(
            "MPT_LOCAL_VIDEOS_DIR",
            str(settings.root / "MoneyPrinterTurbo" / "storage" / "local_videos"),
        )
    ).resolve()
    local_videos_dir.mkdir(parents=True, exist_ok=True)

    raw_queries = [str(term).strip() for term in plan.get("search_terms", []) if str(term).strip()]
    queries = list(dict.fromkeys(raw_queries + [anchor, f"{anchor} underwater", f"{anchor} close up"]))

    selected: list[dict[str, Any]] = []
    seen_ids: set[int] = set()
    provenance: list[dict[str, Any]] = []

    with httpx.Client(timeout=60, follow_redirects=True) as client:
        for query in queries:
            for video in _search_pexels(client, api_key, query, per_page):
                video_id = int(video.get("id") or 0)
                if not video_id or video_id in seen_ids:
                    continue
                duration = float(video.get("duration") or 0)
                if duration < clip_seconds:
                    continue
                page_url = str(video.get("url") or "")
                if require_slug_anchor and not pexels_page_matches_anchor(page_url, anchor):
                    continue
                file_info = choose_pexels_file(video)
                if not file_info:
                    continue

                filename = f"vv-slot-{slot:02d}-pexels-{video_id}.mp4"
                destination = local_videos_dir / filename
                _download(client, str(file_info["link"]), destination)

                creator = video.get("user") or {}
                source_info = {
                    "provider": "pexels",
                    "pexels_id": video_id,
                    "page_url": page_url,
                    "creator": creator.get("name"),
                    "creator_url": creator.get("url"),
                    "query": query,
                    "visual_anchor": anchor,
                    "width": int(file_info.get("width") or 0),
                    "height": int(file_info.get("height") or 0),
                    "duration": duration,
                }
                selected.append(
                    {
                        "provider": "pexels",
                        "url": filename,
                        "duration": int(duration),
                        "source_info": source_info,
                    }
                )
                provenance.append(source_info | {"local_file": filename})
                seen_ids.add(video_id)
                if len(selected) >= target_count:
                    break
            if len(selected) >= target_count:
                break

    slot_dir.mkdir(parents=True, exist_ok=True)
    audit_path = slot_dir / "ai_materials.json"
    audit_path.write_text(
        json.dumps(
            {
                "slot": slot,
                "visual_anchor": anchor,
                "required": target_count,
                "selected": len(selected),
                "materials": provenance,
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    if len(selected) < target_count:
        raise RuntimeError(
            f"Pexels relevance gate found only {len(selected)}/{target_count} usable clips "
            f"whose source page explicitly matches visual anchor '{anchor}'. "
            f"See {audit_path}. Refusing to render with unrelated filler footage."
        )
    return selected
