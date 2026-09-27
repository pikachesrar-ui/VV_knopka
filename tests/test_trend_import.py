import json
from datetime import datetime, timezone

import pytest

from vv_knopka.trend_discovery import PETS_TOPIC_ID, youtube_search_params
from vv_knopka.trend_import import merge_source_manifest, select_candidate, write_attribution_report


def test_youtube_cat_discovery_is_recent_cc_short_pets_search():
    params = youtube_search_params(
        api_key="test-key",
        query="cat|kitten",
        days=30,
        limit=30,
        now=datetime(2026, 8, 29, tzinfo=timezone.utc),
    )
    assert params["type"] == "video"
    assert params["q"] == "cat|kitten"
    assert params["topicId"] == PETS_TOPIC_ID
    assert params["videoLicense"] == "creativeCommon"
    assert params["videoDuration"] == "short"
    assert params["order"] == "viewCount"
    assert params["publishedAfter"].startswith("2026-07-30")


def test_select_candidate_uses_one_based_rank():
    report = {"candidates": [{"video_id": "a"}, {"video_id": "b"}]}
    assert select_candidate(report, 2)["video_id"] == "b"
    with pytest.raises(ValueError):
        select_candidate(report, 0)
    with pytest.raises(ValueError):
        select_candidate(report, 3)


def test_controlled_import_is_prepended_and_attribution_is_recorded(tmp_path):
    source_manifest = tmp_path / "slot" / "sources.json"
    source_manifest.parent.mkdir(parents=True)
    source_manifest.write_text(
        json.dumps(
            {
                "clips": [
                    {
                        "file": "pexels.mp4",
                        "source_url": "https://pexels.example/1",
                        "license": "Pexels License",
                        "commercial_use_allowed": True,
                        "creator": "Stock Author",
                        "provider": "pexels",
                        "provider_id": 1,
                    }
                ]
            }
        ),
        encoding="utf-8",
    )
    imported = {
        "file": "ugc.mp4",
        "source_url": "https://youtube.example/watch?v=cat",
        "source_title": "Funny cat",
        "license": "Creative Commons Attribution (CC BY)",
        "commercial_use_allowed": True,
        "creator": "Cat Creator",
        "provider": "youtube",
        "provider_id": "cat",
        "attribution_required": True,
        "attribution_text": '"Funny cat" by Cat Creator — source — CC BY',
        "human_approved": True,
        "ugc": True,
    }

    merge_source_manifest(source_manifest, imported)
    merged = json.loads(source_manifest.read_text(encoding="utf-8"))
    assert merged["clips"][0]["provider"] == "youtube"
    assert merged["clips"][1]["provider"] == "pexels"
    assert merged["human_review_required"] is True

    attribution = write_attribution_report(source_manifest.parent, source_manifest)
    data = json.loads(attribution.read_text(encoding="utf-8"))
    assert data["required"] is True
    assert len(data["entries"]) == 1
    assert data["entries"][0]["creator"] == "Cat Creator"
