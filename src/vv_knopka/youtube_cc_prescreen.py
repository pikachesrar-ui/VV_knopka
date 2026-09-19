from __future__ import annotations

import json
import os
from typing import Any

import httpx

from .budget import BudgetLedger
from .settings import Settings
from .trend_discovery import YOUTUBE_VIDEOS_URL


PRESCREEN_SCHEMA: dict[str, Any] = {
    "type": "object",
    "additionalProperties": False,
    "required": ["decisions"],
    "properties": {
        "decisions": {
            "type": "array",
            "items": {
                "type": "object",
                "additionalProperties": False,
                "required": [
                    "video_id",
                    "approved",
                    "confidence",
                    "domestic_cat",
                    "creator_branding",
                    "social_ui",
                    "large_added_caption",
                    "compilation_or_repost_style",
                    "reason",
                ],
                "properties": {
                    "video_id": {"type": "string"},
                    "approved": {"type": "boolean"},
                    "confidence": {"type": "number", "minimum": 0, "maximum": 1},
                    "domestic_cat": {"type": "boolean"},
                    "creator_branding": {"type": "boolean"},
                    "social_ui": {"type": "boolean"},
                    "large_added_caption": {"type": "boolean"},
                    "compilation_or_repost_style": {"type": "boolean"},
                    "reason": {"type": "string"},
                },
            },
        }
    },
}


def _extract_output_text(data: dict[str, Any]) -> str:
    if isinstance(data.get("output_text"), str) and data["output_text"]:
        return data["output_text"]
    texts: list[str] = []
    for item in data.get("output", []) or []:
        if not isinstance(item, dict):
            continue
        for content in item.get("content", []) or []:
            if isinstance(content, dict) and isinstance(content.get("text"), str):
                texts.append(content["text"])
    if not texts:
        raise RuntimeError("YouTube CC prescreen response did not contain text")
    return "".join(texts)


def _best_thumbnail(snippet: dict[str, Any]) -> str:
    thumbnails = snippet.get("thumbnails") or {}
    for key in ("maxres", "standard", "high", "medium", "default"):
        item = thumbnails.get(key) or {}
        url = str(item.get("url") or "").strip()
        if url:
            return url
    return ""


def enrich_api_candidates(
    *,
    api_key: str,
    candidates: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Attach canonical channel ids and YouTube thumbnail URLs to API CC candidates."""
    ids = [str(item.get("video_id") or "").strip() for item in candidates]
    ids = [item for item in ids if item]
    if not ids:
        return []
    # videos.list accepts at most 50 ids. The search prescreen intentionally works
    # on a small ranked pool, so one request is enough in normal operation.
    ids = ids[:50]
    with httpx.Client(timeout=45, follow_redirects=True) as client:
        response = client.get(
            YOUTUBE_VIDEOS_URL,
            params={"key": api_key, "part": "snippet", "id": ",".join(ids)},
        )
        response.raise_for_status()
        rows = response.json().get("items", []) or []
    by_id: dict[str, dict[str, Any]] = {}
    for row in rows:
        video_id = str(row.get("id") or "").strip()
        snippet = row.get("snippet") or {}
        if not video_id:
            continue
        by_id[video_id] = {
            "channel_id": str(snippet.get("channelId") or "").strip(),
            "channel_title": str(snippet.get("channelTitle") or "").strip(),
            "thumbnail_url": _best_thumbnail(snippet),
        }

    enriched: list[dict[str, Any]] = []
    for item in candidates:
        video_id = str(item.get("video_id") or "").strip()
        extra = by_id.get(video_id) or {}
        enriched.append(dict(item) | extra)
    return enriched


def diversify_channels(candidates: list[dict[str, Any]], *, max_per_channel: int = 1) -> list[dict[str, Any]]:
    """Keep the ranking but stop one uploader/series from dominating the candidate list."""
    counts: dict[str, int] = {}
    kept: list[dict[str, Any]] = []
    cap = max(int(max_per_channel), 1)
    for item in candidates:
        channel_key = str(item.get("channel_id") or item.get("channel_title") or "").strip().casefold()
        if not channel_key:
            channel_key = f"unknown:{item.get('video_id')}"
        if counts.get(channel_key, 0) >= cap:
            continue
        counts[channel_key] = counts.get(channel_key, 0) + 1
        kept.append(item)
    return kept


def prescreen_decision_passes(decision: dict[str, Any], *, minimum_confidence: float = 0.74) -> bool:
    try:
        confidence = float(decision.get("confidence") or 0.0)
    except (TypeError, ValueError):
        confidence = 0.0
    forbidden = any(
        bool(decision.get(field))
        for field in (
            "creator_branding",
            "social_ui",
            "large_added_caption",
            "compilation_or_repost_style",
        )
    )
    return (
        bool(decision.get("approved"))
        and confidence >= max(float(minimum_confidence), 0.0)
        and bool(decision.get("domestic_cat"))
        and not forbidden
    )


def prescreen_cc_candidates(
    settings: Settings,
    ledger: BudgetLedger,
    *,
    api_key: str,
    candidates: list[dict[str, Any]],
    output_limit: int,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], dict[str, Any]]:
    """Cheap thumbnail gate before downloading CC candidates.

    This only predicts presentation cleanliness from YouTube thumbnails. A source
    that passes still must pass the full four-frame clean-footage gate after download.
    """
    if not candidates:
        return [], [], {"input": 0, "channel_diverse": 0, "reviewed": 0, "approved": 0}
    if not api_key:
        raise ValueError("YOUTUBE_API_KEY is required for official CC thumbnail prescreen")

    material_cfg = settings.raw.get("materials", {})
    model = str(material_cfg.get("vision_model", "gpt-5.6-luna"))
    minimum_confidence = float(material_cfg.get("youtube_cc_prescreen_min_confidence", 0.74))
    estimate_per_batch = float(material_cfg.get("youtube_cc_prescreen_max_estimated_cost_usd", 0.03))
    batch_size = max(1, min(int(material_cfg.get("youtube_cc_prescreen_batch_size", 10)), 12))
    screen_limit = max(int(output_limit) * 2, int(output_limit))
    screen_limit = min(screen_limit, 30)

    enriched = enrich_api_candidates(api_key=api_key, candidates=candidates)
    diverse = diversify_channels(enriched, max_per_channel=1)[:screen_limit]
    reviewable = [item for item in diverse if str(item.get("thumbnail_url") or "").strip()]

    api_openai_key = os.getenv("OPENAI_API_KEY", "").strip()
    if not api_openai_key:
        raise RuntimeError("OPENAI_API_KEY is not set; cannot prescreen YouTube CC thumbnails")

    decisions: list[dict[str, Any]] = []
    for offset in range(0, len(reviewable), batch_size):
        batch = reviewable[offset : offset + batch_size]
        content: list[dict[str, Any]] = [
            {
                "type": "input_text",
                "text": (
                    "Pre-screen YouTube Creative Commons cat-video thumbnails before media download. "
                    "This is NOT a licensing decision; API license verification is separate. Approve only likely "
                    "clean source footage showing a domestic house cat, with no prominent uploader/channel branding, "
                    "@handle/profile/avatar/banner, TikTok/Reels/Shorts UI or watermark, large added meme/headline text, "
                    "split-screen/ranking/collage layout, or obvious compilation/repost packaging. Natural text inside "
                    "the filmed scene is allowed. If the thumbnail is ambiguous, reject. Return one decision for every video_id."
                ),
            }
        ]
        for item in batch:
            content.append(
                {
                    "type": "input_text",
                    "text": (
                        f"video_id={item.get('video_id')}; title={item.get('title')!r}; "
                        f"uploader={item.get('channel_title')!r}"
                    ),
                }
            )
            content.append(
                {
                    "type": "input_image",
                    "image_url": str(item.get("thumbnail_url")),
                    "detail": "low",
                }
            )

        ledger.ensure_room(estimate_per_batch)
        payload = {
            "model": model,
            "input": [{"role": "user", "content": content}],
            "reasoning": {"effort": "none"},
            "text": {
                "format": {
                    "type": "json_schema",
                    "name": "vv_youtube_cc_prescreen",
                    "strict": True,
                    "schema": PRESCREEN_SCHEMA,
                },
                "verbosity": "low",
            },
            "max_output_tokens": 1800,
            "store": False,
        }
        with httpx.Client(timeout=180) as client:
            response = client.post(
                "https://api.openai.com/v1/responses",
                headers={"Authorization": f"Bearer {api_openai_key}", "Content-Type": "application/json"},
                json=payload,
            )
        if response.status_code >= 400:
            raise RuntimeError(f"YouTube CC thumbnail prescreen failed with HTTP {response.status_code}")
        data = response.json()
        parsed = json.loads(_extract_output_text(data))
        batch_decisions = list(parsed.get("decisions") or [])
        decisions.extend(batch_decisions)
        usage = data.get("usage") or {}
        ledger.record(
            model=model,
            input_tokens=int(usage.get("input_tokens", 0)),
            output_tokens=int(usage.get("output_tokens", 0)),
            purpose="youtube-cc-search-prescreen",
        )

    decision_by_id = {
        str(item.get("video_id") or "").strip(): item
        for item in decisions
        if str(item.get("video_id") or "").strip()
    }
    approved: list[dict[str, Any]] = []
    audit: list[dict[str, Any]] = []
    for item in diverse:
        video_id = str(item.get("video_id") or "").strip()
        decision = decision_by_id.get(video_id)
        if not decision:
            audit.append({"video_id": video_id, "approved": False, "reason": "no reviewable thumbnail/decision"})
            continue
        passed = prescreen_decision_passes(decision, minimum_confidence=minimum_confidence)
        row = dict(decision) | {
            "video_id": video_id,
            "title": item.get("title"),
            "channel_title": item.get("channel_title"),
            "thumbnail_url": item.get("thumbnail_url"),
            "prescreen_pass": passed,
        }
        audit.append(row)
        if passed:
            approved.append(
                dict(item)
                | {
                    "clean_thumbnail_prescreen": True,
                    "clean_thumbnail_confidence": float(decision.get("confidence") or 0.0),
                    "clean_thumbnail_reason": str(decision.get("reason") or "").strip(),
                }
            )

    selected = approved[: max(int(output_limit), 1)]
    for rank, item in enumerate(selected, 1):
        item["cc_rank"] = rank
    stats = {
        "input": len(candidates),
        "channel_diverse": len(diverse),
        "reviewed": len(decisions),
        "approved": len(approved),
        "selected": len(selected),
        "max_per_channel": 1,
        "minimum_confidence": minimum_confidence,
    }
    return selected, audit, stats
