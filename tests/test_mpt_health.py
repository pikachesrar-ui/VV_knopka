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
