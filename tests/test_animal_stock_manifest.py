import json

import pytest

from vv_knopka.animal_compilation import write_stock_sources_manifest
from vv_knopka.settings import Settings


def _settings(tmp_path):
    return Settings(raw={"pilot": {"openai_budget_usd": 10.0}}, root=tmp_path)


def _material(provider: str, index: int):
    return {
        "provider": provider,
        "url": f"clip-{index}.mp4",
        "duration": 10 + index,
        "source_info": {
            "page_url": f"https://example.test/{provider}/{index}",
            "creator": f"creator-{index}",
            f"{provider}_id": index,
            "vision_confidence": 0.99,
            "vision_reason": "cat clearly visible",
        },
    }


def test_stock_manifest_preserves_provider_license_provenance_and_duration(tmp_path):
    settings = _settings(tmp_path)
    local_dir = tmp_path / "MoneyPrinterTurbo" / "storage" / "local_videos"
    local_dir.mkdir(parents=True)
    materials = []
    for index in range(1, 7):
        provider = "pexels" if index % 2 else "pixabay"
        (local_dir / f"clip-{index}.mp4").write_bytes(b"video")
        materials.append(_material(provider, index))

    output = tmp_path / "runtime" / "slots" / "02" / "sources.json"
    write_stock_sources_manifest(settings, materials, output, max_clips=6, min_unique_clips=5)
    data = json.loads(output.read_text(encoding="utf-8"))

    assert len(data["clips"]) == 6
    assert {clip["license"] for clip in data["clips"]} == {
        "Pexels License",
        "Pixabay Content License",
    }
    assert all(clip["commercial_use_allowed"] for clip in data["clips"])
    assert all(clip["source_url"] for clip in data["clips"])
    assert [clip["duration"] for clip in data["clips"]] == [11, 12, 13, 14, 15, 16]


def test_stock_manifest_refuses_too_few_unique_clips(tmp_path):
    settings = _settings(tmp_path)
    local_dir = tmp_path / "MoneyPrinterTurbo" / "storage" / "local_videos"
    local_dir.mkdir(parents=True)
    materials = []
    for index in range(1, 4):
        (local_dir / f"clip-{index}.mp4").write_bytes(b"video")
        materials.append(_material("pexels", index))

    output = tmp_path / "sources.json"
    with pytest.raises(RuntimeError, match="need at least 5"):
        write_stock_sources_manifest(settings, materials, output, min_unique_clips=5)
