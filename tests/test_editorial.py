import json
from pathlib import Path

import pytest

from vv_knopka.animal_episode import build_episode_metadata
from vv_knopka.editorial import PROFILE, build_cat_edit, enabled_for_slot, opening_materials
from vv_knopka.manifest import Slot
from vv_knopka.publication_metadata import build_upload_metadata
from vv_knopka.settings import Settings


def settings(tmp_path):
    return Settings(raw={
        "pilot": {"total_shorts": 15, "openai_budget_usd": 10},
        "editorial": {"enabled": True, "start_slot": 21},
        "content": {"animal_slots": [2, 4, 6, 8, 10, 12, 14]},
        "long_run": {"enabled": True, "pipeline_cycle": ["animal_compilation", "ai_short"]},
        "youtube": {"enabled": True, "auto_publish": True},
    }, root=tmp_path)


def highlights(tmp_path, scores):
    path = tmp_path / "highlights.json"
    path.write_text(json.dumps({"version": 3, "clip_seconds": 5,
        "order": list(range(1, len(scores) + 1)),
        "selections": [{"clip_index": i, "score": score, "start": 0,
                        "caption": f"Cat plays with toy {i}", "description": f"Visible action {i}."}
                       for i, score in enumerate(scores, 1)]}), encoding="utf-8")
    return path


def test_profile_never_changes_pilot_or_existing_checkpoint(tmp_path):
    cfg = settings(tmp_path)
    assert not any(enabled_for_slot(cfg, n) for n in range(1, 21))
    assert enabled_for_slot(cfg, 21)
    cfg.raw["editorial"]["start_slot"] = 1
    assert not enabled_for_slot(cfg, 15)


def test_cat_edit_drops_weak_clips_and_keeps_strong_ending(tmp_path):
    source = highlights(tmp_path, [7, 3, 9, 6, 8, 4])
    original = source.read_bytes()
    output = build_cat_edit(settings(tmp_path), source)
    edit = json.loads(output.read_text())
    assert edit["order"] == [3, 1, 4, 5]
    assert edit["excluded_clip_indices"] == [2, 6]
    assert source.read_bytes() == original
    assert build_cat_edit(settings(tmp_path), source).read_bytes() == output.read_bytes()


def test_cat_edit_does_not_fill_quota_with_weak_clips(tmp_path):
    source = highlights(tmp_path, [9, 8, 4, 3, 2, 1])
    with pytest.raises(RuntimeError, match="2 strong cat clips"):
        build_cat_edit(settings(tmp_path), source)
    assert not (tmp_path / "cat-edit.json").exists()


def test_duplicate_or_nonfinite_reviews_fail_closed(tmp_path):
    source = highlights(tmp_path, [9, float("nan"), 8])
    with pytest.raises(ValueError, match="score"):
        build_cat_edit(settings(tmp_path), source)
    source = highlights(tmp_path, [9, 8, 7])
    data = json.loads(source.read_text())
    data["selections"][1]["clip_index"] = 1
    source.write_text(json.dumps(data))
    with pytest.raises(ValueError, match="Duplicate"):
        build_cat_edit(settings(tmp_path), source)


def test_metadata_uses_actual_opening_and_preserves_attribution(tmp_path):
    cfg = settings(tmp_path)
    source = highlights(tmp_path, [7, 9, 8])
    edit = build_cat_edit(cfg, source)
    episode = build_episode_metadata(cfg, slot=22, language="en", plan={"title": "Cats"},
        highlight_manifest=edit, output=tmp_path / "episode.json")
    assert json.loads(episode.read_text())["transition_cards"] == []
    (tmp_path / "sources.json").write_text(json.dumps({"clips": [
        {"attribution_required": True, "attribution_text": "Creator — CC BY"}]}))
    metadata = build_upload_metadata(cfg, slot=Slot(22, "animal_compilation", "en"),
        output=tmp_path / "video.mp4", slot_dir=tmp_path)
    assert metadata["youtube_title"] == "Cats: Cat plays with toy 2 #shorts"
    assert "Creator — CC BY" in metadata["youtube_description"]
    assert "Visible action 2" in metadata["youtube_description"]
    assert metadata["editorial_profile"] == PROFILE


def test_opening_rank_uses_evidence_metadata_not_search_query(tmp_path):
    materials = [{"url": "idle.mp4", "source_info": {"query": "cat playing toy"}},
                 {"url": "action.mp4", "source_info": {"page_url": "https://example.test/cat-playing-toy"}}]
    plan = {"editorial_profile": PROFILE, "visual_anchor": "cat", "search_terms": ["cat playing toy"]}
    assert opening_materials(plan, materials)[0]["url"] == "action.mp4"
    assert materials[0]["url"] == "idle.mp4"
    assert opening_materials({}, materials) is materials


def test_existing_video_blocks_plan_before_any_api_call(tmp_path, monkeypatch):
    from vv_knopka import cli
    cfg = settings(tmp_path)
    target = cfg.runtime_dir / "ready_for_review" / "slot-22-en-animals.mp4"
    target.parent.mkdir(parents=True)
    target.write_bytes(b"existing frozen output")
    monkeypatch.setattr(cli, "load_settings", lambda _: cfg)
    monkeypatch.setattr("sys.argv", ["vv", "plan", "22"])
    with pytest.raises(SystemExit, match="already has a rendered"):
        cli.main()
    assert target.read_bytes() == b"existing frozen output"


def test_ai_new_profile_keeps_curated_order_and_legacy_behavior(tmp_path, monkeypatch):
    from vv_knopka.mpt import MoneyPrinterTurboClient
    from test_mpt_curated_mode import _Client
    cfg = settings(tmp_path)
    cfg.raw["video"] = {"aspect": "9:16", "clip_seconds": 6, "bgm_volume": .08, "subtitle_enabled": True}
    cfg.raw["audio"] = {"edge_voice_en": "voice", "edge_voice_ru": "voice"}
    monkeypatch.setattr("vv_knopka.mpt.httpx.Client", _Client)
    client = MoneyPrinterTurboClient(cfg)
    monkeypatch.setattr(client, "_prepare_vertical_materials", lambda m: m)
    plan = {"editorial_profile": PROFILE, "title": "Cats", "script": "Why do cats play?", "search_terms": ["cat playing"]}
    materials = [{"url": "idle.mp4"}, {"url": "play.mp4", "source_info": {"tags": "cat playing"}}]
    client.create_ai_video(plan, "en", materials=materials)
    assert _Client.last_payload["video_concat_mode"] == "sequential"
    assert _Client.last_payload["video_clip_duration"] == 4
    assert _Client.last_payload["video_materials"][0]["url"] == "play.mp4"
    assert _Client.last_payload["match_materials_to_script"] is False


def test_planner_records_usage_even_when_hook_validation_fails(tmp_path, monkeypatch):
    from vv_knopka.openai_client import OpenAIPlanner
    from vv_knopka.budget import BudgetLedger, BudgetExceeded
    cfg = settings(tmp_path)
    cfg.raw["openai"] = {"writer_model": "gpt-5.6-terra", "max_estimated_cost_per_call_usd": .25,
                          "terra_input_per_million_usd": 2, "terra_output_per_million_usd": 12}
    monkeypatch.setenv("OPENAI_API_KEY", "test-placeholder")
    calls = []
    class Response:
        def raise_for_status(self): pass
        def json(self):
            return {"output_text": json.dumps({"hook": "Why do cats play?", "script": "Generic setup."}),
                    "usage": {"input_tokens": 1000, "output_tokens": 100}}
    class Client:
        def __init__(self, **kwargs): pass
        def __enter__(self): return self
        def __exit__(self, *args): pass
        def post(self, *args, **kwargs):
            calls.append(kwargs["json"])
            return Response()
    monkeypatch.setattr("vv_knopka.openai_client.httpx.Client", Client)
    ledger = BudgetLedger(cfg)
    planner = OpenAIPlanner(cfg, ledger)
    with pytest.raises(RuntimeError, match="exact short hook"):
        planner.create_plan(slot=21, pipeline="ai_short", language="en")
    assert ledger.spent_usd() > 0
    assert calls[0]["max_output_tokens"] == 1800
    cfg.raw["pilot"]["openai_budget_usd"] = ledger.spent_usd()
    with pytest.raises(BudgetExceeded):
        planner.create_plan(slot=21, pipeline="ai_short", language="en")
    assert len(calls) == 1
