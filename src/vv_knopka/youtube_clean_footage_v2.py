from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import httpx

from . import youtube_clean_footage as _v1
from .budget import BudgetLedger
from .settings import Settings


_CLEAN_REVIEW_VERSION = 2
_CLEAN_PROMPT_VERSION = "youtube-clean-footage-v2-contact-sheet-aware"

CLEAN_FOOTAGE_SCHEMA: dict[str, Any] = {
    "type": "object",
    "additionalProperties": False,
    "required": [
        "approved",
        "confidence",
        "cat_visible",
        "creator_branding",
        "social_ui",
        "large_added_caption",
        "source_frame_collage",
        "multi_clip_sequence",
        "compilation_or_repost_style",
        "reason",
    ],
    "properties": {
        "approved": {"type": "boolean"},
        "confidence": {"type": "number", "minimum": 0, "maximum": 1},
        "cat_visible": {"type": "boolean"},
        "creator_branding": {"type": "boolean"},
        "social_ui": {"type": "boolean"},
        "large_added_caption": {"type": "boolean"},
        "source_frame_collage": {"type": "boolean"},
        "multi_clip_sequence": {"type": "boolean"},
        "compilation_or_repost_style": {"type": "boolean"},
        "reason": {"type": "string"},
    },
}


def current_clean_prompt_version() -> str:
    return _CLEAN_PROMPT_VERSION


def current_clean_review_version() -> int:
    return _CLEAN_REVIEW_VERSION


def decision_passes_clean_gate(decision: dict[str, Any], *, minimum_confidence: float = 0.78) -> bool:
    """Fail closed on real source packaging, but never on our own 2x2 analysis layout."""
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
            "source_frame_collage",
            "multi_clip_sequence",
            "compilation_or_repost_style",
        )
    )
    return (
        bool(decision.get("approved"))
        and confidence >= max(float(minimum_confidence), 0.0)
        and bool(decision.get("cat_visible"))
        and not forbidden
    )


def review_clean_youtube_footage(
    settings: Settings,
    ledger: BudgetLedger,
    *,
    video: Path,
    slot: int,
    video_id: str,
    title: str = "",
    creator: str = "",
) -> dict[str, Any]:
    """Review temporal samples without mistaking the generated contact sheet for source editing."""
    video = video.resolve()
    if not video.exists() or video.stat().st_size <= 0:
        raise FileNotFoundError(f"YouTube clean-footage source not found: {video}")

    material_cfg = settings.raw.get("materials", {})
    model = str(material_cfg.get("vision_model", "gpt-5.6-luna"))
    minimum_confidence = float(material_cfg.get("youtube_clean_vision_min_confidence", 0.78))
    estimated = float(material_cfg.get("youtube_clean_vision_max_estimated_cost_usd", 0.02))
    source_hash = _v1._sha256(video)

    review_dir = settings.runtime_dir / "slots" / f"{int(slot):02d}" / "youtube_clean_reviews"
    review_dir.mkdir(parents=True, exist_ok=True)
    safe_id = "".join(ch for ch in str(video_id) if ch.isalnum() or ch in "-_") or source_hash[:12]
    review_path = review_dir / f"{safe_id}.json"
    preview_path = review_dir / f"{safe_id}.jpg"

    if review_path.exists():
        try:
            cached = json.loads(review_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            cached = {}
        if (
            cached.get("version") == _CLEAN_REVIEW_VERSION
            and cached.get("prompt_version") == _CLEAN_PROMPT_VERSION
            and cached.get("source_sha256") == source_hash
        ):
            return cached

    api_key = os.getenv("OPENAI_API_KEY", "").strip()
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY is not set; cannot run YouTube clean-footage vision gate")

    _v1.build_clean_contact_sheet(video, preview_path)
    ledger.ensure_room(estimated)

    prompt = (
        "Review a 2x2 ANALYSIS CONTACT SHEET that OUR PIPELINE generated from ONE candidate cat video. "
        "CRITICAL: the outer 2x2 arrangement is NOT present in the source video. Each tile is a separate timestamp "
        "sampled from the same video. Never reject merely because the provided analysis image has four tiles, and "
        "never call the source a split-screen/collage merely because those four analysis tiles differ. "
        "Set source_frame_collage=true ONLY if an INDIVIDUAL TILE itself visibly contains a split-screen, collage, "
        "ranking panel, stacked source videos, or similar simultaneous multi-source layout. "
        "Set multi_clip_sequence=true ONLY when the timestamps give strong visual evidence that the source video "
        "sequentially stitches together unrelated clips (for example clearly different cats, locations, camera "
        "sources, or hard-edited scenes that cannot reasonably be one continuous event). Normal motion, camera "
        "movement, reframing, or ordinary changes over time are NOT enough. If the temporal evidence is ambiguous, "
        "do not infer a multi-clip sequence from the contact-sheet layout itself. "
        "This is a strict CLEAN-SOURCE presentation gate, not a copyright/licensing decision. Approve only if the "
        "footage looks relatively raw/self-contained and does not visibly carry another social-media account's "
        "packaging. Reject if any sampled source frame shows a prominent creator/channel name, @handle, profile or "
        "avatar/banner, social-platform watermark/UI, TikTok/Instagram/Reels/Shorts-style account chrome, or a large "
        "added meme/headline caption. Small incidental text naturally present in the filmed scene (signs, labels, "
        "plates) is allowed. A tiny non-social camera/date overlay may be tolerated. The cat must be clearly visible "
        "in at least one tile. compilation_or_repost_style should summarize actual SOURCE evidence only; the generated "
        "2x2 analysis sheet itself is never such evidence. Do not infer legal ownership from the image. "
        f"YouTube metadata for context only: title={title!r}; uploader={creator!r}."
    )
    payload = {
        "model": model,
        "input": [
            {
                "role": "user",
                "content": [
                    {"type": "input_text", "text": prompt},
                    {"type": "input_image", "image_url": _v1._data_url(preview_path), "detail": "high"},
                ],
            }
        ],
        "reasoning": {"effort": "none"},
        "text": {
            "format": {
                "type": "json_schema",
                "name": "vv_youtube_clean_footage_v2",
                "strict": True,
                "schema": CLEAN_FOOTAGE_SCHEMA,
            },
            "verbosity": "low",
        },
        "max_output_tokens": 650,
        "store": False,
    }
    with httpx.Client(timeout=180) as client:
        response = client.post(
            "https://api.openai.com/v1/responses",
            headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
            json=payload,
        )
    if response.status_code >= 400:
        raise RuntimeError(
            f"YouTube clean-footage vision failed with HTTP {response.status_code}: "
            f"{_v1._response_error_detail(response)}"
        )
    data = response.json()
    decision = json.loads(_v1._extract_output_text(data))
    passed = decision_passes_clean_gate(decision, minimum_confidence=minimum_confidence)

    usage = data.get("usage") or {}
    ledger.record(
        model=model,
        input_tokens=int(usage.get("input_tokens", 0)),
        output_tokens=int(usage.get("output_tokens", 0)),
        purpose=f"slot-{int(slot)}:youtube-clean-footage-v2:{safe_id}",
    )

    result = {
        "version": _CLEAN_REVIEW_VERSION,
        "prompt_version": _CLEAN_PROMPT_VERSION,
        "reviewed_at": datetime.now(timezone.utc).isoformat(),
        "video_id": str(video_id),
        "source_file": str(video),
        "source_sha256": source_hash,
        "preview": str(preview_path.resolve()),
        "review_file": str(review_path.resolve()),
        "model": model,
        "minimum_confidence": minimum_confidence,
        "clean_footage_approved": passed,
        "decision": decision,
    }
    review_path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    return result


def clean_review_clip_metadata(review: dict[str, Any]) -> dict[str, Any]:
    decision = review.get("decision") or {}
    return {
        "clean_footage_approved": bool(review.get("clean_footage_approved")),
        "clean_footage_confidence": float(decision.get("confidence") or 0.0),
        "clean_footage_reason": str(decision.get("reason") or "").strip(),
        "clean_creator_branding": bool(decision.get("creator_branding")),
        "clean_social_ui": bool(decision.get("social_ui")),
        "clean_large_added_caption": bool(decision.get("large_added_caption")),
        "clean_source_frame_collage": bool(decision.get("source_frame_collage")),
        "clean_multi_clip_sequence": bool(decision.get("multi_clip_sequence")),
        "clean_compilation_or_repost_style": bool(decision.get("compilation_or_repost_style")),
        "clean_review_file": str(review.get("review_file") or ""),
        "clean_review_model": str(review.get("model") or ""),
        "clean_review_version": int(review.get("version") or 0),
        "clean_review_prompt_version": str(review.get("prompt_version") or ""),
        "clean_source_sha256": str(review.get("source_sha256") or ""),
    }
