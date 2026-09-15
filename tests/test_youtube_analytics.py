import csv
import io
import json
import sqlite3
import zipfile
from pathlib import Path

import vv_knopka.youtube_analytics as ya
from vv_knopka.analytics_store import analytics_status, database_path, ingest_statistics_snapshot
from vv_knopka.settings import Settings
from vv_knopka.youtube_analytics import (
    ANALYTICS_SCOPE,
    ANALYTICS_SCOPES,
    export_analytics_bundle,
    import_studio_export,
    sync_analytics,
)


def _settings(tmp_path: Path) -> Settings:
    return Settings(
        raw={
            "pilot": {"runtime_dir": "runtime", "openai_budget_usd": 10.0, "auto_publish": False},
            "youtube": {"enabled": True, "auto_publish": True},
        },
        root=tmp_path,
    )


def _receipt(settings: Settings) -> None:
    ready = settings.runtime_dir / "ready_for_review"
    ready.mkdir(parents=True)
    (ready / "slot-23-en-ai.youtube.json").write_text(
        json.dumps(
            {
                "slot": 23,
                "video_id": "video-23",
                "youtube_url": "https://www.youtube.com/watch?v=video-23",
                "uploaded_at": "2026-09-14T01:30:00Z",
                "actual_privacy": "public",
                "title": "Why Cats Slow-Blink at You #shorts",
            }
        ),
        encoding="utf-8",
    )
    (ready / "slot-23-en-ai.upload.json").write_text(
        json.dumps(
            {
                "slot": 23,
                "pipeline": "ai_short",
                "category": "cats",
                "language": "en",
                "editorial_profile": "direct_v1",
                "youtube_title": "Why Cats Slow-Blink at You #shorts",
            }
        ),
        encoding="utf-8",
    )


class _Request:
    def __init__(self, payload):
        self.payload = payload

    def execute(self):
        return self.payload


class _Reports:
    def __init__(self, responses):
        self.responses = responses
        self.calls = []

    def query(self, **kwargs):
        self.calls.append(kwargs)
        dimension = kwargs.get("dimensions")
        return _Request(self.responses[dimension])


class _Service:
    def __init__(self, responses):
        self.report_api = _Reports(responses)

    def reports(self):
        return self.report_api


def _api_response(headers, rows):
    return {"columnHeaders": [{"name": name} for name in headers], "rows": rows}


def test_analytics_scope_preserves_existing_scopes():
    assert ANALYTICS_SCOPE in ANALYTICS_SCOPES
    assert "https://www.googleapis.com/auth/youtube.upload" in ANALYTICS_SCOPES
    assert "https://www.googleapis.com/auth/youtube.force-ssl" in ANALYTICS_SCOPES


def test_analytics_service_loads_full_scope_set_and_checks_channel(tmp_path, monkeypatch):
    settings = _settings(tmp_path)
    token = settings.runtime_dir / "youtube" / "token.json"
    token.parent.mkdir(parents=True)
    token.write_text("{}", encoding="utf-8")
    captured = {}

    class _Credentials:
        expired = False
        refresh_token = None
        valid = True

        @classmethod
        def from_authorized_user_file(cls, filename, scopes=None):
            captured["filename"] = filename
            captured["scopes"] = tuple(scopes or ())
            return cls()

        def has_scopes(self, scopes):
            return set(scopes).issubset(set(captured["scopes"]))

    youtube = object()
    analytics = object()

    def build(name, version, **_kwargs):
        return youtube if name == "youtube" else analytics

    monkeypatch.setattr(ya, "_google_imports", lambda: (object(), _Credentials, object(), build, object()))
    monkeypatch.setattr(ya, "_require_same_bound_channel", lambda settings, service: {"channel_id": "channel"})

    assert ya._analytics_service(settings) is analytics
    assert set(ANALYTICS_SCOPES).issubset(set(captured["scopes"]))


def test_sync_collects_core_traffic_and_retention(tmp_path):
    settings = _settings(tmp_path)
    _receipt(settings)
    core_headers = [
        "video",
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
    ]
    service = _Service(
        {
            "video": _api_response(core_headers, [["video-23", 174, 90, 14.4, 9.6, 43.6, 7, 1, 2, 3, 0]]),
            "insightTrafficSourceType": _api_response(
                ["insightTrafficSourceType", "views", "engagedViews", "estimatedMinutesWatched"],
                [["SHORTS", 165, 86, 13.8]],
            ),
            "elapsedVideoTimeRatio": _api_response(
                ["elapsedVideoTimeRatio", "audienceWatchRatio", "relativeRetentionPerformance"],
                [[0.0, 1.0, 0.6], [0.5, 0.42, 0.48]],
            ),
        }
    )

    result = sync_analytics(settings, deep=True, slots={23}, service=service)

    assert result["videos_returned"] == 1
    assert result["traffic_rows_inserted"] == 1
    assert result["retention_rows_inserted"] == 2
    with sqlite3.connect(database_path(settings)) as connection:
        metric = connection.execute(
            """
            SELECT views, engaged_views, average_view_duration_seconds,
                   average_percentage_viewed, subscribers_gained, subscribers_lost, shares
            FROM metric_snapshots WHERE video_id = 'video-23'
            """
        ).fetchone()
        traffic = connection.execute(
            "SELECT traffic_source, views FROM traffic_source_snapshots"
        ).fetchone()
    assert metric == (174, 90, 9.6, 43.6, 3, 0, 2)
    assert traffic == ("SHORTS", 165)
    assert any(call["dimensions"] == "video" for call in service.report_api.calls)


def test_if_due_skips_network_service(tmp_path):
    settings = _settings(tmp_path)
    _receipt(settings)
    service = _Service(
        {
            "video": _api_response(
                [
                    "video", "views", "engagedViews", "estimatedMinutesWatched",
                    "averageViewDuration", "averageViewPercentage", "likes", "comments",
                    "shares", "subscribersGained", "subscribersLost",
                ],
                [["video-23", 1, 1, 0.1, 6, 27, 0, 0, 0, 0, 0]],
            )
        }
    )
    sync_analytics(settings, service=service)

    second = sync_analytics(settings, if_due_hours=20, service=service)

    assert second["status"] == "not_due"
    assert len(service.report_api.calls) == 1


def _studio_zip(path: Path) -> None:
    output = io.StringIO(newline="")
    writer = csv.writer(output, lineterminator="\n")
    writer.writerow(
        [
            "Контент",
            "Название видео",
            "Просмотры",
            "Заинтересованные просмотры",
            "Время просмотра (часы)",
            "Средняя продолжительность просмотра",
            "Средний процент просмотра (%)",
            "Отметки \"Нравится\"",
            "Комментарии",
            "Поделились",
            "Подписчики",
            "Продолжили смотреть (%)",
            "Показы значков видео",
            "CTR для значков видео (%)",
        ]
    )
    writer.writerow(
        [
            "video-23",
            "Why Cats Slow-Blink at You #shorts",
            174,
            90,
            "0,24",
            "0:00:09",
            "40,9",
            7,
            1,
            2,
            3,
            "58,2",
            12,
            25,
        ]
    )
    writer.writerow(["unrelated-video", "Old unrelated upload", 999])
    with zipfile.ZipFile(path, "w") as archive:
        archive.writestr("Данные из таблицы.csv", output.getvalue().encode("utf-8-sig"))
        archive.writestr("Итоговые данные.csv", "Дата,Просмотры\n2026-09-14,174\n")


def test_import_studio_zip_is_local_russian_and_idempotent(tmp_path):
    settings = _settings(tmp_path)
    _receipt(settings)
    ingest_statistics_snapshot(
        settings,
        {
            "collected_at": "2026-09-14T03:00:00Z",
            "videos": [{"video_id": "video-23", "slot": 23, "views": 170, "likes": 5, "comments": 0}],
        },
    )
    export = tmp_path / "studio.zip"
    _studio_zip(export)

    first = import_studio_export(settings, export)
    second = import_studio_export(settings, export)

    assert first["known_videos_imported"] == 1
    assert first["unknown_videos_skipped"] == 1
    assert first["snapshots_inserted"] == 1
    assert second["snapshots_inserted"] == 0
    with sqlite3.connect(database_path(settings)) as connection:
        row = connection.execute(
            """
            SELECT views, engaged_views, estimated_minutes_watched,
                   average_view_duration_seconds, average_percentage_viewed,
                   subscribers_net, stayed_to_watch_percentage, impressions,
                   impressions_ctr_percentage
            FROM metric_snapshots WHERE source LIKE 'youtube_studio_csv:%'
            """
        ).fetchone()
        category = connection.execute("SELECT category FROM videos WHERE video_id = 'video-23'").fetchone()[0]
    assert row == (174, 90, 14.4, 9.0, 40.9, 3, 58.2, 12, 25.0)
    assert category == "cats"


def test_export_bundle_contains_shareable_tables_and_local_features(tmp_path):
    settings = _settings(tmp_path)
    _receipt(settings)
    ingest_statistics_snapshot(
        settings,
        {
            "collected_at": "2026-09-15T00:00:00Z",
            "videos": [
                {
                    "video_id": "video-23",
                    "slot": 23,
                    "title": "Why Cats Slow-Blink at You #shorts",
                    "views": 174,
                    "likes": 7,
                    "comments": 1,
                }
            ],
        },
    )
    slot = settings.runtime_dir / "slots" / "23"
    slot.mkdir(parents=True)
    (slot / "plan.json").write_text(
        json.dumps({"hook": "Your cat is trying to tell you something.", "script": "Short script."}),
        encoding="utf-8",
    )

    result = export_analytics_bundle(settings)

    path = Path(result["output_file"])
    with zipfile.ZipFile(path) as archive:
        names = set(archive.namelist())
        features = json.loads(archive.read("local_features.json"))
        combined = b"".join(archive.read(name) for name in names)
    assert {"videos.csv", "metric_snapshots.csv", "checkpoints.csv", "manifest.json"} <= names
    assert features[0]["hook"] == "Your cat is trying to tell you something."
    assert b"refresh_token" not in combined
    assert b"client_secret" not in combined


def test_schema_v2_upgrades_existing_metric_table(tmp_path):
    settings = _settings(tmp_path)
    path = database_path(settings)
    with sqlite3.connect(path) as connection:
        connection.execute(
            """
            CREATE TABLE metric_snapshots(
                id INTEGER PRIMARY KEY,
                video_id TEXT NOT NULL,
                collected_at TEXT NOT NULL,
                age_hours REAL,
                views INTEGER NOT NULL DEFAULT 0,
                likes INTEGER NOT NULL DEFAULT 0,
                comments INTEGER NOT NULL DEFAULT 0,
                engaged_views INTEGER,
                average_view_duration_seconds REAL,
                average_percentage_viewed REAL,
                subscribers_gained INTEGER,
                shares INTEGER,
                stayed_to_watch_percentage REAL,
                source TEXT NOT NULL DEFAULT 'youtube_data_api',
                raw_json TEXT NOT NULL
            )
            """
        )

    status = analytics_status(settings)

    with sqlite3.connect(path) as connection:
        columns = {row[1] for row in connection.execute("PRAGMA table_info(metric_snapshots)")}
    assert status["schema_version"] == 2
    assert {"estimated_minutes_watched", "subscribers_lost", "subscribers_net", "impressions"} <= columns
