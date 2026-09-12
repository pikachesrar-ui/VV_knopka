import json
from pathlib import Path

import pytest

import vv_knopka.youtube_cat_source_v3 as youtube_v3


class DummySettings:
    def __init__(self, root: Path):
        self.root = root
        self.runtime_dir = root / "runtime"
        self.raw = {"animal": {}}


def test_api_search_dedupes_and_marks_official_rights(monkeypatch):
    def fake_discover(*, api_key, query, days, limit):
        assert api_key == "secret"
        assert days == 6000
        assert limit == 20
        return [
            {
                "provider": "youtube",
                "video_id": "cat1",
                "url": "https://www.youtube.com/watch?v=cat1",
                "title": "Funny cat",
                "published_at": "2026-08-01T00:00:00Z",
                "view_count": 1000,
                "views_per_day": 100.0,
                "license": "YouTube Creative Commons Attribution",
                "rights_status": "creative_commons_attribution_required",
            }
        ]

    monkeypatch.setattr(youtube_v3, "discover_youtube_cc_cats", fake_discover)
    found, warnings, diagnostics = youtube_v3.search_cc_candidates_api(
        api_key="secret",
        days=6000,
        scan_per_query=20,
        limit=10,
        queries=["cat", "kitten"],
    )

    assert not warnings
    assert len(found) == 1
    assert found[0]["video_id"] == "cat1"
    assert found[0]["rights_verified"] is True
    assert found[0]["api_status_license"] == "creativeCommon"
    assert found[0]["rights_verification_method"] == "youtube_data_api_status_license"
    assert diagnostics["candidate_count"] == 1


def test_api_report_requires_official_status_evidence():
    report = {
        "source": "youtube_data_api_cc_search",
        "candidates": [
            {
                "rights_verified": True,
                "rights_status": "creative_commons_attribution_required",
                "api_status_license": "standard",
            }
        ],
    }
    with pytest.raises(ValueError, match="lost its official creativeCommon"):
        youtube_v3._api_report_candidate(report, 1)


def test_write_api_report_records_official_backend(tmp_path):
    output = youtube_v3.write_api_report(
        tmp_path / "cc.json",
        candidates=[],
        warnings=[],
        diagnostics={"backend": "youtube_data_api", "candidate_count": 0},
    )
    raw = json.loads(output.read_text(encoding="utf-8"))
    assert raw["source"] == "youtube_data_api_cc_search"
    assert raw["backend"] == "youtube_data_api"
    assert "videoLicense=creativeCommon" in raw["rights_evidence"]


def test_api_import_requires_key_before_download(tmp_path):
    settings = DummySettings(tmp_path)
    with pytest.raises(ValueError, match="YOUTUBE_API_KEY is required"):
        youtube_v3.import_api_report_candidate(
            settings,
            slot=2,
            report_path=tmp_path / "does-not-matter.json",
            rank=1,
            api_key="",
        )
