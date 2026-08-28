from __future__ import annotations

import json
import math
import os
import re
from pathlib import Path
from typing import Any
from urllib.parse import quote, urlparse

import httpx

from .budget import BudgetLedger
from .settings import Settings


_STOPWORDS = {
    "a", "an", "and", "animal", "aquarium", "close", "coral", "footage", "in",
    "macro", "nature", "of", "on", "reef", "sleeping", "the", "texture", "underwater",
    "video", "water", "wild", "wildlife", "with",
}

VISION_DECISION_SCHEMA: dict[str, Any] = {
    "type": "object",
    "additionalProperties": False,
    "required": ["decisions"],
    "properties": {
        "decisions": {
            "type": "array",
            "items": {
                "type": "object",
                "additionalProperties": False,
                "required": ["id", "accepted", "confidence", "reason"],
                "properties": {
                    "id": {"type": "integer"},
                    "accepted": {"type": "boolean"},
                    "confidence": {"type": "number", "minimum": 0, "maximum": 1},
                    "reason": {"type": "string"},
                },
            },
        }
    },
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
    """Weak metadata signal only; never use this as the sole visual gate."""
    path = urlparse(page_url).path.lower()
    normalized = re.sub(r"[^a-z0-9]+", "-", path)
    anchor_normalized = re.sub(r"[^a-z0-9]+", "-", anchor.lower()).strip("-")
    return bool(anchor_normalized and anchor_normalized in normalized)


def _text_matches_anchor(text: str, anchor: str) -> bool:
    normalized = re.sub(r"[^a-z0-9]+", " ", str(text).lower())
    anchor_normalized = re.sub(r"[^a-z0-9]+", " ", anchor.lower()).strip()
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

    def score(item: dict[str, Any]) -> tuple[float, int]:
        width = int(item["width"])
        height = int(item["height"])
        ratio_penalty = abs((width / height) - (9 / 16))
        size_penalty = abs(height - 1280) / 1280
        low_res_penalty = 10.0 if height < 720 else 0.0
        return (ratio_penalty * 5 + size_penalty + low_res_penalty, -height)

    return min(candidates, key=score)


def choose_pixabay_file(video: dict[str, Any]) -> dict[str, Any] | None:
    files: list[dict[str, Any]] = []
    for label, item in (video.get("videos") or {}).items():
        if not isinstance(item, dict) or not item.get("url"):
            continue
        width = int(item.get("width") or 0)
        height = int(item.get("height") or 0)
        if width <= 0 or height <= 0:
            continue
        files.append(
            {
                "label": label,
                "link": item["url"],
                "width": width,
                "height": height,
                "thumbnail": item.get("thumbnail"),
                "size": int(item.get("size") or 0),
            }
        )
    if not files:
        return None

    portrait = [item for item in files if item["height"] >= item["width"]]
    candidates = portrait or files

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
    return list((response.json()).get("videos") or [])


def _search_pixabay(client: httpx.Client, api_key: str, query: str, per_page: int) -> list[dict[str, Any]]:
    response = client.get(
        "https://pixabay.com/api/videos/",
        params={
            "key": api_key,
            "q": query,
            "category": "animals",
            "safesearch": "true",
            "order": "popular",
            "per_page": per_page,
        },
    )
    response.raise_for_status()
    return list((response.json()).get("hits") or [])


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


def _extract_output_text(data: dict[str, Any]) -> str:
    if isinstance(data.get("output_text"), str) and data["output_text"]:
        return data["output_text"]
    texts: list[str] = []
    for item in data.get("output", []):
        if not isinstance(item, dict):
            continue
        for content in item.get("content", []):
            if isinstance(content, dict) and isinstance(content.get("text"), str):
                texts.append(content["text"])
    if not texts:
        raise RuntimeError("OpenAI vision response did not contain text output")
    return "".join(texts)


def _vision_review_batch(
    *,
    settings: Settings,
    ledger: BudgetLedger,
    anchor: str,
    candidates: list[dict[str, Any]],
    slot: int,
) -> list[dict[str, Any]]:
    api_key = os.getenv("OPENAI_API_KEY", "").strip()
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY is not set; cannot run visual relevance gate")
    if not candidates:
        return []

    cfg = settings.raw["openai"]
    materials_cfg = settings.raw.get("materials", {})
    model = str(materials_cfg.get("vision_model", "gpt-5.6-luna"))
    estimated = float(materials_cfg.get("vision_max_estimated_cost_per_call_usd", 0.03))
    ledger.ensure_room(estimated)
    provider = str(candidates[0].get("provider") or "stock")

    content: list[dict[str, Any]] = [
        {
            "type": "input_text",
            "text": (
                f"Review stock-video preview images for a YouTube Short whose mandatory visible main subject is: {anchor!r}. "
                "Accept a candidate only when the requested subject is clearly visible and identifiable in the preview, not merely implied by ocean/reef/context. "
                "Reject unrelated animals, humans/human skin, scenery-only shots, drawings, text screens, and ambiguous close-ups. "
                "The subject may share the frame with other objects, but it must be a meaningful visible subject. "
                "Return one decision for every candidate id."
            ),
        }
    ]
    for candidate in candidates:
        content.append(
            {
                "type": "input_text",
                "text": (
                    f"candidate_id={candidate['id']}; provider={candidate.get('provider')}; "
                    f"query={candidate['query']!r}; metadata_mentions_anchor={candidate.get('metadata_mentions_anchor', False)}"
                ),
            }
        )
        content.append(
            {
                "type": "input_image",
                "image_url": candidate["thumbnail_url"],
                "detail": "low",
            }
        )

    payload = {
        "model": model,
        "input": [{"role": "user", "content": content}],
        "reasoning": {"effort": "none"},
        "text": {
            "format": {
                "type": "json_schema",
                "name": "vv_material_vision_review",
                "strict": True,
                "schema": VISION_DECISION_SCHEMA,
            },
            "verbosity": "low",
        },
        "max_output_tokens": 1800,
        "store": False,
    }
    with httpx.Client(timeout=120) as client:
        response = client.post(
            "https://api.openai.com/v1/responses",
            headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
            json=payload,
        )
        response.raise_for_status()
        data = response.json()

    review = json.loads(_extract_output_text(data))
    usage = data.get("usage") or {}
    ledger.record(
        model=model,
        input_tokens=int(usage.get("input_tokens", 0)),
        output_tokens=int(usage.get("output_tokens", 0)),
        purpose=f"slot-{slot}:{provider}-vision:{anchor}",
    )
    return list(review.get("decisions") or [])


def select_vision_approved_candidates(
    candidates: list[dict[str, Any]],
    decisions: list[dict[str, Any]],
    *,
    minimum_confidence: float,
) -> list[dict[str, Any]]:
    by_id = {int(candidate["id"]): candidate for candidate in candidates}
    approved: list[dict[str, Any]] = []
    for decision in decisions:
        candidate = by_id.get(int(decision.get("id") or 0))
        if not candidate:
            continue
        confidence = float(decision.get("confidence") or 0)
        if not bool(decision.get("accepted")) or confidence < minimum_confidence:
            continue
        approved.append(
            candidate
            | {
                "vision_confidence": confidence,
                "vision_reason": str(decision.get("reason") or ""),
            }
        )
    approved.sort(
        key=lambda item: (
            -float(item.get("vision_confidence") or 0),
            -int(bool(item.get("metadata_mentions_anchor"))),
            int(item["id"]),
        )
    )
    return approved


def _collect_pexels_candidates(
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
    for query in queries:
        for video in _search_pexels(client, api_key, query, per_page):
            video_id = int(video.get("id") or 0)
            if not video_id or video_id in seen_ids:
                continue
            duration = float(video.get("duration") or 0)
            if duration < clip_seconds:
                continue
            file_info = choose_pexels_file(video)
            thumbnail_url = str(video.get("image") or "").strip()
            if not file_info or not thumbnail_url:
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


def _collect_pixabay_candidates(
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
    for query in queries:
        for video in _search_pixabay(client, api_key, query, per_page):
            video_id = int(video.get("id") or 0)
            if not video_id or video_id in seen_ids:
                continue
            duration = float(video.get("duration") or 0)
            if duration < clip_seconds:
                continue
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
            seen_ids.add(video_id)
            if len(candidates) >= max_candidates:
                return candidates
    return candidates


def _review_until_enough(
    *,
    settings: Settings,
    ledger: BudgetLedger,
    anchor: str,
    candidates: list[dict[str, Any]],
    slot: int,
    batch_size: int,
    minimum_confidence: float,
    needed: int,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    all_decisions: list[dict[str, Any]] = []
    approved: list[dict[str, Any]] = []
    for start in range(0, len(candidates), batch_size):
        batch = candidates[start : start + batch_size]
        decisions = _vision_review_batch(
            settings=settings,
            ledger=ledger,
            anchor=anchor,
            candidates=batch,
            slot=slot,
        )
        all_decisions.extend(decisions)
        approved = select_vision_approved_candidates(
            candidates,
            all_decisions,
            minimum_confidence=minimum_confidence,
        )
        if len(approved) >= needed:
            break
    return approved, all_decisions


def _material_from_candidate(
    *,
    candidate: dict[str, Any],
    slot: int,
    anchor: str,
    local_videos_dir: Path,
    download_client: httpx.Client,
) -> tuple[dict[str, Any], dict[str, Any]]:
    provider = str(candidate["provider"])
    video_id = int(candidate["id"])
    file_info = candidate["file_info"]
    filename = f"vv-slot-{slot:02d}-{provider}-{video_id}.mp4"
    destination = local_videos_dir / filename
    _download(download_client, str(file_info["link"]), destination)

    source_info = {
        "provider": provider,
        f"{provider}_id": video_id,
        "page_url": candidate.get("page_url"),
        "creator": candidate.get("creator"),
        "creator_url": candidate.get("creator_url"),
        "query": candidate.get("query"),
        "visual_anchor": anchor,
        "metadata_mentions_anchor": bool(candidate.get("metadata_mentions_anchor")),
        "vision_confidence": float(candidate.get("vision_confidence") or 0),
        "vision_reason": candidate.get("vision_reason"),
        "width": int(file_info.get("width") or 0),
        "height": int(file_info.get("height") or 0),
        "duration": float(candidate["duration"]),
    }
    if provider == "pixabay":
        source_info["tags"] = candidate.get("tags")

    material = {
        "provider": provider,
        "url": filename,
        "duration": int(float(candidate["duration"])),
        "source_info": source_info,
    }
    return material, source_info | {"local_file": filename}


def _load_cached_materials(
    *,
    audit_path: Path,
    anchor: str,
    local_videos_dir: Path,
    target_count: int,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], dict[str, Any]]:
    if not audit_path.exists():
        return [], [], {}
    try:
        audit = json.loads(audit_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return [], [], {}
    if str(audit.get("visual_anchor") or "").lower() != anchor.lower():
        return [], [], audit

    materials: list[dict[str, Any]] = []
    provenance: list[dict[str, Any]] = []
    for info in audit.get("materials", []):
        if len(materials) >= target_count or not isinstance(info, dict):
            break
        filename = str(info.get("local_file") or "").strip()
        provider = str(info.get("provider") or "").strip()
        if not filename or not provider or not (local_videos_dir / filename).exists():
            continue
        duration = int(float(info.get("duration") or 0))
        if duration <= 0:
            continue
        source_info = {key: value for key, value in info.items() if key != "local_file"}
        materials.append(
            {
                "provider": provider,
                "url": filename,
                "duration": duration,
                "source_info": source_info,
            }
        )
        provenance.append(info)
    return materials, provenance, audit


def prepare_pexels_materials(
    settings: Settings,
    plan: dict[str, Any],
    *,
    slot: int,
    slot_dir: Path,
    ledger: BudgetLedger,
) -> list[dict[str, Any]]:
    """Prepare vision-reviewed stock footage from Pexels, then Pixabay fallback.

    The historical function name is kept to avoid breaking the CLI/imports while
    the implementation becomes a multi-source stock curator.
    """
    pexels_key = os.getenv("PEXELS_API_KEY", "").strip()
    if not pexels_key:
        raise RuntimeError("PEXELS_API_KEY is not set in .env")

    video_cfg = settings.raw["video"]
    materials_cfg = settings.raw.get("materials", {})
    clip_seconds = int(video_cfg.get("clip_seconds", 6))
    target_seconds = int(video_cfg.get("target_max_seconds", 45))
    target_count = int(materials_cfg.get("ai_material_count", math.ceil(target_seconds / clip_seconds)))
    pexels_per_page = int(materials_cfg.get("pexels_per_page", 40))
    pixabay_per_page = int(materials_cfg.get("pixabay_per_page", 100))
    max_candidates = int(materials_cfg.get("vision_max_candidates", 30))
    pixabay_max_candidates = int(materials_cfg.get("pixabay_vision_max_candidates", 40))
    batch_size = max(1, int(materials_cfg.get("vision_batch_size", 10)))
    minimum_confidence = float(materials_cfg.get("vision_min_confidence", 0.72))
    anchor = infer_visual_anchor(plan)

    local_videos_dir = Path(
        os.getenv(
            "MPT_LOCAL_VIDEOS_DIR",
            str(settings.root / "MoneyPrinterTurbo" / "storage" / "local_videos"),
        )
    ).resolve()
    local_videos_dir.mkdir(parents=True, exist_ok=True)

    raw_queries = [str(term).strip() for term in plan.get("search_terms", []) if str(term).strip()]
    anchored_queries = [term if anchor in term.lower() else f"{anchor} {term}" for term in raw_queries]
    queries = list(dict.fromkeys(anchored_queries + [anchor, f"{anchor} underwater", f"{anchor} close up"]))

    slot_dir.mkdir(parents=True, exist_ok=True)
    audit_path = slot_dir / "ai_materials.json"
    selected, provenance, previous_audit = _load_cached_materials(
        audit_path=audit_path,
        anchor=anchor,
        local_videos_dir=local_videos_dir,
        target_count=target_count,
    )

    provider_stats: dict[str, Any] = {
        "cache": {"reused": len(selected)},
        "pexels": {"candidates": 0, "vision_reviewed": 0, "vision_approved": 0},
        "pixabay": {"candidates": 0, "vision_reviewed": 0, "vision_approved": 0},
    }
    new_decisions: dict[str, list[dict[str, Any]]] = {"pexels": [], "pixabay": []}

    # If the immediately previous run already exhausted the configured Pexels
    # preview budget for this anchor, do not pay to review the same pool again.
    previous_pexels_reviewed = int(
        ((previous_audit.get("providers") or {}).get("pexels") or {}).get("vision_reviewed")
        or previous_audit.get("vision_reviewed")
        or 0
    )
    pexels_exhausted = previous_pexels_reviewed >= max_candidates

    if len(selected) < target_count and not pexels_exhausted:
        with httpx.Client(timeout=60, follow_redirects=True) as client:
            pexels_candidates = _collect_pexels_candidates(
                client=client,
                api_key=pexels_key,
                queries=queries,
                per_page=pexels_per_page,
                max_candidates=max_candidates,
                clip_seconds=clip_seconds,
                anchor=anchor,
            )
        needed = target_count - len(selected)
        approved, decisions = _review_until_enough(
            settings=settings,
            ledger=ledger,
            anchor=anchor,
            candidates=pexels_candidates,
            slot=slot,
            batch_size=batch_size,
            minimum_confidence=minimum_confidence,
            needed=needed,
        )
        provider_stats["pexels"] = {
            "candidates": len(pexels_candidates),
            "vision_reviewed": len(decisions),
            "vision_approved": len(approved),
        }
        new_decisions["pexels"] = decisions
        with httpx.Client(timeout=120, follow_redirects=True) as client:
            for candidate in approved[:needed]:
                material, source = _material_from_candidate(
                    candidate=candidate,
                    slot=slot,
                    anchor=anchor,
                    local_videos_dir=local_videos_dir,
                    download_client=client,
                )
                selected.append(material)
                provenance.append(source)

    if len(selected) < target_count:
        pixabay_key = os.getenv("PIXABAY_API_KEY", "").strip()
        if not pixabay_key:
            audit = {
                "slot": slot,
                "visual_anchor": anchor,
                "required": target_count,
                "selected": len(selected),
                "minimum_confidence": minimum_confidence,
                "providers": provider_stats,
                "materials": provenance,
                "vision_decisions": new_decisions,
                "next_required_provider": "pixabay",
            }
            audit_path.write_text(json.dumps(audit, ensure_ascii=False, indent=2), encoding="utf-8")
            raise RuntimeError(
                f"Pexels supplied only {len(selected)}/{target_count} vision-approved clips for '{anchor}'. "
                "Add PIXABAY_API_KEY to .env; the next run will reuse approved Pexels clips and search Pixabay "
                f"for the remaining {target_count - len(selected)}. See {audit_path}."
            )

        with httpx.Client(timeout=60, follow_redirects=True) as client:
            pixabay_candidates = _collect_pixabay_candidates(
                client=client,
                api_key=pixabay_key,
                queries=queries,
                per_page=pixabay_per_page,
                max_candidates=pixabay_max_candidates,
                clip_seconds=clip_seconds,
                anchor=anchor,
            )
        needed = target_count - len(selected)
        approved, decisions = _review_until_enough(
            settings=settings,
            ledger=ledger,
            anchor=anchor,
            candidates=pixabay_candidates,
            slot=slot,
            batch_size=batch_size,
            minimum_confidence=minimum_confidence,
            needed=needed,
        )
        provider_stats["pixabay"] = {
            "candidates": len(pixabay_candidates),
            "vision_reviewed": len(decisions),
            "vision_approved": len(approved),
        }
        new_decisions["pixabay"] = decisions
        with httpx.Client(timeout=120, follow_redirects=True) as client:
            for candidate in approved[:needed]:
                material, source = _material_from_candidate(
                    candidate=candidate,
                    slot=slot,
                    anchor=anchor,
                    local_videos_dir=local_videos_dir,
                    download_client=client,
                )
                selected.append(material)
                provenance.append(source)

    audit = {
        "slot": slot,
        "visual_anchor": anchor,
        "required": target_count,
        "selected": len(selected),
        "minimum_confidence": minimum_confidence,
        "providers": provider_stats,
        "materials": provenance,
        "vision_decisions": new_decisions,
    }
    audit_path.write_text(json.dumps(audit, ensure_ascii=False, indent=2), encoding="utf-8")

    if len(selected) < target_count:
        raise RuntimeError(
            f"Multi-source visual relevance gate found only {len(selected)}/{target_count} usable clips "
            f"for visible anchor '{anchor}' after Pexels + Pixabay. See {audit_path}. "
            "Refusing to render with unrelated filler footage."
        )
    return selected[:target_count]
