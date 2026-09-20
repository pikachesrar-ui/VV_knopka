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
            return "found"

    client = Client()
    assert stock_network.get_stock(client, "https://stock.example/video") == "found"
    assert client.calls == 3

    class Forbidden:
        calls = 0

        def get(self, url, **kwargs):
            self.calls += 1
            raise httpx.HTTPStatusError("forbidden", request=httpx.Request("GET", url), response=httpx.Response(403))

    forbidden = Forbidden()
    with pytest.raises(httpx.HTTPStatusError):
        stock_network.get_stock(forbidden, "https://stock.example/video")
    assert forbidden.calls == 1


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
