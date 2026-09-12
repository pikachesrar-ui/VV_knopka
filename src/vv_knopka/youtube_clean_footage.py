from __future__ import annotations

import base64
import hashlib
import json
import os
import shutil
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import httpx

from .budget import BudgetLedger
from .settings import Settings


_CLEAN_REVIEW_VERSION = 1
_CLEAN_PROMPT_VERSION = "youtube-clean-footage-v1"

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
        "compilation_or_repost_style": {"type": "boolean"},
        "reason": {"type": "string"},
    },
}


def _ffmpeg_binary() -> str:
    return os.getenv("IMAGEIO_FFMPEG_EXE", "").strip() or shutil.which("ffmpeg") or "ffmpeg"


def _ffprobe_binary() -> str:
    return shutil.which("ffprobe") or "ffprobe"


def _video_duration(path: Path) -> float:
    completed = subprocess.run(
        [
            _ffprobe_binary(),
            "-v",
            "error",
            "-show_entries",
            "format=duration",
            "-of",
            "default=noprint_wrappers=1:nokey=1",
            str(path),
        ],
        capture_output=True,
        text=True,
        check=False,
        timeout=30,
    )
    if completed.returncode != 0:
        return 0.0
    try:
        return max(float(completed.stdout.strip()), 0.0)
    except ValueError:
        return 0.0


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as fh:
        while True:
            chunk = fh.read(1024 * 1024)
            if not chunk:
                break
            digest.update(chunk)
    return digest.hexdigest()


def _data_url(path: Path) -> str:
    encoded = base64.b64encode(path.read_bytes()).decode("ascii")
    return f"data:image/jpeg;base64,{encoded}"


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
        raise RuntimeError("Clean-footage vision response did not contain text")
    return "".join(texts)


def _response_error_detail(response: httpx.Response) -> str:
    try:
        body = response.json()
    except Exception:
        text = (response.text or "").strip().replace("\n", " ")
        return text[:600] or f"HTTP {response.status_code}"
    error = body.get("error") if isinstance(body, dict) else None
    if isinstance(error, dict):
        message = str(error.get("message") or "").strip()
        if message:
            return message[:700]
    return json.dumps(body, ensure_ascii=False)[:700]


def build_clean_contact_sheet(video: Path, output: Path) -> Path:
    """Sample four points across a vertical clip into one 2x2 review sheet."""
    duration = _video_duration(video)
    if duration <= 0:
        raise RuntimeError(f"Could not determine duration for clean-footage review: {video}")
    output.parent.mkdir(parents=True, exist_ok=True)
    fps = 4.0 / max(duration, 1.0)
    vf = (
        f"fps={fps:.8f},"
        "scale=270:480:force_original_aspect_ratio=decrease,"
        "pad=270:480:(ow-iw)/2:(oh-ih)/2:color=black,"
        "tile=2x2:padding=4:margin=0"
    )
    completed = subprocess.run(
        [
            _ffmpeg_binary(),
            "-y",
            "-i",
            str(video),
            "-vf",
            vf,
            "-frames:v",
            "1",
            "-q:v",
            "4",
            str(output),
        ],
        capture_output=True,
        text=True,
        check=False,
        timeout=90,
    )
    if completed.returncode != 0 or not output.exists() or output.stat().st_size <= 0:
        detail = (completed.stderr or completed.stdout or "").strip()[-1200:]
        raise RuntimeError(f"Could not create clean-footage preview for {video.name}: {detail}")
    return output


def decision_passes_clean_gate(decision: dict[str, Any], *, minimum_confidence: float = 0.78) -> bool:
    """Fail closed if the model reports any social/repost packaging signal."""
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
    """Vision gate for clean, minimally packaged YouTube CC source footage.

    This is a presentation/provenance-risk gate, not a copyright determination.
    The YouTube API license check remains separate and mandatory.
    """
    video = video.resolve()
    if not video.exists() or video.stat().st_size <= 0:
        raise FileNotFoundError(f"YouTube clean-footage source not found: {video}")

    material_cfg = settings.raw.get("materials", {})
    model = str(material_cfg.get("vision_model", "gpt-5.6-luna"))
    minimum_confidence = float(material_cfg.get("youtube_clean_vision_min_confidence", 0.78))
    estimated = float(material_cfg.get("youtube_clean_vision_max_estimated_cost_usd", 0.02))
    source_hash = _sha256(video)

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

    build_clean_contact_sheet(video, preview_path)
    ledger.ensure_room(estimated)

    prompt = (
        "Review this 2x2 contact sheet sampled from one candidate cat video. This is a strict CLEAN-SOURCE "
        "presentation gate for a new edited cat compilation; it is NOT a copyright/licensing decision. "
        "Approve only if the footage looks like a relatively raw/self-contained cat clip that can be edited "
        "without visibly carrying another social-media account's packaging. Reject if ANY sampled frame shows "
        "a prominent creator/channel name, @handle, profile/avatar/banner, social-platform watermark or UI, "
        "TikTok/Instagram/Reels/Shorts-style account chrome, a large added meme/headline caption, split-screen "
        "or collage/ranking layout, or obvious already-compiled/repost packaging. Small incidental text that is "
        "naturally present in the filmed scene (street signs, product labels, license plates) is allowed. A tiny "
        "non-social camera/date overlay may be tolerated, but a watermark identifying another account is not. "
        "The cat must be clearly visible in at least one frame. If uncertain, reject. Do not infer ownership or "
        "legal rights from the image. "
        f"YouTube metadata for context only: title={title!r}; uploader={creator!r}."
    )
    payload = {
        "model": model,
        "input": [
            {
                "role": "user",
                "content": [
                    {"type": "input_text", "text": prompt},
                    {"type": "input_image", "image_url": _data_url(preview_path), "detail": "high"},
                ],
            }
        ],
        "reasoning": {"effort": "none"},
        "text": {
            "format": {
                "type": "json_schema",
                "name": "vv_youtube_clean_footage",
                "strict": True,
                "schema": CLEAN_FOOTAGE_SCHEMA,
            },
            "verbosity": "low",
        },
        "max_output_tokens": 500,
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
            f"{_response_error_detail(response)}"
        )
    data = response.json()
    decision = json.loads(_extract_output_text(data))
    passed = decision_passes_clean_gate(decision, minimum_confidence=minimum_confidence)

    usage = data.get("usage") or {}
    ledger.record(
        model=model,
        input_tokens=int(usage.get("input_tokens", 0)),
        output_tokens=int(usage.get("output_tokens", 0)),
        purpose=f"slot-{int(slot)}:youtube-clean-footage:{safe_id}",
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
        "clean_compilation_or_repost_style": bool(decision.get("compilation_or_repost_style")),
        "clean_review_file": str(review.get("review_file") or ""),
        "clean_review_model": str(review.get("model") or ""),
        "clean_review_version": int(review.get("version") or 0),
        "clean_source_sha256": str(review.get("source_sha256") or ""),
    }
