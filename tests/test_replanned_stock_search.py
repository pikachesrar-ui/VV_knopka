import json

from vv_knopka import pexels_curator
from vv_knopka.settings import Settings


def test_new_plan_searches_pexels_after_old_anchor_exhausted(monkeypatch, tmp_path):
    """An octopus audit cannot skip Pexels for a replacement cat plan."""
    monkeypatch.setenv("PEXELS_API_KEY", "test-key")
    monkeypatch.setenv("MPT_LOCAL_VIDEOS_DIR", str(tmp_path / "local_videos"))
    settings = Settings(
        root=tmp_path,
        raw={
            "pilot": {"runtime_dir": "runtime"},
            "video": {"clip_seconds": 6, "target_max_seconds": 30},
            "materials": {"ai_material_count": 1, "vision_max_candidates": 30},
        },
    )
    slot_dir = tmp_path / "runtime" / "slots" / "31"
    slot_dir.mkdir(parents=True)
    (slot_dir / "ai_materials.json").write_text(
        json.dumps(
            {
                "visual_anchor": "octopus",
                "providers": {
                    "pexels": {"vision_reviewed": 30},
                    "pixabay": {"vision_reviewed": 40},
                },
                "materials": [{"provider": "pexels", "local_file": "old-octopus.mp4"}],
            }
        ),
        encoding="utf-8",
    )

    class OfflineClient:
        def __init__(self, *args, **kwargs):
            pass

        def __enter__(self):
            return self

        def __exit__(self, *args):
            pass

    searched = []

    def collect(**kwargs):
        searched.append(kwargs["anchor"])
        return [{"id": 123, "provider": "pexels"}]

    def review(**kwargs):
        return kwargs["candidates"], [{"id": 123, "accepted": True}]

    def material(**kwargs):
        return {"provider": "pexels", "url": "new-cat.mp4", "duration": 20}, {
            "provider": "pexels",
            "local_file": "new-cat.mp4",
            "vision_confidence": 0.95,
        }

    monkeypatch.setattr(pexels_curator.httpx, "Client", OfflineClient)
    monkeypatch.setattr(pexels_curator, "_collect_pexels_candidates", collect)
    monkeypatch.setattr(pexels_curator, "_review_until_enough", review)
    monkeypatch.setattr(pexels_curator, "_material_from_candidate", material)

    result = pexels_curator.prepare_pexels_materials(
        settings,
        {"visual_anchor": "cat", "search_terms": ["cat grooming fur"]},
        slot=31,
        slot_dir=slot_dir,
        ledger=object(),
    )

    assert searched == ["cat"]
    assert result[0]["url"] == "new-cat.mp4"
    audit = json.loads((slot_dir / "ai_materials.json").read_text(encoding="utf-8"))
    assert audit["visual_anchor"] == "cat"
    assert audit["providers"]["pexels"]["reused_from_previous_audit"] is False
