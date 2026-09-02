import json

import pytest

from vv_knopka.settings import Settings
from vv_knopka.source_history import (
    audit_cat_source_reuse,
    blocked_cat_source_identities,
    blocked_rendered_cat_slots,
    prior_rendered_cat_identities,
)


def _settings(tmp_path):
    return Settings(
        raw={
            "pilot": {"runtime_dir": "runtime", "total_shorts": 15},
            "content": {"animal_slots": [2, 4, 6, 8, 10, 12, 14]},
            "long_run": {
                "cat_source_cooldown_episodes": 5,
                "cat_cooled_reuse_max_sources": 2,
                "cat_cooled_reuse_max_per_history_episode": 1,
            },
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


def _rendered_cat(settings, slot, identity, language="en"):
    ready = settings.runtime_dir / "ready_for_review"
    ready.mkdir(parents=True, exist_ok=True)
    (ready / f"slot-{slot:02d}-{language}-animals.mp4").write_bytes(b"video")
    _write_sources(settings.runtime_dir / "slots" / f"{slot:02d}" / "sources.json", [identity])


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
    assert payload["history_policy"] == "pilot_all_history"


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
    _rendered_cat(settings, 16, ("pexels", "longrun-1"))

    prior = prior_rendered_cat_identities(settings, before_slot=18)
    assert ("pexels", "longrun-1") in prior


def test_longrun_blocks_only_recent_cat_episode_window(tmp_path):
    settings = _settings(tmp_path)
    for slot in [2, 4, 6, 8, 10, 12, 14]:
        _rendered_cat(settings, slot, ("pexels", f"source-{slot}"), language="ru" if slot == 2 else "en")

    # Slot 16 / cat #008 protects only the five immediately preceding cat
    # episodes (#003-#007 => slots 6,8,10,12,14). Sources from #001/#002
    # are old enough to rotate back in only under the bounded cooled fallback.
    assert blocked_rendered_cat_slots(settings, before_slot=16) == [6, 8, 10, 12, 14]
    blocked = blocked_cat_source_identities(settings, before_slot=16)
    assert ("pexels", "source-2") not in blocked
    assert ("pexels", "source-4") not in blocked
    assert ("pexels", "source-6") in blocked
    assert ("pexels", "source-14") in blocked


def test_longrun_audit_allows_two_cooled_reuses_from_different_episodes(tmp_path):
    settings = _settings(tmp_path)
    for slot in [2, 4, 6, 8, 10, 12, 14]:
        _rendered_cat(settings, slot, ("pexels", f"source-{slot}"), language="ru" if slot == 2 else "en")

    current = settings.runtime_dir / "slots" / "16" / "sources.json"
    _write_sources(
        current,
        [("pexels", "source-2"), ("pexels", "source-4"), ("pexels", "brand-new")],
    )

    audit = audit_cat_source_reuse(settings, slot=16, source_manifest=current)
    payload = json.loads(audit.read_text(encoding="utf-8"))
    assert payload["passed"] is True
    assert payload["history_policy"] == "rolling_cat_episode_cooldown"
    assert payload["cooldown_cat_episodes"] == 5
    assert payload["reused_sources"] == []
    assert len(payload["reused_cooled_down_sources"]) == 2
    assert payload["cooled_reuse_by_history_slot"] == {"2": 1, "4": 1}
    assert payload["cooled_reuse_passed"] is True


def test_longrun_audit_rejects_two_cooled_sources_from_same_old_episode(tmp_path):
    settings = _settings(tmp_path)
    ready = settings.runtime_dir / "ready_for_review"
    ready.mkdir(parents=True, exist_ok=True)
    for slot in [2, 4, 6, 8, 10, 12, 14]:
        (ready / f"slot-{slot:02d}-en-animals.mp4").write_bytes(b"video")

    _write_sources(
        settings.runtime_dir / "slots" / "02" / "sources.json",
        [("pexels", "old-a"), ("pexels", "old-b")],
    )
    for slot in [4, 6, 8, 10, 12, 14]:
        _write_sources(
            settings.runtime_dir / "slots" / f"{slot:02d}" / "sources.json",
            [("pexels", f"source-{slot}")],
        )

    current = settings.runtime_dir / "slots" / "16" / "sources.json"
    _write_sources(current, [("pexels", "old-a"), ("pexels", "old-b"), ("pexels", "fresh")])

    with pytest.raises(RuntimeError, match="cat cooled-source reuse gate"):
        audit_cat_source_reuse(settings, slot=16, source_manifest=current)

    payload = json.loads((current.parent / "source_reuse_audit.json").read_text(encoding="utf-8"))
    assert payload["cooled_reuse_by_history_slot"] == {"2": 2}
    assert payload["cooled_reuse_passed"] is False
    assert payload["passed"] is False


def test_longrun_audit_rejects_more_than_two_cooled_sources_total(tmp_path):
    settings = _settings(tmp_path)
    for slot in [2, 4, 6, 8, 10, 12, 14]:
        _rendered_cat(settings, slot, ("pexels", f"source-{slot}"), language="ru" if slot == 2 else "en")
    # Make three old episodes eligible by shrinking the protected window only for this assertion.
    settings.raw["long_run"]["cat_source_cooldown_episodes"] = 4

    current = settings.runtime_dir / "slots" / "16" / "sources.json"
    _write_sources(
        current,
        [
            ("pexels", "source-2"),
            ("pexels", "source-4"),
            ("pexels", "source-6"),
            ("pexels", "fresh"),
        ],
    )

    with pytest.raises(RuntimeError, match="cat cooled-source reuse gate"):
        audit_cat_source_reuse(settings, slot=16, source_manifest=current)

    payload = json.loads((current.parent / "source_reuse_audit.json").read_text(encoding="utf-8"))
    assert len(payload["reused_cooled_down_sources"]) == 3
    assert payload["cooled_reuse_passed"] is False
    assert payload["passed"] is False
