from __future__ import annotations

import json
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path

from .settings import Settings


@dataclass(frozen=True)
class SourceClip:
    file: Path
    source_url: str
    license: str
    commercial_use_allowed: bool
    creator: str = ""


def load_sources(path: Path) -> list[SourceClip]:
    raw = json.loads(path.read_text(encoding="utf-8"))
    clips = [
        SourceClip(
            file=(path.parent / item["file"]).resolve(),
            source_url=item["source_url"],
            license=item["license"],
            commercial_use_allowed=bool(item["commercial_use_allowed"]),
            creator=item.get("creator", ""),
        )
        for item in raw["clips"]
    ]
    if len(clips) < 3:
        raise ValueError("animal compilation needs at least 3 source clips")
    return clips


def render_compilation(settings: Settings, source_manifest: Path, output: Path) -> Path:
    """Render a calm-transition compilation with FFmpeg.

    MVP deliberately inserts NO transition SFX. Each clip gets a tiny visual/audio
    fade and loudness normalization, eliminating the common bass-impact transition.
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
    target = int(settings.raw["video"]["clip_seconds"])
    lufs = float(settings.raw["audio"]["compilation_lufs"])
    peak = float(settings.raw["audio"]["true_peak_db"])

    for index, clip in enumerate(clips, 1):
        dst = work / f"{index:02d}.mp4"
        vf = (
            "scale=1080:1920:force_original_aspect_ratio=increase,"
            "crop=1080:1920,setsar=1,"
            f"fade=t=in:st=0:d=0.08,fade=t=out:st={max(target - 0.08, 0.01):.2f}:d=0.08"
        )
        af = (
            f"loudnorm=I={lufs}:LRA=11:TP={peak},"
            f"afade=t=in:st=0:d=0.05,afade=t=out:st={max(target - 0.06, 0.01):.2f}:d=0.06"
        )
        cmd = [
            "ffmpeg", "-y", "-i", str(clip.file), "-t", str(target),
            "-vf", vf, "-af", af,
            "-r", "30", "-c:v", "libx264", "-preset", "medium", "-crf", "20",
            "-c:a", "aac", "-b:a", "160k", "-ar", "48000", "-ac", "2", str(dst),
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
