import wave
import json

from vv_knopka.animal_compilation import _generate_meow_timeline, _generate_playful_bgm
from vv_knopka import animal_highlights as highlights
from vv_knopka.animal_highlights import candidate_starts
from vv_knopka.animal_episode import build_episode_metadata
from vv_knopka.editorial import PROFILE, build_cat_edit
from vv_knopka.settings import Settings


def _peak_pcm16(path):
    with wave.open(str(path), "rb") as handle:
        assert handle.getnchannels() == 2
        assert handle.getframerate() == 48000
        raw = handle.readframes(handle.getnframes())
    values = memoryview(raw).cast("h")
    return max(abs(int(value)) for value in values)


def test_candidate_starts_cover_beginning_middle_and_end():
    starts = candidate_starts(20.0, 5.0, 4)
    assert starts == [0.0, 5.0, 10.0, 15.0]


def test_short_clip_has_single_zero_start():
    assert candidate_starts(4.0, 5.0, 4) == [0.0]


def test_procedural_cat_audio_is_not_silent(tmp_path):
    bgm = _generate_playful_bgm(tmp_path / "bgm.wav", 0.5)
    meows = _generate_meow_timeline(tmp_path / "meow.wav", 1.0, [0.3])

    assert _peak_pcm16(bgm) > 100
    assert _peak_pcm16(meows) > 100


def test_opening_cat_title_comes_from_reviewed_frames_without_planner_title(monkeypatch, tmp_path):
    settings = Settings(root=tmp_path, raw={
        "pilot": {"total_shorts": 15, "openai_budget_usd": 10},
        "content": {"animal_slots": [2, 4, 6, 8, 10, 12, 14]},
        "long_run": {"enabled": True, "pipeline_cycle": ["animal_compilation", "ai_short"]},
        "editorial": {"enabled": True, "start_slot": 21, "cat_min_clips": 3,
                      "cat_max_clips": 4, "cat_min_score": 6},
        "materials": {"vision_model": "gpt-5.6-luna"},
    })
    manifest = tmp_path / "sources.json"
    manifest.write_text(json.dumps({"clips": [
        {"file": str(tmp_path / f"cat-{i}.mp4"), "duration": 7} for i in range(1, 4)
    ]}))
    monkeypatch.setenv("OPENAI_API_KEY", "test-placeholder")
    monkeypatch.setattr(highlights, "_contact_sheet", lambda *args: args[-1].write_bytes(b"image"))
    monkeypatch.setattr(highlights, "_data_url", lambda *args: "data:image/jpeg;base64,test")
    sent = {}

    class Response:
        status_code = 200

        def raise_for_status(self):
            pass

        def json(self):
            parsed = {"order": [2, 1, 3], "selections": [
                {"clip_index": i, "candidate": "A", "score": 9 - i / 10,
                 "description": "Cat grooms fur" if i == 2 else "Cat looks around",
                 "caption": "Cat grooms fur" if i == 2 else "Cat looks around"}
                for i in range(1, 4)
            ]}
            return {"output": [{"content": [{"text": json.dumps(parsed)}]}], "usage": {}}

    class Client:
        def __init__(self, **kwargs):
            pass

        def __enter__(self):
            return self

        def __exit__(self, *args):
            pass

        def post(self, url, *, headers, json):
            sent.update(json)
            return Response()

    class Ledger:
        def ensure_room(self, estimate):
            pass

        def record(self, **kwargs):
            pass

    monkeypatch.setattr(highlights.httpx, "Client", Client)
    path = highlights.select_highlights(settings, Ledger(), source_manifest=manifest,
        slot_dir=tmp_path, language="en",
        editorial_plan={"editorial_profile": PROFILE, "title": "Cat stretches paw", "hook": "Stretches paw"},
        clip_seconds=5)
    prompt = sent["input"][0]["content"][0]["text"]
    assert "Cat stretches paw" not in prompt
    assert "Stretches paw" not in prompt
    edit = build_cat_edit(settings, path)
    output = build_episode_metadata(settings, slot=22, language="en", plan={"title": "Cat stretches paw"},
        highlight_manifest=edit, output=tmp_path / "episode.json")
    # Stable score sorting makes clip 1 the strongest in this fixture.
    assert json.loads(output.read_text())["youtube_title"] == "Cats: Cat looks around"
