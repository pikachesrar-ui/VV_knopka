import json

from vv_knopka.openai_client import recent_visual_anchors
from vv_knopka.settings import Settings


def _settings(tmp_path):
    return Settings(
        raw={
            "pilot": {"runtime_dir": "runtime"},
            "long_run": {"fact_subject_cooldown": 3},
        },
        root=tmp_path,
    )


def _plan(settings, slot, anchor):
    path = settings.runtime_dir / "slots" / f"{slot:02d}" / "plan.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({"visual_anchor": anchor}), encoding="utf-8")


def test_recent_visual_anchors_uses_newest_distinct_ai_subjects(tmp_path):
    settings = _settings(tmp_path)
    _plan(settings, 1, "octopus")
    _plan(settings, 3, "ant")
    _plan(settings, 5, "butterfly")
    _plan(settings, 7, "owl")

    assert recent_visual_anchors(settings, 9) == ["owl", "butterfly", "ant"]


def test_recent_visual_anchors_deduplicates_repeated_subject(tmp_path):
    settings = _settings(tmp_path)
    _plan(settings, 3, "ant")
    _plan(settings, 5, "owl")
    _plan(settings, 7, "owl")

    assert recent_visual_anchors(settings, 9) == ["owl", "ant"]
