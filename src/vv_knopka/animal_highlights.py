from __future__ import annotations

import base64
import hashlib
import json
import os
import shutil
import subprocess
from pathlib import Path
from typing import Any

import httpx

from .budget import BudgetLedger
from .settings import Settings


def candidate_starts(duration: float, segment_seconds: float, count: int = 4) -> list[float]:
    """Evenly spread candidate segment starts across the usable part of a clip."""
    duration = max(float(duration), 0.0)
    segment_seconds = max(float(segment_seconds), 0.1)
    max_start = max(duration - segment_seconds, 0.0)
    if max_start <= 0 or count <= 1:
        return [0.0]
    values = [max_start * index / (count - 1) for index in range(count)]
    unique: list[float] = []
    for value in values:
        rounded = round(value, 3)
        if not unique or abs(unique[-1] - rounded) >= 0.25:
            unique.append(rounded)
    return unique or [0.0]


def _ffmpeg_binary() -> str:
    return os.getenv("IMAGEIO_FFMPEG_EXE", "").strip() or shutil.which("ffmpeg") or "ffmpeg"


def _ffprobe_duration(path: Path) -> float:
    ffprobe = shutil.which("ffprobe")
    if not ffprobe:
        return 0.0
    result = subprocess.run(
        [
            ffprobe,
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
    )
    if result.returncode != 0:
        return 0.0
    try:
        return max(float(result.stdout.strip()), 0.0)
    except ValueError:
        return 0.0


def _contact_sheet(video: Path, start: float, seconds: float, output: Path) -> Path:
    """Create one 3-frame strip representing a candidate time window."""
    output.parent.mkdir(parents=True, exist_ok=True)
    fps = 3.0 / max(seconds, 0.5)
    vf = (
        f"fps={fps:.6f},"
        "scale=320:568:force_original_aspect_ratio=decrease,"
        "pad=320:568:(ow-iw)/2:(oh-ih)/2:color=black,"
        "tile=3x1:padding=4:margin=0"
    )
    command = [
        _ffmpeg_binary(),
        "-y",
        "-ss",
        f"{start:.3f}",
        "-i",
        str(video),
        "-t",
        f"{seconds:.3f}",
        "-vf",
        vf,
        "-frames:v",
        "1",
        "-q:v",
        "4",
        str(output),
    ]
    completed = subprocess.run(command, capture_output=True, text=True, check=False)
    if completed.returncode != 0 or not output.exists() or output.stat().st_size <= 0:
        detail = (completed.stderr or completed.stdout or "").strip()[-1500:]
        raise RuntimeError(f"Could not create highlight preview for {video.name}: {detail}")
    return output


def _data_url(path: Path) -> str:
    encoded = base64.b64encode(path.read_bytes()).decode("ascii")
    return f"data:image/jpeg;base64,{encoded}"


def _extract_output_text(data: dict[str, Any]) -> str:
    if isinstance(data.get("output_text"), str):
        return data["output_text"]
    texts: list[str] = []
    for item in data.get("output", []):
        if not isinstance(item, dict):
            continue
        for content in item.get("content", []):
            if isinstance(content, dict) and isinstance(content.get("text"), str):
                texts.append(content["text"])
    if not texts:
        raise RuntimeError("Highlight review response did not contain text")
    return "".join(texts)


def _manifest_signature(source_manifest: Path, clip_seconds: float) -> str:
    digest = hashlib.sha256()
    digest.update(source_manifest.read_bytes())
    digest.update(f"|clip_seconds={clip_seconds:.3f}|highlight-v2".encode("utf-8"))
    return digest.hexdigest()


def select_highlights(
    settings: Settings,
    ledger: BudgetLedger,
    *,
    source_manifest: Path,
    slot_dir: Path,
    language: str,
    editorial_plan: dict[str, Any],
    clip_seconds: float,
) -> Path:
    """Pick engaging time windows, captions and ordering using low-cost vision."""
    output = slot_dir / "highlights.json"
    signature = _manifest_signature(source_manifest, clip_seconds)
    if output.exists():
        try:
            cached = json.loads(output.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            cached = {}
        if cached.get("source_signature") == signature and cached.get("version") == 2:
            return output

    raw = json.loads(source_manifest.read_text(encoding="utf-8"))
    clips = raw.get("clips") or []
    if len(clips) < 3:
        raise RuntimeError("Highlight editor requires at least 3 source clips")

    preview_dir = slot_dir / "highlight_previews"
    preview_dir.mkdir(parents=True, exist_ok=True)

    clip_candidates: list[dict[str, Any]] = []
    user_content: list[dict[str, Any]] = []
    language_name = "Russian" if language == "ru" else "English"
    prompt = (
        "You are editing a cute-cat vertical Short. For EACH clip, choose the candidate segment that is "
        "most visually engaging, cute, funny, or action-focused while keeping the cat clearly visible. "
        "Each candidate image is a 3-frame contact sheet from one time window, so prefer a window that shows "
        "an actual action/reaction rather than an idle setup. Then order the clips so the strongest hook is first "
        "and the montage has variety. Write one very short playful on-screen caption per selected clip in "
        f"{language_name}; maximum 5 words, no hashtags, no emojis, no fake claims. "
        "Captions should relate to what is visibly happening, not be generic. "
        f"Editorial concept: title={editorial_plan.get('title')!r}; hook={editorial_plan.get('hook')!r}; "
        f"editorial_value={editorial_plan.get('editorial_value')!r}."
    )
    user_content.append({"type": "input_text", "text": prompt})

    for clip_index, item in enumerate(clips, 1):
        video = Path(str(item["file"])).resolve()
        duration = float(item.get("duration") or 0.0)
        if duration <= 0:
            duration = _ffprobe_duration(video)
        if duration <= 0:
            raise RuntimeError(f"Could not determine duration for {video}")
        starts = candidate_starts(duration, clip_seconds, 4)
        candidate_entries: list[dict[str, Any]] = []
        for candidate_index, start in enumerate(starts):
            label = chr(ord("A") + candidate_index)
            preview = preview_dir / f"clip-{clip_index:02d}-{label}.jpg"
            _contact_sheet(video, start, clip_seconds, preview)
            candidate_entries.append({"label": label, "start": start, "preview": str(preview)})
            user_content.append(
                {
                    "type": "input_text",
                    "text": f"Clip {clip_index}, candidate {label}, start {start:.2f}s",
                }
            )
            user_content.append(
                {"type": "input_image", "image_url": _data_url(preview), "detail": "low"}
            )
        clip_candidates.append(
            {
                "clip_index": clip_index,
                "file": str(video),
                "duration": duration,
                "candidates": candidate_entries,
            }
        )

    count = len(clips)
    selection_item_schema = {
        "type": "object",
        "additionalProperties": False,
        "required": ["clip_index", "candidate", "score", "description", "caption"],
        "properties": {
            "clip_index": {"type": "integer", "minimum": 1, "maximum": count},
            "candidate": {"type": "string", "pattern": "^[A-D]$"},
            "score": {"type": "number", "minimum": 0, "maximum": 10},
            "description": {"type": "string"},
            "caption": {"type": "string"},
        },
    }
    schema = {
        "type": "object",
        "additionalProperties": False,
        "required": ["order", "selections"],
        "properties": {
            "order": {
                "type": "array",
                "minItems": count,
                "maxItems": count,
                "items": {"type": "integer", "minimum": 1, "maximum": count},
            },
            "selections": {
                "type": "array",
                "minItems": count,
                "maxItems": count,
                "items": selection_item_schema,
            },
        },
    }

    materials_cfg = settings.raw.get("materials", {})
    model = str(materials_cfg.get("vision_model", "gpt-5.6-luna"))
    estimate = float(materials_cfg.get("highlight_vision_max_estimated_cost_usd", 0.05))
    ledger.ensure_room(estimate)

    payload = {
        "model": model,
        "input": [{"role": "user", "content": user_content}],
        "reasoning": {"effort": "low"},
        "text": {
            "format": {
                "type": "json_schema",
                "name": "vv_animal_highlights",
                "strict": True,
                "schema": schema,
            },
            "verbosity": "low",
        },
        "store": False,
    }
    api_key = os.getenv("OPENAI_API_KEY", "").strip()
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY is not set")

    with httpx.Client(timeout=180) as client:
        response = client.post(
            "https://api.openai.com/v1/responses",
            headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
            json=payload,
        )
        response.raise_for_status()
        data = response.json()

    parsed = json.loads(_extract_output_text(data))
    usage = data.get("usage") or {}
    ledger.record(
        model=model,
        input_tokens=int(usage.get("input_tokens", 0)),
        output_tokens=int(usage.get("output_tokens", 0)),
        purpose=f"slot-highlight:{slot_dir.name}:{language}",
    )

    selections_by_index: dict[int, dict[str, Any]] = {}
    candidates_by_index = {entry["clip_index"]: entry for entry in clip_candidates}
    for selection in parsed.get("selections", []):
        index = int(selection["clip_index"])
        if index in selections_by_index or index not in candidates_by_index:
            continue
        candidate_map = {
            item["label"]: item for item in candidates_by_index[index]["candidates"]
        }
        chosen = candidate_map.get(str(selection["candidate"]))
        if not chosen:
            continue
        selections_by_index[index] = {
            "clip_index": index,
            "candidate": str(selection["candidate"]),
            "start": float(chosen["start"]),
            "score": float(selection["score"]),
            "description": str(selection["description"]).strip(),
            "caption": str(selection["caption"]).strip()[:80],
        }

    if len(selections_by_index) != count:
        raise RuntimeError(
            f"Highlight editor returned {len(selections_by_index)}/{count} valid selections"
        )

    order_raw = [int(value) for value in parsed.get("order", [])]
    order: list[int] = []
    for value in order_raw:
        if value in selections_by_index and value not in order:
            order.append(value)
    for value in range(1, count + 1):
        if value not in order:
            order.append(value)

    result = {
        "version": 2,
        "source_signature": signature,
        "clip_seconds": float(clip_seconds),
        "language": language,
        "order": order,
        "selections": [selections_by_index[index] for index in range(1, count + 1)],
    }
    output.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    return output
