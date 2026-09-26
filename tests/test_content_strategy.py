import sqlite3

from vv_knopka.analytics_store import database_path, ingest_statistics_snapshot
from vv_knopka.content_strategy import ALL_CATEGORIES, build_strategy_report
from vv_knopka.settings import Settings


def _settings(tmp_path):
    return Settings(
        root=tmp_path,
        raw={
            "pilot": {"runtime_dir": "runtime"},
            "strategy": {
                "production_categories": ["cats", "animals", "other_facts"],
                "minimum_samples": 3,
                "prior_weight": 4.0,
                "exploration_share": 0.2,
            },
        },
    )


def _snapshot(video_id, category, views, likes, duration=30):
    return {
        "collected_at": "2026-01-02T00:00:00+00:00",
        "videos": [{
            "video_id": video_id,
            "slot": int(video_id.split("-")[-1]),
            "category": category,
            "published_at": "2026-01-01T00:00:00+00:00",
            "duration_seconds": duration,
            "views": views,
            "likes": likes,
            "comments": 0,
        }],
    }


def test_strategy_shrinks_small_samples_and_preserves_exploration(tmp_path) -> None:
    settings = _settings(tmp_path)
    ingest_statistics_snapshot(settings, _snapshot("video-1", "cats", 1000, 50))
    ingest_statistics_snapshot(settings, _snapshot("video-2", "animals", 100, 2))

    report = build_strategy_report(settings)

    assert set(report["categories"]) == set(ALL_CATEGORIES)
    assert set(report["allocations"]) == {"cats", "animals", "other_facts"}
    assert report["categories"]["cats"]["samples"] == 1
    assert report["categories"]["cats"]["enough_data"] is False
    assert report["allocations"]["other_facts"] > 0
    assert abs(sum(report["allocations"].values()) - 1.0) < 0.001
    assert report["categories"]["anime"]["production_enabled"] is False


def test_strategy_handles_existing_empty_database(tmp_path) -> None:
    settings = _settings(tmp_path)
    database_path(settings).touch()
    report = build_strategy_report(settings)
    assert report["checkpoint_videos"] == 0
    assert report["allocations"]


def test_strategy_recommends_features_only_after_minimum_sample(tmp_path) -> None:
    settings = _settings(tmp_path)
    for slot in range(1, 4):
        plan_dir = settings.runtime_dir / "slots" / f"{slot:02d}"
        plan_dir.mkdir(parents=True)
        plan_dir.joinpath("plan.json").write_text(
            '{"hook_style":"question","structure_variant":"answer_first"}', encoding="utf-8"
        )
        ingest_statistics_snapshot(settings, _snapshot(f"video-{slot}", "animals", 500 + slot, 20))

    report = build_strategy_report(settings)
    assert report["recommendations"]["hook_style"] == "question"
    assert report["recommendations"]["structure_variant"] == "answer_first"
    assert report["recommendations"]["duration_bucket"] == "25_35s"
