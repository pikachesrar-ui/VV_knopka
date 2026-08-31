import json
from pathlib import Path

import httpx
import pytest

from vv_knopka import acestep_client as ac
from vv_knopka.settings import Settings


def _settings(tmp_path: Path) -> Settings:
    return Settings(
        raw={"pilot": {"runtime_dir": "runtime", "openai_budget_usd": 10.0, "auto_publish": False}},
        root=tmp_path,
    )


class FakeClient:
    def __init__(self, handler, **_kwargs):
        self.handler = handler

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return False

    def post(self, url, **kwargs):
        return self.handler("POST", url, kwargs)

    def get(self, url, **kwargs):
        return self.handler("GET", url, kwargs)


def _response(method: str, url: str, payload=None, *, content: bytes | None = None):
    request = httpx.Request(method, url)
    if content is not None:
        return httpx.Response(200, request=request, content=content)
    return httpx.Response(200, request=request, json=payload)


def test_release_instrumental_uses_documented_async_api(monkeypatch, tmp_path):
    settings = _settings(tmp_path)
    captured = {}

    def handler(method, url, kwargs):
        assert method == "POST"
        assert url.endswith("/release_task")
        captured.update(kwargs["json"])
        return _response(method, url, {"data": {"task_id": "task-1"}, "code": 200, "error": None})

    monkeypatch.setattr(ac.httpx, "Client", lambda **kwargs: FakeClient(handler, **kwargs))
    client = ac.ACEStepClient(settings)

    task_id = client.release_instrumental(prompt="soft piano", duration_seconds=45, bpm=96)

    assert task_id == "task-1"
    assert captured["lyrics"] == "[Instrumental]"
    assert captured["instrumental"] is True
    assert captured["thinking"] is True
    assert captured["audio_duration"] == 45.0
    assert captured["audio_format"] == "wav"
    assert captured["batch_size"] == 1
    assert captured["bpm"] == 96


def test_wait_parses_success_result_json(monkeypatch, tmp_path):
    settings = _settings(tmp_path)
    result = [{
        "file": "/v1/audio?path=%2Ftmp%2Ftrack.wav",
        "seed_value": "42",
        "lm_model": "acestep-5Hz-lm-0.6B",
        "dit_model": "acestep-v15-turbo",
    }]

    def handler(method, url, kwargs):
        assert method == "POST"
        assert url.endswith("/query_result")
        assert kwargs["json"]["task_id_list"] == ["task-1"]
        return _response(
            method,
            url,
            {"data": [{"task_id": "task-1", "status": 1, "result": json.dumps(result)}], "code": 200, "error": None},
        )

    monkeypatch.setattr(ac.httpx, "Client", lambda **kwargs: FakeClient(handler, **kwargs))
    item = ac.ACEStepClient(settings).wait("task-1", timeout_seconds=1, poll_seconds=0)
    assert item["file"].startswith("/v1/audio")
    assert item["seed_value"] == "42"


def test_download_resolves_relative_audio_url(monkeypatch, tmp_path):
    settings = _settings(tmp_path)
    seen = {}

    def handler(method, url, kwargs):
        assert method == "GET"
        seen["url"] = url
        return _response(method, url, content=b"RIFF-test-audio")

    monkeypatch.setattr(ac.httpx, "Client", lambda **kwargs: FakeClient(handler, **kwargs))
    output = tmp_path / "track.wav"
    ac.ACEStepClient(settings).download({"file": "/v1/audio?path=%2Ftmp%2Fa.wav"}, output)

    assert seen["url"] == "http://127.0.0.1:8001/v1/audio?path=%2Ftmp%2Fa.wav"
    assert output.read_bytes() == b"RIFF-test-audio"


def test_process_manager_requires_local_checkout_when_api_offline(monkeypatch, tmp_path):
    settings = _settings(tmp_path)
    monkeypatch.setattr(ac, "api_available", lambda *_args, **_kwargs: False)

    with pytest.raises(RuntimeError, match="setup-acestep-windows"):
        ac.ACEStepProcessManager(settings).ensure_running(timeout_seconds=0.01)
