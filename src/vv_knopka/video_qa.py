from __future__ import annotations

import json
import re
import subprocess
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .settings import Settings


QA_SCHEMA_VERSION = 1
CTA_PATTERNS = (
    "like and subscribe",
    "subscribe",
    "follow for",
    "hit the like",
    "поставь лайк",
    "ставь лайк",
    "подпишись",
    "подписывайся",
)
WATERMARK_MARKERS = ("tiktok.com", "vm.tiktok", "douyin.com", "tiktok watermark")


def _check(
    check_id: str,
    status: str,
    message: str,
    *,
    severity: str = "advisory",
    data: dict[str, Any] | None = None,
) -> dict[str, Any]:
    result: dict[str, Any] = {
        "id": check_id,
        "status": status,
        "severity": severity,
        "message": message,
    }
    if data:
        result["data"] = data
    return result


def _run_process(arguments: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        arguments,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )


def _probe_video(video_file: Path) -> dict[str, Any]:
    result = _run_process(
        [
            "ffprobe",
            "-v",
            "error",
            "-show_streams",
            "-show_format",
            "-of",
            "json",
            str(video_file),
        ]
    )
    if result.returncode != 0:
        raise RuntimeError(f"ffprobe failed: {result.stderr.strip()[-1000:]}")
    try:
        return json.loads(result.stdout)
    except json.JSONDecodeError as exc:
        raise RuntimeError("ffprobe returned invalid JSON") from exc


def _duration(probe: dict[str, Any]) -> float:
    values: list[Any] = [(probe.get("format") or {}).get("duration")]
    values.extend(stream.get("duration") for stream in probe.get("streams") or [])
    for value in values:
        try:
            duration = float(value)
        except (TypeError, ValueError):
            continue
        if duration > 0:
            return duration
    return 0.0


def _parse_black_intervals(text: str) -> list[dict[str, float]]:
    pattern = re.compile(
        r"black_start:(-?[\d.]+)\s+black_end:(-?[\d.]+)\s+black_duration:([\d.]+)"
    )
    return [
        {"start": float(start), "end": float(end), "duration": float(duration)}
        for start, end, duration in pattern.findall(text)
    ]


def _detect_black(video_file: Path, *, window_seconds: float, from_end: bool) -> list[dict[str, float]]:
    arguments = ["ffmpeg", "-hide_banner", "-nostats"]
    if from_end:
        arguments.extend(["-sseof", f"-{window_seconds:.3f}"])
    arguments.extend(["-i", str(video_file)])
    if not from_end:
        arguments.extend(["-t", f"{window_seconds:.3f}"])
    arguments.extend(
        [
            "-an",
            "-vf",
            "blackdetect=d=0.20:pix_th=0.10",
            "-f",
            "null",
            "-",
        ]
    )
    result = _run_process(arguments)
    return _parse_black_intervals(result.stderr)


def _parse_crops(text: str) -> list[tuple[int, int, int, int]]:
    return [
        tuple(int(value) for value in match)
        for match in re.findall(r"crop=(\d+):(\d+):(\d+):(\d+)", text)
    ]


def _detect_crop(video_file: Path, *, duration: float) -> tuple[int, int, int, int] | None:
    sample_seconds = min(max(duration, 1.0), 12.0)
    result = _run_process(
        [
            "ffmpeg",
            "-hide_banner",
            "-nostats",
            "-i",
            str(video_file),
            "-t",
            f"{sample_seconds:.3f}",
            "-an",
            "-vf",
            "fps=1,cropdetect=limit=24:round=2:reset=0",
            "-f",
            "null",
            "-",
        ]
    )
    crops = _parse_crops(result.stderr)
    return Counter(crops).most_common(1)[0][0] if crops else None


def _parse_ebur128(text: str) -> tuple[float | None, float | None]:
    loudness = re.findall(r"\bI:\s*(-?[\d.]+)\s+LUFS", text)
    peak = re.findall(r"\bPeak:\s*(-?[\d.]+)\s+dBFS", text)
    return (
        float(loudness[-1]) if loudness else None,
        float(peak[-1]) if peak else None,
    )


def _analyze_audio(video_file: Path) -> tuple[float | None, float | None]:
    result = _run_process(
        [
            "ffmpeg",
            "-hide_banner",
            "-nostats",
            "-i",
            str(video_file),
            "-map",
            "0:a:0",
            "-af",
            "ebur128=peak=true",
            "-f",
            "null",
            "-",
        ]
    )
    return _parse_ebur128(result.stderr)


def _load_json(path: Path) -> dict[str, Any]:
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return raw if isinstance(raw, dict) else {}


def _source_text(slot_dir: Path) -> str:
    values: list[str] = []
    for name in (
        "sources.json",
        "ai_materials.json",
        "animal_audio_sources.json",
        "cat-edit.json",
    ):
        path = slot_dir / name
        if not path.exists():
            continue
        try:
            values.append(path.read_text(encoding="utf-8"))
        except OSError:
            continue
    return "\n".join(values).casefold()


def _subtitle_timing_check(slot_dir: Path, duration: float) -> dict[str, Any]:
    candidates = sorted(slot_dir.glob("*.srt"))
    if not candidates:
        return _check(
            "subtitle_sync",
            "SKIP",
            "No standalone SRT timing file; burned-in subtitle sync needs later frame/audio analysis.",
        )
    text = candidates[0].read_text(encoding="utf-8-sig", errors="replace")
    matches = re.findall(
        r"(\d{2}):(\d{2}):(\d{2})[,.](\d{3})\s+-->\s+"
        r"(\d{2}):(\d{2}):(\d{2})[,.](\d{3})",
        text,
    )
    if not matches:
        return _check("subtitle_sync", "WARN", "SRT exists but no valid timing ranges were parsed.")
    ranges: list[tuple[float, float]] = []
    for values in matches:
        numbers = [int(value) for value in values]
        start = numbers[0] * 3600 + numbers[1] * 60 + numbers[2] + numbers[3] / 1000
        end = numbers[4] * 3600 + numbers[5] * 60 + numbers[6] + numbers[7] / 1000
        ranges.append((start, end))
    valid = all(start >= 0 and end > start for start, end in ranges)
    ordered = all(ranges[index][0] >= ranges[index - 1][0] for index in range(1, len(ranges)))
    within_video = ranges[-1][1] <= duration + 0.75
    if valid and ordered and within_video:
        return _check(
            "subtitle_sync",
            "PASS",
            f"{len(ranges)} subtitle ranges are ordered and end within the video.",
            data={"file": str(candidates[0]), "last_end_seconds": round(ranges[-1][1], 3)},
        )
    return _check(
        "subtitle_sync",
        "WARN",
        "Subtitle timing ranges are invalid, unordered, or extend past the video.",
        data={"file": str(candidates[0]), "last_end_seconds": round(ranges[-1][1], 3)},
    )


def _text_outro_check(slot_dir: Path, metadata: dict[str, Any]) -> dict[str, Any]:
    pipeline = str(metadata.get("pipeline") or "")
    profile = str(metadata.get("editorial_profile") or "")
    if pipeline == "ai_short":
        plan = _load_json(slot_dir / "plan.json")
        tail = " ".join(str(plan.get("script") or "").casefold().split()[-24:])
        matched = [pattern for pattern in CTA_PATTERNS if pattern in tail]
        if matched:
            return _check(
                "outro_text",
                "FAIL",
                "Script tail contains a like/follow/subscribe CTA.",
                severity="critical",
                data={"matched": matched},
            )
        return _check("outro_text", "PASS", "No like/follow/subscribe CTA found in the script tail.")

    episode = _load_json(slot_dir / "episode.json")
    end_text = str(episode.get("end_text") or "").strip()
    if profile == "direct_v1":
        return _check("outro_text", "PASS", "direct_v1 cat renderer does not use an outro card.")
    if end_text:
        return _check(
            "outro_text",
            "WARN",
            "Legacy cat episode metadata contains an end card; retained for historical videos only.",
            data={"end_text": end_text},
        )
    return _check("outro_text", "PASS", "No configured outro text was found.")


def _visual_pacing_check(settings: Settings, slot_dir: Path, metadata: dict[str, Any]) -> dict[str, Any]:
    pipeline = str(metadata.get("pipeline") or "")
    if pipeline == "ai_short":
        seconds = float(settings.raw.get("editorial", {}).get("ai_clip_seconds", 4))
        status = "PASS" if 3.5 <= seconds <= 6.5 else "WARN"
        return _check(
            "visual_pacing",
            status,
            f"Configured AI visual segment length is {seconds:.1f}s.",
            data={"seconds_per_visual": seconds},
        )
    edit = _load_json(slot_dir / "cat-edit.json")
    selections = edit.get("selections") or []
    configured = float(settings.raw.get("animal", {}).get("clip_seconds", 5))
    status = "PASS" if selections and 3.5 <= configured <= 6.5 else "WARN"
    return _check(
        "visual_pacing",
        status,
        f"Cat cut has {len(selections)} selected moments at about {configured:.1f}s each.",
        data={"moments": len(selections), "seconds_per_visual": configured},
    )


def _failure_report(video_file: Path, metadata: dict[str, Any], message: str) -> dict[str, Any]:
    check = _check("qa_runtime", "FAIL", message, severity="critical")
    return {
        "schema_version": QA_SCHEMA_VERSION,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "mode": "shadow",
        "video_file": str(video_file),
        "slot": int(metadata.get("slot") or 0),
        "pipeline": metadata.get("pipeline"),
        "editorial_profile": metadata.get("editorial_profile"),
        "summary": {"status": "FAIL", "critical_failures": 1, "warnings": 0, "checks": 1},
        "checks": [check],
    }


def run_video_qa(settings: Settings, video_file: Path, metadata: dict[str, Any]) -> dict[str, Any]:
    qa_cfg = settings.raw.get("qa", {})
    mode = str(qa_cfg.get("mode") or "shadow")
    slot = int(metadata.get("slot") or 0)
    slot_dir = settings.runtime_dir / "slots" / f"{slot:02d}"
    probe = _probe_video(video_file)
    streams = probe.get("streams") or []
    video_stream = next((stream for stream in streams if stream.get("codec_type") == "video"), None)
    audio_stream = next((stream for stream in streams if stream.get("codec_type") == "audio"), None)
    duration = _duration(probe)
    checks: list[dict[str, Any]] = []

    if video_stream is None:
        checks.append(_check("video_stream", "FAIL", "No video stream.", severity="critical"))
        width = height = 0
    else:
        checks.append(_check("video_stream", "PASS", "Video stream is present."))
        width = int(video_stream.get("width") or 0)
        height = int(video_stream.get("height") or 0)

    if (width, height) == (1080, 1920):
        checks.append(_check("resolution", "PASS", "Resolution is exactly 1080x1920."))
    else:
        checks.append(
            _check(
                "resolution",
                "FAIL",
                f"Expected 1080x1920, found {width}x{height}.",
                severity="critical",
                data={"width": width, "height": height},
            )
        )

    recommended_min = float(qa_cfg.get("recommended_min_seconds", 25))
    recommended_max = float(qa_cfg.get("recommended_max_seconds", 35))
    hard_min = float(qa_cfg.get("hard_min_seconds", 10))
    hard_max = float(qa_cfg.get("hard_max_seconds", 60))
    if duration < hard_min or duration > hard_max:
        checks.append(
            _check(
                "duration",
                "FAIL",
                f"Duration {duration:.2f}s is outside hard range {hard_min:.0f}-{hard_max:.0f}s.",
                severity="critical",
                data={"duration_seconds": round(duration, 3)},
            )
        )
    elif recommended_min <= duration <= recommended_max:
        checks.append(
            _check(
                "duration",
                "PASS",
                f"Duration {duration:.2f}s is inside recommended range.",
                data={"duration_seconds": round(duration, 3)},
            )
        )
    else:
        checks.append(
            _check(
                "duration",
                "WARN",
                f"Duration {duration:.2f}s is safe but outside recommended {recommended_min:.0f}-{recommended_max:.0f}s.",
                data={"duration_seconds": round(duration, 3)},
            )
        )

    if video_stream is not None:
        crop = _detect_crop(video_file, duration=duration)
        if crop is None:
            checks.append(_check("black_bars", "SKIP", "cropdetect returned no stable crop."))
        else:
            crop_width, crop_height, offset_x, offset_y = crop
            width_ratio = crop_width / width if width else 0
            height_ratio = crop_height / height if height else 0
            if width_ratio < 0.97 or height_ratio < 0.97:
                checks.append(
                    _check(
                        "black_bars",
                        "WARN",
                        "Repeated cropdetect result suggests persistent dark borders.",
                        data={
                            "crop": f"{crop_width}:{crop_height}:{offset_x}:{offset_y}",
                            "width_ratio": round(width_ratio, 3),
                            "height_ratio": round(height_ratio, 3),
                        },
                    )
                )
            else:
                checks.append(_check("black_bars", "PASS", "No persistent black bars detected."))

        opening_black = _detect_black(video_file, window_seconds=1.5, from_end=False)
        black_open = any(item["start"] <= 0.05 and item["duration"] >= 0.25 for item in opening_black)
        checks.append(
            _check(
                "first_frame",
                "WARN" if black_open else "PASS",
                "Opening contains at least 0.25s of black/title-card-like frames."
                if black_open
                else "Opening is not predominantly black.",
                data={"black_intervals": opening_black},
            )
        )
        ending_black = _detect_black(video_file, window_seconds=2.0, from_end=True)
        black_tail = any(item["duration"] >= 0.50 for item in ending_black)
        checks.append(
            _check(
                "black_tail",
                "WARN" if black_tail else "PASS",
                "Final two seconds contain a long black segment."
                if black_tail
                else "No long black segment detected at the end.",
                data={"black_intervals": ending_black},
            )
        )

    if audio_stream is None:
        checks.append(_check("audio_stream", "FAIL", "No audio stream.", severity="critical"))
    else:
        checks.append(_check("audio_stream", "PASS", "Audio stream is present."))
        loudness, peak = _analyze_audio(video_file)
        if peak is None:
            checks.append(_check("audio_peak", "SKIP", "True peak could not be parsed."))
        elif peak >= 0:
            checks.append(
                _check(
                    "audio_peak",
                    "FAIL",
                    f"True peak is {peak:.1f} dBFS; clipping risk.",
                    severity="critical",
                    data={"peak_dbfs": peak},
                )
            )
        elif peak > -0.5:
            checks.append(
                _check(
                    "audio_peak",
                    "WARN",
                    f"True peak is {peak:.1f} dBFS; headroom is very small.",
                    data={"peak_dbfs": peak},
                )
            )
        else:
            checks.append(
                _check("audio_peak", "PASS", f"True peak is {peak:.1f} dBFS.", data={"peak_dbfs": peak})
            )

        if loudness is None:
            checks.append(_check("integrated_loudness", "SKIP", "Integrated loudness could not be parsed."))
        elif -24 <= loudness <= -10:
            checks.append(
                _check(
                    "integrated_loudness",
                    "PASS",
                    f"Integrated loudness is {loudness:.1f} LUFS.",
                    data={"lufs": loudness},
                )
            )
        else:
            checks.append(
                _check(
                    "integrated_loudness",
                    "WARN",
                    f"Integrated loudness {loudness:.1f} LUFS is outside the review band -24 to -10.",
                    data={"lufs": loudness},
                )
            )

    pipeline = str(metadata.get("pipeline") or "")
    if pipeline == "ai_short":
        music = settings.raw.get("music", {})
        volume = float(music.get("ai_volume", 0.10))
        ducking = bool(music.get("ai_ducking", music.get("ducking", False)))
        status = "PASS" if volume <= 0.15 and ducking else "WARN"
        checks.append(
            _check(
                "voice_music_policy",
                status,
                f"AI mix configuration: music={volume:.2f}, voice ducking={ducking}. Final stem ratio is not measurable from one mixed track.",
                data={"music_volume": volume, "ducking": ducking},
            )
        )
    else:
        checks.append(_check("voice_music_policy", "SKIP", "Cat compilations have no narration stem."))

    if pipeline == "ai_short" and bool(settings.raw.get("video", {}).get("subtitle_enabled", False)):
        position = float(settings.raw.get("video", {}).get("subtitle_custom_position", 74))
        font_size = float(settings.raw.get("video", {}).get("subtitle_font_size", 52))
        estimated_bottom = position + font_size / 1920 * 100
        status = "PASS" if estimated_bottom <= 80 else "WARN"
        checks.append(
            _check(
                "safe_zone_bottom",
                status,
                f"Configured subtitle bottom estimate is {estimated_bottom:.1f}% of frame height.",
                data={"position_percent": position, "estimated_bottom_percent": round(estimated_bottom, 2)},
            )
        )
    else:
        checks.append(_check("safe_zone_bottom", "SKIP", "No generated narration subtitles for this pipeline."))

    checks.append(
        _check(
            "safe_zone_right",
            "SKIP",
            "Right-side 15% subject safety needs object/text detection; no claim is fabricated in local v0.",
        )
    )
    checks.append(_subtitle_timing_check(slot_dir, duration))
    checks.append(_text_outro_check(slot_dir, metadata))
    checks.append(_visual_pacing_check(settings, slot_dir, metadata))

    source_text = _source_text(slot_dir)
    matched_markers = [marker for marker in WATERMARK_MARKERS if marker in source_text]
    if matched_markers:
        checks.append(
            _check(
                "watermark_source",
                "FAIL",
                "Source metadata contains a TikTok/Douyin/watermark marker.",
                severity="critical",
                data={"matched": matched_markers},
            )
        )
    else:
        checks.append(
            _check(
                "watermark_source",
                "SKIP",
                "No risky source marker found; pixel-level watermark detection is not available in local v0.",
            )
        )

    critical_failures = sum(
        1 for item in checks if item["status"] == "FAIL" and item["severity"] == "critical"
    )
    warnings = sum(1 for item in checks if item["status"] in {"WARN", "SKIP"})
    if any(item["status"] == "FAIL" for item in checks):
        overall = "FAIL"
    elif warnings:
        overall = "WARN"
    else:
        overall = "PASS"
    return {
        "schema_version": QA_SCHEMA_VERSION,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "mode": mode,
        "video_file": str(video_file.resolve()),
        "slot": slot,
        "pipeline": metadata.get("pipeline"),
        "editorial_profile": metadata.get("editorial_profile"),
        "summary": {
            "status": overall,
            "critical_failures": critical_failures,
            "warnings": warnings,
            "checks": len(checks),
        },
        "checks": checks,
    }


def _slot_number(path: Path) -> int:
    match = re.match(r"slot-(\d+)-", path.name)
    return int(match.group(1)) if match else 10**9


def qa_report_path(video_file: Path) -> Path:
    return video_file.with_suffix(".qa.json")


def _write_report(video_file: Path, report: dict[str, Any]) -> Path:
    path = qa_report_path(video_file)
    path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    return path


def qa_ready(
    settings: Settings,
    *,
    limit: int | None = None,
    newest: bool = False,
    include_uploaded: bool = False,
) -> list[dict[str, Any]]:
    if not bool(settings.raw.get("qa", {}).get("enabled", True)):
        return []
    ready = settings.runtime_dir / "ready_for_review"
    if not ready.exists():
        return []
    metadata_paths = sorted(ready.glob("slot-*.upload.json"), key=_slot_number, reverse=newest)
    results: list[dict[str, Any]] = []
    for metadata_path in metadata_paths:
        receipt = metadata_path.with_suffix(".youtube.json")
        if receipt.exists() and not include_uploaded:
            continue
        metadata = _load_json(metadata_path)
        configured = str(metadata.get("video_file") or "").strip()
        fallback = metadata_path.with_name(metadata_path.name.removesuffix(".upload.json") + ".mp4")
        video_file = Path(configured) if configured else fallback
        try:
            if not video_file.exists():
                raise FileNotFoundError(f"video file not found: {video_file}")
            report = run_video_qa(settings, video_file, metadata)
        except Exception as exc:
            report = _failure_report(video_file, metadata, f"{type(exc).__name__}: {exc}")
        report_path = _write_report(video_file, report)
        results.append({**report, "report_file": str(report_path)})
        if limit is not None and len(results) >= max(int(limit), 0):
            break
    return results
