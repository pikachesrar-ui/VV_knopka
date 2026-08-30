import vv_knopka.animal_audio_sources_v4 as source_v4
from vv_knopka.animal_audio_sources_v4 import (
    _deep_pexels_collector,
    _deep_pixabay_collector,
    _expanded_queries,
)


class _Response:
    def __init__(self, payload):
        self._payload = payload

    def raise_for_status(self):
        return None

    def json(self):
        return self._payload


class _Client:
    def __init__(self):
        self.pages = []

    def get(self, url, *, headers=None, params=None):
        page = int((params or {}).get("page") or 1)
        query = str((params or {}).get("query") or "")
        self.pages.append((query, page))
        if page == 1:
            videos = [_video(100)]
        elif page == 2:
            videos = [_video(200)]
        else:
            videos = []
        return _Response({"videos": videos})


class _PixabayClient:
    def get(self, url, *, headers=None, params=None):
        return _Response({"hits": [_pixabay_video(300)]})


def _video(video_id):
    return {
        "id": video_id,
        "duration": 12,
        "image": f"https://img/{video_id}.jpg",
        "url": f"https://www.pexels.com/video/cat-{video_id}/",
        "user": {"name": "Creator", "url": "https://www.pexels.com/@creator"},
        "video_files": [
            {
                "file_type": "video/mp4",
                "link": f"https://cdn/{video_id}.mp4",
                "width": 720,
                "height": 1280,
            }
        ],
    }


def _pixabay_video(video_id):
    return {
        "id": video_id,
        "duration": 10,
        "pageURL": f"https://pixabay.com/videos/id-{video_id}/",
        "user": "Creator",
        "user_id": 42,
        "tags": "cat, kitten, pet",
        "videos": {
            "medium": {
                "url": f"https://cdn.pixabay/{video_id}.mp4",
                "width": 720,
                "height": 1280,
                "thumbnail": f"https://img.pixabay/{video_id}.jpg",
                "size": 12345,
            }
        },
    }


def test_deep_pexels_keeps_paging_after_prior_popular_result(monkeypatch):
    monkeypatch.setattr(source_v4._base, "has_audio_stream", lambda *args, **kwargs: True)
    collector = _deep_pexels_collector(prior={("pexels", "100")}, pages_per_query=3)
    client = _Client()

    found = collector(
        client=client,
        api_key="key",
        queries=["cat"],
        per_page=40,
        max_candidates=1,
        clip_seconds=5,
        anchor="cat",
        aspect_tolerance=0.08,
    )

    assert [item["id"] for item in found] == [200]
    assert found[0]["search_page"] == 2
    assert found[0]["remote_audio_probe"] == "confirmed"
    assert ("cat", 2) in client.pages


def test_remote_audio_prefilter_skips_silent_candidate_before_cap(monkeypatch):
    def probe(url, **kwargs):
        return False if "/100.mp4" in str(url) else True

    monkeypatch.setattr(source_v4._base, "has_audio_stream", probe)
    collector = _deep_pexels_collector(prior=set(), pages_per_query=3)
    client = _Client()

    found = collector(
        client=client,
        api_key="key",
        queries=["cat"],
        per_page=40,
        max_candidates=1,
        clip_seconds=5,
        anchor="cat",
        aspect_tolerance=0.08,
    )

    assert [item["id"] for item in found] == [200]
    assert ("cat", 2) in client.pages


def test_deep_pixabay_uses_pixabay_file_and_tag_helpers(monkeypatch):
    monkeypatch.setattr(source_v4._base, "has_audio_stream", lambda *args, **kwargs: True)
    collector = _deep_pixabay_collector(prior=set(), pages_per_query=1)

    found = collector(
        client=_PixabayClient(),
        api_key="key",
        queries=["cat"],
        per_page=100,
        max_candidates=1,
        clip_seconds=5,
        anchor="cat",
    )

    assert [item["id"] for item in found] == [300]
    assert found[0]["file_info"]["width"] == 720
    assert found[0]["file_info"]["height"] == 1280
    assert found[0]["metadata_mentions_anchor"] is True
    assert found[0]["remote_audio_probe"] == "confirmed"
    assert found[0]["search_order"] == "popular"


def test_expanded_queries_adds_diversity_without_duplicates():
    queries = _expanded_queries(["cat", "cat playing"])
    assert queries[0:2] == ["cat", "cat playing"]
    assert queries.count("cat") == 1
    assert "kitten" in queries
    assert "house cat" in queries
    assert "cat eating" in queries
    assert "domestic cat" in queries
