from __future__ import annotations

import hashlib
import json
import math
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .analytics_store import database_path
from .settings import Settings


ALL_CATEGORIES = ("cats", "animals", "anime", "movies", "theories", "other_facts")


def _enabled(settings: Settings, key: str, default: list[str]) -> list[str]:
    raw = settings.raw.get("strategy", {}).get(key, default)
    result = [str(value).strip().lower() for value in raw if str(value).strip().lower() in ALL_CATEGORIES]
    return list(dict.fromkeys(result)) or list(default)


def _video_score(row: sqlite3.Row) -> float:
    views = max(float(row["views"] or 0), 0.0)
    likes = max(float(row["likes"] or 0), 0.0)
    comments = max(float(row["comments"] or 0), 0.0)
    apv = row["average_percentage_viewed"]
    stayed = row["stayed_to_watch_percentage"]
    subscribers = max(float(row["subscribers_net"] or 0), 0.0)
    score = math.log1p(views)
    score += min(likes / max(views, 1.0), 0.20) * 8.0
    score += min(comments / max(views, 1.0), 0.10) * 6.0
    score += min(subscribers / max(views, 1.0), 0.05) * 12.0
    if apv is not None:
        score += max(min(float(apv), 200.0), 0.0) / 100.0
    if stayed is not None:
        score += max(min(float(stayed), 100.0), 0.0) / 100.0
    return score


def build_strategy_report(settings: Settings) -> dict[str, Any]:
    """Build a local, conservative category report from checkpoint data only."""
    production = _enabled(settings, "production_categories", ["cats", "animals", "other_facts"])
    minimum = max(int(settings.raw.get("strategy", {}).get("minimum_samples", 3)), 1)
    prior_weight = max(float(settings.raw.get("strategy", {}).get("prior_weight", 4.0)), 0.0)
    exploration = min(max(float(settings.raw.get("strategy", {}).get("exploration_share", 0.20)), 0.0), 0.50)
    path = database_path(settings)
    rows: list[sqlite3.Row] = []
    if path.exists():
        try:
            connection = sqlite3.connect(path)
            connection.row_factory = sqlite3.Row
            rows = connection.execute(
                """
                SELECT v.video_id, v.slot, v.category, v.duration_seconds,
                       c.checkpoint_hours, s.views, s.likes,
                       s.comments, s.average_percentage_viewed,
                       s.stayed_to_watch_percentage, s.subscribers_net
                FROM metric_checkpoints c
                JOIN videos v ON v.video_id = c.video_id
                JOIN metric_snapshots s ON s.id = c.snapshot_id
                WHERE c.checkpoint_hours = (
                    SELECT MAX(c2.checkpoint_hours) FROM metric_checkpoints c2
                    WHERE c2.video_id = c.video_id
                )
                """
            ).fetchall()
            connection.close()
        except sqlite3.OperationalError:
            rows = []

    by_category: dict[str, list[float]] = {name: [] for name in ALL_CATEGORIES}
    for row in rows:
        category = str(row["category"] or "unknown").lower()
        if category in by_category:
            by_category[category].append(_video_score(row))
    all_scores = [value for values in by_category.values() for value in values]
    global_mean = sum(all_scores) / len(all_scores) if all_scores else 1.0

    categories: dict[str, dict[str, Any]] = {}
    raw_weights: dict[str, float] = {}
    for category in ALL_CATEGORIES:
        values = by_category[category]
        observed = sum(values) / len(values) if values else global_mean
        posterior = (sum(values) + prior_weight * global_mean) / (len(values) + prior_weight) if prior_weight else observed
        eligible = category in production
        categories[category] = {
            "samples": len(values),
            "observed_score": round(observed, 4),
            "shrunk_score": round(posterior, 4),
            "enough_data": len(values) >= minimum,
            "production_enabled": eligible,
        }
        if eligible:
            raw_weights[category] = max(posterior, 0.05)

    total = sum(raw_weights.values()) or 1.0
    allocations = {key: value / total for key, value in raw_weights.items()}
    uniform = 1.0 / max(len(allocations), 1)
    allocations = {
        key: round((1.0 - exploration) * value + exploration * uniform, 4)
        for key, value in allocations.items()
    }
    feature_values: dict[str, dict[str, list[float]]] = {
        "hook_style": {},
        "structure_variant": {},
        "duration_bucket": {},
    }
    for row in rows:
        slot = int(row["slot"] or 0)
        plan: dict[str, Any] = {}
        if slot > 0:
            plan_path = settings.runtime_dir / "slots" / f"{slot:02d}" / "plan.json"
            try:
                plan = json.loads(plan_path.read_text(encoding="utf-8"))
            except (FileNotFoundError, OSError, json.JSONDecodeError):
                plan = {}
        duration = float(row["duration_seconds"] or 0)
        if duration <= 0:
            duration_bucket = "unknown"
        elif duration < 25:
            duration_bucket = "under_25s"
        elif duration <= 35:
            duration_bucket = "25_35s"
        else:
            duration_bucket = "over_35s"
        features = {
            "hook_style": str(plan.get("hook_style") or "unknown"),
            "structure_variant": str(plan.get("structure_variant") or "unknown"),
            "duration_bucket": duration_bucket,
        }
        score = _video_score(row)
        for feature, value in features.items():
            feature_values[feature].setdefault(value, []).append(score)

    feature_report: dict[str, dict[str, Any]] = {}
    recommendations: dict[str, str | None] = {}
    for feature, groups in feature_values.items():
        summaries: dict[str, Any] = {}
        best_value: str | None = None
        best_score = -1.0
        for value, values in groups.items():
            posterior = (sum(values) + prior_weight * global_mean) / (len(values) + prior_weight) if prior_weight else sum(values) / len(values)
            summaries[value] = {
                "samples": len(values),
                "shrunk_score": round(posterior, 4),
                "enough_data": len(values) >= minimum,
            }
            if len(values) >= minimum and posterior > best_score and value != "unknown":
                best_value, best_score = value, posterior
        feature_report[feature] = summaries
        recommendations[feature] = best_value
    result = {
        "schema_version": 1,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "checkpoint_videos": len(rows),
        "minimum_samples": minimum,
        "exploration_share": exploration,
        "categories": categories,
        "allocations": allocations,
        "features": feature_report,
        "recommendations": recommendations,
        "note": "Small samples are shrunk toward the channel mean; exploration is always preserved.",
    }
    output = settings.runtime_dir / "analytics" / "strategy-report.json"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    result["output_file"] = str(output)
    return result


def recommend_category(
    settings: Settings,
    *,
    slot: int,
    pipeline: str,
    report: dict[str, Any] | None = None,
) -> str:
    if pipeline == "animal_compilation":
        return "cats"
    report = report or build_strategy_report(settings)
    allowed = [name for name in report["allocations"] if name != "cats"]
    if not allowed:
        return "animals"
    total = sum(float(report["allocations"][name]) for name in allowed) or 1.0
    point = int(hashlib.sha256(f"vv-category:{slot}".encode()).hexdigest()[:8], 16) / 0xFFFFFFFF
    cursor = 0.0
    for name in allowed:
        cursor += float(report["allocations"][name]) / total
        if point <= cursor:
            return name
    return allowed[-1]


def planner_feedback_guidance(report: dict[str, Any]) -> str:
    recommendations = report.get("recommendations") or {}
    parts: list[str] = []
    labels = {
        "hook_style": "hook style",
        "structure_variant": "structure",
        "duration_bucket": "duration bucket",
    }
    for key, label in labels.items():
        value = recommendations.get(key)
        if value:
            parts.append(f"historically supported {label}: {value}")
    if not parts:
        return "There is not enough checkpoint evidence to prefer a hook, structure, or duration; keep exploring."
    return "Use these channel signals as soft preferences, not rigid rules: " + "; ".join(parts) + "."
