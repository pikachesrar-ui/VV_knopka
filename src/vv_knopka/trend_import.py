from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import subprocess
from pathlib import Path
from typing import Any

from dotenv import load_dotenv

from .animal_audio_sources import has_audible_audio
from .settings import Settings, load_settings


def _ffprobe_duration(path: Path) -> float:
    ffprobe = shutil.which("ffprobe")
    if not ffprobe:
        raise RuntimeError("ffprobe is required for controlled cat trend import")
    completed = subprocess.run(
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
    if completed.returncode != 0:
        detail = (completed.stderr or completed.stdout or "").strip()[-800:]
        raise RuntimeError(f"Could not inspect imported video duration: {detail}")
    try:
        return max(float(completed.stdout.strip()), 0.0)
    except ValueError as exc:
        raise RuntimeError("Could not parse imported video duration") from exc


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def select_candidate(report: dict[str, Any], rank: int) -> dict[str, Any]:
    candidates = report.get("candidates") or []
    index = int(rank) - 1
    if index < 0 or index >= len(candidates):
        raise ValueError(f"candidate must be 1..{len(candidates)}")
    candidate = candidates[index]
    if not isinstance(candidate, dict):
        raise ValueError("selected trend candidate is malformed")
    return dict(candidate)


def _identity(item: dict[str, Any]) -> tuple[str, str]:
    provider = str(item.get("provider") or "").strip().lower()
    provider_id = str(item.get("provider_id") or item.get("video_id") or "").strip()
    if provider_id:
        return provider, provider_id
    return provider, str(item.get("source_url") or item.get("url") or item.get("file") or "")


def merge_source_manifest(
    source_manifest: Path,
    imported_clip: dict[str, Any],
) -> Path:
    existing: dict[str, Any] = {}
    if source_manifest.exists():
        try:
            existing = json.loads(source_manifest.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            existing = {}

    clips = [imported_clip]
    seen = {_identity(imported_clip)}
    for item in existing.get("clips", []):
        if not isinstance(item, dict):
            continue
        identity = _identity(item)
        if identity in seen:
            continue
        clips.append(dict(item))
        seen.add(identity)

    source_manifest.parent.mkdir(parents=True, exist_ok=True)
    source_manifest.write_text(
        json.dumps(
            {
                "source_policy": "mixed licensed sources: human-approved UGC plus licensed stock",
                "require_audible_audio": True,
                "human_review_required": True,
                "clips": clips,
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    return source_manifest


def write_attribution_report(slot_dir: Path, source_manifest: Path) -> Path:
    raw = json.loads(source_manifest.read_text(encoding="utf-8"))
    entries: list[dict[str, Any]] = []
    for item in raw.get("clips", []):
        if not isinstance(item, dict) or not item.get("attribution_required"):
            continue
        entries.append(
            {
                "provider": item.get("provider"),
                "provider_id": item.get("provider_id"),
                "creator": item.get("creator"),
                "title": item.get("source_title"),
                "source_url": item.get("source_url"),
                "license": item.get("license"),
                "attribution_text": item.get("attribution_text"),
            }
        )
    output = slot_dir / "attribution.json"
    output.write_text(
        json.dumps(
            {
                "version": 1,
                "required": bool(entries),
                "entries": entries,
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    return output


def import_trend_candidate(
    settings: Settings,
    *,
    slot: int,
    report_path: Path,
    rank: int,
    local_file: Path,
    confirm_match: bool,
) -> tuple[Path, Path, dict[str, Any]]:
    if not confirm_match:
        raise ValueError(
            "Controlled import requires --confirm-match: confirm the local file is the exact video from the selected report candidate."
        )
    if not report_path.exists():
        raise FileNotFoundError(f"trend report not found: {report_path}")
    if not local_file.exists() or not local_file.is_file() or local_file.stat().st_size <= 0:
        raise FileNotFoundError(f"local video file not found: {local_file}")

    report = json.loads(report_path.read_text(encoding="utf-8"))
    candidate = select_candidate(report, rank)
    provider = str(candidate.get("provider") or "").strip().lower()
    rights_status = str(candidate.get("rights_status") or "").strip()
    if provider != "youtube" or rights_status != "creative_commons_attribution_required":
        raise ValueError(
            "Automatic rights mapping currently accepts only YouTube candidates discovered as Creative Commons Attribution."
        )

    animal_cfg = settings.raw.get("animal", {})
    minimum_mean_db = float(animal_cfg.get("min_source_mean_volume_db", -55.0))
    minimum_seconds = float(animal_cfg.get("clip_seconds", 5.0))
    duration = _ffprobe_duration(local_file)
    if duration < minimum_seconds:
        raise ValueError(
            f"imported trend video is only {duration:.2f}s; need at least {minimum_seconds:.2f}s"
        )
    audible, mean_db = has_audible_audio(local_file, minimum_mean_db=minimum_mean_db)
    if not audible:
        raise ValueError(
            f"imported trend video has no usable source audio above {minimum_mean_db:.1f} dB mean threshold"
        )

    source_sha256 = _sha256(local_file)
    video_id = str(candidate.get("video_id") or "unknown")
    suffix = local_file.suffix.lower() or ".mp4"
    import_dir = settings.runtime_dir / "imports" / f"slot-{int(slot):02d}"
    import_dir.mkdir(parents=True, exist_ok=True)
    destination = import_dir / f"youtube-{video_id}-{source_sha256[:10]}{suffix}"
    if not destination.exists():
        shutil.copy2(local_file, destination)

    creator = str(candidate.get("channel_title") or "").strip()
    title = str(candidate.get("title") or "").strip()
    source_url = str(candidate.get("url") or "").strip()
    attribution = f'"{title}" by {creator} — {source_url} — Creative Commons Attribution (CC BY)'
    imported_clip = {
        "file": str(destination.resolve()),
        "source_url": source_url,
        "source_title": title,
        "license": "Creative Commons Attribution (CC BY)",
        "commercial_use_allowed": True,
        "creator": creator,
        "provider": "youtube",
        "provider_id": video_id,
        "duration": duration,
        "has_audio": True,
        "mean_volume_db": mean_db,
        "source_sha256": source_sha256,
        "ugc": True,
        "trend_rank": int(rank),
        "published_at": candidate.get("published_at"),
        "view_count_at_discovery": int(candidate.get("view_count") or 0),
        "views_per_day_at_discovery": float(candidate.get("views_per_day") or 0.0),
        "attribution_required": True,
        "attribution_text": attribution,
        "human_approved": True,
        "rights_status": rights_status,
    }

    slot_dir = settings.runtime_dir / "slots" / f"{int(slot):02d}"
    slot_dir.mkdir(parents=True, exist_ok=True)
    source_manifest = merge_source_manifest(slot_dir / "sources.json", imported_clip)
    attribution_report = write_attribution_report(slot_dir, source_manifest)
    return source_manifest, attribution_report, imported_clip


def main() -> None:
    load_dotenv()
    parser = argparse.ArgumentParser(prog="vv-cat-import")
    parser.add_argument("slot", type=int)
    parser.add_argument("--config", default="config/pilot.toml")
    parser.add_argument("--report", default="runtime/trends/youtube-cat-cc.json")
    parser.add_argument("--candidate", type=int, required=True, help="1-based rank from vv-cat-trends")
    parser.add_argument("--file", required=True, help="Local media file corresponding exactly to the selected candidate")
    parser.add_argument(
        "--confirm-match",
        action="store_true",
        help="Confirm that --file is the exact selected source video and not a different upload",
    )
    args = parser.parse_args()

    settings = load_settings(args.config)
    source_manifest, attribution_report, imported = import_trend_candidate(
        settings,
        slot=args.slot,
        report_path=Path(args.report).resolve(),
        rank=args.candidate,
        local_file=Path(args.file).resolve(),
        confirm_match=args.confirm_match,
    )
    print(f"Imported UGC: {imported['source_title']}")
    print(f"Creator: {imported['creator']}")
    print(f"Source: {imported['source_url']}")
    print(f"Audio mean: {imported['mean_volume_db']} dB")
    print(f"Sources: {source_manifest}")
    print(f"Attribution: {attribution_report}")
    print("Next: run `vv render-animal %d`; stock will only fill any remaining source slots." % args.slot)


if __name__ == "__main__":
    main()
