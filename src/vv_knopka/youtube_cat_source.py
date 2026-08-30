from __future__ import annotations

import argparse
import hashlib
import json
import shutil
from pathlib import Path
from typing import Any

from dotenv import load_dotenv
from yt_dlp import YoutubeDL
from yt_dlp.utils import DownloadError

from .animal_audio_sources import has_audible_audio, is_short_portrait, video_dimensions
from .animal_episode import build_episode_metadata
from .animal_highlights import select_highlights
from .animal_v3 import render_cat_v3
from .budget import BudgetLedger
from .cat_compilation import build_generic_cat_plan
from .manifest import build_manifest
from .settings import Settings, load_settings
from .trend_discovery import _is_creative_commons
from .trend_import import _ffprobe_duration, merge_source_manifest, write_attribution_report


_VIDEO_SUFFIXES = {".mp4", ".mkv", ".webm", ".mov", ".m4v"}


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def fetch_youtube_metadata(url: str) -> dict[str, Any]:
    source_url = str(url or "").strip()
    if not source_url:
        raise ValueError("YouTube URL is required")
    options = {
        "quiet": True,
        "no_warnings": True,
        "skip_download": True,
        "noplaylist": True,
        "socket_timeout": 30,
    }
    try:
        with YoutubeDL(options) as ydl:
            info = ydl.extract_info(source_url, download=False)
    except DownloadError as exc:
        raise ValueError(f"Could not read YouTube metadata for {source_url}") from exc
    info = dict(info or {})
    return {
        "video_id": str(info.get("id") or "").strip(),
        "title": str(info.get("title") or "").strip(),
        "creator": str(info.get("channel") or info.get("uploader") or "").strip(),
        "creator_id": str(info.get("channel_id") or info.get("uploader_id") or "").strip(),
        "source_url": str(info.get("webpage_url") or source_url).strip(),
        "license": str(info.get("license") or "").strip(),
        "duration": float(info.get("duration") or 0.0),
        "upload_date": str(info.get("upload_date") or "").strip(),
        "view_count": int(info.get("view_count") or 0),
    }


def require_verified_cc(metadata: dict[str, Any]) -> str:
    license_name = str(metadata.get("license") or "").strip()
    if not _is_creative_commons(license_name):
        raise ValueError(
            "YouTube metadata does not verify Creative Commons Attribution. "
            "Production CC download/import is blocked."
        )
    return license_name


def _download_cc_media(url: str, *, destination_dir: Path, video_id: str) -> Path:
    destination_dir.mkdir(parents=True, exist_ok=True)
    template = str(destination_dir / "youtube-cc-%(id)s.%(ext)s")
    options = {
        "format": "bv*[ext=mp4]+ba[ext=m4a]/b[ext=mp4]/bv*+ba/b",
        "merge_output_format": "mp4",
        "outtmpl": template,
        "noplaylist": True,
        "socket_timeout": 30,
        "windowsfilenames": True,
        "quiet": False,
    }
    try:
        with YoutubeDL(options) as ydl:
            ydl.extract_info(url, download=True)
    except DownloadError as exc:
        raise RuntimeError("yt-dlp could not download the verified CC YouTube source") from exc

    matches: list[Path] = []
    for path in destination_dir.glob(f"youtube-cc-{video_id}.*"):
        if not path.is_file() or path.suffix.lower() not in _VIDEO_SUFFIXES or path.stat().st_size <= 0:
            continue
        if video_dimensions(path) is None:
            continue
        matches.append(path)
    if not matches:
        raise RuntimeError("CC download completed but no merged video file could be located")
    matches.sort(key=lambda path: (path.suffix.lower() != ".mp4", -path.stat().st_size, path.name))
    return matches[0].resolve()


def _validate_cat_media(settings: Settings, path: Path) -> dict[str, Any]:
    animal_cfg = settings.raw.get("animal", {})
    min_seconds = float(animal_cfg.get("clip_seconds", 5.0))
    min_mean_db = float(animal_cfg.get("min_source_mean_volume_db", -55.0))
    tolerance = float(animal_cfg.get("source_aspect_tolerance", 0.08))

    dimensions = video_dimensions(path)
    if dimensions is None:
        raise ValueError("Could not read imported video dimensions")
    width, height = dimensions
    if not is_short_portrait(width, height, tolerance=tolerance):
        raise ValueError(
            f"YouTube cat source is {width}x{height}; production/test cat sources must already be near 9:16 portrait"
        )

    duration = _ffprobe_duration(path)
    if duration < min_seconds:
        raise ValueError(f"YouTube cat source is only {duration:.2f}s; need at least {min_seconds:.2f}s")

    audible, mean_db = has_audible_audio(path, minimum_mean_db=min_mean_db)
    if not audible:
        raise ValueError(f"YouTube cat source has no usable audio above {min_mean_db:.1f} dB mean threshold")

    return {
        "duration": duration,
        "has_audio": True,
        "mean_volume_db": mean_db,
        "source_width": width,
        "source_height": height,
        "source_aspect_ratio": round(width / height, 6),
        "source_sha256": _sha256(path),
    }


def import_cc_url(settings: Settings, *, slot: int, url: str) -> tuple[Path, Path, dict[str, Any]]:
    metadata = fetch_youtube_metadata(url)
    license_name = require_verified_cc(metadata)
    video_id = str(metadata.get("video_id") or "unknown")
    import_dir = settings.runtime_dir / "imports" / f"slot-{int(slot):02d}" / "youtube-cc"
    media = _download_cc_media(str(metadata["source_url"]), destination_dir=import_dir, video_id=video_id)
    validation = _validate_cat_media(settings, media)

    creator = str(metadata.get("creator") or "")
    title = str(metadata.get("title") or "")
    source_url = str(metadata.get("source_url") or url)
    attribution = f'"{title}" by {creator} — {source_url} — {license_name}'
    clip = {
        "file": str(media),
        "source_url": source_url,
        "source_title": title,
        "license": license_name,
        "commercial_use_allowed": True,
        "creator": creator,
        "provider": "youtube",
        "provider_id": video_id,
        "ugc": True,
        "attribution_required": True,
        "attribution_text": attribution,
        "rights_status": "creative_commons_attribution_required",
        "rights_verified": True,
        "human_approved": True,
        "publication_allowed": True,
        **validation,
    }

    slot_dir = settings.runtime_dir / "slots" / f"{int(slot):02d}"
    slot_dir.mkdir(parents=True, exist_ok=True)
    source_manifest = merge_source_manifest(slot_dir / "sources.json", clip)
    attribution_report = write_attribution_report(slot_dir, source_manifest)
    return source_manifest, attribution_report, clip


def _test_only_dir(settings: Settings, slot: int) -> Path:
    return settings.runtime_dir / "test_only" / f"slot-{int(slot):02d}"


def _merge_test_only_manifest(path: Path, clip: dict[str, Any]) -> Path:
    current: dict[str, Any] = {}
    if path.exists():
        try:
            current = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            current = {}

    clips = [dict(clip)]
    identity = (str(clip.get("provider") or ""), str(clip.get("provider_id") or clip.get("source_sha256") or ""))
    for item in current.get("clips", []):
        if not isinstance(item, dict):
            continue
        item_identity = (str(item.get("provider") or ""), str(item.get("provider_id") or item.get("source_sha256") or ""))
        if item_identity == identity:
            continue
        clips.append(dict(item))

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(
            {
                "version": 1,
                "purpose": "private quality comparison only",
                "do_not_publish": True,
                "publication_allowed": False,
                "source_policy": "unverified YouTube media supplied locally; isolated from production",
                "clips": clips,
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    return path


def add_test_only_file(
    settings: Settings,
    *,
    slot: int,
    url: str,
    local_file: Path,
    confirm_match: bool,
) -> tuple[Path, dict[str, Any]]:
    if not confirm_match:
        raise ValueError("test-only import requires --confirm-match for the local file and YouTube URL")
    if not local_file.exists() or not local_file.is_file() or local_file.stat().st_size <= 0:
        raise FileNotFoundError(f"local test video not found: {local_file}")

    metadata = fetch_youtube_metadata(url)
    validation = _validate_cat_media(settings, local_file)
    source_sha = str(validation["source_sha256"])
    video_id = str(metadata.get("video_id") or "unknown")
    test_dir = _test_only_dir(settings, slot)
    media_dir = test_dir / "media"
    media_dir.mkdir(parents=True, exist_ok=True)
    suffix = local_file.suffix.lower() or ".mp4"
    destination = media_dir / f"youtube-{video_id}-{source_sha[:10]}{suffix}"
    if not destination.exists():
        shutil.copy2(local_file, destination)

    license_name = str(metadata.get("license") or "Standard/unverified YouTube license")
    clip = {
        "file": str(destination.resolve()),
        "source_url": str(metadata.get("source_url") or url),
        "source_title": str(metadata.get("title") or ""),
        "license": license_name,
        "commercial_use_allowed": False,
        "creator": str(metadata.get("creator") or ""),
        "provider": "youtube",
        "provider_id": video_id,
        "ugc": True,
        "rights_status": "test_only_unverified",
        "rights_verified": False,
        "attribution_required": False,
        "do_not_publish": True,
        "publication_allowed": False,
        **validation,
    }
    manifest = _merge_test_only_manifest(test_dir / "sources.json", clip)
    (test_dir / "DO_NOT_PUBLISH.txt").write_text(
        "TEST-ONLY MEDIA. Rights are not verified for publication. Do not move this render/source manifest into production.\n",
        encoding="utf-8",
    )
    return manifest, clip


def _animal_slot(settings: Settings, slot: int):
    slots = {item.slot: item for item in build_manifest(settings)}
    selected = slots.get(int(slot))
    if selected is None or selected.pipeline != "animal_compilation":
        raise ValueError(f"slot {slot} is not an animal_compilation slot")
    return selected


def render_test_only(settings: Settings, *, slot: int) -> Path:
    slot_info = _animal_slot(settings, slot)
    test_dir = _test_only_dir(settings, slot)
    source_manifest = test_dir / "sources.json"
    if not source_manifest.exists():
        raise FileNotFoundError(f"test-only source manifest not found: {source_manifest}")
    raw = json.loads(source_manifest.read_text(encoding="utf-8"))
    if raw.get("do_not_publish") is not True or raw.get("publication_allowed") is not False:
        raise RuntimeError("Refusing test render because the test-only publication lock is missing")
    clips = [item for item in raw.get("clips", []) if isinstance(item, dict)]
    if len(clips) < 3:
        raise RuntimeError("Add at least 3 test-only YouTube cat clips before rendering a comparison montage")
    if any(item.get("do_not_publish") is not True or item.get("publication_allowed") is not False for item in clips):
        raise RuntimeError("Every test-only clip must carry do_not_publish=true and publication_allowed=false")

    plan = build_generic_cat_plan(slot_info.language)
    plan["title"] = "ТЕСТ — Котики" if slot_info.language == "ru" else "TEST — Cats"
    plan["editorial_value"] = "Private quality comparison only; source rights are not verified for publication."
    (test_dir / "effective-plan.json").write_text(json.dumps(plan, ensure_ascii=False, indent=2), encoding="utf-8")

    ledger = BudgetLedger(settings)
    animal_cfg = settings.raw.get("animal", {})
    highlights = select_highlights(
        settings,
        ledger,
        source_manifest=source_manifest,
        slot_dir=test_dir,
        language=slot_info.language,
        editorial_plan=plan,
        clip_seconds=float(animal_cfg.get("clip_seconds", 5)),
    )
    episode = build_episode_metadata(
        settings,
        slot=int(slot),
        language=slot_info.language,
        plan=plan,
        highlight_manifest=highlights,
        output=test_dir / "episode.json",
    )
    output = test_dir / "render-test-only.mp4"
    return render_cat_v3(
        settings,
        source_manifest,
        highlights,
        episode,
        output,
        language=slot_info.language,
    )


def main() -> None:
    load_dotenv()
    parser = argparse.ArgumentParser(prog="vv-cat-youtube")
    parser.add_argument("--config", default="config/pilot.toml")
    sub = parser.add_subparsers(dest="command", required=True)

    cc = sub.add_parser("cc", help="Verify CC BY, download and import one YouTube cat source")
    cc.add_argument("slot", type=int)
    cc.add_argument("--url", required=True)

    test_add = sub.add_parser(
        "test-add",
        help="Add an already-local YouTube file to an isolated do-not-publish comparison pool",
    )
    test_add.add_argument("slot", type=int)
    test_add.add_argument("--url", required=True)
    test_add.add_argument("--file", required=True)
    test_add.add_argument("--confirm-match", action="store_true")

    test_render = sub.add_parser("test-render", help="Render only the isolated test-only YouTube pool")
    test_render.add_argument("slot", type=int)

    args = parser.parse_args()
    settings = load_settings(args.config)

    if args.command == "cc":
        source_manifest, attribution, clip = import_cc_url(settings, slot=args.slot, url=args.url)
        print(f"Imported YouTube CC: {clip['source_title']}")
        print(f"Creator: {clip['creator']}")
        print(f"Verified license: {clip['license']}")
        print(f"Dimensions: {clip['source_width']}x{clip['source_height']}")
        print(f"Audio mean: {clip['mean_volume_db']} dB")
        print(f"Sources: {source_manifest}")
        print(f"Attribution: {attribution}")
        print(f"Next: run `vv render-animal {args.slot}`; stock only fills remaining source slots.")
        return

    if args.command == "test-add":
        manifest, clip = add_test_only_file(
            settings,
            slot=args.slot,
            url=args.url,
            local_file=Path(args.file).resolve(),
            confirm_match=args.confirm_match,
        )
        print(f"Added TEST-ONLY YouTube source: {clip['source_title']}")
        print("Rights: UNVERIFIED; do_not_publish=true; publication_allowed=false")
        print(f"Dimensions: {clip['source_width']}x{clip['source_height']}")
        print(f"Manifest: {manifest}")
        print(f"After at least 3 clips: `vv-cat-youtube test-render {args.slot}`")
        return

    if args.command == "test-render":
        print(render_test_only(settings, slot=args.slot))
        print("TEST-ONLY output. Do not publish or move it into runtime/ready_for_review.")
        return


if __name__ == "__main__":
    main()
