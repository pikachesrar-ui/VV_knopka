from __future__ import annotations

import json
import os
from typing import Any

import httpx

from .budget import BudgetLedger
from .settings import Settings


FACT_CHECK_SCHEMA: dict[str, Any] = {
    "type": "object",
    "additionalProperties": False,
    "required": ["pass", "summary", "claims"],
    "properties": {
        "pass": {"type": "boolean"},
        "summary": {"type": "string"},
        "claims": {
            "type": "array",
            "minItems": 1,
            "items": {
                "type": "object",
                "additionalProperties": False,
                "required": ["claim", "status", "reason"],
                "properties": {
                    "claim": {"type": "string"},
                    "status": {
                        "type": "string",
                        "enum": ["supported", "unsupported", "uncertain"],
                    },
                    "reason": {"type": "string"},
                },
            },
        },
    },
}


def _extract_output_text(data: dict[str, Any]) -> str:
    direct = data.get("output_text")
    if isinstance(direct, str) and direct.strip():
        return direct
    texts: list[str] = []
    for item in data.get("output") or []:
        if not isinstance(item, dict):
            continue
        for content in item.get("content") or []:
            if isinstance(content, dict) and isinstance(content.get("text"), str):
                texts.append(content["text"])
    if not texts:
        raise RuntimeError("Fact-check response did not contain structured text output")
    return "".join(texts)


def _web_evidence(data: dict[str, Any]) -> tuple[int, list[str]]:
    calls = 0
    sources: list[str] = []
    seen: set[str] = set()
    for item in data.get("output") or []:
        if not isinstance(item, dict) or item.get("type") != "web_search_call":
            continue
        calls += 1
        action = item.get("action") or {}
        for source in action.get("sources") or []:
            if not isinstance(source, dict):
                continue
            url = str(source.get("url") or "").strip()
            if url and url not in seen:
                seen.add(url)
                sources.append(url)
    return calls, sources


class FactChecker:
    """Verify an AI Short plan with one bounded OpenAI web-search tool call."""

    def __init__(self, settings: Settings, ledger: BudgetLedger):
        self.settings = settings
        self.ledger = ledger
        self.api_key = os.getenv("OPENAI_API_KEY", "").strip()
        if not self.api_key:
            raise RuntimeError("OPENAI_API_KEY is not set")

    def check(self, *, slot: int, plan: dict[str, Any]) -> dict[str, Any]:
        cfg = self.settings.raw.get("openai", {})
        model = str(cfg.get("fact_check_model") or "gpt-5.6-luna")
        max_estimated = float(cfg.get("fact_check_max_estimated_cost_usd", 0.05))
        max_tool_calls = max(int(cfg.get("fact_check_max_tool_calls", 1)), 1)
        web_search_call_usd = max(float(cfg.get("web_search_call_usd", 0.01)), 0.0)
        self.ledger.ensure_room(max_estimated)

        fact_items = [
            str(value).strip()
            for value in (plan.get("fact_check_items") or [])
            if str(value).strip()
        ]
        if not fact_items:
            fact_items = [str(plan.get("script") or "").strip()]
        fact_items = [value for value in fact_items if value]
        if not fact_items:
            return {
                "passed": False,
                "pass": False,
                "summary": "No factual claims were provided for verification.",
                "claims": [],
                "evidence_sources": [],
                "web_search_calls": 0,
                "model": model,
            }

        prompt = (
            "You are a strict factual verification gate for a short educational animal/nature video.\n"
            "Use web search before deciding. Verify every material factual claim, not merely whether it sounds plausible.\n"
            "Prefer authoritative scientific, university, museum, government, major encyclopedia, or primary sources.\n"
            "PASS only when every claim is well supported by the evidence you found. If a claim is species-specific but "
            "the video presents it as true of a broader animal, mark it unsupported. If evidence is ambiguous, conflicting, "
            "too weak, or you cannot verify it with this search, mark it uncertain and FAIL. Do not rescue the script by "
            "rewriting its claims.\n\n"
            f"Title: {str(plan.get('title') or '')}\n"
            f"Visual anchor: {str(plan.get('visual_anchor') or '')}\n"
            f"Script: {str(plan.get('script') or '')}\n"
            f"Claims requested for checking: {json.dumps(fact_items, ensure_ascii=False)}"
        )

        payload = {
            "model": model,
            "input": prompt,
            "reasoning": {"effort": "low"},
            "tools": [{"type": "web_search", "search_context_size": "medium"}],
            "tool_choice": "required",
            "max_tool_calls": max_tool_calls,
            "include": ["web_search_call.action.sources"],
            "text": {
                "format": {
                    "type": "json_schema",
                    "name": "vv_fact_check",
                    "strict": True,
                    "schema": FACT_CHECK_SCHEMA,
                },
                "verbosity": "low",
            },
            "store": False,
        }
        with httpx.Client(timeout=180) as client:
            response = client.post(
                "https://api.openai.com/v1/responses",
                headers={"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"},
                json=payload,
            )
            response.raise_for_status()
            data = response.json()

        verdict = json.loads(_extract_output_text(data))
        web_calls, sources = _web_evidence(data)
        usage = data.get("usage") or {}
        self.ledger.record(
            model=model,
            input_tokens=int(usage.get("input_tokens", 0)),
            output_tokens=int(usage.get("output_tokens", 0)),
            purpose=f"slot-{slot}:fact-check",
            fixed_cost_usd=web_calls * web_search_call_usd,
        )

        claim_results = list(verdict.get("claims") or [])
        all_supported = bool(claim_results) and all(
            str(item.get("status") or "") == "supported"
            for item in claim_results
            if isinstance(item, dict)
        )
        passed = bool(verdict.get("pass")) and all_supported and web_calls >= 1 and bool(sources)
        return {
            "passed": passed,
            "pass": bool(verdict.get("pass")),
            "summary": str(verdict.get("summary") or "").strip(),
            "claims": claim_results,
            "evidence_sources": sources,
            "web_search_calls": web_calls,
            "model": model,
            "input_tokens": int(usage.get("input_tokens", 0)),
            "output_tokens": int(usage.get("output_tokens", 0)),
        }
