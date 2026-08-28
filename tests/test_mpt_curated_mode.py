from vv_knopka.mpt import MoneyPrinterTurboClient
from vv_knopka.settings import Settings


class _Response:
    def raise_for_status(self):
        return None

    def json(self):
        return {"data": {"task_id": "task-1"}}


class _Client:
    last_payload = None

    def __init__(self, *args, **kwargs):
        pass

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def post(self, url, headers=None, json=None):
        _Client.last_payload = json
        return _Response()


def test_curated_materials_use_random_concat_for_non_overlapping_segments(monkeypatch, tmp_path):
    monkeypatch.setattr("vv_knopka.mpt.httpx.Client", _Client)
    settings = Settings(
        raw={
            "pilot": {"openai_budget_usd": 10.0},
            "video": {
                "aspect": "9:16",
                "clip_seconds": 6,
                "visual_transition": "FadeIn",
                "bgm_volume": 0.08,
                "subtitle_enabled": True,
            },
            "audio": {
                "edge_voice_ru": "ru-RU-SvetlanaNeural-Female",
                "edge_voice_en": "en-US-AriaNeural-Female",
            },
        },
        root=tmp_path,
    )
    client = MoneyPrinterTurboClient(settings)
    plan = {
        "title": "Octopus",
        "script": "Test",
        "search_terms": ["octopus underwater"],
    }

    client.create_ai_video(
        plan,
        "ru",
        materials=[{"provider": "pexels", "url": "clip.mp4", "duration": 20}],
    )

    assert _Client.last_payload["video_source"] == "local"
    assert _Client.last_payload["video_concat_mode"] == "random"
    assert _Client.last_payload["match_materials_to_script"] is False
