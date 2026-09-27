"""Local editorial decisions; no additional provider requests."""
from __future__ import annotations

import json
import math
import re
from pathlib import Path
from typing import Any

from .settings import Settings


PROFILE = "direct_v1"


def enabled_for_slot(settings: Settings, slot: int) -> bool:
    cfg = settings.raw.get("editorial", {})
    pilot_end = int(settings.raw.get("pilot", {}).get("total_shorts", 15))
    return bool(cfg.get("enabled", False)) and slot >= max(
        pilot_end + 1, int(cfg.get("start_slot", 21))
    )


def build_cat_edit(settings: Settings, highlights_path: Path) -> Path:
    """Keep a bounded set of strong reviewed windows, with a strong ending.

    Keep the full source manifest and reviews for provenance/reuse audits. A
    weak review fails closed and is cached, so retries do not buy more reviews.
    """
    raw = json.loads(highlights_path.read_text(encoding="utf-8"))
    cfg = settings.raw.get("editorial", {})
    minimum = int(cfg.get("cat_min_clips", 3))
    maximum = int(cfg.get("cat_max_clips", 4))
    threshold = float(cfg.get("cat_min_score", 6.0))
    if not 3 <= minimum <= maximum or not 0 <= threshold <= 10:
        raise ValueError("Invalid editorial cat limits")
    selections = raw.get("selections", [])
    indices = [int(item["clip_index"]) for item in selections]
    if len(indices) != len(set(indices)):
        raise ValueError("Duplicate highlight clip indices")
    accepted = []
    for item in selections:
        score = float(item.get("score", 0))
        if not math.isfinite(score) or not 0 <= score <= 10:
            raise ValueError("Invalid highlight score")
        if score >= threshold:
            accepted.append(item)
    accepted.sort(key=lambda item: (-float(item["score"]), int(item["clip_index"])))
    if len(accepted) < minimum:
        raise RuntimeError(
            f"Editorial quality gate: {len(accepted)} strong cat clips; need {minimum}. "
            "Cached highlights retained; no automatic paid retry."
        )
    chosen = accepted[:maximum]
    # Best first, second-best last; avoid ending on the weakest accepted clip.
    ordered = chosen[:1] + chosen[2:] + chosen[1:2]
    result = {
        **raw,
        "editorial_profile": PROFILE,
        "order": [int(item["clip_index"]) for item in ordered],
        "selections": ordered,
        "excluded_clip_indices": [i for i in indices if i not in {int(x["clip_index"]) for x in ordered}],
        "selection_policy": {"min_score": threshold, "min_clips": minimum, "max_clips": maximum},
    }
    output = highlights_path.with_name("cat-edit.json")
    output.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    return output


def opening_materials(plan: dict[str, Any], materials: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Prefer metadata relevant to the opening query, preserving approved inputs.

    This is a transparent lexical heuristic, not temporal scene understanding.
    A query match is deliberately excluded: search results can be unrelated.
    """
    if plan.get("editorial_profile") != PROFILE or not plan.get("search_terms"):
        return materials
    anchor = set(re.findall(r"\w+", str(plan.get("visual_anchor", "")).lower()))
    terms = set(re.findall(r"\w+", str(plan["search_terms"][0]).lower())) - anchor
    def score(item: dict[str, Any]) -> int:
        info = item.get("source_info") or {}
        text = " ".join(str(info.get(key, "")) for key in ("source_url", "page_url", "tags", "vision_reason"))
        return len(terms & set(re.findall(r"\w+", text.lower())))
    return sorted(materials, key=score, reverse=True)
