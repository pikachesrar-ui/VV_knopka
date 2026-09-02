from __future__ import annotations

import json
import os
from typing import Any

import httpx

from .budget import BudgetLedger
from .settings import Settings


SHORT_PLAN_SCHEMA: dict[str, Any] = {
    "type": "object",
    "additionalProperties": False,
    "required": [
        "title", "hook", "script", "visual_anchor", "search_terms", "caption", "hashtags",
        "editorial_value", "fact_check_items", "ai_disclosure_recommended"
    ],
    "properties": {
        "title": {"type": "string"},
        "hook": {"type": "string"},
        "script": {"type": "string"},
        "visual_anchor": {"type": "string"},
        "search_terms": {"type": "array", "minItems": 4, "maxItems": 10, "items": {"type": "string"}},
        "caption": {"type": "string"},
        "hashtags": {"type": "array", "minItems": 3, "maxItems": 8, "items": {"type": "string"}},
        "editorial_value": {"type": "string"},
        "fact_check_items": {"type": "array", "items": {"type": "string"}},
        "ai_disclosure_recommended": {"type": "boolean"},
    },
}


STOCK_FRIENDLY_AI_ANCHORS = (
    "cat",
    "dog",
    "octopus",
    "bee",
    "ant",
    "penguin",
    "dolphin",
    "elephant",
    "horse",
    "rabbit",
    "fox",
    "owl",
    "parrot",
    "turtle",
    "snake",
    "butterfly",
    "spider",
    "frog",
    "duck",
    "chicken",
)


def recent_visual_anchors(settings: Settings, current_slot: int, *, limit: int | None = None) -> list[str]:
    """Return newest distinct AI visual anchors first for the subject cooldown."""
    if limit is None:
        limit = int(settings.raw.get("long_run", {}).get("fact_subject_cooldown", 6))
    limit = max(int(limit), 0)
    if limit == 0:
        return []

    anchors: list[str] = []
    for slot in range(int(current_slot) - 1, 0, -1):
        path = settings.runtime_dir / "slots" / f"{slot:02d}" / "plan.json"
        if not path.exists():
            continue
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        anchor = str(payload.get("visual_anchor") or "").strip().lower()
        if anchor and anchor not in anchors:
            anchors.append(anchor)
        if len(anchors) >= limit:
            break
    return anchors


class OpenAIPlanner:
    def __init__(self, settings: Settings, ledger: BudgetLedger):
        self.settings = settings
        self.ledger = ledger
        self.api_key = os.getenv("OPENAI_API_KEY", "").strip()
        if not self.api_key:
            raise RuntimeError("OPENAI_API_KEY is not set")

    def create_plan(
        self,
        *,
        slot: int,
        pipeline: str,
        language: str,
        topic_hint: str | None = None,
    ) -> dict[str, Any]:
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
                "must add a clear original framing rather than being a raw repost montage. Give it one coherent "
                "episode theme so the clips feel related, not random. The rendered compilation has no voiceover "
                "and no background music: its sound comes from the original clips plus a short meow on black title cards. "
                "Never request bass drops, impact booms, or loud transition effects."
            )

        topic_instruction = ""
        if topic_hint:
            normalized_topic = topic_hint.strip()
            topic_instruction = (
                f"\nExplicit user topic request: {normalized_topic!r}. Honor this request rather than choosing a different animal."
            )
            if normalized_topic.lower() in {"cat", "cats", "kitten", "kittens", "кот", "коты", "котики", "кошки"}:
                topic_instruction += (
                    " This is a domestic-cat compilation: set visual_anchor exactly to \"cat\". "
                    "Choose ONE stock-friendly subtheme for the episode, such as cats with toys, cats and boxes, "
                    "sleepy cats, curious reactions, climbing/jumping, dramatic stares, playful hunting, meowing or purring. "
                    "All search terms must contain the exact word \"cat\" AND reflect that same subtheme. "
                    "Favor visually useful terms that can also plausibly return clips with original sound, such as "
                    "cat meowing, cat purring, cat playing, or cat interacting, when they fit the chosen theme. "
                    "Do not use the phrase \"Daily Dose of Cats\" or any close imitation of it anywhere. "
                    "Title must be a short original episode title, preferably 2-4 words and never a permanent series name. "
                    "The hook is metadata only; do not write it as a voiceover instruction."
                )
        elif pipeline == "ai_short":
            cooldown = int(self.settings.raw.get("long_run", {}).get("fact_subject_cooldown", 6))
            recent = recent_visual_anchors(self.settings, slot, limit=cooldown)
            available = [anchor for anchor in STOCK_FRIENDLY_AI_ANCHORS if anchor not in set(recent)]
            if not available:
                available = list(STOCK_FRIENDLY_AI_ANCHORS)
            recent_text = ", ".join(recent) if recent else "none"
            topic_instruction = (
                "\nSTOCK-AVAILABILITY AND SUBJECT-COOLDOWN CONSTRAINT: choose the main subject from "
                f"this exact stock-friendly visual_anchor list: {', '.join(available)}. "
                f"Recent AI subjects still on cooldown ({max(cooldown, 0)}-subject window): {recent_text}. "
                "Do not choose a cooldown subject unless the available list had to reset because every supported subject was blocked. "
                "Do not narrow the subject to a rare species, subspecies, breed, or scientific name. "
                "The factual story itself must genuinely apply to the chosen broad animal, so do not use generic "
                "footage to illustrate a claim that is only true of a rare species. "
                "Prefer a visually demonstrable behavior that can be represented by several distinct licensed stock clips."
            )

        pilot_total = int(self.settings.raw.get("pilot", {}).get("total_shorts", 15))
        slot_label = f"Pilot slot: {slot}/{pilot_total}." if slot <= pilot_total else f"Long-run sequence slot: {slot}."
        prompt = f"""You are the editor of a review-first Shorts pipeline.
Niche: Animals / Nature Curiosities.
Language: {language_name}.
Pipeline: {pipeline}.
{slot_label}
{task}{topic_instruction}
For visual_anchor, return one concise ENGLISH noun or noun phrase naming the visible main subject that must be present in every stock clip (examples: "octopus", "cat", "bee").
Every search term must include that exact visual_anchor. Avoid ambiguous standalone visual terms such as "skin texture", "reef", "ocean", or "forest" that could retrieve footage without the main subject.
Search terms must describe generic footage that can be found on licensed stock providers such as Pexels/Pixabay.
Keep the title natural, original and not deceptive clickbait. Hashtags must not claim something unsupported.
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
        with httpx.Client(timeout=120) as client:
            response = client.post(
                "https://api.openai.com/v1/responses",
                headers={"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"},
                json=payload,
            )
            response.raise_for_status()
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
