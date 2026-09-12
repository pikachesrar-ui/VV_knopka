import httpx
import pytest

import vv_knopka.mpt_health as mpt_health


class DummySettings:
    mpt_base_url = "http://127.0.0.1:8080"


class FakeClient:
    def __init__(self, *, response=None, error=None, **kwargs):
        self.response = response
        self.error = error

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def get(self, url):
        if self.error:
            raise self.error
        return self.response


class FakeProcess:
    returncode = None

    def poll(self):
        return None


def test_mpt_health_accepts_reachable_non_5xx(monkeypatch):
    response = httpx.Response(200, request=httpx.Request("GET", "http://127.0.0.1:8080/docs"))
    monkeypatch.setattr(mpt_health.httpx, "Client", lambda **kwargs: FakeClient(response=response))
    mpt_health.require_mpt_available(DummySettings())


def test_mpt_health_reports_actionable_offline_error(monkeypatch):
    request = httpx.Request("GET", "http://127.0.0.1:8080/docs")
    error = httpx.ConnectError("connection refused", request=request)
    monkeypatch.setattr(mpt_health.httpx, "Client", lambda **kwargs: FakeClient(error=error))

    with pytest.raises(RuntimeError, match="MoneyPrinterTurbo API is not reachable") as exc:
        mpt_health.require_mpt_available(DummySettings())

    assert "uv run python main.py" in str(exc.value)


def test_mpt_health_rejects_server_error(monkeypatch):
    response = httpx.Response(503, request=httpx.Request("GET", "http://127.0.0.1:8080/docs"))
    monkeypatch.setattr(mpt_health.httpx, "Client", lambda **kwargs: FakeClient(response=response))

    with pytest.raises(RuntimeError, match="returned HTTP 503"):
        mpt_health.require_mpt_available(DummySettings())


def test_ensure_mpt_autostarts_only_when_endpoint_is_offline(monkeypatch):
    probes = iter(
        [
            (False, None, "connection refused"),
            (True, 200, None),
        ]
    )
    starts = []
    monkeypatch.setattr(mpt_health, "_probe_mpt", lambda *args, **kwargs: next(probes))
    monkeypatch.setattr(
        mpt_health,
        "start_mpt_background",
        lambda settings: starts.append(settings) or FakeProcess(),
    )

    settings = DummySettings()
    mpt_health.ensure_mpt_available(
        settings,
        startup_timeout_seconds=1,
        poll_seconds=0.01,
    )

    assert starts == [settings]


def test_ensure_mpt_does_not_start_second_server_on_http_5xx(monkeypatch):
    starts = []
    monkeypatch.setattr(mpt_health, "_probe_mpt", lambda *args, **kwargs: (False, 503, None))
    monkeypatch.setattr(
        mpt_health,
        "start_mpt_background",
        lambda settings: starts.append(settings) or FakeProcess(),
    )

    with pytest.raises(RuntimeError, match="returned HTTP 503"):
        mpt_health.ensure_mpt_available(DummySettings())

    assert starts == []
