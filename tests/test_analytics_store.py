import json
import sqlite3
from pathlib import Path

from vv_knopka.analytics_store import (
    analytics_status,
    database_path,
    ingest_statistics_snapshot,
)
from vv_knopka.settings import Settings
from vv_knopka import youtube_observability as yo


def _settings(tmp_path: Path) -> Settings:
    return Settings(
        raw={
            "pilot": {"runtime_dir": "runtime", "openai_budget_usd": 10.0, "auto_publish": False},
            "youtube": {"enabled": True, "auto_publish": True},
        },
        root=tmp_path,
    )


def _snapshot(collected_at: str, *, views: int, category: str | None = None) -> dict:
    video = {
        "slot": 23,
        "video_id": "video-23",
        "youtube_url": "https://www.youtube.com/watch?v=video-23",
        "pipeline": "ai_short",
        "editorial_profile": "direct_v1",
        "language": "en",
        "title": "A test Short",
        "published_at": "2026-09-01T00:00:00Z",
        "privacy_status": "public",
        "views": views,
        "likes": 2,
        "comments": 1,
    }
    if category is not None:
        video["category"] = category
    return {
        "collected_at": collected_at,
        "channel_id": "channel",
        "channel_title": "Knopka322",
        "videos": [video],
    }


def test_ingest_is_idempotent_and_infers_legacy_category(tmp_path):
    settings = _settings(tmp_path)
    snapshot = _snapshot("2026-09-02T01:00:00Z", views=10)

    first = ingest_statistics_snapshot(settings, snapshot)
    second = ingest_statistics_snapshot(settings, snapshot)

    assert first["snapshots_inserted"] == 1
    assert second["snapshots_inserted"] == 0
    status = analytics_status(settings)
    assert status["videos"] == 1
    assert status["snapshots"] == 1
    assert status["checkpoints"]["24h"] == 1

    with sqlite3.connect(database_path(settings)) as connection:
        category = connection.execute(
            "SELECT category FROM videos WHERE video_id = 'video-23'"
        ).fetchone()[0]
    assert category == "animals"


def test_checkpoints_select_first_snapshot_after_each_target(tmp_path):
    settings = _settings(tmp_path)
    ingest_statistics_snapshot(
        settings,
        _snapshot("2026-09-02T06:00:00Z", views=30, category="other_facts"),
    )
    ingest_statistics_snapshot(
        settings,
        _snapshot("2026-09-02T00:06:00Z", views=24, category="other_facts"),
    )
    ingest_statistics_snapshot(
        settings,
        _snapshot("2026-09-04T02:00:00Z", views=72, category="other_facts"),
    )
    ingest_statistics_snapshot(
        settings,
        _snapshot("2026-09-08T01:00:00Z", views=168, category="other_facts"),
    )

    with sqlite3.connect(database_path(settings)) as connection:
        rows = connection.execute(
            """
            SELECT c.checkpoint_hours, s.views, ROUND(s.age_hours, 1)
            FROM metric_checkpoints c
            JOIN metric_snapshots s ON s.id = c.snapshot_id
            ORDER BY c.checkpoint_hours
            """
        ).fetchall()
        category = connection.execute(
            "SELECT category FROM videos WHERE video_id = 'video-23'"
        ).fetchone()[0]

    assert rows == [(24, 24, 24.1), (72, 72, 74.0), (168, 168, 169.0)]
    assert category == "other_facts"


def test_shadow_store_failure_does_not_block_json_history(monkeypatch, tmp_path):
    settings = _settings(tmp_path)
    snapshot = _snapshot("2026-09-02T01:00:00Z", views=10)

    def fail_store(*_args, **_kwargs):
        raise sqlite3.OperationalError("database is locked")

    monkeypatch.setattr(yo, "ingest_statistics_snapshot", fail_store)
    yo._save_statistics_snapshot(settings, snapshot)

    latest = json.loads(
        (settings.runtime_dir / "youtube" / "statistics.json").read_text(encoding="utf-8")
    )
    history = (
        settings.runtime_dir / "youtube" / "statistics-history.jsonl"
    ).read_text(encoding="utf-8").splitlines()

    assert latest["analytics_store"]["status"] == "warning"
    assert "database is locked" in latest["analytics_store"]["error"]
    assert len(history) == 1
