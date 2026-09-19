import json
from pathlib import Path

import pytest

from vv_knopka import long_run_conveyor as conveyor
from vv_knopka.longrun_recovery import (
    recovery_state,
    terminal_ai_failure,
    unblock_after_manual_replan,
    write_recovery,
)
from vv_knopka.settings import Settings


def _settings(tmp_path, *, max_extra=0.55):
    return Settings(
        root=tmp_path,
        raw={
            "pilot": {"total_shorts": 30, "runtime_dir": "runtime", "openai_budget_usd": 10.0},
            "long_run": {"enabled": True, "pipeline_cycle": ["ai_short", "animal_compilation"]},
            "animal": {"language_cycle": ["en"]},
            "recovery": {"enabled": True, "max_replans_per_slot": 1, "max_estimated_extra_usd": max_extra},
            "materials": {"min_unique_ai_materials": 3},
            "openai": {"max_estimated_cost_per_call_usd": 0.25, "fact_check_max_estimated_cost_usd": 0.05},
        },
    )


def _audit(settings, anchor, selected=2):
    directory = settings.runtime_dir / "slots" / "31"
    directory.mkdir(parents=True, exist_ok=True)
    (directory / "plan.json").write_text(json.dumps({"visual_anchor": anchor}), encoding="utf-8")
    (directory / "ai_materials.json").write_text(
        json.dumps({
            "visual_anchor": anchor,
            "selected": selected,
            "providers": {"pexels": {"vision_reviewed": 30}, "pixabay": {"vision_reviewed": 40}},
        }),
        encoding="utf-8",
    )


def _runner(monkeypatch):
    monkeypatch.setattr(conveyor._base, "_validate_conveyor_lock", lambda *a: None)

    class MPT:
        def __init__(self, settings):
            pass

        def close(self):
            pass

    monkeypatch.setattr(conveyor._base, "MPTProcessManager", MPT)


def test_exhausted_footage_replans_once_and_preserves_audit(monkeypatch, tmp_path):
    settings = _settings(tmp_path)
    _audit(settings, "octopus")
    _runner(monkeypatch)
    calls = []
    output = settings.runtime_dir / "ready_for_review" / "slot-31-en-ai.mp4"

    def render(settings, config_path, slot, mpt):
        calls.append("render")
        if len(calls) == 1:
            raise RuntimeError("child command failed (1): render-ai 31")
        output.parent.mkdir(parents=True)
        output.write_bytes(b"video")
        return output

    def plan(config, *args):
        calls.append(args)
        _audit(settings, "cat", selected=8)

    monkeypatch.setattr(conveyor._base, "_render_one", render)
    monkeypatch.setattr(conveyor, "_run_current_cli", plan)

    results = conveyor.run_longrun_batch(settings, config_path=tmp_path / "config" / "pilot.toml", count=1)

    assert results == [output]
    assert calls == ["render", ("plan", "31", "--avoid-anchor", "octopus"), "render"]
    archive = settings.runtime_dir / "slots" / "31" / "auto-recovery" / "original-plan"
    assert json.loads((archive / "plan.json").read_text())["visual_anchor"] == "octopus"
    assert recovery_state(settings, 31)["status"] == "recovered"


def test_second_exhausted_subject_blocks_slot_and_next_cycle_can_continue(monkeypatch, tmp_path):
    settings = _settings(tmp_path)
    _audit(settings, "octopus")
    _runner(monkeypatch)

    def render(settings, config_path, slot, mpt):
        raise RuntimeError("child command failed (1): render-ai 31")

    monkeypatch.setattr(conveyor._base, "_render_one", render)
    monkeypatch.setattr(conveyor, "_run_current_cli", lambda config, *args: _audit(settings, "cat"))

    with pytest.raises(RuntimeError, match="render-ai 31"):
        conveyor.run_longrun_batch(settings, config_path=tmp_path / "config" / "pilot.toml", count=1)

    state = recovery_state(settings, 31)
    assert state["status"] == "blocked"
    assert state["replans_used"] == 1
    assert state["failed_anchor"] == "cat"
    assert [(s.slot, s.pipeline) for s in conveyor.pending_longrun_slots(settings, count=1)] == [
        (32, "animal_compilation")
    ]


def test_transient_failure_does_not_replan_or_skip(monkeypatch, tmp_path):
    settings = _settings(tmp_path)
    _runner(monkeypatch)
    monkeypatch.setattr(
        conveyor._base, "_render_one", lambda *args: (_ for _ in ()).throw(RuntimeError("HTTP 503"))
    )
    monkeypatch.setattr(
        conveyor, "_run_current_cli", lambda *args: pytest.fail("a network failure cannot replan")
    )

    with pytest.raises(RuntimeError, match="HTTP 503"):
        conveyor.run_longrun_batch(settings, config_path=tmp_path / "config" / "pilot.toml", count=1)
    assert not recovery_state(settings, 31)
    assert conveyor.pending_longrun_slots(settings, count=1)[0].slot == 31


def test_recovery_budget_guard_blocks_before_paid_retry(monkeypatch, tmp_path):
    settings = _settings(tmp_path, max_extra=0.10)
    _audit(settings, "octopus")
    _runner(monkeypatch)
    monkeypatch.setattr(
        conveyor._base, "_render_one",
        lambda *args: (_ for _ in ()).throw(RuntimeError("child command failed (1): render-ai 31")),
    )
    monkeypatch.setattr(conveyor, "_run_current_cli", lambda *args: pytest.fail("no paid retry allowed"))

    with pytest.raises(RuntimeError, match="budget guard"):
        conveyor.run_longrun_batch(settings, config_path=tmp_path / "config" / "pilot.toml", count=1)
    assert recovery_state(settings, 31)["status"] == "blocked"


def test_stale_factcheck_is_not_mistaken_for_a_fresh_rejection(tmp_path):
    settings = _settings(tmp_path)
    directory = settings.runtime_dir / "slots" / "31"
    directory.mkdir(parents=True)
    (directory / "plan-candidate.json").write_text('{"visual_anchor":"octopus"}')
    (directory / "fact-check.json").write_text('{"visual_anchor":"octopus","passed":false}')
    assert terminal_ai_failure(settings, 31, RuntimeError("child command failed (1): plan 31"), not_before=10**11) is None


def test_fresh_factcheck_failure_tries_another_subject(monkeypatch, tmp_path):
    settings = _settings(tmp_path)
    _runner(monkeypatch)
    slot_dir = settings.runtime_dir / "slots" / "31"
    output = settings.runtime_dir / "ready_for_review" / "slot-31-en-ai.mp4"
    calls = []

    def render(*args):
        calls.append("render")
        if len(calls) == 1:
            slot_dir.mkdir(parents=True)
            (slot_dir / "plan-candidate.json").write_text('{"visual_anchor":"octopus"}')
            (slot_dir / "fact-check.json").write_text('{"visual_anchor":"octopus","passed":false}')
            raise RuntimeError("child command failed (1): plan 31")
        output.parent.mkdir(parents=True)
        output.write_bytes(b"video")
        return output

    def plan(config, *args):
        calls.append(args)
        slot_dir.joinpath("plan.json").write_text('{"visual_anchor":"cat"}')

    monkeypatch.setattr(conveyor._base, "_render_one", render)
    monkeypatch.setattr(conveyor, "_run_current_cli", plan)
    assert conveyor.run_longrun_batch(settings, config_path=tmp_path / "config" / "pilot.toml", count=1) == [output]
    assert calls == ["render", ("plan", "31", "--avoid-anchor", "octopus"), "render"]


def test_temporary_replacement_failure_retries_same_replacement(monkeypatch, tmp_path):
    settings = _settings(tmp_path)
    _runner(monkeypatch)
    _audit(settings, "octopus")
    output = settings.runtime_dir / "ready_for_review" / "slot-31-en-ai.mp4"
    plans = []

    def plan(config, *args):
        plans.append(args)
        if len(plans) == 1:
            raise RuntimeError("HTTP 503")
        _audit(settings, "cat", selected=8)

    def render(*args):
        if len(plans) < 2:
            raise RuntimeError("child command failed (1): render-ai 31")
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_bytes(b"video")
        return output

    monkeypatch.setattr(conveyor._base, "_render_one", render)
    monkeypatch.setattr(conveyor, "_run_current_cli", plan)
    config = tmp_path / "config" / "pilot.toml"
    with pytest.raises(RuntimeError, match="HTTP 503"):
        conveyor.run_longrun_batch(settings, config_path=config, count=1)
    assert recovery_state(settings, 31)["status"] == "retry_replacement"
    assert conveyor.pending_longrun_slots(settings, count=1)[0].slot == 31
    assert conveyor.run_longrun_batch(settings, config_path=config, count=1) == [output]
    assert plans == [("plan", "31", "--avoid-anchor", "octopus")] * 2
    assert recovery_state(settings, 31)["status"] == "recovered"


def test_duration_shortage_is_terminal_only_after_both_providers_reviewed(tmp_path):
    settings = _settings(tmp_path)
    settings.raw["video"] = {"clip_seconds": 6}
    local = tmp_path / "MoneyPrinterTurbo" / "storage" / "local_videos"
    local.mkdir(parents=True)
    materials = []
    for i in range(3):
        filename = f"clip-{i}.mp4"
        (local / filename).write_bytes(b"video")
        materials.append({"local_file": filename, "provider": "pexels", "vision_confidence": 0.9, "duration": 5})
    directory = settings.runtime_dir / "slots" / "31"
    directory.mkdir(parents=True)
    (directory / "plan.json").write_text('{"visual_anchor":"octopus"}')
    audit = {"visual_anchor": "octopus", "selected": 3, "materials": materials,
             "providers": {"pexels": {"vision_reviewed": 30}, "pixabay": {"vision_reviewed": 40}}}
    (directory / "ai_materials.json").write_text(json.dumps(audit))
    failure = RuntimeError("child command failed (1): render-ai 31")
    reason = terminal_ai_failure(settings, 31, failure)
    assert reason is not None and "reusable footage" in reason[0]
    audit["providers"]["pixabay"]["vision_reviewed"] = 0
    (directory / "ai_materials.json").write_text(json.dumps(audit))
    assert terminal_ai_failure(settings, 31, failure) is None


def test_manual_unblock_requires_passed_new_anchor(tmp_path):
    settings = _settings(tmp_path)
    write_recovery(settings, 31, {
        "status": "blocked", "reason": "no footage", "failed_anchor": "octopus", "replans_used": 1
    })
    _audit(settings, "cat", selected=8)
    with pytest.raises(RuntimeError, match="successful fact-check"):
        unblock_after_manual_replan(settings, 31)
    (settings.runtime_dir / "slots" / "31" / "fact-check.json").write_text(
        '{"visual_anchor":"cat","passed":true}', encoding="utf-8"
    )
    unblock_after_manual_replan(settings, 31)
    assert recovery_state(settings, 31)["status"] == "manual_resume"
