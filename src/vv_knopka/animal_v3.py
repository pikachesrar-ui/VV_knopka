from __future__ import annotations

import json
import math
import os
import shutil
import subprocess
import textwrap
from array import array
from pathlib import Path
from typing import Any

from .animal_compilation import (
    _escape_filter_path,
    _ffprobe_has_audio,
    _system_font,
    _write_pcm_stereo,
    load_sources,
)
from .settings import Settings


def _quick_meow_samples(sample_rate: int = 48000, variant: int = 0) -> array:
    """Fallback-only short bright chirp; real meow asset is preferred."""
    duration = 0.30
    total = int(duration * sample_rate)
    base_shift = (variant % 3 - 1) * 45.0
    phase = 0.0
    pcm = array("h")
    for frame in range(total):
        t = frame / sample_rate
        if t < 0.09:
            frequency = 720.0 + base_shift + 330.0 * (t / 0.09)
        else:
            frequency = 1050.0 + base_shift - 430.0 * ((t - 0.09) / (duration - 0.09))
        frequency += 24.0 * math.sin(2 * math.pi * 21.0 * t)
        phase += 2 * math.pi * frequency / sample_rate
        attack = min(t / 0.012, 1.0)
        release = max(0.0, 1.0 - max(t - 0.12, 0.0) / (duration - 0.12))
        envelope = attack * (1.0 if t < 0.12 else release**1.7)
        tone = math.sin(phase) + 0.27 * math.sin(2 * phase) + 0.08 * math.sin(3 * phase)
        value = max(-1.0, min(1.0, 0.31 * envelope * tone))
        sample = int(value * 32767)
        pcm.append(sample)
        pcm.append(sample)
    return pcm


def _generate_quick_meow(path: Path, variant: int = 0) -> Path:
    _write_pcm_stereo(path, _quick_meow_samples(48000, variant), 48000)
    return path


def _resolve_meow(settings: Settings, work: Path) -> tuple[Path, bool]:
    """Use one persistent real meow asset when supplied, otherwise fallback."""
    animal_cfg = settings.raw.get("animal", {})
    configured = os.getenv("CAT_MEOW_FILE", "").strip() or str(
        animal_cfg.get("meow_file", "runtime/assets/cat-transition-meow.mp3")
    ).strip()
    if configured:
        candidate = Path(configured)
        if not candidate.is_absolute():
            candidate = (settings.root / candidate).resolve()
        if candidate.exists() and candidate.stat().st_size > 0:
            return candidate, False
    fallback = _generate_quick_meow(work / "fallback-quick-meow.wav")
    return fallback, True


def _wrap_card_text(text: str, *, width: int = 22) -> str:
    """Wrap title cards to phone-safe lines instead of letting drawtext overflow."""
    clean = " ".join(str(text or "").replace("\n", " ").split())
    if not clean:
        return ""

    lines: list[str] = []
    # Number and title are more legible when the episode number gets its own line.
    if clean.startswith("#") and " — " in clean:
        number, title = clean.split(" — ", 1)
        lines.append(number.strip())
        lines.extend(
            textwrap.wrap(
                title.strip(),
                width=max(int(width), 8),
                break_long_words=False,
                break_on_hyphens=False,
            )
            or [title.strip()]
        )
    else:
        lines.extend(
            textwrap.wrap(
                clean,
                width=max(int(width), 8),
                break_long_words=False,
                break_on_hyphens=False,
            )
            or [clean]
        )
    return "\n".join(lines[:4])


def _render_black_card(
    *,
    output: Path,
    text: str,
    duration: float,
    font: Path,
    font_size: int,
    meow: Path,
    meow_volume: float,
    wrap_chars: int,
) -> Path:
    output.parent.mkdir(parents=True, exist_ok=True)
    wrapped = _wrap_card_text(text, width=wrap_chars)
    text_file = output.with_suffix(".txt")
    text_file.write_text(wrapped, encoding="utf-8")

    escaped_font = _escape_filter_path(font)
    escaped_text_file = _escape_filter_path(text_file)
    video_filter = (
        f"drawtext=fontfile='{escaped_font}':textfile='{escaped_text_file}':"
        f"fontcolor=white:fontsize={font_size}:line_spacing=18:borderw=2:bordercolor=black@0.5:"
        "x=(w-text_w)/2:y=(h-text_h)/2"
    )
    audio_filter = (
        f"[1:a]atrim=0:{duration:.3f},asetpts=N/SR/TB,volume={meow_volume:.3f},"
        f"apad=pad_dur={duration:.3f},alimiter=limit=0.95[a]"
    )
    command = [
        "ffmpeg",
        "-y",
        "-f",
        "lavfi",
        "-i",
        f"color=c=black:s=1080x1920:r=30:d={duration:.3f}",
        "-i",
        str(meow),
        "-vf",
        video_filter,
        "-filter_complex",
        audio_filter,
        "-map",
        "0:v:0",
        "-map",
        "[a]",
        "-t",
        f"{duration:.3f}",
        "-r",
        "30",
        "-c:v",
        "libx264",
        "-preset",
        "medium",
        "-crf",
        "20",
        "-pix_fmt",
        "yuv420p",
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
        str(output),
    ]
    subprocess.run(command, check=True)
    return output


def _render_highlight_clip(
    *,
    source: Path,
    output: Path,
    start: float,
    seconds: float,
    source_audio_volume: float,
    lufs: float,
    peak: float,
    require_audio: bool,
) -> Path:
    video_graph = (
        "[0:v]split=2[bg][fg];"
        "[bg]scale=1080:1920:force_original_aspect_ratio=increase,"
        "crop=1080:1920,gblur=sigma=32[bgv];"
        "[fg]scale=1080:1920:force_original_aspect_ratio=decrease[fgv];"
        "[bgv][fgv]overlay=(W-w)/2:(H-h)/2,format=yuv420p[v]"
    )
    has_audio = _ffprobe_has_audio(source)
    if require_audio and not has_audio:
        raise RuntimeError(f"Cat source unexpectedly has no audio stream: {source}")

    command = ["ffmpeg", "-y", "-ss", f"{start:.3f}", "-i", str(source)]
    if has_audio:
        audio_filter = (
            f"loudnorm=I={lufs}:LRA=11:TP={peak},"
            f"volume={source_audio_volume:.3f},"
            f"apad=pad_dur={seconds:.3f}[a]"
        )
        command += [
            "-filter_complex",
            video_graph + ";[0:a:0]" + audio_filter,
            "-map",
            "[v]",
            "-map",
            "[a]",
        ]
    else:
        command += [
            "-f",
            "lavfi",
            "-t",
            f"{seconds:.3f}",
            "-i",
            "anullsrc=channel_layout=stereo:sample_rate=48000",
            "-filter_complex",
            video_graph,
            "-map",
            "[v]",
            "-map",
            "1:a:0",
        ]

    command += [
        "-t",
        f"{seconds:.3f}",
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
        "192k",
        "-ar",
        "48000",
        "-ac",
        "2",
        str(output),
    ]
    subprocess.run(command, check=True)
    return output


def render_cat_v3(
    settings: Settings,
    source_manifest: Path,
    highlight_manifest: Path,
    episode_manifest: Path,
    output: Path,
    *,
    language: str,
) -> Path:
    """Render cat montage with title cards, real source audio and no music/voiceover."""
    if shutil.which("ffmpeg") is None:
        raise RuntimeError("ffmpeg is not on PATH")
    clips = load_sources(source_manifest)
    highlights = json.loads(highlight_manifest.read_text(encoding="utf-8"))
    episode = json.loads(episode_manifest.read_text(encoding="utf-8"))
    selections = {
        int(item["clip_index"]): item
        for item in highlights.get("selections", [])
        if isinstance(item, dict) and item.get("clip_index") is not None
    }
    order = [int(value) for value in highlights.get("order", []) if int(value) in selections]
    if len(order) < 3:
        raise RuntimeError("Cat renderer needs at least three selected highlights")

    font = _system_font()
    if font is None:
        raise RuntimeError("No suitable system font found for Cat title cards")

    animal_cfg = settings.raw.get("animal", {})
    audio_cfg = settings.raw.get("audio", {})
    clip_seconds = float(animal_cfg.get("clip_seconds", 5))
    intro_seconds = float(animal_cfg.get("intro_card_seconds", 0.9))
    transition_seconds = float(animal_cfg.get("transition_card_seconds", 0.75))
    end_seconds = float(animal_cfg.get("end_card_seconds", 1.0))
    meow_volume = float(animal_cfg.get("meow_volume", 0.9))
    source_audio_volume = float(animal_cfg.get("source_audio_volume", 1.0))
    lufs = float(audio_cfg.get("compilation_lufs", -16.0))
    peak = float(audio_cfg.get("true_peak_db", -1.5))
    title_font_size = int(animal_cfg.get("title_font_size", 64))
    transition_font_size = int(animal_cfg.get("transition_font_size", 58))
    end_font_size = int(animal_cfg.get("end_font_size", 64))
    wrap_chars = int(animal_cfg.get("card_wrap_chars", 22))
    require_audio = bool(animal_cfg.get("require_source_audio", True))

    work = settings.runtime_dir / "tmp" / (output.stem + "-v4")
    work.mkdir(parents=True, exist_ok=True)
    meow, fallback_meow = _resolve_meow(settings, work)
    if fallback_meow:
        print(
            "Real cat meow asset not found; using procedural fallback. "
            "Place a chosen sound at runtime/assets/cat-transition-meow.mp3 or set CAT_MEOW_FILE."
        )
    else:
        print(f"Cat meow asset: {meow}")

    display_title = str(episode.get("display_title") or "#001 — Cat Chaos")
    sequence: list[Path] = [
        _render_black_card(
            output=work / "000-intro.mp4",
            text=display_title,
            duration=intro_seconds,
            font=font,
            font_size=title_font_size,
            meow=meow,
            meow_volume=meow_volume,
            wrap_chars=wrap_chars,
        )
    ]

    for position, clip_index in enumerate(order, start=1):
        selection = selections[clip_index]
        clip = clips[clip_index - 1]
        if position > 1:
            sequence.append(
                _render_black_card(
                    output=work / f"{position:03d}-card.mp4",
                    text=display_title,
                    duration=transition_seconds,
                    font=font,
                    font_size=transition_font_size,
                    meow=meow,
                    meow_volume=meow_volume,
                    wrap_chars=wrap_chars,
                )
            )
        sequence.append(
            _render_highlight_clip(
                source=clip.file,
                output=work / f"{position:03d}-clip.mp4",
                start=max(float(selection.get("start") or 0.0), 0.0),
                seconds=clip_seconds,
                source_audio_volume=source_audio_volume,
                lufs=lufs,
                peak=peak,
                require_audio=require_audio,
            )
        )

    sequence.append(
        _render_black_card(
            output=work / "999-end.mp4",
            text=str(episode.get("end_text") or ("Спасибо за просмотр" if language == "ru" else "Thanks for watching")),
            duration=end_seconds,
            font=font,
            font_size=end_font_size,
            meow=meow,
            meow_volume=meow_volume,
            wrap_chars=wrap_chars,
        )
    )

    concat_file = work / "concat.txt"
    concat_file.write_text(
        "".join(f"file '{path.as_posix()}'\n" for path in sequence),
        encoding="utf-8",
    )
    concat_output = work / "cat-cards-concat.mp4"
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

    output.parent.mkdir(parents=True, exist_ok=True)
    # Product decision: no BGM. Keep only source audio and the meow on black cards.
    subprocess.run(
        [
            "ffmpeg",
            "-y",
            "-i",
            str(concat_output),
            "-map",
            "0:v:0",
            "-map",
            "0:a:0",
            "-c",
            "copy",
            "-movflags",
            "+faststart",
            str(output),
        ],
        check=True,
    )
    return output
