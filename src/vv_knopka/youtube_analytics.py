from __future__ import annotations

import csv
import hashlib
import io
import json
import re
import sqlite3
import zipfile
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Iterable

from .analytics_store import (
    analytics_status,
    database_path,
    ingest_retention,
    ingest_statistics_snapshot,
    ingest_traffic_sources,
    latest_successful_sync,
    record_sync_run,
)
from .settings import Settings
from .youtube_metadata_backfill import METADATA_SCOPES, _require_same_bound_channel
from .youtube_observability import _load_receipts, _receipt_identity
from .youtube_uploader import (
    _google_imports,
    _save_token,
    channel_binding_path,
    client_secret_path,
    token_path,
)


ANALYTICS_SCOPE = "https://www.googleapis.com/auth/yt-analytics.readonly"
ANALYTICS_SCOPES = tuple(dict.fromkeys((*METADATA_SCOPES, ANALYTICS_SCOPE)))
CORE_METRICS = (
    "views",
    "engagedViews",
    "estimatedMinutesWatched",
    "averageViewDuration",
    "averageViewPercentage",
    "likes",
    "comments",
    "shares",
    "subscribersGained",
    "subscribersLost",
)
TRAFFIC_METRICS = ("views", "engagedViews", "estimatedMinutesWatched")
RETENTION_METRICS = ("audienceWatchRatio", "relativeRetentionPerformance")


def _read_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return value if isinstance(value, dict) else {}


def _target_index(settings: Settings) -> dict[str, dict[str, Any]]:
    targets: dict[str, dict[str, Any]] = {}
    for receipt_path, receipt in _load_receipts(settings):
        video_id = str(receipt.get("video_id") or "").strip()
        if not video_id:
            continue
        pipeline, language = _receipt_identity(receipt_path, receipt)
        upload_path = receipt_path.with_name(receipt_path.name.replace(".youtube.json", ".upload.json"))
        upload = _read_json(upload_path)
        slot = int(receipt.get("slot") or upload.get("slot") or 0)
        targets[video_id] = {
            "slot": slot,
            "video_id": video_id,
            "youtube_url": receipt.get("youtube_url") or f"https://www.youtube.com/watch?v={video_id}",
            "pipeline": pipeline or upload.get("pipeline"),
            "category": upload.get("category"),
            "editorial_profile": upload.get("editorial_profile"),
            "language": language or upload.get("language"),
            "title": receipt.get("title") or upload.get("youtube_title"),
            "published_at": receipt.get("uploaded_at"),
            "privacy_status": receipt.get("actual_privacy"),
        }
    return targets


def authorize_analytics(settings: Settings) -> dict[str, str]:
    """Upgrade the existing token while preserving upload/edit scopes and channel binding."""
    _, _, InstalledAppFlow, build, _ = _google_imports()
    secret = client_secret_path(settings)
    if not secret.exists():
        raise RuntimeError(f"YouTube OAuth client file not found: {secret}")

    token = token_path(settings)
    previous_token = token.read_text(encoding="utf-8") if token.exists() else None
    flow = InstalledAppFlow.from_client_secrets_file(str(secret), scopes=list(ANALYTICS_SCOPES))
    credentials = flow.run_local_server(port=0, open_browser=True, access_type="offline", prompt="consent")
    youtube = build("youtube", "v3", credentials=credentials, cache_discovery=False)
    try:
        current = _require_same_bound_channel(settings, youtube)
    except Exception:
        if previous_token is not None:
            token.write_text(previous_token, encoding="utf-8")
        raise

    _save_token(token, credentials)
    binding_path = channel_binding_path(settings)
    binding = _read_json(binding_path)
    binding["scope"] = list(ANALYTICS_SCOPES)
    binding["analytics_authorized_at"] = datetime.now(timezone.utc).isoformat()
    binding_path.write_text(json.dumps(binding, ensure_ascii=False, indent=2), encoding="utf-8")
    return current


def _analytics_service(settings: Settings):
    Request, Credentials, _, build, _ = _google_imports()
    token = token_path(settings)
    if not token.exists():
        raise RuntimeError("YouTube OAuth token is missing. Run `vv-youtube auth-analytics` first.")
    credentials = Credentials.from_authorized_user_file(str(token), scopes=list(ANALYTICS_SCOPES))
    if credentials.expired and credentials.refresh_token:
        credentials.refresh(Request())
        _save_token(token, credentials)
    has_scopes = getattr(credentials, "has_scopes", None)
    if not credentials.valid or not callable(has_scopes) or not bool(has_scopes([ANALYTICS_SCOPE])):
        raise RuntimeError(
            "Current token cannot read YouTube Analytics. Run `vv-youtube auth-analytics` once, then retry."
        )
    youtube = build("youtube", "v3", credentials=credentials, cache_discovery=False)
    _require_same_bound_channel(settings, youtube)
    return build("youtubeAnalytics", "v2", credentials=credentials, cache_discovery=False)


def _chunks(values: list[str], size: int = 50) -> Iterable[list[str]]:
    for index in range(0, len(values), size):
        yield values[index : index + size]


def _report_rows(response: dict[str, Any]) -> list[dict[str, Any]]:
    headers = [str(item.get("name") or "") for item in response.get("columnHeaders") or []]
    return [dict(zip(headers, row)) for row in response.get("rows") or []]


def _date_part(value: Any) -> date | None:
    text = str(value or "").strip()
    if not text:
        return None
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    try:
        return datetime.fromisoformat(text).date()
    except ValueError:
        return None


def _core_entry(target: dict[str, Any], row: dict[str, Any]) -> dict[str, Any]:
    return {
        **target,
        "views": row.get("views"),
        "engaged_views": row.get("engagedViews"),
        "estimated_minutes_watched": row.get("estimatedMinutesWatched"),
        "average_view_duration_seconds": row.get("averageViewDuration"),
        "average_percentage_viewed": row.get("averageViewPercentage"),
        "likes": row.get("likes"),
        "comments": row.get("comments"),
        "shares": row.get("shares"),
        "subscribers_gained": row.get("subscribersGained"),
        "subscribers_lost": row.get("subscribersLost"),
        "analytics_raw": row,
    }


def sync_analytics(
    settings: Settings,
    *,
    deep: bool = False,
    slots: set[int] | None = None,
    if_due_hours: float = 0,
    service: Any | None = None,
) -> dict[str, Any]:
    """Collect owner-only metrics. No OpenAI call is made."""
    now = datetime.now(timezone.utc)
    mode = "deep" if deep else "core"
    previous = latest_successful_sync(settings, mode=mode)
    if if_due_hours > 0 and previous is not None:
        elapsed = (now - previous).total_seconds() / 3600.0
        if elapsed < if_due_hours:
            return {"status": "not_due", "mode": mode, "last_sync": previous.isoformat(), "age_hours": elapsed}

    targets = _target_index(settings)
    if slots is not None:
        targets = {key: value for key, value in targets.items() if int(value.get("slot") or 0) in slots}
    if not targets:
        return {"status": "no_videos", "mode": mode, "videos": 0}

    analytics = service or _analytics_service(settings)
    collected_at = now.isoformat()
    end_date = now.date().isoformat()
    entries: list[dict[str, Any]] = []
    traffic_rows: list[dict[str, Any]] = []
    retention_rows: list[dict[str, Any]] = []
    warnings: list[str] = []

    try:
        ids = list(targets)
        for batch in _chunks(ids):
            starts = [_date_part(targets[video_id].get("published_at")) for video_id in batch]
            start = min((item for item in starts if item is not None), default=now.date() - timedelta(days=30))
            response = analytics.reports().query(
                ids="channel==MINE",
                startDate=start.isoformat(),
                endDate=end_date,
                metrics=",".join(CORE_METRICS),
                dimensions="video",
                filters=f"video=={','.join(batch)}",
                sort="-views",
                maxResults=len(batch),
            ).execute()
            for row in _report_rows(response):
                video_id = str(row.get("video") or "")
                target = targets.get(video_id)
                if target is not None:
                    entries.append(_core_entry(target, row))

        returned_ids = {str(entry.get("video_id") or "") for entry in entries}
        api_videos_returned = len(returned_ids)
        for video_id, target in targets.items():
            if video_id not in returned_ids:
                entries.append({**target, "views": 0, "likes": 0, "comments": 0})

        snapshot = {"collected_at": collected_at, "videos": entries}
        core_result = ingest_statistics_snapshot(settings, snapshot, source="youtube_analytics_api")

        if deep:
            for video_id, target in targets.items():
                start = (_date_part(target.get("published_at")) or now.date() - timedelta(days=30)).isoformat()
                try:
                    response = analytics.reports().query(
                        ids="channel==MINE",
                        startDate=start,
                        endDate=end_date,
                        metrics=",".join(TRAFFIC_METRICS),
                        dimensions="insightTrafficSourceType",
                        filters=f"video=={video_id}",
                    ).execute()
                    for row in _report_rows(response):
                        traffic_rows.append(
                            {
                                "video_id": video_id,
                                "slot": target.get("slot"),
                                "traffic_source": row.get("insightTrafficSourceType"),
                                "views": row.get("views"),
                                "engaged_views": row.get("engagedViews"),
                                "estimated_minutes_watched": row.get("estimatedMinutesWatched"),
                            }
                        )
                except Exception as exc:
                    warnings.append(f"slot {target.get('slot')} traffic: {type(exc).__name__}: {exc}")
                try:
                    response = analytics.reports().query(
                        ids="channel==MINE",
                        startDate=start,
                        endDate=end_date,
                        metrics=",".join(RETENTION_METRICS),
                        dimensions="elapsedVideoTimeRatio",
                        filters=f"video=={video_id}",
                    ).execute()
                    for row in _report_rows(response):
                        retention_rows.append(
                            {
                                "video_id": video_id,
                                "slot": target.get("slot"),
                                "elapsed_video_time_ratio": row.get("elapsedVideoTimeRatio"),
                                "audience_watch_ratio": row.get("audienceWatchRatio"),
                                "relative_retention_performance": row.get("relativeRetentionPerformance"),
                            }
                        )
                except Exception as exc:
                    warnings.append(f"slot {target.get('slot')} retention: {type(exc).__name__}: {exc}")

        traffic_inserted = ingest_traffic_sources(settings, traffic_rows, collected_at=collected_at)
        retention_inserted = ingest_retention(settings, retention_rows, collected_at=collected_at)
        result = {
            "status": "ok",
            "mode": mode,
            "collected_at": collected_at,
            "videos_requested": len(targets),
            "videos_returned": api_videos_returned,
            "snapshots_inserted": core_result["snapshots_inserted"],
            "traffic_rows_inserted": traffic_inserted,
            "retention_rows_inserted": retention_inserted,
            "warnings": warnings,
        }
        record_sync_run(settings, collected_at=collected_at, mode=mode, status="ok", details=result)
        return result
    except Exception as exc:
        details = {"error": f"{type(exc).__name__}: {exc}", "videos_requested": len(targets)}
        record_sync_run(settings, collected_at=collected_at, mode=mode, status="failed", details=details)
        raise


def _normalized_header(value: str) -> str:
    return re.sub(r"[^a-zа-яё0-9]+", " ", value.casefold()).strip()


HEADER_ALIASES = {
    "video_id": {"контент", "content", "video", "video id"},
    "title": {"название видео", "video title"},
    "published_at": {"время публикации видео", "video publish time"},
    "duration_seconds": {"продолжительность", "duration"},
    "views": {"просмотры", "views"},
    "engaged_views": {"заинтересованные просмотры", "engaged views"},
    "watch_time_hours": {"время просмотра часы", "watch time hours"},
    "average_view_duration_seconds": {
        "средняя продолжительность просмотра",
        "average view duration",
    },
    "average_percentage_viewed": {"средний процент просмотра", "average percentage viewed"},
    "likes": {"отметки нравится", "likes"},
    "comments": {"комментарии", "comments"},
    "shares": {"поделились", "shares"},
    "subscribers_net": {"подписчики", "subscribers"},
    "stayed_to_watch_percentage": {
        "продолжили смотреть",
        "stayed to watch",
        "viewed vs swiped away",
    },
    "impressions": {"показы значков видео", "impressions"},
    "impressions_ctr_percentage": {
        "ctr для значков видео",
        "impressions click through rate",
    },
}


def _canonical_headers(fieldnames: list[str]) -> dict[str, str]:
    result: dict[str, str] = {}
    for original in fieldnames:
        normalized = _normalized_header(original)
        for canonical, aliases in HEADER_ALIASES.items():
            if normalized in aliases:
                result[canonical] = original
                break
    return result


def _number(value: Any) -> float | None:
    text = str(value or "").strip().replace("\u00a0", "").replace(" ", "").replace("%", "")
    if not text:
        return None
    if "," in text and "." not in text:
        text = text.replace(",", ".")
    try:
        return float(text)
    except ValueError:
        return None


def _duration_seconds(value: Any) -> float | None:
    text = str(value or "").strip()
    if not text:
        return None
    if ":" not in text:
        return _number(text)
    try:
        parts = [float(part.replace(",", ".")) for part in text.split(":")]
    except ValueError:
        return None
    total = 0.0
    for part in parts:
        total = total * 60 + part
    return total


def _decode_csv(payload: bytes) -> str | None:
    for encoding in ("utf-8-sig", "utf-16", "cp1251"):
        try:
            return payload.decode(encoding)
        except UnicodeDecodeError:
            continue
    return None


def _csv_payloads(path: Path) -> tuple[list[tuple[str, bytes]], str]:
    raw = path.read_bytes()
    fingerprint = hashlib.sha256(raw).hexdigest()[:16]
    if zipfile.is_zipfile(path):
        with zipfile.ZipFile(path) as archive:
            payloads = [
                (info.filename, archive.read(info))
                for info in archive.infolist()
                if not info.is_dir() and info.filename.casefold().endswith(".csv")
            ]
        return payloads, fingerprint
    return [(path.name, raw)], fingerprint


def _latest_public_counts(settings: Settings) -> dict[str, dict[str, int]]:
    analytics_status(settings)
    result: dict[str, dict[str, int]] = {}
    with sqlite3.connect(database_path(settings)) as connection:
        rows = connection.execute(
            """
            SELECT video_id, views, likes, comments
            FROM metric_snapshots
            WHERE source = 'youtube_data_api'
            ORDER BY collected_at DESC
            """
        ).fetchall()
    for video_id, views, likes, comments in rows:
        result.setdefault(str(video_id), {"views": int(views), "likes": int(likes), "comments": int(comments)})
    return result


def import_studio_export(settings: Settings, export_path: Path) -> dict[str, Any]:
    """Import a Russian or English Advanced Mode CSV/ZIP without any network call."""
    path = export_path.resolve()
    if not path.exists():
        raise FileNotFoundError(path)
    payloads, fingerprint = _csv_payloads(path)
    targets = _target_index(settings)
    public_counts = _latest_public_counts(settings)
    imported: dict[str, dict[str, Any]] = {}
    unknown_video_ids: set[str] = set()
    tables_seen = 0

    for name, payload in payloads:
        text = _decode_csv(payload)
        if text is None:
            continue
        reader = csv.DictReader(io.StringIO(text))
        if not reader.fieldnames:
            continue
        headers = _canonical_headers([str(item) for item in reader.fieldnames])
        if "video_id" not in headers or "views" not in headers:
            continue
        tables_seen += 1
        for raw_row in reader:
            video_id = str(raw_row.get(headers["video_id"]) or "").strip()
            target = targets.get(video_id)
            if target is None:
                if video_id and _normalized_header(video_id) not in {"итоговое значение", "total"}:
                    unknown_video_ids.add(video_id)
                continue
            values = {
                key: raw_row.get(original)
                for key, original in headers.items()
                if key not in {"video_id", "title", "published_at", "duration_seconds"}
            }
            fallback = public_counts.get(video_id, {})
            parsed_views = _number(values.get("views"))
            parsed_likes = _number(values.get("likes"))
            parsed_comments = _number(values.get("comments"))
            entry = {
                **target,
                "title": raw_row.get(headers.get("title", "")) or target.get("title"),
                "views": int(parsed_views if parsed_views is not None else fallback.get("views", 0)),
                "likes": int(parsed_likes if parsed_likes is not None else fallback.get("likes", 0)),
                "comments": int(parsed_comments if parsed_comments is not None else fallback.get("comments", 0)),
                "engaged_views": _number(values.get("engaged_views")),
                "estimated_minutes_watched": (
                    round(_number(values.get("watch_time_hours")) * 60, 6)
                    if _number(values.get("watch_time_hours")) is not None
                    else None
                ),
                "average_view_duration_seconds": _duration_seconds(values.get("average_view_duration_seconds")),
                "average_percentage_viewed": _number(values.get("average_percentage_viewed")),
                "shares": _number(values.get("shares")),
                "subscribers_net": _number(values.get("subscribers_net")),
                "stayed_to_watch_percentage": _number(values.get("stayed_to_watch_percentage")),
                "impressions": _number(values.get("impressions")),
                "impressions_ctr_percentage": _number(values.get("impressions_ctr_percentage")),
                "studio_export": {"table": name, "columns": list(headers)},
            }
            imported[video_id] = entry

    collected_at = datetime.fromtimestamp(path.stat().st_mtime, timezone.utc).isoformat()
    snapshot = {"collected_at": collected_at, "videos": list(imported.values())}
    result = ingest_statistics_snapshot(
        settings,
        snapshot,
        source=f"youtube_studio_csv:{fingerprint}",
    )
    return {
        "export_file": str(path),
        "fingerprint": fingerprint,
        "csv_files": len(payloads),
        "metric_tables": tables_seen,
        "known_videos_imported": len(imported),
        "unknown_videos_skipped": len(unknown_video_ids),
        "snapshots_inserted": result["snapshots_inserted"],
    }


def _write_csv(archive: zipfile.ZipFile, name: str, columns: list[str], rows: list[sqlite3.Row]) -> None:
    output = io.StringIO(newline="")
    writer = csv.writer(output, lineterminator="\n")
    writer.writerow(columns)
    for row in rows:
        writer.writerow([row[column] for column in columns])
    archive.writestr(name, output.getvalue().encode("utf-8-sig"))


def _local_features(settings: Settings, videos: list[sqlite3.Row]) -> list[dict[str, Any]]:
    result: list[dict[str, Any]] = []
    for video in videos:
        slot = int(video["slot"] or 0)
        if slot <= 0:
            continue
        slot_dir = settings.runtime_dir / "slots" / f"{slot:02d}"
        plan = _read_json(slot_dir / "plan.json")
        feature = {
            "slot": slot,
            "video_id": video["video_id"],
            "category": video["category"],
            "pipeline": video["pipeline"],
            "editorial_profile": video["editorial_profile"],
            "title": video["title"],
        }
        for key in (
            "hook",
            "script",
            "visual_anchor",
            "topic",
            "payoff",
            "structure",
            "word_count",
        ):
            if key in plan:
                feature[key] = plan[key]
        result.append(feature)
    return result


def export_analytics_bundle(settings: Settings, output_path: Path | None = None) -> dict[str, Any]:
    """Create one small ZIP that the user can upload for future analysis."""
    status = analytics_status(settings)
    generated_at = datetime.now(timezone.utc)
    if output_path is None:
        root = settings.runtime_dir / "analytics" / "exports"
        root.mkdir(parents=True, exist_ok=True)
        output_path = root / f"vv-analytics-{generated_at:%Y%m%d-%H%M%S}.zip"
    else:
        output_path = output_path.resolve()
        output_path.parent.mkdir(parents=True, exist_ok=True)

    tables = {
        "videos": "SELECT * FROM videos ORDER BY slot, video_id",
        "metric_snapshots": "SELECT * FROM metric_snapshots ORDER BY collected_at, video_id",
        "checkpoints": """
            SELECT c.video_id, v.slot, c.checkpoint_hours, s.collected_at, s.age_hours,
                   s.views, s.likes, s.comments, s.engaged_views,
                   s.average_view_duration_seconds, s.average_percentage_viewed,
                   s.subscribers_gained, s.subscribers_lost, s.subscribers_net,
                   s.shares, s.stayed_to_watch_percentage, s.source
            FROM metric_checkpoints c
            JOIN videos v ON v.video_id = c.video_id
            JOIN metric_snapshots s ON s.id = c.snapshot_id
            ORDER BY v.slot, c.checkpoint_hours
        """,
        "traffic_sources": "SELECT * FROM traffic_source_snapshots ORDER BY collected_at, video_id, views DESC",
        "retention": "SELECT * FROM retention_snapshots ORDER BY collected_at, video_id, elapsed_video_time_ratio",
        "sync_runs": "SELECT * FROM analytics_sync_runs ORDER BY collected_at",
    }
    with sqlite3.connect(database_path(settings)) as connection:
        connection.row_factory = sqlite3.Row
        data: dict[str, tuple[list[str], list[sqlite3.Row]]] = {}
        for name, query in tables.items():
            cursor = connection.execute(query)
            columns = [str(item[0]) for item in cursor.description]
            data[name] = (columns, cursor.fetchall())
        video_rows = data["videos"][1]

    manifest = {
        "generated_at": generated_at.isoformat(),
        "schema_version": status["schema_version"],
        "channel_note": "Owner-only analytics export for VV_knopka; contains no OAuth tokens or API keys.",
        "missing_metric_note": (
            "stayed_to_watch_percentage remains null unless an imported Studio export contains that exact column. "
            "It is never fabricated from engaged views."
        ),
        "files": [f"{name}.csv" for name in tables] + ["local_features.json", "manifest.json"],
    }
    with zipfile.ZipFile(output_path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for name, (columns, rows) in data.items():
            _write_csv(archive, f"{name}.csv", columns, rows)
        archive.writestr(
            "local_features.json",
            json.dumps(_local_features(settings, video_rows), ensure_ascii=False, indent=2).encode("utf-8"),
        )
        archive.writestr("manifest.json", json.dumps(manifest, ensure_ascii=False, indent=2).encode("utf-8"))
    return {"output_file": str(output_path), "videos": len(video_rows), **status}
