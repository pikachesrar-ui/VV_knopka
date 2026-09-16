import json
from pathlib import Path

from vv_knopka import video_qa as vq
from vv_knopka.settings import Settings


def _settings(tmp_path: Path) -> Settings:
    return Settings(
        raw={
            "pilot": {"runtime_dir": "runtime", "openai_budget_usd": 10.0, "auto_publish": False},
            "youtube": {"enabled": True, "auto_publish": True},
            "qa": {
                "enabled": True,
                "mode": "shadow",
                "recommended_min_seconds": 25,
                "recommended_max_seconds": 35,
                "hard_min_seconds": 10,
                "hard_max_seconds": 60,
            },
            "editorial": {"ai_clip_seconds": 4},
            "video": {
                "subtitle_enabled": True,
                "subtitle_custom_position": 74,
                "subtitle_font_size": 52,
            },
            "music": {"ai_volume": 0.10, "ai_ducking": True},
            "animal": {"clip_seconds": 5},
        },
        root=tmp_path,
    )


def test_parsers_extract_ffmpeg_measurements():
    text = (
        "[blackdetect] black_start:0 black_end:0.4 black_duration:0.4\n"
        "[Parsed_cropdetect] crop=1080:1800:0:60\n"
        "I: -16.2 LUFS\nPeak: -1.1 dBFS\n"
    )
    assert vq._parse_black_intervals(text) == [{"start": 0.0, "end": 0.4, "duration": 0.4}]
    assert vq._parse_crops(text) == [(1080, 1800, 0, 60)]
    assert vq._parse_ebur128(text) == (-16.2, -1.1)


def test_shadow_qa_writes_report_for_healthy_ai_short(monkeypatch, tmp_path):
    settings = _settings(tmp_path)
    ready = settings.runtime_dir / "ready_for_review"
    slot_dir = settings.runtime_dir / "slots" / "23"
    ready.mkdir(parents=True)
    slot_dir.mkdir(parents=True)
    video = ready / "slot-23-en-ai.mp4"
    video.write_bytes(b"video")
    metadata = {
        "slot": 23,
        "pipeline": "ai_short",
        "editorial_profile": "direct_v1",
        "video_file": str(video),
    }
    metadata_path = ready / "slot-23-en-ai.upload.json"
    metadata_path.write_text(json.dumps(metadata), encoding="utf-8")
    (slot_dir / "plan.json").write_text(
        json.dumps({"script": "A strong opening. The mechanism follows. Final payoff."}),
        encoding="utf-8",
    )

    monkeypatch.setattr(
        vq,
        "_probe_video",
        lambda _path: {
            "format": {"duration": "29.5"},
            "streams": [
                {"codec_type": "video", "width": 1080, "height": 1920},
                {"codec_type": "audio"},
            ],
        },
    )
    monkeypatch.setattr(vq, "_detect_crop", lambda *_args, **_kwargs: (1080, 1920, 0, 0))
    monkeypatch.setattr(vq, "_detect_black", lambda *_args, **_kwargs: [])
    monkeypatch.setattr(vq, "_analyze_audio", lambda _path: (-16.0, -1.0))

    reports = vq.qa_ready(settings)

    assert len(reports) == 1
    assert reports[0]["summary"]["critical_failures"] == 0
    checks = {item["id"]: item for item in reports[0]["checks"]}
    assert checks["resolution"]["status"] == "PASS"
    assert checks["duration"]["status"] == "PASS"
    assert checks["audio_peak"]["status"] == "PASS"
    assert checks["outro_text"]["status"] == "PASS"
    assert video.with_suffix(".qa.json").exists()


def test_qa_marks_wrong_resolution_and_missing_audio_critical(monkeypatch, tmp_path):
    settings = _settings(tmp_path)
    video = tmp_path / "bad.mp4"
    video.write_bytes(b"video")
    monkeypatch.setattr(
        vq,
        "_probe_video",
        lambda _path: {
            "format": {"duration": "30"},
            "streams": [{"codec_type": "video", "width": 720, "height": 1280}],
        },
    )
    monkeypatch.setattr(vq, "_detect_crop", lambda *_args, **_kwargs: (720, 1280, 0, 0))
    monkeypatch.setattr(vq, "_detect_black", lambda *_args, **_kwargs: [])

    report = vq.run_video_qa(
        settings,
        video,
        {"slot": 23, "pipeline": "ai_short", "editorial_profile": "direct_v1"},
    )

    checks = {item["id"]: item for item in report["checks"]}
    assert checks["resolution"]["status"] == "FAIL"
    assert checks["audio_stream"]["status"] == "FAIL"
    assert report["summary"]["critical_failures"] == 2
    assert report["summary"]["status"] == "FAIL"


def test_ready_scan_skips_uploaded_receipts(monkeypatch, tmp_path):
    settings = _settings(tmp_path)
    ready = settings.runtime_dir / "ready_for_review"
    ready.mkdir(parents=True)
    video = ready / "slot-23-en-ai.mp4"
    video.write_bytes(b"video")
    metadata = ready / "slot-23-en-ai.upload.json"
    metadata.write_text(
        json.dumps({"slot": 23, "pipeline": "ai_short", "video_file": str(video)}),
        encoding="utf-8",
    )
    metadata.with_suffix(".youtube.json").write_text("{}", encoding="utf-8")
    monkeypatch.setattr(vq, "run_video_qa", lambda *_args, **_kwargs: {})

    assert vq.qa_ready(settings) == []
