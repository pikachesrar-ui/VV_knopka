import json

from vv_knopka.animal_audio_sources_v3 import (
    _filtered_collector,
    _remove_prior_from_cached_materials,
    _remove_prior_from_manifest,
)


def test_remove_prior_from_manifest(tmp_path):
    path = tmp_path / "sources.json"
    path.write_text(
        json.dumps(
            {
                "clips": [
                    {"provider": "pexels", "provider_id": 1, "file": "a.mp4"},
                    {"provider": "pexels", "provider_id": 2, "file": "b.mp4"},
                ]
            }
        ),
        encoding="utf-8",
    )
    removed = _remove_prior_from_manifest(path, {("pexels", "1")})
    payload = json.loads(path.read_text(encoding="utf-8"))
    assert [str(item["provider_id"]) for item in payload["clips"]] == ["2"]
    assert len(removed) == 1
    assert removed[0]["provider_id"] == "1"


def test_remove_prior_from_cached_materials(tmp_path):
    path = tmp_path / "ai_materials.json"
    path.write_text(
        json.dumps(
            {
                "materials": [
                    {"provider": "pexels", "pexels_id": 10, "local_file": "a.mp4"},
                    {"provider": "pixabay", "pixabay_id": 20, "local_file": "b.mp4"},
                ]
            }
        ),
        encoding="utf-8",
    )
    removed = _remove_prior_from_cached_materials(path, {("pexels", "10")})
    payload = json.loads(path.read_text(encoding="utf-8"))
    assert len(payload["materials"]) == 1
    assert payload["materials"][0]["provider"] == "pixabay"
    assert payload["cross_episode_cache_filter_removed"] == 1
    assert len(removed) == 1


def test_filtered_collector_excludes_prior_ids():
    def original(**kwargs):
        return [{"id": 1}, {"id": 2}, {"id": 3}]

    collect = _filtered_collector(original, provider="pexels", prior={("pexels", "2")})
    assert [item["id"] for item in collect(query="cat")] == [1, 3]
