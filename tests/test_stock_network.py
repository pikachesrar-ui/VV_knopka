from pathlib import Path
from contextlib import contextmanager

import httpx
import pytest

from vv_knopka import pexels_curator, stock_network


def test_stock_search_retries_only_transport_errors(monkeypatch):
    monkeypatch.setattr(stock_network.time, "sleep", lambda _: None)

    class Client:
        calls = 0

        def get(self, url, **kwargs):
            self.calls += 1
            if self.calls < 3:
                raise httpx.ConnectError("reset")
            return httpx.Response(200, request=httpx.Request("GET", url))

    client = Client()
    assert stock_network.get_stock(client, "https://stock.example/video").status_code == 200
    assert client.calls == 3

    class Forbidden:
        calls = 0

        def get(self, url, **kwargs):
            self.calls += 1
            raise httpx.HTTPStatusError("forbidden", request=httpx.Request("GET", url), response=httpx.Response(403))

    forbidden = Forbidden()
    with pytest.raises(RuntimeError, match="HTTP 403") as caught:
        stock_network.get_stock(
            forbidden, "https://stock.example/video?key=secret", params={"key": "also-secret"}
        )
    assert forbidden.calls == 1
    assert "secret" not in str(caught.value)


def test_stock_search_retries_temporary_http_status(monkeypatch):
    monkeypatch.setattr(stock_network.time, "sleep", lambda _: None)

    class Client:
        calls = 0

        def get(self, url, **kwargs):
            self.calls += 1
            status = 503 if self.calls < 3 else 200
            request = httpx.Request("GET", url, params=kwargs.get("params"))
            return httpx.Response(status, request=request)

    client = Client()
    response = stock_network.get_stock(
        client, "https://stock.example/video", params={"key": "top-secret"}
    )
    assert response.status_code == 200
    assert client.calls == 3


def test_stock_download_discards_partial_file_before_retry(monkeypatch, tmp_path: Path):
    monkeypatch.setattr(pexels_curator.time, "sleep", lambda _: None)
    target = tmp_path / "clip.mp4"

    class Response:
        def __init__(self, fail):
            self.fail = fail

        def raise_for_status(self):
            pass

        def iter_bytes(self):
            yield b"bad" if self.fail else b"good"
            if self.fail:
                raise httpx.ReadError("broken stream")

    class Client:
        calls = 0

        @contextmanager
        def stream(self, method, url):
            self.calls += 1
            yield Response(fail=self.calls == 1)

    client = Client()
    pexels_curator._download(client, "https://stock.example/clip", target)
    assert client.calls == 2
    assert target.read_bytes() == b"good"
    assert not target.with_suffix(".mp4.part").exists()
