import json

import vv_knopka.animal_audio_sources_v5 as source_v5
from vv_knopka.animal_audio_sources_v5 import (
    recover_failed_audit_sources,
    seed_cooled_history_sources,
)
from vv_knopka.settings import Settings


def _clip(tmp_path, provider, provider_id):
    path = tmp_path / f"{provider}-{provider_id}.mp4"
    path.write_bytes(b"video")
    return {
        "provider": provider,
        "provider_id": provider_id,
        "file": str(path),
        "source_url": f"https://example/{provider_id}",
        "license": "test",
        "commercial_use_allowed": True,
    }


def _settings(tmp_path, *, cooldown=1):
    return Settings(
        raw={
            "pilot": {"runtime_dir": "runtime", "total_shorts": 15},
            "long_run": {"cat_source_cooldown_episodes": cooldown},
            "animal": {"material_count": 6},
        },
        root=tmp_path,
    )


def _write_history(settings, slot, clips, language="en"):
    ready = settings.runtime_dir / "ready_for_review"
    ready.mkdir(parents=True, exist_ok=True)
    (ready / f"slot-{slot:02d}-{language}-animals.mp4").write_bytes(b"video")
    path = settings.runtime_dir / "slots" / f"{slot:02d}" / "sources.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({"clips": clips}), encoding="utf-8")


def test_recovers_fresh_stock_from_failed_audio_audit(tmp_path):
    slot_dir = tmp_path / "slot"
    slot_dir.mkdir()
    source_manifest = slot_dir / "sources.json"
    fresh = _clip(tmp_path, "pexels", "200")
    prior = _clip(tmp_path, "pexels", "100")
    (slot_dir / "animal_audio_sources.json").write_text(
        json.dumps({"selected_sources": [prior, fresh]}),
        encoding="utf-8",
    )

    recovered = recover_failed_audit_sources(
        slot_dir=slot_dir,
        source_manifest=source_manifest,
        prior={("pexels", "100")},
    )

    assert recovered == 1
    payload = json.loads(source_manifest.read_text(encoding="utf-8"))
    assert [item["provider_id"] for item in payload["clips"]] == ["200"]
    assert payload["recovered_from_failed_audio_audit"] == 1


def test_does_not_recover_missing_or_non_stock_files(tmp_path):
    slot_dir = tmp_path / "slot"
    slot_dir.mkdir()
    missing = {
        "provider": "pexels",
        "provider_id": "300",
        "file": str(tmp_path / "missing.mp4"),
    }
    youtube = _clip(tmp_path, "youtube", "abc")
    (slot_dir / "animal_audio_sources.json").write_text(
        json.dumps({"selected_sources": [missing, youtube]}),
        encoding="utf-8",
    )

    recovered = recover_failed_audit_sources(
        slot_dir=slot_dir,
        source_manifest=slot_dir / "sources.json",
        prior=set(),
    )

    assert recovered == 0


def test_cooled_history_seed_uses_old_local_stock_but_not_recent_window(tmp_path):
    settings = _settings(tmp_path, cooldown=1)
    old = _clip(tmp_path, "pexels", "old")
    recent = _clip(tmp_path, "pexels", "recent")
    _write_history(settings, 2, [old], language="ru")
    _write_history(settings, 4, [recent])

    source_manifest = settings.runtime_dir / "slots" / "16" / "sources.json"
    seeded = seed_cooled_history_sources(
        settings,
        slot=16,
        source_manifest=source_manifest,
        protected={("pexels", "recent")},
        max_sources=10,
    )

    assert [item["provider_id"] for item in seeded] == ["old"]
    assert seeded[0]["reused_from_slot"] == 2
    payload = json.loads(source_manifest.read_text(encoding="utf-8"))
    assert [item["provider_id"] for item in payload["clips"]] == ["old"]


def test_retry_after_failed_minimum_uses_fresh_then_cooled_local_stock(tmp_path, monkeypatch):
    settings = _settings(tmp_path, cooldown=1)
    old1 = _clip(tmp_path, "pexels", "old-1")
    old2 = _clip(tmp_path, "pixabay", "old-2")
    recent = _clip(tmp_path, "pexels", "recent")
    _write_history(settings, 2, [old1, old2], language="ru")
    _write_history(settings, 4, [recent])

    slot_dir = settings.runtime_dir / "slots" / "16"
    slot_dir.mkdir(parents=True, exist_ok=True)
    fresh = _clip(tmp_path, "pexels", "fresh")
    (slot_dir / "animal_audio_sources.json").write_text(
        json.dumps(
            {
                "required_minimum": 5,
                "selected": 1,
                "selected_sources": [fresh],
            }
        ),
        encoding="utf-8",
    )
    source_manifest = slot_dir / "sources.json"
    calls = []

    def fake_ensure(settings_arg, plan, *, slot, slot_dir, source_manifest, ledger):
        payload = json.loads(source_manifest.read_text(encoding="utf-8"))
        calls.append([item["provider_id"] for item in payload["clips"]])
        return source_manifest

    monkeypatch.setattr(source_v5, "_ensure_audio_animal_sources", fake_ensure)

    result = source_v5.ensure_audio_animal_sources(
        settings,
        {"search_terms": ["cat"]},
        slot=16,
        slot_dir=slot_dir,
        source_manifest=source_manifest,
        ledger=None,
    )

    assert result == source_manifest
    assert calls == [["fresh", "old-1", "old-2"]]
    assert "recent" not in calls[0]


def test_first_fresh_failure_falls_back_within_same_invocation(tmp_path, monkeypatch):
    settings = _settings(tmp_path, cooldown=1)
    old = _clip(tmp_path, "pexels", "old")
    recent = _clip(tmp_path, "pexels", "recent")
    _write_history(settings, 2, [old], language="ru")
    _write_history(settings, 4, [recent])

    slot_dir = settings.runtime_dir / "slots" / "16"
    slot_dir.mkdir(parents=True, exist_ok=True)
    source_manifest = slot_dir / "sources.json"
    fresh = _clip(tmp_path, "pexels", "fresh")
    calls = []

    def fake_ensure(settings_arg, plan, *, slot, slot_dir, source_manifest, ledger):
        calls.append(1)
        if len(calls) == 1:
            (slot_dir / "animal_audio_sources.json").write_text(
                json.dumps(
                    {
                        "required_minimum": 5,
                        "selected": 1,
                        "selected_sources": [fresh],
                    }
                ),
                encoding="utf-8",
            )
            raise RuntimeError("Vertical audible-source gate found only 1/5 usable cat clips")
        payload = json.loads(source_manifest.read_text(encoding="utf-8"))
        assert [item["provider_id"] for item in payload["clips"]] == ["fresh", "old"]
        return source_manifest

    monkeypatch.setattr(source_v5, "_ensure_audio_animal_sources", fake_ensure)

    result = source_v5.ensure_audio_animal_sources(
        settings,
        {"search_terms": ["cat"]},
        slot=16,
        slot_dir=slot_dir,
        source_manifest=source_manifest,
        ledger=None,
    )

    assert result == source_manifest
    assert len(calls) == 2
