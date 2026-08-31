from __future__ import annotations

import argparse
from pathlib import Path

from dotenv import load_dotenv

from .settings import load_settings
from .youtube_observability import collect_statistics, verify_receipts
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
    sub.add_parser("pending-count")
    sub.add_parser("verify", help="Verify processing/privacy state of uploaded receipt videos")
    sub.add_parser("stats", help="Collect current views/likes/comments for uploaded receipt videos")

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
