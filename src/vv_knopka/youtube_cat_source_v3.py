from __future__ import annotations

import argparse
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import httpx
from dotenv import load_dotenv

from .settings import Settings, load_settings
from .trend_discovery import YOUTUBE_VIDEOS_URL, discover_youtube_cc_cats
from .trend_import import merge_source_manifest, write_attribution_report
from .youtube_cat_source import (
    _download_cc_media,
    _validate_cat_media,
    add_test_only_file,
    fetch_youtube_metadata,
    import_cc_url,
    render_test_only,
)
from .youtube_cat_source_v2 import (
    import_cc_report_candidate as import_filter_report_candidate,
    search_cc_candidates as search_cc_candidates_no_key,
    write_cc_report as write_no_key_report,
)


_DEFAULT_API_REPORT = Path("runtime/trends/youtube-cat-cc-official.json")
_DEFAULT_NO_KEY_REPORT = Path("runtime/trends/youtube-cat-cc-filtered.json")
_DEFAULT_API_QUERIES = ("cat|kitten",)


def search_cc_candidates_api(
    *,
    api_key: str,
    days: int = 6000,
    scan_per_query: int = 30,
    limit: int = 15,
    queries: list[str] | None = None,
) -> tuple[list[dict[str, Any]], list[str], dict[str, Any]]:
    """Discover Creative Commons cats with the official YouTube Data API.

    The search request uses videoLicense=creativeCommon and the detail request
    rechecks status.license == creativeCommon. No OAuth or channel access is
    required for this public-data workflow.
    """
    requested = [
        str(value).strip()
        for value in (queries or list(_DEFAULT_API_QUERIES))
        if str(value).strip()
    ]
    per_query = max(1, min(int(scan_per_query), 50))
    warnings: list[str] = []
    merged: list[dict[str, Any]] = []
    seen: set[str] = set()
    diagnostics: dict[str, Any] = {
        "backend": "youtube_data_api",
        "exact_license_filter": "creativeCommon",
        "queries": {},
    }

    for query in requested:
        try:
            found = discover_youtube_cc_cats(
                api_key=api_key,
                query=query,
                days=max(int(days), 1),
                limit=per_query,
            )
        except httpx.HTTPStatusError as exc:
            response = exc.response
            detail = ""
            try:
                payload = response.json()
                error = payload.get("error") if isinstance(payload, dict) else None
                if isinstance(error, dict):
                    detail = str(error.get("message") or "").strip()
            except Exception:
                detail = ""
            suffix = f": {detail}" if detail else ""
            warnings.append(f"{query}: YouTube Data API HTTP {response.status_code}{suffix}")
            diagnostics["queries"][query] = {"returned": 0, "accepted": 0}
            continue
        except httpx.HTTPError as exc:
            warnings.append(f"{query}: YouTube Data API request failed: {type(exc).__name__}")
            diagnostics["queries"][query] = {"returned": 0, "accepted": 0}
            continue

        accepted = 0
        for item in found:
            video_id = str(item.get("video_id") or "").strip()
            if not video_id or video_id in seen:
                continue
            seen.add(video_id)
            accepted += 1
            merged.append(
                dict(item)
                | {
                    "rights_verified": True,
                    "rights_verification_method": "youtube_data_api_status_license",
                    "cc_search_query": query,
                    "api_status_license": "creativeCommon",
                }
            )
        diagnostics["queries"][query] = {
            "returned": len(found),
            "accepted": accepted,
        }

    merged.sort(
        key=lambda item: (
            -float(item.get("views_per_day") or 0.0),
            -int(item.get("view_count") or 0),
            str(item.get("published_at") or ""),
        )
    )
    selected = merged[: max(int(limit), 1)]
    for rank, item in enumerate(selected, 1):
        item["cc_rank"] = rank
    diagnostics["candidate_count"] = len(selected)
    return selected, warnings, diagnostics


def write_api_report(
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
                "version": 3,
                "source": "youtube_data_api_cc_search",
                "backend": "youtube_data_api",
                "created_at": datetime.now(timezone.utc).isoformat(),
                "rights_evidence": "YouTube Data API search.videoLicense=creativeCommon + videos.status.license=creativeCommon",
                "policy": {
                    "attribution_required": True,
                    "human_review_required": True,
                    "note": (
                        "Candidates are filtered and rechecked as Creative Commons by the official YouTube Data API. "
                        "Import repeats the status.license check before media download."
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


def _api_report_candidate(report: dict[str, Any], rank: int) -> dict[str, Any]:
    if report.get("source") != "youtube_data_api_cc_search":
        raise ValueError("official CC import requires a youtube_data_api_cc_search report")
    candidates = report.get("candidates") or []
    index = int(rank) - 1
    if index < 0 or index >= len(candidates):
        raise ValueError(f"candidate must be 1..{len(candidates)}")
    item = candidates[index]
    if not isinstance(item, dict):
        raise ValueError("selected official CC candidate is malformed")
    if item.get("rights_verified") is not True:
        raise ValueError("selected candidate does not carry verified YouTube API rights evidence")
    if item.get("rights_status") != "creative_commons_attribution_required":
        raise ValueError("selected candidate is not marked as Creative Commons")
    if item.get("api_status_license") != "creativeCommon":
        raise ValueError("selected candidate lost its official creativeCommon status evidence")
    return dict(item)


def verify_api_cc_status(*, api_key: str, video_id: str) -> dict[str, Any]:
    """Recheck the current YouTube status license immediately before download."""
    with httpx.Client(timeout=45, follow_redirects=True) as client:
        response = client.get(
            YOUTUBE_VIDEOS_URL,
            params={
                "key": api_key,
                "part": "status,snippet",
                "id": video_id,
            },
        )
        response.raise_for_status()
        items = response.json().get("items", [])
    if not items:
        raise ValueError("YouTube Data API no longer returns the selected video")
    item = items[0]
    status = item.get("status") or {}
    if str(status.get("license") or "") != "creativeCommon":
        raise ValueError("Current YouTube Data API status is not creativeCommon; refusing production download")
    snippet = item.get("snippet") or {}
    return {
        "license": "YouTube Creative Commons Attribution",
        "title": str(snippet.get("title") or "").strip(),
        "creator": str(snippet.get("channelTitle") or "").strip(),
    }


def import_api_report_candidate(
    settings: Settings,
    *,
    slot: int,
    report_path: Path,
    rank: int,
    api_key: str,
) -> tuple[Path, Path, dict[str, Any]]:
    if not api_key:
        raise ValueError("YOUTUBE_API_KEY is required to recheck an official API CC candidate")
    if not report_path.exists():
        raise FileNotFoundError(f"CC report not found: {report_path}")
    report = json.loads(report_path.read_text(encoding="utf-8"))
    candidate = _api_report_candidate(report, rank)

    video_id = str(candidate.get("video_id") or "").strip()
    url = str(candidate.get("url") or "").strip()
    if not video_id or not url:
        raise ValueError("selected official CC candidate has no usable YouTube id/url")

    verified = verify_api_cc_status(api_key=api_key, video_id=video_id)
    import_dir = settings.runtime_dir / "imports" / f"slot-{int(slot):02d}" / "youtube-cc"
    media = _download_cc_media(url, destination_dir=import_dir, video_id=video_id)
    validation = _validate_cat_media(settings, media)

    # yt-dlp metadata is useful for canonical URL/uploader details, but the
    # official API status above is the rights authority for this flow.
    try:
        meta = fetch_youtube_metadata(url)
    except ValueError:
        meta = {}
    actual_id = str(meta.get("video_id") or "").strip()
    if actual_id and actual_id != video_id:
        raise ValueError("download target metadata resolves to a different YouTube video")

    title = str(meta.get("title") or verified.get("title") or candidate.get("title") or "").strip()
    creator = str(meta.get("creator") or verified.get("creator") or candidate.get("channel_title") or "").strip()
    source_url = str(meta.get("source_url") or url).strip()
    license_name = "YouTube Creative Commons Attribution"
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
        "rights_verification_method": "youtube_data_api_status_license",
        "api_status_license": "creativeCommon",
        "cc_search_query": candidate.get("cc_search_query"),
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

    cc_search = sub.add_parser("cc-search", help="Prefer official YouTube Data API Creative Commons search")
    cc_search.add_argument("--days", type=int, default=6000)
    cc_search.add_argument("--limit", type=int, default=15)
    cc_search.add_argument("--scan-per-query", type=int, default=30)
    cc_search.add_argument("--query", action="append", default=None)
    cc_search.add_argument("--report", default=None)
    cc_search.add_argument("--no-key", action="store_true", help="Force the legacy no-key CC-filter backend")

    cc_import = sub.add_parser("cc-import", help="Import one candidate from a saved CC report")
    cc_import.add_argument("slot", type=int)
    cc_import.add_argument("--candidate", type=int, required=True)
    cc_import.add_argument("--report", default=None)

    cc = sub.add_parser("cc", help="Legacy strict URL import when yt-dlp directly reports a CC license")
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
    api_key = os.getenv("YOUTUBE_API_KEY", "").strip()

    if args.command == "cc-search":
        use_api = bool(api_key) and not args.no_key
        if use_api:
            print("YouTube CC search: official YouTube Data API (videoLicense=creativeCommon)")
            print("Public metadata only; no OAuth, no channel login, no media download")
            candidates, warnings, diagnostics = search_cc_candidates_api(
                api_key=api_key,
                days=args.days,
                scan_per_query=args.scan_per_query,
                limit=args.limit,
                queries=args.query,
            )
            report_path = Path(args.report) if args.report else _DEFAULT_API_REPORT
            report = write_api_report(
                report_path,
                candidates=candidates,
                warnings=warnings,
                diagnostics=diagnostics,
            )
            evidence_label = "API-CC"
        else:
            print("YouTube CC search fallback: platform CC filter + yt-dlp metadata hydration")
            print("No Google Cloud/API key used; no account login; no media download")
            candidates, warnings, diagnostics = search_cc_candidates_no_key(
                days=args.days,
                scan_per_query=args.scan_per_query,
                limit=args.limit,
                queries=args.query,
            )
            report_path = Path(args.report) if args.report else _DEFAULT_NO_KEY_REPORT
            report = write_no_key_report(
                report_path,
                candidates=candidates,
                warnings=warnings,
                diagnostics=diagnostics,
            )
            evidence_label = "filter"

        print(f"Creative Commons cat candidates: {len(candidates)}")
        print(report)
        for item in candidates:
            print(
                f"[{int(item['cc_rank']):02d}] [{evidence_label}] "
                f"{int(item.get('view_count') or 0):,} views | {item.get('title')} | {item.get('url')}"
            )
        if warnings:
            print(f"Warnings: {len(warnings)} (saved in report)")
            for warning in warnings[:3]:
                print(f"- {warning}")
        if candidates:
            print("Next: `vv-cat-youtube cc-import 2 --candidate N`")
        else:
            print("No CC candidates found. Send the report diagnostics rather than widening the scan blindly.")
        return

    if args.command == "cc-import":
        report_path = Path(args.report) if args.report else (_DEFAULT_API_REPORT if api_key else _DEFAULT_NO_KEY_REPORT)
        report_path = report_path.resolve()
        if not report_path.exists():
            raise FileNotFoundError(f"CC report not found: {report_path}")
        report = json.loads(report_path.read_text(encoding="utf-8"))
        if report.get("source") == "youtube_data_api_cc_search":
            source_manifest, attribution, clip = import_api_report_candidate(
                settings,
                slot=args.slot,
                report_path=report_path,
                rank=args.candidate,
                api_key=api_key,
            )
        else:
            source_manifest, attribution, clip = import_filter_report_candidate(
                settings,
                slot=args.slot,
                report_path=report_path,
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
