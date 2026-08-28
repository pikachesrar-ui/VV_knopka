from __future__ import annotations

import json
import math
import os
import re
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

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

    cfg = settings.raw["openai"]
    materials_cfg = settings.raw.get("materials", {})
    model = str(materials_cfg.get("vision_model", "gpt-5.6-luna"))
    estimated = float(materials_cfg.get("vision_max_estimated_cost_per_call_usd", 0.03))
    ledger.ensure_room(estimated)

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
                    f"candidate_id={candidate['id']}; pexels_query={candidate['query']!r}; "
                    f"slug_mentions_anchor={candidate['slug_mentions_anchor']}"
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
        purpose=f"slot-{slot}:pexels-vision:{anchor}",
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
            -int(bool(item.get("slug_mentions_anchor"))),
            int(item["id"]),
        )
    )
    return approved


def _collect_candidates(
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
                    "id": video_id,
                    "query": query,
                    "page_url": page_url,
                    "thumbnail_url": thumbnail_url,
                    "duration": duration,
                    "creator": creator.get("name"),
                    "creator_url": creator.get("url"),
                    "file_info": file_info,
                    "slug_mentions_anchor": pexels_page_matches_anchor(page_url, anchor),
                }
            )
            seen_ids.add(video_id)
            if len(candidates) >= max_candidates:
                return candidates
    return candidates


def prepare_pexels_materials(
    settings: Settings,
    plan: dict[str, Any],
    *,
    slot: int,
    slot_dir: Path,
    ledger: BudgetLedger,
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
    max_candidates = int(materials_cfg.get("vision_max_candidates", 30))
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

    with httpx.Client(timeout=60, follow_redirects=True) as pexels_client:
        candidates = _collect_candidates(
            client=pexels_client,
            api_key=api_key,
            queries=queries,
            per_page=per_page,
            max_candidates=max_candidates,
            clip_seconds=clip_seconds,
            anchor=anchor,
        )

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
        if len(approved) >= target_count:
            break

    selected_candidates = approved[:target_count]
    selected: list[dict[str, Any]] = []
    provenance: list[dict[str, Any]] = []
    with httpx.Client(timeout=120, follow_redirects=True) as download_client:
        for candidate in selected_candidates:
            video_id = int(candidate["id"])
            file_info = candidate["file_info"]
            filename = f"vv-slot-{slot:02d}-pexels-{video_id}.mp4"
            destination = local_videos_dir / filename
            _download(download_client, str(file_info["link"]), destination)
            source_info = {
                "provider": "pexels",
                "pexels_id": video_id,
                "page_url": candidate["page_url"],
                "creator": candidate.get("creator"),
                "creator_url": candidate.get("creator_url"),
                "query": candidate["query"],
                "visual_anchor": anchor,
                "slug_mentions_anchor": bool(candidate.get("slug_mentions_anchor")),
                "vision_confidence": float(candidate.get("vision_confidence") or 0),
                "vision_reason": candidate.get("vision_reason"),
                "width": int(file_info.get("width") or 0),
                "height": int(file_info.get("height") or 0),
                "duration": float(candidate["duration"]),
            }
            selected.append(
                {
                    "provider": "pexels",
                    "url": filename,
                    "duration": int(float(candidate["duration"])),
                    "source_info": source_info,
                }
            )
            provenance.append(source_info | {"local_file": filename})

    audit = {
        "slot": slot,
        "visual_anchor": anchor,
        "required": target_count,
        "candidate_count": len(candidates),
        "vision_reviewed": len(all_decisions),
        "vision_approved": len(approved),
        "selected": len(selected),
        "minimum_confidence": minimum_confidence,
        "materials": provenance,
        "vision_decisions": all_decisions,
    }
    audit_path.write_text(json.dumps(audit, ensure_ascii=False, indent=2), encoding="utf-8")

    if len(selected) < target_count:
        raise RuntimeError(
            f"Pexels visual relevance gate found only {len(selected)}/{target_count} usable clips "
            f"after reviewing {len(all_decisions)} previews for visible anchor '{anchor}'. "
            f"See {audit_path}. Refusing to render with unrelated filler footage."
        )
    return selected
