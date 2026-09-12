from __future__ import annotations

import json
import math
import os
import shutil
import subprocess
import wave
from array import array
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .settings import Settings


_PROVIDER_LICENSES = {
    "pexels": "Pexels License",
    "pixabay": "Pixabay Content License",
}


@dataclass(frozen=True)
class SourceClip:
    file: Path
    source_url: str
    license: str
    commercial_use_allowed: bool
    creator: str = ""
    provider: str = ""
    duration: float = 0.0


def load_sources(path: Path) -> list[SourceClip]:
    raw = json.loads(path.read_text(encoding="utf-8"))
    clips = [
        SourceClip(
            file=Path(item["file"]).resolve()
            if Path(item["file"]).is_absolute()
            else (path.parent / item["file"]).resolve(),
            source_url=item["source_url"],
            license=item["license"],
            commercial_use_allowed=bool(item["commercial_use_allowed"]),
            creator=item.get("creator", ""),
            provider=item.get("provider", ""),
            duration=float(item.get("duration") or 0.0),
        )
        for item in raw["clips"]
    ]
    if len(clips) < 3:
        raise ValueError("animal compilation needs at least 3 source clips")
    return clips


def write_stock_sources_manifest(
    settings: Settings,
    materials: list[dict[str, Any]],
    output: Path,
    *,
    max_clips: int = 6,
    min_unique_clips: int = 5,
) -> Path:
    """Turn vision-approved stock into an explicit licensed source manifest."""
    local_dir = Path(
        os.getenv(
            "MPT_LOCAL_VIDEOS_DIR",
            str(settings.root / "MoneyPrinterTurbo" / "storage" / "local_videos"),
        )
    ).resolve()

    clips: list[dict[str, Any]] = []
    seen: set[tuple[str, str]] = set()
    for material in materials:
        provider = str(material.get("provider") or "").lower().strip()
        filename = str(material.get("url") or "").strip()
        info = dict(material.get("source_info") or {})
        page_url = str(info.get("page_url") or "").strip()
        license_name = _PROVIDER_LICENSES.get(provider)
        identity = (provider, filename)
        if not provider or not filename or not page_url or not license_name or identity in seen:
            continue
        source_file = local_dir / filename
        if not source_file.exists() or source_file.stat().st_size <= 0:
            continue
        clips.append(
            {
                "file": str(source_file),
                "source_url": page_url,
                "license": license_name,
                "commercial_use_allowed": True,
                "creator": str(info.get("creator") or ""),
                "provider": provider,
                "provider_id": info.get(f"{provider}_id"),
                "duration": float(material.get("duration") or info.get("duration") or 0.0),
                "vision_confidence": info.get("vision_confidence"),
                "vision_reason": info.get("vision_reason"),
            }
        )
        seen.add(identity)
        if len(clips) >= max_clips:
            break

    if len(clips) < min_unique_clips:
        raise RuntimeError(
            f"Animal stock gate has only {len(clips)} unique licensed clips; "
            f"need at least {min_unique_clips} before rendering."
        )

    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(
            {"source_policy": "vision-approved licensed stock", "clips": clips},
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    return output


def _ffprobe_has_audio(path: Path) -> bool:
    ffprobe = shutil.which("ffprobe")
    if not ffprobe:
        return False
    result = subprocess.run(
        [
            ffprobe,
            "-v",
            "error",
            "-select_streams",
            "a:0",
            "-show_entries",
            "stream=index",
            "-of",
            "csv=p=0",
            str(path),
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    return result.returncode == 0 and bool(result.stdout.strip())


def _system_font() -> Path | None:
    if os.name == "nt":
        root = Path(os.environ.get("WINDIR", r"C:\Windows")) / "Fonts"
        for name in ("arialbd.ttf", "segoeuib.ttf", "arial.ttf", "segoeui.ttf"):
            path = root / name
            if path.exists():
                return path
    for candidate in (
        Path("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"),
        Path("/usr/share/fonts/truetype/liberation2/LiberationSans-Bold.ttf"),
    ):
        if candidate.exists():
            return candidate
    return None


def _escape_filter_path(path: Path) -> str:
    return path.resolve().as_posix().replace(":", r"\:")


def _escape_drawtext(text: str) -> str:
    return (
        text.replace("\\", r"\\")
        .replace(":", r"\:")
        .replace("'", r"\'")
        .replace("%", r"\%")
        .replace(",", r"\,")
        .replace("[", r"\[")
        .replace("]", r"\]")
    )


def _load_highlights(
    path: Path | None,
    clip_count: int,
) -> tuple[list[int], dict[int, dict[str, Any]]]:
    default_order = list(range(1, clip_count + 1))
    if path is None or not path.exists():
        return default_order, {}
    raw = json.loads(path.read_text(encoding="utf-8"))
    selections: dict[int, dict[str, Any]] = {}
    for item in raw.get("selections", []):
        try:
            index = int(item["clip_index"])
        except (KeyError, TypeError, ValueError):
            continue
        if 1 <= index <= clip_count:
            selections[index] = dict(item)
    order: list[int] = []
    for value in raw.get("order", []):
        try:
            index = int(value)
        except (TypeError, ValueError):
            continue
        if 1 <= index <= clip_count and index not in order:
            order.append(index)
    for index in default_order:
        if index not in order:
            order.append(index)
    return order, selections


def _write_pcm_stereo(path: Path, samples: array, sample_rate: int = 48000) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(path), "wb") as handle:
        handle.setnchannels(2)
        handle.setsampwidth(2)
        handle.setframerate(sample_rate)
        handle.writeframes(samples.tobytes())


def _generate_playful_bgm(path: Path, duration: float, sample_rate: int = 48000) -> Path:
    """Create a quiet copyright-free bell-like backing track procedurally."""
    total = max(int(duration * sample_rate), 1)
    note_seconds = 1.15
    notes = (523.25, 659.25, 783.99, 659.25, 587.33, 698.46, 880.00, 698.46)
    pcm = array("h")
    for frame in range(total):
        t = frame / sample_rate
        note_index = int(t / note_seconds) % len(notes)
        local = t % note_seconds
        frequency = notes[note_index]
        attack = min(local / 0.025, 1.0)
        envelope = attack * math.exp(-2.8 * local)
        tremolo = 0.88 + 0.12 * math.sin(2 * math.pi * 0.35 * t)
        tone = (
            math.sin(2 * math.pi * frequency * t)
            + 0.32 * math.sin(2 * math.pi * frequency * 2.0 * t)
            + 0.12 * math.sin(2 * math.pi * frequency * 3.0 * t)
        )
        value = max(-1.0, min(1.0, 0.105 * envelope * tremolo * tone))
        pan = 0.08 * math.sin(2 * math.pi * 0.07 * t)
        pcm.append(int(value * (1.0 - pan) * 32767))
        pcm.append(int(value * (1.0 + pan) * 32767))
    _write_pcm_stereo(path, pcm, sample_rate)
    return path


def _meow_wave(sample_rate: int, variant: int = 0) -> list[float]:
    duration = 0.58
    total = int(duration * sample_rate)
    result: list[float] = []
    base_shift = (variant % 3 - 1) * 55.0
    phase = 0.0
    for frame in range(total):
        t = frame / sample_rate
        if t < 0.18:
            frequency = 610.0 + base_shift + (260.0 * t / 0.18)
        else:
            frequency = 870.0 + base_shift - (330.0 * (t - 0.18) / (duration - 0.18))
        frequency += 18.0 * math.sin(2 * math.pi * 18.0 * t)
        phase += 2 * math.pi * frequency / sample_rate
        attack = min(t / 0.035, 1.0)
        release = max(0.0, 1.0 - max(t - 0.32, 0.0) / (duration - 0.32))
        envelope = attack * (0.92 if t < 0.32 else release**1.6)
        tone = math.sin(phase) + 0.30 * math.sin(2 * phase) + 0.10 * math.sin(3 * phase)
        result.append(max(-1.0, min(1.0, 0.34 * envelope * tone)))
    return result


def _generate_meow_timeline(
    path: Path,
    duration: float,
    cut_times: list[float],
    sample_rate: int = 48000,
) -> Path:
    total_frames = max(int(duration * sample_rate), 1)
    pcm = array("h", [0]) * (total_frames * 2)
    for number, cut in enumerate(cut_times):
        meow = _meow_wave(sample_rate, number)
        start_frame = max(int((cut - 0.10) * sample_rate), 0)
        for offset, value in enumerate(meow):
            frame = start_frame + offset
            if frame >= total_frames:
                break
            sample = int(value * 32767)
            left_index = frame * 2
            right_index = left_index + 1
            pcm[left_index] = max(-32768, min(32767, pcm[left_index] + sample))
            pcm[right_index] = max(-32768, min(32767, pcm[right_index] + sample))
    _write_pcm_stereo(path, pcm, sample_rate)
    return path


def render_compilation(
    settings: Settings,
    source_manifest: Path,
    output: Path,
    *,
    highlight_manifest: Path | None = None,
) -> Path:
    """Render selected highlights and mix source audio + quiet music + soft meows."""
    if shutil.which("ffmpeg") is None:
        raise RuntimeError("ffmpeg is not on PATH")
    clips = load_sources(source_manifest)
    if not all(c.commercial_use_allowed and c.source_url and c.license for c in clips):
        raise ValueError("every source clip must have provenance and commercial-use permission")
    missing = [str(c.file) for c in clips if not c.file.exists()]
    if missing:
        raise FileNotFoundError("missing source clips: " + ", ".join(missing))

    work = settings.runtime_dir / "tmp" / output.stem
    work.mkdir(parents=True, exist_ok=True)
    animal_cfg = settings.raw.get("animal", {})
    target = float(animal_cfg.get("clip_seconds", 5))
    lufs = float(settings.raw["audio"]["compilation_lufs"])
    peak = float(settings.raw["audio"]["true_peak_db"])
    caption_size = int(animal_cfg.get("caption_font_size", 58))
    caption_y = float(animal_cfg.get("caption_y", 0.76))
    source_audio_volume = float(animal_cfg.get("source_audio_volume", 0.75))
    bgm_volume = float(animal_cfg.get("bgm_volume", 0.55))
    meow_volume = float(animal_cfg.get("meow_volume", 0.75))

    order, selections = _load_highlights(highlight_manifest, len(clips))
    font = _system_font()

    normalized: list[Path] = []
    for sequence_index, clip_index in enumerate(order, 1):
        clip = clips[clip_index - 1]
        selection = selections.get(clip_index, {})
        start = max(float(selection.get("start") or 0.0), 0.0)
        caption = str(selection.get("caption") or "").strip()
        dst = work / f"{sequence_index:02d}.mp4"
        fade_out_start = max(target - 0.06, 0.01)

        video_graph = (
            "[0:v]split=2[bg][fg];"
            "[bg]scale=1080:1920:force_original_aspect_ratio=increase,"
            "crop=1080:1920,gblur=sigma=32[bgv];"
            "[fg]scale=1080:1920:force_original_aspect_ratio=decrease[fgv];"
            "[bgv][fgv]overlay=(W-w)/2:(H-h)/2,format=yuv420p,"
            f"fade=t=in:st=0:d=0.05,fade=t=out:st={fade_out_start:.2f}:d=0.05"
        )
        if caption and font:
            escaped_font = _escape_filter_path(font)
            escaped_text = _escape_drawtext(caption)
            video_graph += (
                f",drawtext=fontfile='{escaped_font}':text='{escaped_text}':"
                f"fontcolor=white:fontsize={caption_size}:borderw=3:bordercolor=black@0.90:"
                f"x=(w-text_w)/2:y=h*{caption_y:.3f}:"
                "enable='between(t,0.35,4.45)'"
            )
        video_graph += "[v]"

        audio_filter = (
            f"loudnorm=I={lufs}:LRA=11:TP={peak},"
            f"volume={source_audio_volume:.3f},"
            "afade=t=in:st=0:d=0.03,"
            f"afade=t=out:st={max(target - 0.05, 0.01):.2f}:d=0.05"
        )

        has_audio = _ffprobe_has_audio(clip.file)
        cmd = ["ffmpeg", "-y", "-ss", f"{start:.3f}", "-i", str(clip.file)]
        if has_audio:
            cmd += [
                "-t",
                f"{target:.3f}",
                "-filter_complex",
                video_graph,
                "-map",
                "[v]",
                "-map",
                "0:a:0",
                "-af",
                audio_filter,
            ]
        else:
            cmd += [
                "-f",
                "lavfi",
                "-t",
                f"{target:.3f}",
                "-i",
                "anullsrc=channel_layout=stereo:sample_rate=48000",
                "-t",
                f"{target:.3f}",
                "-filter_complex",
                video_graph,
                "-map",
                "[v]",
                "-map",
                "1:a:0",
            ]

        cmd += [
            "-r",
            "30",
            "-c:v",
            "libx264",
            "-preset",
            "medium",
            "-crf",
            "20",
            "-c:a",
            "aac",
            "-b:a",
            "160k",
            "-ar",
            "48000",
            "-ac",
            "2",
            "-shortest",
            str(dst),
        ]
        subprocess.run(cmd, check=True)
        normalized.append(dst)

    concat_file = work / "concat.txt"
    concat_file.write_text(
        "".join(f"file '{path.as_posix()}'\n" for path in normalized),
        encoding="utf-8",
    )
    concat_output = work / "visual-audio-concat.mp4"
    subprocess.run(
        [
            "ffmpeg",
            "-y",
            "-f",
            "concat",
            "-safe",
            "0",
            "-i",
            str(concat_file),
            "-c",
            "copy",
            str(concat_output),
        ],
        check=True,
    )

    total_duration = len(normalized) * target
    bgm = _generate_playful_bgm(work / "procedural-playful-bgm.wav", total_duration)
    cut_times = [target * index for index in range(1, len(normalized))]
    meows = _generate_meow_timeline(
        work / "soft-meow-transitions.wav",
        total_duration,
        cut_times,
    )

    output.parent.mkdir(parents=True, exist_ok=True)
    mix = (
        "[0:a]aresample=48000[src];"
        f"[1:a]volume={bgm_volume:.3f}[bg];"
        f"[2:a]volume={meow_volume:.3f}[mew];"
        "[src][bg][mew]amix=inputs=3:duration=first:dropout_transition=0:normalize=0,"
        "alimiter=limit=0.95[a]"
    )
    subprocess.run(
        [
            "ffmpeg",
            "-y",
            "-i",
            str(concat_output),
            "-i",
            str(bgm),
            "-i",
            str(meows),
            "-filter_complex",
            mix,
            "-map",
            "0:v:0",
            "-map",
            "[a]",
            "-c:v",
            "copy",
            "-c:a",
            "aac",
            "-b:a",
            "192k",
            "-ar",
            "48000",
            "-ac",
            "2",
            "-movflags",
            "+faststart",
            "-shortest",
            str(output),
        ],
        check=True,
    )
    return output
