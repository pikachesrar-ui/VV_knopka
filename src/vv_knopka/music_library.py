from __future__ import annotations

import hashlib
import json
import shutil
import subprocess
from pathlib import Path
from typing import Any

from .settings import Settings

_AUDIO_SUFFIXES = (".wav", ".mp3", ".m4a", ".aac", ".ogg", ".flac", ".opus")
_PIPELINE_PREFIXES = {
    "ai_short": ("curious", "calm", "facts", "generic"),
    "animal_compilation": ("cute", "playful", "calm", "generic"),
}


def music_config(settings: Settings) -> dict[str, Any]:
    return dict(settings.raw.get("music", {}) or {})


def music_library_dir(settings: Settings) -> Path:
    configured = str(music_config(settings).get("library_dir") or "runtime/assets/music").strip()
    path = Path(configured)
    return path if path.is_absolute() else (settings.root / path).resolve()


def music_enabled(settings: Settings) -> bool:
    return bool(music_config(settings).get("enabled", False))


def available_tracks(settings: Settings, *, pipeline: str | None = None) -> list[Path]:
    root = music_library_dir(settings)
    if not root.exists():
        return []
    tracks = [
        path.resolve()
        for path in root.iterdir()
        if path.is_file() and path.suffix.lower() in _AUDIO_SUFFIXES and path.stat().st_size > 0
    ]
    tracks.sort(key=lambda path: path.name.casefold())
    if not pipeline:
        return tracks

    prefixes = _PIPELINE_PREFIXES.get(str(pipeline), ("generic",))
    ranked: list[Path] = []
    for prefix in prefixes:
        ranked.extend(path for path in tracks if path.stem.casefold().startswith(prefix))
    ranked.extend(path for path in tracks if path not in ranked)
    return ranked


def _recent_track_names(settings: Settings, *, slot: int, cooldown: int) -> set[str]:
    names: set[str] = set()
    if cooldown <= 0:
        return names
    for previous in range(max(int(slot) - 1, 1), 0, -1):
        audit = settings.runtime_dir / "slots" / f"{previous:02d}" / "music.json"
        if not audit.exists():
            continue
        try:
            payload = json.loads(audit.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        name = str(payload.get("track_name") or "").strip()
        if name:
            names.add(name.casefold())
        if len(names) >= cooldown:
            break
    return names


def select_background_track(settings: Settings, *, slot: int, pipeline: str) -> Path | None:
    if not music_enabled(settings):
        return None
    tracks = available_tracks(settings, pipeline=pipeline)
    if not tracks:
        return None

    cooldown = max(int(music_config(settings).get("cooldown_shorts", 5)), 0)
    blocked = _recent_track_names(settings, slot=slot, cooldown=cooldown)
    eligible = [path for path in tracks if path.name.casefold() not in blocked]
    if not eligible:
        eligible = tracks

    index = (max(int(slot), 1) - 1) % len(eligible)
    return eligible[index]


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def write_music_audit(
    settings: Settings,
    *,
    slot: int,
    pipeline: str,
    track: Path,
    slot_dir: Path,
    applied_to_video: bool,
) -> Path:
    cfg = music_config(settings)
    root = music_library_dir(settings)
    try:
        display_path = str(track.resolve().relative_to(root))
    except ValueError:
        display_path = str(track.resolve())
    payload = {
        "slot": int(slot),
        "pipeline": str(pipeline),
        "track_name": track.name,
        "track_file": display_path,
        "sha256": _sha256(track),
        "ai_generated": bool(cfg.get("ai_generated", True)),
        "generator": str(cfg.get("generator") or "ACE-Step"),
        "applied_to_video": bool(applied_to_video),
        "music_volume_ai": float(cfg.get("ai_volume", 0.10)),
        "music_volume_cat": float(cfg.get("cat_volume", 0.07)),
        "ducking": bool(cfg.get("ducking", True)),
    }
    path = slot_dir / "music.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return path


def mix_background_music(
    settings: Settings,
    *,
    video: Path,
    track: Path,
    pipeline: str,
) -> Path:
    """Mix a library track under the existing video audio, preserving the video stream."""
    ffmpeg = shutil.which("ffmpeg")
    if not ffmpeg:
        raise RuntimeError("ffmpeg is not on PATH")
    if not video.exists() or video.stat().st_size <= 0:
        raise FileNotFoundError(video)
    if not track.exists() or track.stat().st_size <= 0:
        raise FileNotFoundError(track)

    cfg = music_config(settings)
    volume = float(cfg.get("cat_volume", 0.07) if pipeline == "animal_compilation" else cfg.get("ai_volume", 0.10))
    ducking = bool(cfg.get("ducking", True))
    temporary = video.with_name(video.stem + ".music-tmp.mp4")

    if ducking:
        audio_graph = (
            "[0:a]aresample=48000[main];"
            f"[1:a]aresample=48000,volume={volume:.4f}[music];"
            "[music][main]sidechaincompress=threshold=0.035:ratio=8:attack=20:release=350[ducked];"
            "[main][ducked]amix=inputs=2:duration=first:dropout_transition=0:normalize=0,"
            "alimiter=limit=0.95[a]"
        )
    else:
        audio_graph = (
            "[0:a]aresample=48000[main];"
            f"[1:a]aresample=48000,volume={volume:.4f}[music];"
            "[main][music]amix=inputs=2:duration=first:dropout_transition=0:normalize=0,"
            "alimiter=limit=0.95[a]"
        )

    command = [
        ffmpeg,
        "-y",
        "-i",
        str(video),
        "-stream_loop",
        "-1",
        "-i",
        str(track),
        "-filter_complex",
        audio_graph,
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
        "-shortest",
        "-movflags",
        "+faststart",
        str(temporary),
    ]
    completed = subprocess.run(command, capture_output=True, text=True, check=False)
    if completed.returncode != 0 or not temporary.exists() or temporary.stat().st_size <= 0:
        detail = (completed.stderr or completed.stdout or "").strip()[-2500:]
        raise RuntimeError(f"Background music mix failed: {detail}")
    temporary.replace(video)
    return video


def prepare_music_for_slot(
    settings: Settings,
    *,
    slot: int,
    pipeline: str,
    slot_dir: Path,
    video: Path | None = None,
) -> Path | None:
    """Select/audit a track; optionally apply it when a final video is supplied."""
    track = select_background_track(settings, slot=slot, pipeline=pipeline)
    if track is None:
        return None
    applied = video is not None
    if video is not None:
        mix_background_music(settings, video=video, track=track, pipeline=pipeline)
    write_music_audit(
        settings,
        slot=slot,
        pipeline=pipeline,
        track=track,
        slot_dir=slot_dir,
        applied_to_video=applied,
    )
    return track
