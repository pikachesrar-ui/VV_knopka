from vv_knopka.animal_audio_sources_v4 import _deep_pexels_collector, _expanded_queries


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


def test_deep_pexels_keeps_paging_after_prior_popular_result():
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
    assert ("cat", 2) in client.pages


def test_expanded_queries_adds_diversity_without_duplicates():
    queries = _expanded_queries(["cat", "cat playing"])
    assert queries[0:2] == ["cat", "cat playing"]
    assert queries.count("cat") == 1
    assert "kitten" in queries
    assert "house cat" in queries
