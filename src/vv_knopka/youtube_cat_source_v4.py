from __future__ import annotations

import argparse
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from dotenv import load_dotenv

from .budget import BudgetLedger
from .settings import Settings, load_settings
from .trend_import import write_attribution_report
from .youtube_cat_source import add_test_only_file, import_cc_url, render_test_only
from .youtube_cat_source_v2 import import_cc_report_candidate as import_filter_report_candidate
from .youtube_cat_source_v3 import (
    _DEFAULT_API_REPORT,
    _DEFAULT_NO_KEY_REPORT,
    import_api_report_candidate,
    search_cc_candidates_api,
    search_cc_candidates_no_key,
    write_api_report,
    write_no_key_report,
)
from .youtube_clean_footage import clean_review_clip_metadata, review_clean_youtube_footage


def _clip_identity(item: dict[str, Any]) -> tuple[str, str]:
    provider = str(item.get("provider") or "").strip().lower()
    provider_id = str(item.get("provider_id") or "").strip()
    if provider_id:
        return provider, provider_id
    return provider, str(item.get("source_url") or item.get("file") or "").strip()


def _rewrite_manifest_clip(source_manifest: Path, clip: dict[str, Any]) -> None:
    raw = json.loads(source_manifest.read_text(encoding="utf-8"))
    identity = _clip_identity(clip)
    clips: list[dict[str, Any]] = []
    replaced = False
    for item in raw.get("clips", []) or []:
        if not isinstance(item, dict):
            continue
        if _clip_identity(item) == identity:
            if not replaced:
                clips.append(dict(clip))
                replaced = True
            continue
        clips.append(item)
    if not replaced:
        clips.insert(0, dict(clip))
    raw["clips"] = clips
    raw["require_clean_youtube_footage"] = True
    raw["source_policy"] = (
        "clean-reviewed YouTube Creative Commons plus licensed vertical stock with audible source audio"
    )
    source_manifest.write_text(json.dumps(raw, ensure_ascii=False, indent=2), encoding="utf-8")


def _remove_manifest_clip(source_manifest: Path, clip: dict[str, Any]) -> None:
    if not source_manifest.exists():
        return
    raw = json.loads(source_manifest.read_text(encoding="utf-8"))
    identity = _clip_identity(clip)
    kept = [
        item
        for item in (raw.get("clips") or [])
        if isinstance(item, dict) and _clip_identity(item) != identity
    ]
    raw["clips"] = kept
    raw["require_clean_youtube_footage"] = True
    raw["source_policy"] = (
        "clean-reviewed YouTube Creative Commons plus licensed vertical stock with audible source audio"
        if any(str(item.get("provider") or "").lower() == "youtube" for item in kept)
        else "licensed vertical stock with audible source audio"
    )
    source_manifest.write_text(json.dumps(raw, ensure_ascii=False, indent=2), encoding="utf-8")


def _clean_gate_imported_clip(
    settings: Settings,
    *,
    slot: int,
    source_manifest: Path,
    clip: dict[str, Any],
) -> tuple[dict[str, Any], dict[str, Any]]:
    ledger = BudgetLedger(settings)
    review = review_clean_youtube_footage(
        settings,
        ledger,
        video=Path(str(clip["file"])),
        slot=slot,
        video_id=str(clip.get("provider_id") or ""),
        title=str(clip.get("source_title") or ""),
        creator=str(clip.get("creator") or ""),
    )
    clip = dict(clip) | clean_review_clip_metadata(review)
    if clip.get("clean_footage_approved") is not True:
        _remove_manifest_clip(source_manifest, clip)
        write_attribution_report(source_manifest.parent, source_manifest)
        reason = str(clip.get("clean_footage_reason") or "clean-footage review rejected the source")
        raise ValueError(
            "YouTube CC candidate passed the license/format gates but failed the clean-footage anti-repost gate: "
            f"{reason}"
        )
    _rewrite_manifest_clip(source_manifest, clip)
    write_attribution_report(source_manifest.parent, source_manifest)
    return clip, review


def clean_existing_youtube_sources(
    settings: Settings,
    *,
    slot: int,
) -> tuple[Path, Path, dict[str, Any]]:
    slot_dir = settings.runtime_dir / "slots" / f"{int(slot):02d}"
    source_manifest = slot_dir / "sources.json"
    if not source_manifest.exists():
        raise FileNotFoundError(f"source manifest not found: {source_manifest}")
    raw = json.loads(source_manifest.read_text(encoding="utf-8"))
    clips = raw.get("clips") or []
    ledger = BudgetLedger(settings)

    kept: list[dict[str, Any]] = []
    reviews: list[dict[str, Any]] = []
    youtube_seen = 0
    youtube_kept = 0
    youtube_rejected = 0

    for item in clips:
        if not isinstance(item, dict):
            continue
        if str(item.get("provider") or "").strip().lower() != "youtube":
            kept.append(item)
            continue
        youtube_seen += 1
        video = Path(str(item.get("file") or ""))
        if not video.exists() or video.stat().st_size <= 0:
            youtube_rejected += 1
            reviews.append(
                {
                    "provider_id": item.get("provider_id"),
                    "approved": False,
                    "reason": "source file missing",
                }
            )
            continue

        review = review_clean_youtube_footage(
            settings,
            ledger,
            video=video,
            slot=slot,
            video_id=str(item.get("provider_id") or ""),
            title=str(item.get("source_title") or ""),
            creator=str(item.get("creator") or ""),
        )
        updated = dict(item) | clean_review_clip_metadata(review)
        reviews.append(
            {
                "provider_id": item.get("provider_id"),
                "title": item.get("source_title"),
                "creator": item.get("creator"),
                "approved": bool(updated.get("clean_footage_approved")),
                "confidence": updated.get("clean_footage_confidence"),
                "creator_branding": updated.get("clean_creator_branding"),
                "social_ui": updated.get("clean_social_ui"),
                "large_added_caption": updated.get("clean_large_added_caption"),
                "compilation_or_repost_style": updated.get("clean_compilation_or_repost_style"),
                "reason": updated.get("clean_footage_reason"),
                "review_file": updated.get("clean_review_file"),
            }
        )
        if updated.get("clean_footage_approved") is True:
            kept.append(updated)
            youtube_kept += 1
        else:
            youtube_rejected += 1

    raw["clips"] = kept
    raw["require_clean_youtube_footage"] = True
    raw["source_policy"] = (
        "clean-reviewed YouTube Creative Commons plus licensed vertical stock with audible source audio"
        if any(str(item.get("provider") or "").lower() == "youtube" for item in kept)
        else "licensed vertical stock with audible source audio"
    )
    source_manifest.write_text(json.dumps(raw, ensure_ascii=False, indent=2), encoding="utf-8")
    attribution = write_attribution_report(slot_dir, source_manifest)

    audit = {
        "version": 1,
        "slot": int(slot),
        "created_at": datetime.now(timezone.utc).isoformat(),
        "youtube_seen": youtube_seen,
        "youtube_kept": youtube_kept,
        "youtube_rejected": youtube_rejected,
        "reviews": reviews,
    }
    audit_path = slot_dir / "youtube_clean_audit.json"
    audit_path.write_text(json.dumps(audit, ensure_ascii=False, indent=2), encoding="utf-8")
    return source_manifest, attribution, audit


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

    cc_import = sub.add_parser("cc-import", help="Import one CC candidate and require the clean-footage gate")
    cc_import.add_argument("slot", type=int)
    cc_import.add_argument("--candidate", type=int, required=True)
    cc_import.add_argument("--report", default=None)

    cc_clean = sub.add_parser("cc-clean", help="Review existing YouTube production clips and remove packaged/repost-like footage")
    cc_clean.add_argument("slot", type=int)

    cc = sub.add_parser("cc", help="Legacy strict URL CC import plus clean-footage gate")
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
        clip, review = _clean_gate_imported_clip(
            settings,
            slot=args.slot,
            source_manifest=source_manifest,
            clip=clip,
        )
        attribution = write_attribution_report(source_manifest.parent, source_manifest)
        print(f"Imported YouTube CC candidate: {clip['source_title']}")
        print(f"Creator: {clip['creator']}")
        print(f"Rights evidence: {clip['rights_verification_method']}")
        print(f"License: {clip['license']}")
        print(f"Dimensions: {clip['source_width']}x{clip['source_height']}")
        print(f"Audio mean: {clip['mean_volume_db']} dB")
        print(
            f"Clean-footage gate: PASS | confidence={clip['clean_footage_confidence']:.2f} | "
            f"{clip['clean_footage_reason']}"
        )
        print(f"Clean review: {review.get('review_file') or clip.get('clean_review_file')}")
        print(f"Sources: {source_manifest}")
        print(f"Attribution: {attribution}")
        print(f"Next: `vv render-animal {args.slot}`")
        return

    if args.command == "cc-clean":
        source_manifest, attribution, audit = clean_existing_youtube_sources(settings, slot=args.slot)
        print(f"YouTube clean-footage audit: {audit['youtube_kept']} kept / {audit['youtube_seen']} reviewed")
        for item in audit["reviews"]:
            verdict = "PASS" if item.get("approved") else "REJECT"
            print(
                f"[{verdict}] {item.get('provider_id')} | confidence={float(item.get('confidence') or 0):.2f} | "
                f"{item.get('reason')}"
            )
        print(f"Audit: {source_manifest.parent / 'youtube_clean_audit.json'}")
        print(f"Sources: {source_manifest}")
        print(f"Attribution: {attribution}")
        return

    if args.command == "cc":
        source_manifest, attribution, clip = import_cc_url(settings, slot=args.slot, url=args.url)
        clip, review = _clean_gate_imported_clip(
            settings,
            slot=args.slot,
            source_manifest=source_manifest,
            clip=clip,
        )
        print(f"Imported direct-metadata YouTube CC: {clip['source_title']}")
        print(f"Clean-footage gate: PASS | {clip['clean_footage_reason']}")
        print(f"Clean review: {review.get('review_file') or clip.get('clean_review_file')}")
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
