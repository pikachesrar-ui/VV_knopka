import wave

from vv_knopka.animal_compilation import _generate_meow_timeline, _generate_playful_bgm
from vv_knopka.animal_highlights import candidate_starts


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
