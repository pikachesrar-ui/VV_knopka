import json

import pytest

from vv_knopka.material_fallback import CuratedMaterialFallbackError, load_duration_sufficient_materials
from vv_knopka.settings import Settings


def _settings(tmp_path):
    return Settings(
        raw={
            "video": {"clip_seconds": 6},
            "materials": {
                "min_unique_ai_materials": 3,
                "min_reusable_stock_seconds": 36,
                "max_segments_per_source": 4,
                "vision_min_confidence": 0.72,
            },
            "pilot": {"openai_budget_usd": 10.0, "runtime_dir": "runtime"},
        },
        root=tmp_path,
    )


def _write_audit(settings, slot_dir, items):
    local_dir = settings.root / "MoneyPrinterTurbo" / "storage" / "local_videos"
    local_dir.mkdir(parents=True)
    materials = []
    for index, duration in enumerate(items, start=1):
        filename = f"clip-{index}.mp4"
        (local_dir / filename).write_bytes(b"video")
        materials.append(
            {
                "provider": "pexels" if index < 3 else "pixabay",
                "local_file": filename,
                "duration": duration,
                "vision_confidence": 0.95,
                "visual_anchor": "octopus",
            }
        )
    slot_dir.mkdir(parents=True)
    (slot_dir / "ai_materials.json").write_text(
        json.dumps({"visual_anchor": "octopus", "materials": materials}),
        encoding="utf-8",
    )


def test_accepts_three_long_vision_approved_sources(tmp_path):
    settings = _settings(tmp_path)
    slot_dir = tmp_path / "runtime" / "slots" / "01"
    _write_audit(settings, slot_dir, [20, 15, 10])

    materials, stats = load_duration_sufficient_materials(
        settings,
        slot_dir=slot_dir,
        expected_anchor="octopus",
    )

    assert len(materials) == 3
    assert stats["unique_sources"] == 3
    assert stats["reusable_seconds"] == 45.0


def test_rejects_too_few_unique_sources_even_if_long(tmp_path):
    settings = _settings(tmp_path)
    slot_dir = tmp_path / "runtime" / "slots" / "01"
    _write_audit(settings, slot_dir, [60, 60])

    with pytest.raises(CuratedMaterialFallbackError, match="need at least 3"):
        load_duration_sufficient_materials(
            settings,
            slot_dir=slot_dir,
            expected_anchor="octopus",
        )


def test_rejects_cache_for_old_visual_anchor_after_replan(tmp_path):
    settings = _settings(tmp_path)
    slot_dir = tmp_path / "runtime" / "slots" / "03"
    _write_audit(settings, slot_dir, [20, 20, 20])

    with pytest.raises(CuratedMaterialFallbackError, match="does not match current plan anchor"):
        load_duration_sufficient_materials(
            settings,
            slot_dir=slot_dir,
            expected_anchor="penguin",
        )
