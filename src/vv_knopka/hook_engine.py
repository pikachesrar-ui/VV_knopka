from __future__ import annotations

import re
from typing import Any, Iterable


GENERIC_OPENINGS = (
    "did you know",
    "have you ever wondered",
    "you won't believe",
    "you wont believe",
    "in this video",
)


def normalize_hook(value: Any) -> str:
    return " ".join(str(value or "").strip().split())


def hook_style(value: Any) -> str:
    text = normalize_hook(value)
    lowered = text.casefold()
    if text.endswith("?"):
        return "question"
    if re.search(r"\b(why|how|what|when)\b", lowered):
        return "curiosity"
    if re.search(r"\b(can|never|only|without|before|after)\b", lowered):
        return "contrast"
    return "statement"


def score_hook(value: Any) -> float:
    """Cheap deterministic pre-publication score, not a promise of performance."""
    text = normalize_hook(value)
    words = re.findall(r"[\w’'-]+", text, flags=re.UNICODE)
    if not words:
        return -100.0
    lowered = text.casefold()
    score = 0.0
    if 5 <= len(words) <= 10:
        score += 3.0
    elif len(words) <= 12:
        score += 1.0
    else:
        score -= min((len(words) - 12) * 0.5, 4.0)
    if text.endswith("?"):
        score += 1.2
    if re.search(r"\b(why|how|what|can|without|inside|seconds?)\b", lowered):
        score += 1.0
    if any(opening in lowered for opening in GENERIC_OPENINGS):
        score -= 4.0
    if text.count("!") > 1 or text.isupper():
        score -= 1.5
    return round(score, 2)


def assess_hooks(selected: Any, candidates: Iterable[Any] = ()) -> dict[str, Any]:
    chosen = normalize_hook(selected)
    unique: list[str] = []
    for raw in [chosen, *list(candidates)]:
        value = normalize_hook(raw)
        if value and value.casefold() not in {item.casefold() for item in unique}:
            unique.append(value)
    scored = [
        {"text": value, "score": score_hook(value), "style": hook_style(value)}
        for value in unique[:3]
    ]
    return {
        "selected": chosen,
        "selected_score": score_hook(chosen),
        "selected_style": hook_style(chosen),
        "candidates": scored,
        "selection_method": "single_planner_call_plus_local_audit",
    }
