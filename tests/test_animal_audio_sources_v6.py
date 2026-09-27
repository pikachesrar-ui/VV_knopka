import json

import vv_knopka.animal_audio_sources_v6 as source_v6
from vv_knopka.animal_audio_sources_v6 import (
    _fresh_only_finish_factory,
    _retry_safe_seed_factory,
    _strict_remote_audio_probe_factory,
)


def test_remote_probe_rejects_effectively_silent_stream(monkeypatch):
    monkeypatch.setattr(source_v6._base, "has_audio_stream", lambda *args, **kwargs: True)
    monkeypatch.setattr(source_v6._base, "mean_audio_volume_db", lambda *args, **kwargs: -80.0)
    probe = _strict_remote_audio_probe_factory(minimum_mean_db=-55.0, probe_seconds=6.0)

    assert probe({"link": "https://cdn/test.mp4"}) is False


def test_remote_probe_accepts_measured_audible_stream(monkeypatch):
    monkeypatch.setattr(source_v6._base, "has_audio_stream", lambda *args, **kwargs: True)
    monkeypatch.setattr(source_v6._base, "mean_audio_volume_db", lambda *args, **kwargs: -30.0)
    probe = _strict_remote_audio_probe_factory(minimum_mean_db=-55.0, probe_seconds=6.0)

    assert probe({"link": "https://cdn/test.mp4"}) is True


def test_remote_probe_keeps_unmeasurable_cdn_as_unknown(monkeypatch):
    monkeypatch.setattr(source_v6._base, "has_audio_stream", lambda *args, **kwargs: None)
    monkeypatch.setattr(source_v6._base, "mean_audio_volume_db", lambda *args, **kwargs: None)
    probe = _strict_remote_audio_probe_factory(minimum_mean_db=-55.0, probe_seconds=6.0)

    assert probe({"link": "https://cdn/test.mp4"}) is None


def test_finish_excludes_remote_cooled_history_and_caps_unknowns():
    finish = _fresh_only_finish_factory(unknown_candidate_cap=2)
    fresh_confirmed = [{"id": 1}, {"id": 2}]
    fresh_unknown = [{"id": 3}, {"id": 4}, {"id": 5}, {"id": 6}]
    cooled_confirmed = [{"id": 100}]
    cooled_unknown = [{"id": 101}]

    result = finish(
        fresh_confirmed,
        fresh_unknown,
        cooled_confirmed,
        cooled_unknown,
        max_candidates=6,
    )

    assert [item["id"] for item in result] == [1, 2, 3, 4]


def test_retry_does_not_stack_another_cooled_fallback(tmp_path):
    manifest = tmp_path / "sources.json"
    manifest.write_text(
        json.dumps(
            {
                "clips": [
                    {
                        "provider": "pexels",
                        "provider_id": "old",
                        "cooled_down_reuse": True,
                        "reused_from_slot": 4,
                    }
                ]
            }
        ),
        encoding="utf-8",
    )
    calls = []

    def original_seed(*args, **kwargs):
        calls.append((args, kwargs))
        return [{"provider_id": "should-not-happen"}]

    seed = _retry_safe_seed_factory(original_seed)
    result = seed(
        object(),
        slot=16,
        source_manifest=manifest,
        protected=set(),
        max_sources=2,
    )

    assert result == []
    assert calls == []
