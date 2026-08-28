from __future__ import annotations

import json
import os
from typing import Any

import httpx

from .budget import BudgetLedger
from .openai_auth import safe_openai_error
from .settings import Settings


SHORT_PLAN_SCHEMA: dict[str, Any] = {
    "type": "object",
    "additionalProperties": False,
    "required": [
        "title", "hook", "script", "search_terms", "caption", "hashtags",
        "editorial_value", "fact_check_items", "ai_disclosure_recommended"
    ],
    "properties": {
        "title": {"type": "string"},
        "hook": {"type": "string"},
        "script": {"type": "string"},
        "search_terms": {"type": "array", "minItems": 4, "maxItems": 10, "items": {"type": "string"}},
        "caption": {"type": "string"},
        "hashtags": {"type": "array", "minItems": 3, "maxItems": 8, "items": {"type": "string"}},
        "editorial_value": {"type": "string"},
        "fact_check_items": {"type": "array", "items": {"type": "string"}},
        "ai_disclosure_recommended": {"type": "boolean"},
    },
}


class OpenAIPlanner:
    def __init__(self, settings: Settings, ledger: BudgetLedger):
        self.settings = settings
        self.ledger = ledger
        self.api_key = os.getenv("OPENAI_API_KEY", "").strip()
        if not self.api_key:
            raise RuntimeError("OPENAI_API_KEY is not set")

    def create_plan(self, *, slot: int, pipeline: str, language: str) -> dict[str, Any]:
        cfg = self.settings.raw["openai"]
        model = cfg["writer_model"]
        self.ledger.ensure_room(float(cfg["max_estimated_cost_per_call_usd"]))

        language_name = "Russian" if language == "ru" else "English"
        if pipeline == "ai_short":
            task = (
                "Create one original 25-45 second YouTube Short about a surprising, well-established "
                "animal behavior or nature curiosity. Build a strong first-second hook and a compact payoff. "
                "Do not invent studies, statistics, quotations, rescue stories, or events. Avoid medical advice."
            )
        else:
            task = (
                "Create an editorial concept for a 25-45 second cute/funny animal compilation. The final video "
                "must add a clear original framing or running joke rather than being a raw repost montage. "
                "Write short optional on-screen/voiceover lines that can connect licensed clips. Never request "
                "bass drops, impact booms, or loud transition effects."
            )

        prompt = f"""You are the editor of a review-first Shorts pilot.
Niche: Animals / Nature Curiosities.
Language: {language_name}.
Pipeline: {pipeline}.
Slot: {slot}/15.
{task}
Search terms must describe generic footage that can be found on licensed stock providers such as Pexels/Pixabay.
Keep the title natural, not deceptive clickbait. Hashtags must not claim something unsupported.
Return only the requested structured object."""

        payload = {
            "model": model,
            "input": prompt,
            "reasoning": {"effort": cfg.get("writer_reasoning_effort", "low")},
            "text": {
                "format": {
                    "type": "json_schema",
                    "name": "vv_short_plan",
                    "strict": True,
                    "schema": SHORT_PLAN_SCHEMA,
                },
                "verbosity": "low",
            },
            "store": False,
        }
        try:
            with httpx.Client(timeout=120) as client:
                response = client.post(
                    "https://api.openai.com/v1/responses",
                    headers={"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"},
                    json=payload,
                )
        except httpx.RequestError as exc:
            raise RuntimeError(f"Could not reach OpenAI API: {type(exc).__name__}") from None

        if response.status_code >= 400:
            raise RuntimeError(safe_openai_error(response))
        data = response.json()

        text = data.get("output_text") or _extract_output_text(data)
        plan = json.loads(text)
        usage = data.get("usage") or {}
        self.ledger.record(
            model=model,
            input_tokens=int(usage.get("input_tokens", 0)),
            output_tokens=int(usage.get("output_tokens", 0)),
            purpose=f"slot-{slot}:{pipeline}:{language}",
        )
        return plan


def _extract_output_text(data: dict[str, Any]) -> str:
    texts: list[str] = []
    for item in data.get("output", []):
        for content in item.get("content", []) if isinstance(item, dict) else []:
            if isinstance(content, dict) and isinstance(content.get("text"), str):
                texts.append(content["text"])
    if not texts:
        raise RuntimeError("OpenAI response did not contain text output")
    return "".join(texts)
