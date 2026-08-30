import json

import pytest

from vv_knopka.settings import Settings
from vv_knopka.source_history import audit_cat_source_reuse, prior_rendered_cat_identities


def _settings(tmp_path):
    return Settings(
        raw={
            "pilot": {"runtime_dir": "runtime"},
            "content": {"animal_slots": [2, 4, 6, 8, 10, 12, 14]},
        },
        root=tmp_path,
    )


def _write_sources(path, identities):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(
            {
                "clips": [
                    {"provider": provider, "provider_id": provider_id, "source_url": f"https://x/{provider_id}"}
                    for provider, provider_id in identities
                ]
            }
        ),
        encoding="utf-8",
    )


def test_source_reuse_gate_allows_one_repeat(tmp_path):
    settings = _settings(tmp_path)
    ready = settings.runtime_dir / "ready_for_review"
    ready.mkdir(parents=True)
    (ready / "slot-02-ru-animals.mp4").write_bytes(b"video")
    _write_sources(settings.runtime_dir / "slots" / "02" / "sources.json", [("pexels", "1"), ("pexels", "2")])
    current = settings.runtime_dir / "slots" / "04" / "sources.json"
    _write_sources(current, [("pexels", "1"), ("pexels", "3")])

    audit = audit_cat_source_reuse(settings, slot=4, source_manifest=current)
    payload = json.loads(audit.read_text(encoding="utf-8"))
    assert payload["passed"] is True
    assert len(payload["reused_sources"]) == 1


def test_source_reuse_gate_rejects_two_or_more_repeats(tmp_path):
    settings = _settings(tmp_path)
    ready = settings.runtime_dir / "ready_for_review"
    ready.mkdir(parents=True)
    (ready / "slot-02-ru-animals.mp4").write_bytes(b"video")
    _write_sources(settings.runtime_dir / "slots" / "02" / "sources.json", [("pexels", "1"), ("youtube", "abc")])
    current = settings.runtime_dir / "slots" / "04" / "sources.json"
    _write_sources(current, [("pexels", "1"), ("youtube", "abc"), ("pexels", "3")])

    with pytest.raises(RuntimeError, match="cat source reuse gate"):
        audit_cat_source_reuse(settings, slot=4, source_manifest=current)
    payload = json.loads((current.parent / "source_reuse_audit.json").read_text(encoding="utf-8"))
    assert payload["passed"] is False


def test_history_discovers_rendered_longrun_cat_slots(tmp_path):
    settings = _settings(tmp_path)
    ready = settings.runtime_dir / "ready_for_review"
    ready.mkdir(parents=True)
    (ready / "slot-16-en-animals.mp4").write_bytes(b"video")
    _write_sources(
        settings.runtime_dir / "slots" / "16" / "sources.json",
        [("pexels", "longrun-1")],
    )

    prior = prior_rendered_cat_identities(settings, before_slot=18)
    assert ("pexels", "longrun-1") in prior
