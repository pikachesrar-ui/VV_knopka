"""Check real FFmpeg output for sharp sounds in otherwise quiet cat footage."""

import math
import re
import shutil
import subprocess
import wave
from pathlib import Path

import pytest

from vv_knopka.animal_v3 import _cat_audio_filter


@pytest.mark.skipif(shutil.which("ffmpeg") is None, reason="FFmpeg required")
def test_cat_audio_caps_sudden_peaks_without_silencing_quiet_footage(tmp_path: Path) -> None:
    source = tmp_path / "source.wav"
    output = tmp_path / "leveled.wav"
    rate = 48000
    with wave.open(str(source), "wb") as audio:
        audio.setnchannels(1)
        audio.setsampwidth(2)
        audio.setframerate(rate)
        samples = bytearray()
        for index in range(rate * 2):
            time = index / rate
            quiet_tone = 0.065 * math.sin(2 * math.pi * 440 * time)
            sharp_sound = 0.88 * math.sin(2 * math.pi * 700 * time) if 0.8 < time < 0.84 else 0
            value = max(-1, min(1, quiet_tone + sharp_sound))
            samples.extend(int(value * 32767).to_bytes(2, "little", signed=True))
        audio.writeframes(samples)

    subprocess.run(
        ["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-i", str(source),
         "-af", _cat_audio_filter(lufs=-16, peak=-8, source_audio_volume=1), str(output)],
        check=True,
    )
    analysis = subprocess.run(
        ["ffmpeg", "-hide_banner", "-i", str(output), "-af", "volumedetect", "-f", "null", "-"],
        capture_output=True, text=True, check=True,
    )
    peak = float(re.search(r"max_volume: (-?[\d.]+) dB", analysis.stderr).group(1))
    assert peak <= -7.5
    with wave.open(str(output)) as audio:
        assert audio.getnframes() / audio.getframerate() == pytest.approx(2, abs=0.02)
        assert any(audio.readframes(4096))
