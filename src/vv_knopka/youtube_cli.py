from __future__ import annotations

import argparse
from pathlib import Path

from dotenv import load_dotenv

from .settings import load_settings
from .youtube_metadata_backfill import (
    authorize_metadata_edit,
    backfill_published_metadata,
    parse_slot_spec,
)
from .youtube_observability import build_performance_report, collect_statistics, verify_receipts
from .youtube_pending_metadata import upgrade_pending_metadata
from .youtube_uploader import (
    active_upload_limit,
    authorize_and_bind,
    channel_binding_path,
    client_secret_path,
    pending_ready_count,
    token_path,
    upload_ready,
)


def main() -> None:
    load_dotenv()
    parser = argparse.ArgumentParser(prog="vv-youtube")
    parser.add_argument("--config", default="config/pilot.toml")
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("status")
    sub.add_parser("auth")
    sub.add_parser(
        "auth-metadata",
        help="Reauthorize the already-bound channel with metadata-edit scope without changing the channel binding",
    )
    backfill = sub.add_parser(
        "backfill-metadata",
        help="Add discovery tags/hashtags to already-uploaded videos; dry-run unless --apply is supplied",
    )
    backfill.add_argument("--slots", default=None, help="Slot list/range, for example 1-11 or 1,3,5-8")
    backfill.add_argument("--apply", action="store_true")

    pending_upgrade = sub.add_parser(
        "upgrade-pending-metadata",
        help="Add discovery tags/hashtags to unpublished ready sidecars without touching video bytes",
    )
    pending_upgrade.add_argument("--slots", default=None, help="Slot list/range, for example 12-15")
    pending_upgrade.add_argument("--apply", action="store_true")

    sub.add_parser("pending-count")
    sub.add_parser("verify", help="Verify processing/privacy state of uploaded receipt videos")
    sub.add_parser("stats", help="Collect current views/likes/comments for uploaded receipt videos")
    report = sub.add_parser("report", help="Rank latest YouTube stats using age-aware performance metrics")
    report.add_argument("--limit", type=int, default=10)

    upload = sub.add_parser("upload-ready")
    upload.add_argument("--limit", type=int, default=None)
    upload.add_argument("--newest", action="store_true")
    upload.add_argument("--dry-run", action="store_true")

    args = parser.parse_args()
    settings = load_settings(Path(args.config).resolve())

    if args.command == "status":
        pending = pending_ready_count(settings)
        cooldown = active_upload_limit(settings)
        print(f"youtube enabled: {settings.youtube_enabled}")
        print(f"youtube auto_publish: {settings.youtube_auto_publish}")
        print(f"requested privacy: {settings.raw.get('youtube', {}).get('privacy_status', 'public')}")
        print(f"client secret: {client_secret_path(settings)} ({'present' if client_secret_path(settings).exists() else 'missing'})")
        print(f"oauth token: {token_path(settings)} ({'present' if token_path(settings).exists() else 'missing'})")
        print(f"channel binding: {channel_binding_path(settings)} ({'present' if channel_binding_path(settings).exists() else 'missing'})")
        print(f"pending ready uploads: {pending}")
        if cooldown is not None:
            print(f"upload limit cooldown until: {cooldown.get('retry_not_before')}")
        return

    if args.command == "pending-count":
        print(pending_ready_count(settings))
        return

    if args.command == "auth":
        channel = authorize_and_bind(settings)
        print(f"YouTube channel bound: {channel['channel_title']} ({channel['channel_id']})")
        print(f"Token: {token_path(settings)}")
        print(f"Binding: {channel_binding_path(settings)}")
        return

    if args.command == "auth-metadata":
        channel = authorize_metadata_edit(settings)
        print(f"YouTube metadata-edit authorization ready: {channel['channel_title']} ({channel['channel_id']})")
        print(f"Token upgraded in place: {token_path(settings)}")
        print("Existing upload automation remains bound to the same channel.")
        return

    if args.command == "backfill-metadata":
        try:
            slots = parse_slot_spec(args.slots)
        except ValueError as exc:
            parser.error(str(exc))
        results = backfill_published_metadata(settings, slots=slots, apply=bool(args.apply))
        if not results:
            print("No uploaded receipt videos matched the requested slots.")
            return
        changed = 0
        applied = 0
        missing = 0
        for item in results:
            if item.get("missing"):
                missing += 1
                print(f"MISSING slot {item['slot']}: YouTube video {item['video_id']} was not returned by the API")
                continue
            tags = ", ".join(item.get("added_tags") or []) or "none"
            hashtags = " ".join(item.get("added_hashtags") or []) or "none"
            if item.get("changed"):
                changed += 1
            if item.get("applied"):
                applied += 1
                prefix = "UPDATED"
            elif item.get("changed"):
                prefix = "DRY RUN"
            else:
                prefix = "UNCHANGED"
            print(f"{prefix} slot {item['slot']}: +tags=[{tags}] | +hashtags=[{hashtags}]")
        mode = "APPLY" if args.apply else "DRY RUN"
        print(f"{mode} summary: {len(results)} videos | changed={changed} | applied={applied} | missing={missing}")
        if not args.apply and changed:
            print("Nothing was changed on YouTube. Re-run with --apply after reviewing this output.")
        return

    if args.command == "upgrade-pending-metadata":
        try:
            slots = parse_slot_spec(args.slots)
        except ValueError as exc:
            parser.error(str(exc))
        results = upgrade_pending_metadata(settings, slots=slots, apply=bool(args.apply))
        if not results:
            print("No unpublished ready metadata matched the requested slots.")
            return
        changed = 0
        applied = 0
        for item in results:
            tags = ", ".join(item.get("added_tags") or []) or "none"
            hashtags = " ".join(item.get("added_hashtags") or []) or "none"
            if item.get("changed"):
                changed += 1
            if item.get("applied"):
                applied += 1
                prefix = "UPDATED"
            elif item.get("changed"):
                prefix = "DRY RUN"
            else:
                prefix = "UNCHANGED"
            print(f"{prefix} slot {item['slot']}: +tags=[{tags}] | +hashtags=[{hashtags}]")
        mode = "APPLY" if args.apply else "DRY RUN"
        print(f"{mode} summary: {len(results)} pending sidecars | changed={changed} | applied={applied}")
        if not args.apply and changed:
            print("No local upload sidecar was changed. Re-run with --apply after reviewing this output.")
        return

    if args.command == "verify":
        results = verify_receipts(settings)
        if not results:
            print("No uploaded receipt videos to verify.")
            return
        failed = False
        for item in results:
            state = item["publication_state"]
            if state in {"FAILED", "MISSING"}:
                failed = True
            print(
                f"slot {item['slot']}: {state} | "
                f"upload={item.get('upload_status')} processing={item.get('processing_status')} "
                f"privacy={item.get('privacy_status')}"
            )
        if failed:
            raise SystemExit(74)
        return

    if args.command == "stats":
        snapshot = collect_statistics(settings)
        videos = snapshot.get("videos") or []
        print(
            f"YouTube stats: {len(videos)} videos | collected {snapshot.get('collected_at')} | "
            f"{snapshot.get('channel_title', '')}"
        )
        for item in videos:
            print(
                f"slot {item['slot']}: {item['views']} views | "
                f"{item['likes']} likes | {item['comments']} comments | {item.get('title')}"
            )
        return

    if args.command == "report":
        performance = build_performance_report(settings)
        videos = performance.get("videos") or []
        pipelines = performance.get("pipelines") or {}
        if not videos:
            print("No local YouTube statistics snapshot yet. Run `vv-youtube stats` first.")
            return
        print(
            f"YouTube performance report | stats={performance.get('statistics_collected_at')} | "
            f"{performance.get('channel_title', '')}"
        )
        for name, item in sorted(pipelines.items()):
            print(
                f"{name}: {item['videos']} videos | avg views={item['average_views']:.1f} | "
                f"avg views/hour={item['average_views_per_hour']:.2f} | "
                f"likes/1k={item['average_likes_per_1000_views']:.2f} | "
                f"comments/1k={item['average_comments_per_1000_views']:.2f}"
            )
        print("Top by age-adjusted views/hour:")
        for item in videos[: max(int(args.limit), 0)]:
            print(
                f"slot {item['slot']}: {item['views']} views | {item['views_per_hour']:.2f}/h | "
                f"likes/1k={item['likes_per_1000_views']:.2f} | age={item['age_hours']:.1f}h | "
                f"{item.get('title')}"
            )
        return

    if args.command == "upload-ready":
        results = upload_ready(
            settings,
            limit=args.limit,
            newest=bool(args.newest),
            dry_run=bool(args.dry_run),
        )
        if not results:
            print("No pending ready_for_review uploads.")
            return

        deferred = False
        for result in results:
            if result.get("dry_run"):
                tags = ", ".join(result.get("tags") or [])
                extra = f" | tags={tags}" if tags else ""
                print(
                    f"DRY RUN slot {result['slot']}: {result['title']} -> "
                    f"{result['requested_privacy']} | {result['video_file']}{extra}"
                )
            elif result.get("deferred"):
                deferred = True
                print(
                    f"DEFERRED slot {result.get('slot')}: YouTube daily upload limit reached. "
                    f"Retry not before {result.get('retry_not_before')}."
                )
            elif result.get("skipped"):
                print(f"SKIP slot {result.get('slot')}: already uploaded as {result.get('video_id')}")
            else:
                print(
                    f"UPLOADED slot {result['slot']}: {result['youtube_url']} | "
                    f"requested={result['requested_privacy']} actual={result['actual_privacy']}"
                )

        if deferred:
            raise SystemExit(75)
        return


if __name__ == "__main__":
    main()
