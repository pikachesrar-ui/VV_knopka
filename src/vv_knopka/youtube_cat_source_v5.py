from __future__ import annotations

import argparse
import json
import os
from pathlib import Path

from dotenv import load_dotenv

from .budget import BudgetLedger
from .settings import load_settings
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
from .youtube_cat_source_v4 import _clean_gate_imported_clip, clean_existing_youtube_sources
from .youtube_cc_prescreen import prescreen_cc_candidates


_CLEAN_DEFAULT_QUERIES = (
    "funny cat",
    "funny kitten",
    "cat playing",
    "cat reaction",
)


def main() -> None:
    load_dotenv()
    parser = argparse.ArgumentParser(prog="vv-cat-youtube")
    parser.add_argument("--config", default="config/pilot.toml")
    sub = parser.add_subparsers(dest="command", required=True)

    cc_search = sub.add_parser("cc-search", help="Official CC search with thumbnail clean-source prescreen")
    cc_search.add_argument("--days", type=int, default=6000)
    cc_search.add_argument("--limit", type=int, default=15)
    cc_search.add_argument("--scan-per-query", type=int, default=20)
    cc_search.add_argument("--query", action="append", default=None)
    cc_search.add_argument("--report", default=None)
    cc_search.add_argument("--no-key", action="store_true", help="Force the legacy no-key CC-filter backend")

    cc_import = sub.add_parser("cc-import", help="Import one CC candidate and require the full clean-footage gate")
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
            queries = args.query or list(_CLEAN_DEFAULT_QUERIES)
            # Search wider than the requested output so the thumbnail gate has
            # room to reject packaged/repost-like candidates. The helper still
            # caps each API search request at 50 results.
            pool_limit = min(max(int(args.limit) * 3, int(args.scan_per_query)), 50)
            print("YouTube CC search v5: official API + clean thumbnail prescreen")
            print("No OAuth/channel login; thumbnails only at prescreen; no media download")
            raw_candidates, warnings, diagnostics = search_cc_candidates_api(
                api_key=api_key,
                days=args.days,
                scan_per_query=args.scan_per_query,
                limit=pool_limit,
                queries=queries,
            )
            ledger = BudgetLedger(settings)
            candidates, clean_audit, clean_stats = prescreen_cc_candidates(
                settings,
                ledger,
                api_key=api_key,
                candidates=raw_candidates,
                output_limit=max(int(args.limit), 1),
            )
            diagnostics["clean_thumbnail_prescreen"] = clean_stats
            diagnostics["clean_thumbnail_prescreen_audit"] = clean_audit
            report_path = Path(args.report) if args.report else _DEFAULT_API_REPORT
            report = write_api_report(
                report_path,
                candidates=candidates,
                warnings=warnings,
                diagnostics=diagnostics,
            )
            evidence_label = "API-CC+CLEAN?"
            print(
                "Thumbnail prescreen: "
                f"{clean_stats.get('selected', 0)} selected / "
                f"{clean_stats.get('reviewed', 0)} reviewed / "
                f"{clean_stats.get('input', 0)} raw CC"
            )
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
            clean_suffix = ""
            if item.get("clean_thumbnail_prescreen") is True:
                clean_suffix = f" | clean-thumb={float(item.get('clean_thumbnail_confidence') or 0):.2f}"
            print(
                f"[{int(item['cc_rank']):02d}] [{evidence_label}] "
                f"{int(item.get('view_count') or 0):,} views | {item.get('title')} | "
                f"{item.get('channel_title')}{clean_suffix} | {item.get('url')}"
            )
        if warnings:
            print(f"Warnings: {len(warnings)} (saved in report)")
            for warning in warnings[:3]:
                print(f"- {warning}")
        if candidates:
            print("Next: `vv-cat-youtube cc-import 2 --candidate N`")
            print("Thumbnail CLEAN? is only a prescreen; cc-import still runs the strict four-frame gate.")
        else:
            print("No clean-looking CC candidates survived thumbnail prescreen. Inspect report diagnostics.")
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
