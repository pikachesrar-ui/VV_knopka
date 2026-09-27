import io
import sys

from vv_knopka import youtube_cli


def test_stats_prints_all_videos_with_cp1251_console(monkeypatch):
    output = io.BytesIO()
    console = io.TextIOWrapper(output, encoding="cp1251", errors="strict", write_through=True)
    monkeypatch.setattr(sys, "stdout", console)
    monkeypatch.setattr(sys, "argv", ["vv-youtube", "stats"])
    monkeypatch.setattr(youtube_cli, "load_settings", lambda *args: object())
    monkeypatch.setattr(youtube_cli, "collect_statistics", lambda *args: {
        "channel_title": "Кнопка", "collected_at": "2026-09-20T17:31:03Z",
        "videos": [
            {"slot": 31, "views": 1, "likes": 0, "comments": 0, "title": "Котики 😹"},
            {"slot": 32, "views": 583, "likes": 28, "comments": 0, "title": "Cats"},
        ],
    })

    youtube_cli.main()

    lines = output.getvalue().decode("cp1251")
    assert "YouTube stats: 2 videos" in lines
    assert "Кнопка" in lines
    assert "slot 31: 1 views" in lines
    assert "Котики \\U0001f639" in lines
    assert "slot 32: 583 views" in lines
