from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

from vv_knopka import youtube_uploader as yu


def _settings(tmp_path):
    return SimpleNamespace(runtime_dir=tmp_path / "runtime")


def test_extracts_upload_limit_reason_from_google_error_content():
    exc = RuntimeError("request failed")
    exc.content = json.dumps({
        "error": {
            "errors": [
                {
                    "domain": "youtube.video",
                    "reason": "uploadLimitExceeded",
                    "message": "The user has exceeded the number of videos they may upload.",
                }
            ]
        }
    }).encode("utf-8")

    assert yu._youtube_error_reasons(exc) == {"uploadLimitExceeded"}


def test_active_upload_limit_returns_future_cooldown(tmp_path):
    settings = _settings(tmp_path)
    retry = datetime.now(timezone.utc) + timedelta(hours=23)
    path = yu.upload_limit_state_path(settings)
    path.write_text(json.dumps({
        "reason": "uploadLimitExceeded",
        "slot": 7,
        "observed_at": datetime.now(timezone.utc).isoformat(),
        "retry_not_before": retry.isoformat(),
    }), encoding="utf-8")

    state = yu.active_upload_limit(settings)

    assert state is not None
    assert state["slot"] == 7


def test_upload_ready_stops_cleanly_at_daily_limit_after_prior_success(tmp_path, monkeypatch):
    settings = _settings(tmp_path)
    ready = settings.runtime_dir / "ready_for_review"
    ready.mkdir(parents=True)
    for slot in (1, 2, 3):
        (ready / f"slot-{slot:02d}-en-ai.upload.json").write_text("{}", encoding="utf-8")

    calls: list[int] = []

    def fake_upload_one(_settings, path, *, dry_run=False):
        slot = int(path.name.split("-", 2)[1])
        calls.append(slot)
        if slot == 2:
            raise yu.YouTubeUploadLimitReached(
                "daily limit",
                slot=slot,
                retry_not_before="2026-08-31T18:00:00+00:00",
            )
        return {"slot": slot, "video_id": f"video-{slot}"}

    monkeypatch.setattr(yu, "upload_one", fake_upload_one)

    results = yu.upload_ready(settings)

    assert calls == [1, 2]
    assert results[0]["video_id"] == "video-1"
    assert results[1]["deferred"] is True
    assert results[1]["slot"] == 2


def test_pending_ready_count_ignores_receipted_uploads(tmp_path):
    settings = _settings(tmp_path)
    ready = settings.runtime_dir / "ready_for_review"
    ready.mkdir(parents=True)
    first = ready / "slot-01-en-ai.upload.json"
    second = ready / "slot-02-en-animals.upload.json"
    first.write_text("{}", encoding="utf-8")
    second.write_text("{}", encoding="utf-8")
    first.with_suffix(".youtube.json").write_text("{}", encoding="utf-8")

    assert yu.pending_ready_count(settings) == 1
