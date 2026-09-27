import json

from vv_knopka.cat_theme import (
    apply_theme_to_plan,
    build_theme_only_plan,
    build_theme_payload,
    prepare_theme_source_refresh,
    rank_themes,
    stamp_source_manifest_theme,
)


def _candidate(rank, title, subreddit, score):
    return {
        "trend_rank": rank,
        "title": title,
        "subreddit": subreddit,
        "community_score": score,
        "url": f"https://reddit.example/{rank}",
    }


def test_repeated_mischief_signal_beats_single_unrelated_reference():
    candidates = [
        _candidate(1, "Trying to watch TV", "CatsAreAssholes", 0.90),
        _candidate(2, "Not a spa... Disrespectful!", "CatsAreAssholes", 0.75),
        _candidate(3, "Every. Single. Day!", "CatsAreAssholes", 0.70),
        _candidate(4, "Cute kitten sleeping", "cats", 1.20),
    ]
    ranked = rank_themes(candidates)
    assert ranked
    assert ranked[0]["theme_id"] == "cat_mischief"
    assert ranked[0]["evidence_count"] == 3


def test_theme_payload_is_localized_and_stock_search_terms_stay_cat_anchored():
    report = {
        "discovered_at": "2026-08-30T00:00:00+00:00",
        "candidates": [
            _candidate(1, "Hired this cleaning lady but she's doing a terrible job", "Catswithjobs", 1.0),
            _candidate(2, "Supermodel", "Catswithjobs", 0.8),
        ],
    }
    payload = build_theme_payload(report, slot=2, language="ru")
    assert payload["theme_id"] == "important_jobs"
    assert payload["episode_title"] == "Важные кошачьи дела"
    assert payload["theme_signature"]
    assert len(payload["search_terms"]) >= 6
    assert all("cat" in term.casefold() for term in payload["search_terms"])
    assert payload["rights_policy"]["reddit_media_auto_import"] is False


def test_theme_can_build_and_override_an_animal_plan_without_writer_call():
    report = {
        "candidates": [
            _candidate(1, "My cat won't stop bringing in nuts??", "WhatsWrongWithYourCat", 1.0),
            _candidate(2, "Self-cleaning mode is triggered", "WhatsWrongWithYourCat", 0.7),
        ]
    }
    theme = build_theme_payload(report, slot=4, language="en")
    base = build_theme_only_plan(theme)
    effective = apply_theme_to_plan(
        {
            **base,
            "title": "Old random cats",
            "search_terms": ["cat generic"],
        },
        theme,
    )
    assert effective["title"] == "Cat Logic"
    assert effective["visual_anchor"] == "cat"
    assert effective["search_terms"] == theme["search_terms"]
    assert effective["trend_theme"]["theme_id"] == "weird_cat_logic"
    assert "Reddit" in effective["editorial_value"]


def test_changed_theme_archives_old_sources_then_same_signature_reuses_cache(tmp_path):
    slot_dir = tmp_path / "runtime" / "slots" / "02"
    slot_dir.mkdir(parents=True)
    source_manifest = slot_dir / "sources.json"
    source_manifest.write_text(
        json.dumps({"clips": [{"provider": "pexels", "provider_id": 123, "file": "old.mp4"}]}),
        encoding="utf-8",
    )
    (slot_dir / "ai_materials.json").write_text(json.dumps({"materials": [{"url": "old.mp4"}]}), encoding="utf-8")

    report = {"candidates": [_candidate(1, "Trying to watch TV", "CatsAreAssholes", 1.0)]}
    theme = build_theme_payload(report, slot=2, language="ru")

    assert prepare_theme_source_refresh(source_manifest, slot_dir, theme) is True
    refreshed = json.loads(source_manifest.read_text(encoding="utf-8"))
    assert refreshed["clips"] == []
    assert refreshed["trend_theme_id"] == theme["theme_id"]
    assert list(slot_dir.glob("sources-before-theme-*.json"))
    assert not (slot_dir / "ai_materials.json").exists()
    assert list(slot_dir.glob("ai_materials-before-theme-*.json"))

    source_manifest.write_text(
        json.dumps({"clips": [{"provider": "pexels", "provider_id": 456, "file": "new.mp4"}]}),
        encoding="utf-8",
    )
    stamp_source_manifest_theme(source_manifest, theme)
    assert prepare_theme_source_refresh(source_manifest, slot_dir, theme) is False
    reused = json.loads(source_manifest.read_text(encoding="utf-8"))
    assert reused["clips"][0]["provider_id"] == 456
