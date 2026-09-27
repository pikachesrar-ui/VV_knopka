from vv_knopka.mpt import MoneyPrinterTurboClient, normalize_transition
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


def test_none_transition_maps_to_mpt_null():
    assert normalize_transition("none") is None
    assert normalize_transition("off") is None
    assert normalize_transition(None) is None
    assert normalize_transition("FadeIn") == "FadeIn"


def test_curated_materials_use_random_concat_and_short_style(monkeypatch, tmp_path):
    monkeypatch.setattr("vv_knopka.mpt.httpx.Client", _Client)
    settings = Settings(
        raw={
            "pilot": {"openai_budget_usd": 10.0},
            "video": {
                "aspect": "9:16",
                "clip_seconds": 6,
                "visual_transition": "none",
                "bgm_volume": 0.08,
                "subtitle_enabled": True,
                "subtitle_font_size": 52,
                "subtitle_position": "custom",
                "subtitle_custom_position": 74.0,
                "subtitle_stroke_width": 2.2,
            },
            "audio": {
                "edge_voice_ru": "ru-RU-SvetlanaNeural-Female",
                "edge_voice_en": "en-US-AriaNeural-Female",
            },
        },
        root=tmp_path,
    )
    client = MoneyPrinterTurboClient(settings)
    monkeypatch.setattr(client, "_ensure_windows_cyrillic_font", lambda: "VVKnopka-Cyrillic.ttf")
    monkeypatch.setattr(client, "_prepare_vertical_materials", lambda materials: materials)
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

    payload = _Client.last_payload
    assert payload["video_source"] == "local"
    assert payload["video_concat_mode"] == "random"
    assert payload["video_transition_mode"] is None
    assert payload["match_materials_to_script"] is False
    assert payload["font_name"] == "VVKnopka-Cyrillic.ttf"
    assert payload["font_size"] == 52
    assert payload["subtitle_position"] == "custom"
    assert payload["custom_position"] == 74.0
    assert payload["stroke_width"] == 2.2
