from __future__ import annotations

import json
import os
import shutil
import subprocess
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


def load_sources(path: Path) -> list[SourceClip]:
    raw = json.loads(path.read_text(encoding="utf-8"))
    clips = [
        SourceClip(
            file=(path.parent / item["file"]).resolve(),
            source_url=item["source_url"],
            license=item["license"],
            commercial_use_allowed=bool(item["commercial_use_allowed"]),
            creator=item.get("creator", ""),
            provider=item.get("provider", ""),
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
    """Convert vision-approved Pexels/Pixabay materials into animal sources.json.

    The stock curator already downloaded each accepted file into MPT's ignored
    local_videos directory. This function preserves source provenance and records
    the provider license explicitly before the FFmpeg compilation gate can pass.
    """
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
            {
                "source_policy": "vision-approved licensed stock",
                "clips": clips,
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    return output


def _ffprobe_has_audio(path: Path) -> bool:
    ffprobe = shutil.which("ffprobe")
    if not ffprobe:
        # The Windows full FFmpeg package normally includes ffprobe. If it is
        # missing, be conservative and let optional audio mapping handle it.
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


def render_compilation(settings: Settings, source_manifest: Path, output: Path) -> Path:
    """Render a calm-transition animal compilation with FFmpeg.

    No transition SFX are inserted. Source audio is normalized when present;
    stock clips without audio get a silent stereo track so one mute provider file
    cannot break the full compilation. Every frame uses a 9:16 blur-fill layout,
    keeping the complete sharp source centered instead of black bars or hard crop.
    """
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
    normalized: list[Path] = []
    animal_cfg = settings.raw.get("animal", {})
    target = int(animal_cfg.get("clip_seconds", 5))
    lufs = float(settings.raw["audio"]["compilation_lufs"])
    peak = float(settings.raw["audio"]["true_peak_db"])

    for index, clip in enumerate(clips, 1):
        dst = work / f"{index:02d}.mp4"
        fade_out_start = max(target - 0.08, 0.01)
        video_graph = (
            "[0:v]split=2[bg][fg];"
            "[bg]scale=1080:1920:force_original_aspect_ratio=increase,"
            "crop=1080:1920,gblur=sigma=32[bgv];"
            "[fg]scale=1080:1920:force_original_aspect_ratio=decrease[fgv];"
            "[bgv][fgv]overlay=(W-w)/2:(H-h)/2,format=yuv420p,"
            f"fade=t=in:st=0:d=0.08,fade=t=out:st={fade_out_start:.2f}:d=0.08[v]"
        )
        audio_filter = (
            f"loudnorm=I={lufs}:LRA=11:TP={peak},"
            f"afade=t=in:st=0:d=0.05,afade=t=out:st={max(target - 0.06, 0.01):.2f}:d=0.06"
        )

        has_audio = _ffprobe_has_audio(clip.file)
        cmd = ["ffmpeg", "-y", "-i", str(clip.file)]
        if has_audio:
            cmd += [
                "-t",
                str(target),
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
                str(target),
                "-i",
                "anullsrc=channel_layout=stereo:sample_rate=48000",
                "-t",
                str(target),
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
    concat_file.write_text("".join(f"file '{p.as_posix()}'\n" for p in normalized), encoding="utf-8")
    output.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(
        ["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", str(concat_file), "-c", "copy", str(output)],
        check=True,
    )
    return output
