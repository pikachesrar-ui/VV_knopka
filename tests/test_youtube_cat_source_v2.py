import json
from pathlib import Path

import pytest

import vv_knopka.youtube_cat_source_v2 as cc_v2


def test_youtube_cc_search_url_uses_creative_commons_filter():
    url = cc_v2.youtube_cc_search_url("funny cats")
    assert "search_query=funny+cats" in url
    assert f"sp={cc_v2._YOUTUBE_CC_FILTER_SP}" in url


def test_cc_filtered_search_accepts_missing_license_but_rejects_explicit_standard(monkeypatch):
    monkeypatch.setattr(
        cc_v2,
        "_filtered_search_targets",
        lambda query, scan_per_query: (
            [
                ("cc-empty", "https://www.youtube.com/watch?v=cc-empty"),
                ("std", "https://www.youtube.com/watch?v=std"),
                ("cc-direct", "https://www.youtube.com/watch?v=cc-direct"),
            ],
            cc_v2.youtube_cc_search_url(query),
        ),
    )

    metadata = {
        "cc-empty": {
            "video_id": "cc-empty",
            "title": "Funny cat one",
            "creator": "A",
            "source_url": "https://www.youtube.com/watch?v=cc-empty",
            "license": "",
            "duration": 20,
            "upload_date": "20250101",
            "view_count": 100,
        },
        "std": {
            "video_id": "std",
            "title": "Standard cat",
            "creator": "B",
            "source_url": "https://www.youtube.com/watch?v=std",
            "license": "Standard YouTube License",
            "duration": 20,
            "upload_date": "20250101",
            "view_count": 9999,
        },
        "cc-direct": {
            "video_id": "cc-direct",
            "title": "Funny cat two",
            "creator": "C",
            "source_url": "https://www.youtube.com/watch?v=cc-direct",
            "license": "Creative Commons Attribution license (reuse allowed)",
            "duration": 25,
            "upload_date": "20250101",
            "view_count": 200,
        },
    }
    monkeypatch.setattr(
        cc_v2,
        "fetch_youtube_metadata",
        lambda url: metadata[url.split("v=", 1)[1]],
    )

    found, warnings, diagnostics = cc_v2.search_cc_candidates(
        days=6000,
        scan_per_query=20,
        limit=10,
        queries=["funny cats"],
    )

    assert not warnings
    assert [item["video_id"] for item in found] == ["cc-direct", "cc-empty"]
    assert found[0]["rights_verification_method"] == "youtube_cc_search_filter+yt_dlp_license"
    assert found[1]["rights_verification_method"] == "youtube_cc_search_filter"
    assert diagnostics["queries"]["funny cats"]["filtered_results"] == 3
    assert diagnostics["queries"]["funny cats"]["accepted"] == 2


def test_cc_report_candidate_requires_filter_provenance():
    with pytest.raises(ValueError, match="youtube_cc_filtered_search"):
        cc_v2._report_candidate({"source": "something_else", "candidates": []}, 1)

    report = {
        "source": "youtube_cc_filtered_search",
        "filter_sp": cc_v2._YOUTUBE_CC_FILTER_SP,
        "candidates": [
            {
                "video_id": "abc",
                "url": "https://www.youtube.com/watch?v=abc",
                "rights_verified": True,
                "rights_status": "creative_commons_attribution_required",
                "cc_filter_sp": cc_v2._YOUTUBE_CC_FILTER_SP,
            }
        ],
    }
    assert cc_v2._report_candidate(report, 1)["video_id"] == "abc"


def test_cc_import_rejects_current_explicit_standard_license(tmp_path, monkeypatch):
    report_path = tmp_path / "report.json"
    report_path.write_text(
        json.dumps(
            {
                "source": "youtube_cc_filtered_search",
                "filter_sp": cc_v2._YOUTUBE_CC_FILTER_SP,
                "candidates": [
                    {
                        "video_id": "abc",
                        "url": "https://www.youtube.com/watch?v=abc",
                        "rights_verified": True,
                        "rights_status": "creative_commons_attribution_required",
                        "cc_filter_sp": cc_v2._YOUTUBE_CC_FILTER_SP,
                        "rights_verification_method": "youtube_cc_search_filter",
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(
        cc_v2,
        "fetch_youtube_metadata",
        lambda url: {
            "video_id": "abc",
            "source_url": url,
            "license": "Standard YouTube License",
        },
    )

    class DummySettings:
        runtime_dir = tmp_path / "runtime"

    with pytest.raises(ValueError, match="non-CC license"):
        cc_v2.import_cc_report_candidate(
            DummySettings(),
            slot=2,
            report_path=report_path,
            rank=1,
        )
