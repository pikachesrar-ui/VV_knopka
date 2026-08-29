from __future__ import annotations

import asyncio
import json
import math
import shutil
import subprocess
import wave
from array import array
from pathlib import Path
from typing import Any

import edge_tts

from .animal_compilation import (
    _escape_drawtext,
    _escape_filter_path,
    _ffprobe_has_audio,
    _generate_playful_bgm,
    _system_font,
    _write_pcm_stereo,
    load_sources,
)
from .settings import Settings


def _audio_duration(path: Path) -> float:
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


def _quick_meow_samples(sample_rate: int = 48000, variant: int = 0) -> array:
    """Generate a short bright transition chirp shaped like a quick meow.

    It intentionally avoids a bass transient. The 0.30s envelope is much faster
    than the previous 0.58s procedural sound and fits a 0.35s black card.
    """
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


async def _save_edge_voice(text: str, voice: str, output: Path) -> None:
    communicate = edge_tts.Communicate(text=text, voice=voice, rate="+8%")
    await communicate.save(str(output))


def _synthesize_intro_voice(text: str, voice: str, output: Path) -> Path:
    output.parent.mkdir(parents=True, exist_ok=True)
    if output.exists() and output.stat().st_size > 0:
        return output
    try:
        asyncio.run(_save_edge_voice(text, voice, output))
    except Exception as exc:
        raise RuntimeError(f"Edge TTS could not synthesize cat intro voice: {exc}") from exc
    if not output.exists() or output.stat().st_size <= 0:
        raise RuntimeError("Edge TTS returned no intro audio")
    return output


def _render_black_card(
    *,
    output: Path,
    text: str,
    duration: float,
    font: Path,
    font_size: int,
    meow: Path,
    meow_volume: float,
    voice: Path | None = None,
    voice_delay_seconds: float = 0.22,
) -> Path:
    escaped_font = _escape_filter_path(font)
    escaped_text = _escape_drawtext(text)
    video_filter = (
        f"drawtext=fontfile='{escaped_font}':text='{escaped_text}':"
        f"fontcolor=white:fontsize={font_size}:borderw=2:bordercolor=black@0.5:"
        "x=(w-text_w)/2:y=(h-text_h)/2"
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
    ]
    if voice is not None:
        command += ["-i", str(voice)]
        delay_ms = max(int(voice_delay_seconds * 1000), 0)
        audio_filter = (
            f"[1:a]volume={meow_volume:.3f},apad=pad_dur={duration:.3f}[m];"
            f"[2:a]adelay={delay_ms}|{delay_ms},volume=1.0,apad=pad_dur={duration:.3f}[v];"
            "[m][v]amix=inputs=2:duration=longest:dropout_transition=0:normalize=0,"
            "alimiter=limit=0.95[a]"
        )
    else:
        audio_filter = (
            f"[1:a]volume={meow_volume:.3f},apad=pad_dur={duration:.3f},"
            "alimiter=limit=0.95[a]"
        )
    command += [
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
) -> Path:
    video_graph = (
        "[0:v]split=2[bg][fg];"
        "[bg]scale=1080:1920:force_original_aspect_ratio=increase,"
        "crop=1080:1920,gblur=sigma=32[bgv];"
        "[fg]scale=1080:1920:force_original_aspect_ratio=decrease[fgv];"
        "[bgv][fgv]overlay=(W-w)/2:(H-h)/2,format=yuv420p[v]"
    )
    audio_filter = (
        f"loudnorm=I={lufs}:LRA=11:TP={peak},"
        f"volume={source_audio_volume:.3f}"
    )
    has_audio = _ffprobe_has_audio(source)
    command = ["ffmpeg", "-y", "-ss", f"{start:.3f}", "-i", str(source)]
    if has_audio:
        command += [
            "-t",
            f"{seconds:.3f}",
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
        command += [
            "-f",
            "lavfi",
            "-t",
            f"{seconds:.3f}",
            "-i",
            "anullsrc=channel_layout=stereo:sample_rate=48000",
            "-t",
            f"{seconds:.3f}",
            "-filter_complex",
            video_graph,
            "-map",
            "[v]",
            "-map",
            "1:a:0",
        ]
    command += [
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
    """Render Cat v3: intro title+voice, black mini-cards, highlights and music."""
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
        raise RuntimeError("Cat v3 needs at least three selected highlights")

    font = _system_font()
    if font is None:
        raise RuntimeError("No suitable system font found for Cat v3 title cards")

    animal_cfg = settings.raw.get("animal", {})
    audio_cfg = settings.raw.get("audio", {})
    clip_seconds = float(animal_cfg.get("clip_seconds", 5))
    transition_seconds = float(animal_cfg.get("transition_card_seconds", 0.35))
    configured_intro_seconds = float(animal_cfg.get("intro_card_seconds", 1.8))
    meow_volume = float(animal_cfg.get("meow_volume", 0.82))
    bgm_volume = float(animal_cfg.get("bgm_volume", 0.42))
    source_audio_volume = float(animal_cfg.get("source_audio_volume", 0.82))
    lufs = float(audio_cfg.get("compilation_lufs", -16.0))
    peak = float(audio_cfg.get("true_peak_db", -1.5))
    title_font_size = int(animal_cfg.get("title_font_size", 72))
    transition_font_size = int(animal_cfg.get("transition_font_size", 64))
    intro_delay = float(animal_cfg.get("intro_voice_delay_seconds", 0.22))
    intro_voice_enabled = bool(animal_cfg.get("intro_voice_enabled", True))

    work = settings.runtime_dir / "tmp" / (output.stem + "-v3")
    work.mkdir(parents=True, exist_ok=True)

    voice_file: Path | None = None
    if intro_voice_enabled:
        voice_name = str(audio_cfg.get("edge_voice_ru") if language == "ru" else audio_cfg.get("edge_voice_en"))
        voice_file = _synthesize_intro_voice(
            str(episode.get("intro_voice") or ""),
            voice_name,
            work / "intro-voice.mp3",
        )
    voice_duration = _audio_duration(voice_file) if voice_file else 0.0
    intro_seconds = max(configured_intro_seconds, voice_duration + intro_delay + 0.10)

    meow_files = [
        _generate_quick_meow(work / f"quick-meow-{index}.wav", index)
        for index in range(3)
    ]

    sequence: list[Path] = []
    intro = _render_black_card(
        output=work / "000-intro.mp4",
        text=str(episode.get("display_title") or "#001 — Cat Chaos"),
        duration=intro_seconds,
        font=font,
        font_size=title_font_size,
        meow=meow_files[0],
        meow_volume=meow_volume,
        voice=voice_file,
        voice_delay_seconds=intro_delay,
    )
    sequence.append(intro)

    cards_by_clip = {
        int(item["clip_index"]): str(item.get("text") or "")
        for item in episode.get("transition_cards", [])
        if isinstance(item, dict) and item.get("clip_index") is not None
    }

    for position, clip_index in enumerate(order, start=1):
        selection = selections[clip_index]
        clip = clips[clip_index - 1]
        if position > 1:
            card_text = cards_by_clip.get(clip_index) or ("Следующий котик" if language == "ru" else "Next cat")
            sequence.append(
                _render_black_card(
                    output=work / f"{position:03d}-card.mp4",
                    text=card_text,
                    duration=transition_seconds,
                    font=font,
                    font_size=transition_font_size,
                    meow=meow_files[(position - 1) % len(meow_files)],
                    meow_volume=meow_volume,
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
            )
        )

    concat_file = work / "concat.txt"
    concat_file.write_text("".join(f"file '{path.as_posix()}'\n" for path in sequence), encoding="utf-8")
    concat_output = work / "cat-v3-concat.mp4"
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

    total_duration = _audio_duration(concat_output)
    if total_duration <= 0:
        total_duration = intro_seconds + len(order) * clip_seconds + max(len(order) - 1, 0) * transition_seconds
    bgm = _generate_playful_bgm(work / "procedural-playful-bgm.wav", total_duration)

    output.parent.mkdir(parents=True, exist_ok=True)
    mix = (
        "[0:a]aresample=48000[src];"
        f"[1:a]volume={bgm_volume:.3f}[bg];"
        "[src][bg]amix=inputs=2:duration=first:dropout_transition=0:normalize=0,"
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
