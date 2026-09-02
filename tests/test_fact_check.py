import json
from pathlib import Path

from vv_knopka.budget import BudgetLedger
from vv_knopka.fact_check import FactChecker
from vv_knopka.settings import Settings


class FakeResponse:
    def __init__(self, payload):
        self.payload = payload

    def raise_for_status(self):
        return None

    def json(self):
        return self.payload


class FakeClient:
    def __init__(self, payload, **kwargs):
        self.payload = payload
        self.request_json = None

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def post(self, url, *, headers, json):
        self.request_json = json
        return FakeResponse(self.payload)


def _settings(tmp_path: Path) -> Settings:
    return Settings(
        raw={
            "pilot": {"runtime_dir": "runtime", "openai_budget_usd": 10.0, "auto_publish": False},
            "openai": {
                "terra_input_per_million_usd": 2.0,
                "terra_output_per_million_usd": 12.0,
                "luna_input_per_million_usd": 0.20,
                "luna_output_per_million_usd": 1.20,
                "fact_check_model": "gpt-5.6-luna",
                "fact_check_max_estimated_cost_usd": 0.05,
                "fact_check_max_tool_calls": 1,
                "web_search_call_usd": 0.01,
            },
        },
        root=tmp_path,
    )


def _api_payload(*, passed: bool, status: str = "supported", sources: bool = True):
    verdict = {
        "pass": passed,
        "summary": "verified" if passed else "claim is not sufficiently supported",
        "claims": [
            {
                "claim": "Owls have feather adaptations that can reduce flight noise.",
                "status": status,
                "reason": "Evidence supports this description." if status == "supported" else "Evidence is insufficient.",
            }
        ],
    }
    web_item = {
        "type": "web_search_call",
        "id": "ws_1",
        "status": "completed",
        "action": {
            "type": "search",
            "sources": ([{"type": "url", "url": "https://example.edu/owl"}] if sources else []),
        },
    }
    return {
        "output": [
            web_item,
            {
                "type": "message",
                "content": [{"type": "output_text", "text": json.dumps(verdict)}],
            },
        ],
        "usage": {"input_tokens": 1000, "output_tokens": 100},
    }


def _plan():
    return {
        "title": "Why Owls Fly Quietly",
        "visual_anchor": "owl",
        "script": "Owls have feather adaptations that can reduce flight noise.",
        "fact_check_items": ["Owls have feather adaptations that can reduce flight noise."],
    }


def test_fact_checker_requires_web_evidence_and_records_tool_cost(monkeypatch, tmp_path):
    settings = _settings(tmp_path)
    ledger = BudgetLedger(settings)
    payload = _api_payload(passed=True)
    client = FakeClient(payload)
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    monkeypatch.setattr("vv_knopka.fact_check.httpx.Client", lambda **kwargs: client)

    result = FactChecker(settings, ledger).check(slot=17, plan=_plan())

    assert result["passed"] is True
    assert result["web_search_calls"] == 1
    assert result["evidence_sources"] == ["https://example.edu/owl"]
    assert ledger.spent_usd() > 0.01
    assert client.request_json["max_tool_calls"] == 1
    assert client.request_json["tool_choice"] == "required"
    assert client.request_json["tools"][0]["type"] == "web_search"


def test_fact_checker_fails_when_claim_is_uncertain(monkeypatch, tmp_path):
    settings = _settings(tmp_path)
    ledger = BudgetLedger(settings)
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    monkeypatch.setattr(
        "vv_knopka.fact_check.httpx.Client",
        lambda **kwargs: FakeClient(_api_payload(passed=False, status="uncertain")),
    )

    result = FactChecker(settings, ledger).check(slot=17, plan=_plan())

    assert result["passed"] is False


def test_fact_checker_fails_closed_when_search_returns_no_sources(monkeypatch, tmp_path):
    settings = _settings(tmp_path)
    ledger = BudgetLedger(settings)
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    monkeypatch.setattr(
        "vv_knopka.fact_check.httpx.Client",
        lambda **kwargs: FakeClient(_api_payload(passed=True, sources=False)),
    )

    result = FactChecker(settings, ledger).check(slot=17, plan=_plan())

    assert result["pass"] is True
    assert result["passed"] is False
