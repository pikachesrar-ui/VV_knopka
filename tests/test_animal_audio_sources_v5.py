import json

from vv_knopka.animal_audio_sources_v5 import recover_failed_audit_sources


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
