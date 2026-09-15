from __future__ import annotations

import json
import re
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .settings import Settings


SCHEMA_VERSION = 3
CHECKPOINT_HOURS = (24, 72, 168)
CHECKPOINT_MAX_LAG_HOURS = 24


def database_path(settings: Settings) -> Path:
    root = settings.runtime_dir / "analytics"
    root.mkdir(parents=True, exist_ok=True)
    return root / "analytics.sqlite3"


def _parse_datetime(value: Any) -> datetime | None:
    text = str(value or "").strip()
    if not text:
        return None
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    try:
        parsed = datetime.fromisoformat(text)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _as_int(value: Any, *, optional: bool = False) -> int | None:
    if value is None or value == "":
        return None if optional else 0
    try:
        return max(int(value), 0)
    except (TypeError, ValueError):
        return None if optional else 0


def infer_category(video: dict[str, Any]) -> str:
    explicit = str(video.get("category") or "").strip().lower()
    if explicit:
        return explicit
    searchable = " ".join(
        str(video.get(key) or "") for key in ("title", "topic", "hook", "script")
    ).casefold()
    if re.search(r"\b(cats?|kittens?)\b", searchable):
        return "cats"
    pipeline = str(video.get("pipeline") or "").strip().lower()
    if pipeline == "animal_compilation":
        return "cats"
    if pipeline == "ai_short":
        return "animals"
    return "unknown"


def _connect(path: Path) -> sqlite3.Connection:
    connection = sqlite3.connect(path, timeout=30)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    connection.execute("PRAGMA journal_mode = WAL")
    connection.execute("PRAGMA synchronous = NORMAL")
    return connection


def _initialize(connection: sqlite3.Connection) -> None:
    connection.executescript(
        """
        CREATE TABLE IF NOT EXISTS metadata (
            key TEXT PRIMARY KEY,
            value TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS videos (
            video_id TEXT PRIMARY KEY,
            slot INTEGER NOT NULL DEFAULT 0,
            channel_id TEXT,
            channel_title TEXT,
            youtube_url TEXT,
            pipeline TEXT,
            category TEXT NOT NULL DEFAULT 'unknown',
            editorial_profile TEXT,
            language TEXT,
            title TEXT,
            duration_seconds REAL,
            published_at TEXT,
            privacy_status TEXT,
            first_seen_at TEXT NOT NULL,
            last_seen_at TEXT NOT NULL
        );

        CREATE INDEX IF NOT EXISTS idx_videos_slot ON videos(slot);
        CREATE INDEX IF NOT EXISTS idx_videos_category ON videos(category);

        CREATE TABLE IF NOT EXISTS metric_snapshots (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            video_id TEXT NOT NULL,
            collected_at TEXT NOT NULL,
            age_hours REAL,
            views INTEGER NOT NULL DEFAULT 0,
            likes INTEGER NOT NULL DEFAULT 0,
            comments INTEGER NOT NULL DEFAULT 0,
            engaged_views INTEGER,
            estimated_minutes_watched REAL,
            average_view_duration_seconds REAL,
            average_percentage_viewed REAL,
            subscribers_gained INTEGER,
            subscribers_lost INTEGER,
            subscribers_net INTEGER,
            shares INTEGER,
            stayed_to_watch_percentage REAL,
            impressions INTEGER,
            impressions_ctr_percentage REAL,
            source TEXT NOT NULL DEFAULT 'youtube_data_api',
            raw_json TEXT NOT NULL,
            FOREIGN KEY(video_id) REFERENCES videos(video_id) ON DELETE CASCADE,
            UNIQUE(video_id, collected_at, source)
        );

        CREATE INDEX IF NOT EXISTS idx_metric_snapshots_video_age
            ON metric_snapshots(video_id, age_hours);

        CREATE TABLE IF NOT EXISTS metric_checkpoints (
            video_id TEXT NOT NULL,
            checkpoint_hours INTEGER NOT NULL,
            snapshot_id INTEGER NOT NULL,
            PRIMARY KEY(video_id, checkpoint_hours),
            FOREIGN KEY(video_id) REFERENCES videos(video_id) ON DELETE CASCADE,
            FOREIGN KEY(snapshot_id) REFERENCES metric_snapshots(id) ON DELETE CASCADE,
            CHECK(checkpoint_hours IN (24, 72, 168))
        );

        CREATE TABLE IF NOT EXISTS traffic_source_snapshots (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            video_id TEXT NOT NULL,
            collected_at TEXT NOT NULL,
            traffic_source TEXT NOT NULL,
            views INTEGER,
            engaged_views INTEGER,
            estimated_minutes_watched REAL,
            source TEXT NOT NULL DEFAULT 'youtube_analytics_api',
            raw_json TEXT NOT NULL,
            FOREIGN KEY(video_id) REFERENCES videos(video_id) ON DELETE CASCADE,
            UNIQUE(video_id, collected_at, traffic_source, source)
        );

        CREATE TABLE IF NOT EXISTS retention_snapshots (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            video_id TEXT NOT NULL,
            collected_at TEXT NOT NULL,
            elapsed_video_time_ratio REAL NOT NULL,
            audience_watch_ratio REAL,
            relative_retention_performance REAL,
            source TEXT NOT NULL DEFAULT 'youtube_analytics_api',
            raw_json TEXT NOT NULL,
            FOREIGN KEY(video_id) REFERENCES videos(video_id) ON DELETE CASCADE,
            UNIQUE(video_id, collected_at, elapsed_video_time_ratio, source)
        );

        CREATE TABLE IF NOT EXISTS analytics_sync_runs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            collected_at TEXT NOT NULL,
            mode TEXT NOT NULL,
            status TEXT NOT NULL,
            details_json TEXT NOT NULL
        );
        """
    )
    # Existing user databases are upgraded in place; no destructive rebuild is needed.
    existing_columns = {
        str(row[1]) for row in connection.execute("PRAGMA table_info(metric_snapshots)").fetchall()
    }
    additions = {
        "estimated_minutes_watched": "REAL",
        "subscribers_lost": "INTEGER",
        "subscribers_net": "INTEGER",
        "impressions": "INTEGER",
        "impressions_ctr_percentage": "REAL",
    }
    for name, sql_type in additions.items():
        if name not in existing_columns:
            connection.execute(f"ALTER TABLE metric_snapshots ADD COLUMN {name} {sql_type}")
    video_columns = {
        str(row[1]) for row in connection.execute("PRAGMA table_info(videos)").fetchall()
    }
    if "duration_seconds" not in video_columns:
        connection.execute("ALTER TABLE videos ADD COLUMN duration_seconds REAL")
    # Rich analytics v1 used to create a synthetic zero row when Analytics API
    # had not processed a newly published video yet. Those rows contain none of
    # the owner-only fields and no analytics_raw payload, so they can be removed
    # without touching legitimate zero-view reports returned by the API.
    connection.execute(
        """
        DELETE FROM metric_snapshots
        WHERE source = 'youtube_analytics_api'
          AND engaged_views IS NULL
          AND estimated_minutes_watched IS NULL
          AND average_view_duration_seconds IS NULL
          AND average_percentage_viewed IS NULL
          AND subscribers_gained IS NULL
          AND subscribers_lost IS NULL
          AND shares IS NULL
          AND instr(raw_json, '"analytics_raw"') = 0
        """
    )
    # A checkpoint is useful only near its target. A first snapshot collected
    # days later must not masquerade as a 24h/72h measurement.
    connection.execute(
        """
        DELETE FROM metric_checkpoints
        WHERE EXISTS (
            SELECT 1
            FROM metric_snapshots AS snapshot
            WHERE snapshot.id = metric_checkpoints.snapshot_id
              AND snapshot.age_hours > metric_checkpoints.checkpoint_hours + ?
        )
        """,
        (float(CHECKPOINT_MAX_LAG_HOURS),),
    )
    connection.execute(
        """
        INSERT INTO metadata(key, value) VALUES('schema_version', ?)
        ON CONFLICT(key) DO UPDATE SET value = excluded.value
        """,
        (str(SCHEMA_VERSION),),
    )
    connection.execute(f"PRAGMA user_version = {SCHEMA_VERSION}")


def _refresh_checkpoints(connection: sqlite3.Connection, video_id: str) -> None:
    for hours in CHECKPOINT_HOURS:
        candidate = connection.execute(
            """
            SELECT id
            FROM metric_snapshots
            WHERE video_id = ? AND age_hours >= ? AND age_hours <= ?
            ORDER BY age_hours ASC, collected_at ASC
            LIMIT 1
            """,
            (video_id, float(hours), float(hours + CHECKPOINT_MAX_LAG_HOURS)),
        ).fetchone()
        if candidate is None:
            connection.execute(
                "DELETE FROM metric_checkpoints WHERE video_id = ? AND checkpoint_hours = ?",
                (video_id, hours),
            )
            continue
        connection.execute(
            """
            INSERT INTO metric_checkpoints(video_id, checkpoint_hours, snapshot_id)
            VALUES(?, ?, ?)
            ON CONFLICT(video_id, checkpoint_hours)
            DO UPDATE SET snapshot_id = excluded.snapshot_id
            """,
            (video_id, hours, int(candidate["id"])),
        )


def ingest_statistics_snapshot(
    settings: Settings,
    snapshot: dict[str, Any],
    *,
    source: str = "youtube_data_api",
) -> dict[str, Any]:
    """Persist one public-metrics snapshot without making any network or LLM calls."""
    path = database_path(settings)
    collected_at = str(snapshot.get("collected_at") or datetime.now(timezone.utc).isoformat())
    collected_dt = _parse_datetime(collected_at)
    channel_id = str(snapshot.get("channel_id") or "").strip() or None
    channel_title = str(snapshot.get("channel_title") or "").strip() or None
    videos = [item for item in (snapshot.get("videos") or []) if isinstance(item, dict)]

    snapshots_inserted = 0
    with _connect(path) as connection:
        _initialize(connection)
        for video in videos:
            video_id = str(video.get("video_id") or "").strip()
            if not video_id:
                continue
            published_at = str(video.get("published_at") or "").strip() or None
            published_dt = _parse_datetime(published_at)
            age_hours = None
            if collected_dt is not None and published_dt is not None:
                age_hours = max((collected_dt - published_dt).total_seconds() / 3600.0, 0.0)

            connection.execute(
                """
                INSERT INTO videos(
                    video_id, slot, channel_id, channel_title, youtube_url, pipeline,
                    category, editorial_profile, language, title, duration_seconds,
                    published_at, privacy_status, first_seen_at, last_seen_at
                ) VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(video_id) DO UPDATE SET
                    slot = CASE WHEN excluded.slot > 0 THEN excluded.slot ELSE videos.slot END,
                    channel_id = COALESCE(excluded.channel_id, videos.channel_id),
                    channel_title = COALESCE(excluded.channel_title, videos.channel_title),
                    youtube_url = COALESCE(excluded.youtube_url, videos.youtube_url),
                    pipeline = COALESCE(excluded.pipeline, videos.pipeline),
                    category = CASE WHEN excluded.category != 'unknown' THEN excluded.category ELSE videos.category END,
                    editorial_profile = COALESCE(excluded.editorial_profile, videos.editorial_profile),
                    language = COALESCE(excluded.language, videos.language),
                    title = COALESCE(excluded.title, videos.title),
                    duration_seconds = COALESCE(excluded.duration_seconds, videos.duration_seconds),
                    published_at = COALESCE(excluded.published_at, videos.published_at),
                    privacy_status = COALESCE(excluded.privacy_status, videos.privacy_status),
                    last_seen_at = excluded.last_seen_at
                """,
                (
                    video_id,
                    int(video.get("slot") or 0),
                    channel_id,
                    channel_title,
                    video.get("youtube_url"),
                    video.get("pipeline"),
                    infer_category(video),
                    video.get("editorial_profile"),
                    video.get("language"),
                    video.get("title"),
                    video.get("duration_seconds"),
                    published_at,
                    video.get("privacy_status"),
                    collected_at,
                    collected_at,
                ),
            )
            cursor = connection.execute(
                """
                INSERT OR IGNORE INTO metric_snapshots(
                    video_id, collected_at, age_hours, views, likes, comments,
                    engaged_views, estimated_minutes_watched,
                    average_view_duration_seconds, average_percentage_viewed,
                    subscribers_gained, subscribers_lost, subscribers_net, shares,
                    stayed_to_watch_percentage, impressions,
                    impressions_ctr_percentage, source, raw_json
                ) VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    video_id,
                    collected_at,
                    age_hours,
                    _as_int(video.get("views")),
                    _as_int(video.get("likes")),
                    _as_int(video.get("comments")),
                    _as_int(video.get("engaged_views"), optional=True),
                    video.get("estimated_minutes_watched"),
                    video.get("average_view_duration_seconds"),
                    video.get("average_percentage_viewed"),
                    _as_int(video.get("subscribers_gained"), optional=True),
                    _as_int(video.get("subscribers_lost"), optional=True),
                    _as_int(video.get("subscribers_net"), optional=True),
                    _as_int(video.get("shares"), optional=True),
                    video.get("stayed_to_watch_percentage"),
                    _as_int(video.get("impressions"), optional=True),
                    video.get("impressions_ctr_percentage"),
                    source,
                    json.dumps(video, ensure_ascii=False, separators=(",", ":")),
                ),
            )
            snapshots_inserted += max(int(cursor.rowcount), 0)
            _refresh_checkpoints(connection, video_id)

        checkpoint_counts = {
            f"{hours}h": int(
                connection.execute(
                    "SELECT COUNT(*) FROM metric_checkpoints WHERE checkpoint_hours = ?",
                    (hours,),
                ).fetchone()[0]
            )
            for hours in CHECKPOINT_HOURS
        }

    return {
        "status": "ok",
        "database": str(path),
        "schema_version": SCHEMA_VERSION,
        "videos_upserted": len([v for v in videos if str(v.get("video_id") or "").strip()]),
        "snapshots_inserted": snapshots_inserted,
        "checkpoints": checkpoint_counts,
    }


def ingest_traffic_sources(
    settings: Settings,
    rows: list[dict[str, Any]],
    *,
    collected_at: str,
    source: str = "youtube_analytics_api",
) -> int:
    path = database_path(settings)
    inserted = 0
    with _connect(path) as connection:
        _initialize(connection)
        for row in rows:
            video_id = str(row.get("video_id") or "").strip()
            traffic_source = str(row.get("traffic_source") or "").strip()
            if not video_id or not traffic_source:
                continue
            cursor = connection.execute(
                """
                INSERT OR IGNORE INTO traffic_source_snapshots(
                    video_id, collected_at, traffic_source, views, engaged_views,
                    estimated_minutes_watched, source, raw_json
                ) VALUES(?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    video_id,
                    collected_at,
                    traffic_source,
                    _as_int(row.get("views"), optional=True),
                    _as_int(row.get("engaged_views"), optional=True),
                    row.get("estimated_minutes_watched"),
                    source,
                    json.dumps(row, ensure_ascii=False, separators=(",", ":")),
                ),
            )
            inserted += max(int(cursor.rowcount), 0)
    return inserted


def ingest_retention(
    settings: Settings,
    rows: list[dict[str, Any]],
    *,
    collected_at: str,
    source: str = "youtube_analytics_api",
) -> int:
    path = database_path(settings)
    inserted = 0
    with _connect(path) as connection:
        _initialize(connection)
        for row in rows:
            video_id = str(row.get("video_id") or "").strip()
            ratio = row.get("elapsed_video_time_ratio")
            if not video_id or ratio is None:
                continue
            cursor = connection.execute(
                """
                INSERT OR IGNORE INTO retention_snapshots(
                    video_id, collected_at, elapsed_video_time_ratio,
                    audience_watch_ratio, relative_retention_performance,
                    source, raw_json
                ) VALUES(?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    video_id,
                    collected_at,
                    float(ratio),
                    row.get("audience_watch_ratio"),
                    row.get("relative_retention_performance"),
                    source,
                    json.dumps(row, ensure_ascii=False, separators=(",", ":")),
                ),
            )
            inserted += max(int(cursor.rowcount), 0)
    return inserted


def record_sync_run(
    settings: Settings,
    *,
    collected_at: str,
    mode: str,
    status: str,
    details: dict[str, Any],
) -> None:
    path = database_path(settings)
    with _connect(path) as connection:
        _initialize(connection)
        connection.execute(
            "INSERT INTO analytics_sync_runs(collected_at, mode, status, details_json) VALUES(?, ?, ?, ?)",
            (collected_at, mode, status, json.dumps(details, ensure_ascii=False, separators=(",", ":"))),
        )


def latest_successful_sync(settings: Settings, *, mode: str = "core") -> datetime | None:
    path = database_path(settings)
    with _connect(path) as connection:
        _initialize(connection)
        value = connection.execute(
            "SELECT MAX(collected_at) FROM analytics_sync_runs WHERE mode = ? AND status = 'ok'",
            (mode,),
        ).fetchone()[0]
    return _parse_datetime(value)


def import_statistics_history(
    settings: Settings,
    history_path: Path | None = None,
) -> dict[str, Any]:
    """Idempotently import the existing JSONL history into SQLite."""
    path = history_path or (settings.runtime_dir / "youtube" / "statistics-history.jsonl")
    if not path.exists():
        return {
            "history_file": str(path),
            "lines_seen": 0,
            "invalid_lines": 0,
            "snapshots_inserted": 0,
        }

    lines_seen = 0
    invalid_lines = 0
    snapshots_inserted = 0
    with path.open("r", encoding="utf-8-sig") as handle:
        for line in handle:
            text = line.strip()
            if not text:
                continue
            lines_seen += 1
            try:
                snapshot = json.loads(text)
            except json.JSONDecodeError:
                invalid_lines += 1
                continue
            if not isinstance(snapshot, dict):
                invalid_lines += 1
                continue
            result = ingest_statistics_snapshot(settings, snapshot)
            snapshots_inserted += int(result.get("snapshots_inserted") or 0)

    return {
        "history_file": str(path),
        "lines_seen": lines_seen,
        "invalid_lines": invalid_lines,
        "snapshots_inserted": snapshots_inserted,
    }


def analytics_status(settings: Settings) -> dict[str, Any]:
    path = database_path(settings)
    with _connect(path) as connection:
        _initialize(connection)
        videos = int(connection.execute("SELECT COUNT(*) FROM videos").fetchone()[0])
        snapshots = int(connection.execute("SELECT COUNT(*) FROM metric_snapshots").fetchone()[0])
        latest = connection.execute("SELECT MAX(collected_at) FROM metric_snapshots").fetchone()[0]
        checkpoints = {
            f"{hours}h": int(
                connection.execute(
                    "SELECT COUNT(*) FROM metric_checkpoints WHERE checkpoint_hours = ?",
                    (hours,),
                ).fetchone()[0]
            )
            for hours in CHECKPOINT_HOURS
        }
        traffic_sources = int(connection.execute("SELECT COUNT(*) FROM traffic_source_snapshots").fetchone()[0])
        retention_points = int(connection.execute("SELECT COUNT(*) FROM retention_snapshots").fetchone()[0])
        latest_rich_sync = connection.execute(
            "SELECT MAX(collected_at) FROM analytics_sync_runs WHERE status = 'ok'"
        ).fetchone()[0]
    return {
        "database": str(path),
        "schema_version": SCHEMA_VERSION,
        "videos": videos,
        "snapshots": snapshots,
        "latest_collected_at": latest,
        "checkpoints": checkpoints,
        "traffic_sources": traffic_sources,
        "retention_points": retention_points,
        "latest_rich_sync": latest_rich_sync,
    }
