from __future__ import annotations

import argparse
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any
from urllib.parse import quote_plus

from dotenv import load_dotenv
from yt_dlp import YoutubeDL
from yt_dlp.utils import DownloadError

from .settings import Settings, load_settings
from .trend_discovery import _is_creative_commons
from .trend_import import merge_source_manifest, write_attribution_report
from .youtube_cat_source import (
    _download_cc_media,
    _validate_cat_media,
    add_test_only_file,
    fetch_youtube_metadata,
    import_cc_url,
    render_test_only,
)


# YouTube's Creative Commons feature filter. This is the same `sp=` value used
# by the browser search UI for Creative Commons results. yt-dlp's
# YoutubeSearchURLIE explicitly supports search URLs with `sp=` filters.
_YOUTUBE_CC_FILTER_SP = "EgIwAQ%253D%253D"
_DEFAULT_CC_REPORT = Path("runtime/trends/youtube-cat-cc-filtered.json")
_DEFAULT_CC_QUERIES = (
    "funny cat shorts",
    "cats being cats",
    "funny kittens shorts",
    "cat fails shorts",
)


def youtube_cc_search_url(query: str) -> str:
    return (
        "https://www.youtube.com/results?search_query="
        f"{quote_plus(str(query).strip())}&sp={_YOUTUBE_CC_FILTER_SP}"
    )


def _flat_video_target(item: dict[str, Any]) -> tuple[str, str] | None:
    video_id = str(item.get("id") or "").strip()
    url = str(item.get("webpage_url") or item.get("url") or "").strip()
    if video_id and not url.startswith(("https://", "http://")):
        url = f"https://www.youtube.com/watch?v={video_id}"
    if not video_id and url.startswith(("https://", "http://")):
        marker = "watch?v="
        if marker in url:
            video_id = url.split(marker, 1)[1].split("&", 1)[0]
    if not video_id or not url.startswith(("https://", "http://")):
        return None
    return video_id, url


def _parse_upload_date(value: str) -> datetime | None:
    text = str(value or "").strip()
    if len(text) != 8 or not text.isdigit():
        return None
    try:
        return datetime.strptime(text, "%Y%m%d").replace(tzinfo=timezone.utc)
    except ValueError:
        return None


def _filtered_search_targets(query: str, *, scan_per_query: int) -> tuple[list[tuple[str, str]], str]:
    search_url = youtube_cc_search_url(query)
    options = {
        "quiet": True,
        "no_warnings": True,
        "skip_download": True,
        "extract_flat": "in_playlist",
        "playlistend": max(int(scan_per_query), 1),
        "socket_timeout": 30,
    }
    try:
        with YoutubeDL(options) as ydl:
            result = ydl.extract_info(search_url, download=False)
    except DownloadError as exc:
        raise RuntimeError(f"YouTube CC-filtered search failed for query {query!r}") from exc

    targets: list[tuple[str, str]] = []
    seen: set[str] = set()
    for raw in (result or {}).get("entries", []) or []:
        if not isinstance(raw, dict):
            continue
        target = _flat_video_target(raw)
        if target is None:
            continue
        video_id, url = target
        if video_id in seen:
            continue
        seen.add(video_id)
        targets.append((video_id, url))
        if len(targets) >= max(int(scan_per_query), 1):
            break
    return targets, search_url


def search_cc_candidates(
    *,
    days: int = 6000,
    scan_per_query: int = 20,
    limit: int = 15,
    queries: list[str] | None = None,
) -> tuple[list[dict[str, Any]], list[str], dict[str, Any]]:
    """Discover CC cats via YouTube's own Creative Commons search filter.

    `license` is optional in yt-dlp. A result selected by YouTube's CC filter is
    therefore retained when the direct metadata license field is empty. If the
    direct field is present and explicitly non-CC, the candidate fails closed.
    """
    requested = [
        str(value).strip()
        for value in (queries or list(_DEFAULT_CC_QUERIES))
        if str(value).strip()
    ]
    cutoff = datetime.now(timezone.utc) - timedelta(days=max(int(days), 1))
    warnings: list[str] = []
    candidates: list[dict[str, Any]] = []
    seen: set[str] = set()
    diagnostics: dict[str, Any] = {
        "backend": "youtube_cc_search_filter+yt_dlp_hydration",
        "filter_sp": _YOUTUBE_CC_FILTER_SP,
        "queries": {},
    }

    for query in requested:
        try:
            targets, search_url = _filtered_search_targets(query, scan_per_query=scan_per_query)
        except RuntimeError as exc:
            warnings.append(str(exc))
            diagnostics["queries"][query] = {"filtered_results": 0, "hydrated": 0, "accepted": 0}
            continue

        hydrated = 0
        accepted = 0
        for expected_id, url in targets:
            if expected_id in seen:
                continue
            try:
                meta = fetch_youtube_metadata(url)
            except ValueError as exc:
                warnings.append(f"{expected_id}: {exc}")
                continue
            hydrated += 1

            actual_id = str(meta.get("video_id") or "").strip()
            if actual_id and actual_id != expected_id:
                warnings.append(f"{expected_id}: hydrated to different video id {actual_id}")
                continue

            direct_license = str(meta.get("license") or "").strip()
            if direct_license and not _is_creative_commons(direct_license):
                # Contradictory explicit metadata wins over filter provenance.
                continue

            duration = float(meta.get("duration") or 0.0)
            if duration and (duration < 5.0 or duration > 180.0):
                continue

            uploaded = _parse_upload_date(str(meta.get("upload_date") or ""))
            if uploaded is not None and uploaded < cutoff:
                continue

            video_id = actual_id or expected_id
            if video_id in seen:
                continue
            seen.add(video_id)
            accepted += 1
            candidates.append(
                {
                    "provider": "youtube",
                    "video_id": video_id,
                    "url": str(meta.get("source_url") or url),
                    "title": str(meta.get("title") or "").strip(),
                    "channel_title": str(meta.get("creator") or "").strip(),
                    "published_at": str(meta.get("upload_date") or "").strip(),
                    "view_count": int(meta.get("view_count") or 0),
                    "duration_seconds": duration,
                    "license": direct_license or "YouTube Creative Commons Attribution",
                    "direct_license_metadata": direct_license or None,
                    "rights_status": "creative_commons_attribution_required",
                    "rights_verified": True,
                    "rights_verification_method": (
                        "youtube_cc_search_filter+yt_dlp_license"
                        if direct_license
                        else "youtube_cc_search_filter"
                    ),
                    "attribution_required": True,
                    "cc_search_query": query,
                    "cc_search_url": search_url,
                    "cc_filter_sp": _YOUTUBE_CC_FILTER_SP,
                    "auto_download": False,
                    "import_status": "cc_filter_candidate",
                }
            )

        diagnostics["queries"][query] = {
            "filtered_results": len(targets),
            "hydrated": hydrated,
            "accepted": accepted,
            "search_url": search_url,
        }

    candidates.sort(
        key=lambda item: (
            -int(item.get("view_count") or 0),
            str(item.get("published_at") or ""),
        )
    )
    selected = candidates[: max(int(limit), 1)]
    for rank, item in enumerate(selected, 1):
        item["cc_rank"] = rank
    diagnostics["candidate_count"] = len(selected)
    return selected, warnings, diagnostics


def write_cc_report(
    path: Path,
    *,
    candidates: list[dict[str, Any]],
    warnings: list[str],
    diagnostics: dict[str, Any],
) -> Path:
    output = path.resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(
            {
                "version": 2,
                "source": "youtube_cc_filtered_search",
                "created_at": datetime.now(timezone.utc).isoformat(),
                "rights_evidence": "YouTube Creative Commons advanced search filter",
                "filter_sp": _YOUTUBE_CC_FILTER_SP,
                "policy": {
                    "attribution_required": True,
                    "human_review_required": True,
                    "note": (
                        "Candidates originate from YouTube's Creative Commons search filter. "
                        "An explicit contradictory standard-license metadata value rejects a candidate. "
                        "Import rehydrates metadata and checks the report provenance before download."
                    ),
                },
                "diagnostics": diagnostics,
                "warnings": warnings,
                "candidates": candidates,
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    return output


def _report_candidate(report: dict[str, Any], rank: int) -> dict[str, Any]:
    if report.get("source") != "youtube_cc_filtered_search":
        raise ValueError("CC import requires a youtube_cc_filtered_search report")
    if str(report.get("filter_sp") or "") != _YOUTUBE_CC_FILTER_SP:
        raise ValueError("CC report does not contain the expected YouTube Creative Commons filter evidence")
    candidates = report.get("candidates") or []
    index = int(rank) - 1
    if index < 0 or index >= len(candidates):
        raise ValueError(f"candidate must be 1..{len(candidates)}")
    item = candidates[index]
    if not isinstance(item, dict):
        raise ValueError("selected CC candidate is malformed")
    if item.get("rights_verified") is not True or item.get("rights_status") != "creative_commons_attribution_required":
        raise ValueError("selected candidate does not carry verified CC-filter evidence")
    if str(item.get("cc_filter_sp") or "") != _YOUTUBE_CC_FILTER_SP:
        raise ValueError("selected candidate lost its YouTube CC-filter provenance")
    return dict(item)


def import_cc_report_candidate(
    settings: Settings,
    *,
    slot: int,
    report_path: Path,
    rank: int,
) -> tuple[Path, Path, dict[str, Any]]:
    if not report_path.exists():
        raise FileNotFoundError(f"CC report not found: {report_path}")
    report = json.loads(report_path.read_text(encoding="utf-8"))
    candidate = _report_candidate(report, rank)

    url = str(candidate.get("url") or "").strip()
    expected_id = str(candidate.get("video_id") or "").strip()
    if not url or not expected_id:
        raise ValueError("selected CC candidate has no usable YouTube URL/video id")

    meta = fetch_youtube_metadata(url)
    actual_id = str(meta.get("video_id") or "").strip()
    if actual_id and actual_id != expected_id:
        raise ValueError("selected CC candidate now resolves to a different YouTube video")

    direct_license = str(meta.get("license") or "").strip()
    if direct_license and not _is_creative_commons(direct_license):
        raise ValueError(
            "Current YouTube metadata explicitly reports a non-CC license; refusing download despite old search evidence"
        )
    license_name = direct_license or "YouTube Creative Commons Attribution"

    import_dir = settings.runtime_dir / "imports" / f"slot-{int(slot):02d}" / "youtube-cc"
    media = _download_cc_media(url, destination_dir=import_dir, video_id=expected_id)
    validation = _validate_cat_media(settings, media)

    creator = str(meta.get("creator") or candidate.get("channel_title") or "").strip()
    title = str(meta.get("title") or candidate.get("title") or "").strip()
    source_url = str(meta.get("source_url") or url).strip()
    attribution = f'"{title}" by {creator} — {source_url} — {license_name}'
    clip = {
        "file": str(media),
        "source_url": source_url,
        "source_title": title,
        "license": license_name,
        "commercial_use_allowed": True,
        "creator": creator,
        "provider": "youtube",
        "provider_id": expected_id,
        "ugc": True,
        "attribution_required": True,
        "attribution_text": attribution,
        "rights_status": "creative_commons_attribution_required",
        "rights_verified": True,
        "rights_verification_method": str(candidate.get("rights_verification_method") or "youtube_cc_search_filter"),
        "cc_search_query": candidate.get("cc_search_query"),
        "cc_search_url": candidate.get("cc_search_url"),
        "human_approved": True,
        "publication_allowed": True,
        **validation,
    }

    slot_dir = settings.runtime_dir / "slots" / f"{int(slot):02d}"
    slot_dir.mkdir(parents=True, exist_ok=True)
    source_manifest = merge_source_manifest(slot_dir / "sources.json", clip)
    attribution_report = write_attribution_report(slot_dir, source_manifest)
    return source_manifest, attribution_report, clip


def main() -> None:
    load_dotenv()
    parser = argparse.ArgumentParser(prog="vv-cat-youtube")
    parser.add_argument("--config", default="config/pilot.toml")
    sub = parser.add_subparsers(dest="command", required=True)

    cc_search = sub.add_parser("cc-search", help="Search YouTube through its Creative Commons feature filter")
    cc_search.add_argument("--days", type=int, default=6000)
    cc_search.add_argument("--limit", type=int, default=15)
    cc_search.add_argument("--scan-per-query", type=int, default=20)
    cc_search.add_argument("--query", action="append", default=None)
    cc_search.add_argument("--report", default=str(_DEFAULT_CC_REPORT))

    cc_import = sub.add_parser("cc-import", help="Import one candidate from the CC-filtered search report")
    cc_import.add_argument("slot", type=int)
    cc_import.add_argument("--candidate", type=int, required=True)
    cc_import.add_argument("--report", default=str(_DEFAULT_CC_REPORT))

    cc = sub.add_parser("cc", help="Strict URL import when yt-dlp directly reports a CC license")
    cc.add_argument("slot", type=int)
    cc.add_argument("--url", required=True)

    test_add = sub.add_parser("test-add", help="Add an already-local YouTube file to isolated do-not-publish testing")
    test_add.add_argument("slot", type=int)
    test_add.add_argument("--url", required=True)
    test_add.add_argument("--file", required=True)
    test_add.add_argument("--confirm-match", action="store_true")

    test_render = sub.add_parser("test-render", help="Render only the isolated test-only YouTube pool")
    test_render.add_argument("slot", type=int)

    args = parser.parse_args()
    settings = load_settings(args.config)

    if args.command == "cc-search":
        print("YouTube CC search v2: platform Creative Commons filter + yt-dlp metadata hydration")
        print("No Google Cloud, no API key, no account login, no media download")
        candidates, warnings, diagnostics = search_cc_candidates(
            days=args.days,
            scan_per_query=args.scan_per_query,
            limit=args.limit,
            queries=args.query,
        )
        report = write_cc_report(
            Path(args.report),
            candidates=candidates,
            warnings=warnings,
            diagnostics=diagnostics,
        )
        print(f"CC-filtered cat candidates: {len(candidates)}")
        print(report)
        for item in candidates:
            evidence = "metadata+filter" if item.get("direct_license_metadata") else "filter"
            print(
                f"[{int(item['cc_rank']):02d}] [{evidence}] {int(item.get('view_count') or 0):,} views | "
                f"{item.get('title')} | {item.get('url')}"
            )
        if warnings:
            print(f"Warnings: {len(warnings)} (saved in report)")
        if candidates:
            print("Next: `vv-cat-youtube cc-import 2 --candidate N`")
        else:
            print("No CC-filtered candidates survived hydration. Send the report diagnostics; do not increase scan blindly.")
        return

    if args.command == "cc-import":
        source_manifest, attribution, clip = import_cc_report_candidate(
            settings,
            slot=args.slot,
            report_path=Path(args.report).resolve(),
            rank=args.candidate,
        )
        print(f"Imported YouTube CC candidate: {clip['source_title']}")
        print(f"Creator: {clip['creator']}")
        print(f"Rights evidence: {clip['rights_verification_method']}")
        print(f"License: {clip['license']}")
        print(f"Dimensions: {clip['source_width']}x{clip['source_height']}")
        print(f"Audio mean: {clip['mean_volume_db']} dB")
        print(f"Sources: {source_manifest}")
        print(f"Attribution: {attribution}")
        print(f"Next: `vv render-animal {args.slot}`")
        return

    if args.command == "cc":
        source_manifest, attribution, clip = import_cc_url(settings, slot=args.slot, url=args.url)
        print(f"Imported direct-metadata YouTube CC: {clip['source_title']}")
        print(f"Sources: {source_manifest}")
        print(f"Attribution: {attribution}")
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
        print(f"Manifest: {manifest}")
        return

    if args.command == "test-render":
        print(render_test_only(settings, slot=args.slot))
        print("TEST-ONLY output. Do not publish or move it into runtime/ready_for_review.")
        return


if __name__ == "__main__":
    main()
