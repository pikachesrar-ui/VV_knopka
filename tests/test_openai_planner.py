import json

from vv_knopka.openai_client import STOCK_FRIENDLY_AI_ANCHORS, _previous_visual_anchors
from vv_knopka.settings import Settings


def test_stock_friendly_anchor_list_avoids_rare_species():
    assert "cat" in STOCK_FRIENDLY_AI_ANCHORS
    assert "dog" in STOCK_FRIENDLY_AI_ANCHORS
    assert "penguin" in STOCK_FRIENDLY_AI_ANCHORS
    assert "superb lyrebird" not in STOCK_FRIENDLY_AI_ANCHORS


def test_previous_visual_anchors_are_read_from_earlier_slots(tmp_path):
    settings = Settings(
        raw={"pilot": {"openai_budget_usd": 10.0, "runtime_dir": "runtime"}},
        root=tmp_path,
    )
    slot1 = settings.runtime_dir / "slots" / "01"
    slot1.mkdir(parents=True)
    (slot1 / "plan.json").write_text(
        json.dumps({"visual_anchor": "octopus"}),
        encoding="utf-8",
    )

    assert _previous_visual_anchors(settings, 3) == ["octopus"]
