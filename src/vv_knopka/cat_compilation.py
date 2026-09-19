from __future__ import annotations

from typing import Any


_GENERIC_SEARCH_TERMS = (
    "cat funny reaction",
    "cat playing",
    "cat jumping",
    "cat running",
    "cat curious",
    "cat interacting with human",
    "cat meowing",
    "cat purring",
)


def build_generic_cat_plan(language: str) -> dict[str, Any]:
    """Return the intentionally broad editorial plan for cat compilations.

    Product decision: cat compilations should not promise a narrow theme that
    licensed stock cannot reliably satisfy. The editorial identity comes from
    the numbered cards, pacing, highlight selection and real source audio.
    """
    language = "ru" if str(language).strip().lower() == "ru" else "en"
    title = "Котики" if language == "ru" else "Cats"
    hook = (
        "Просто короткая подборка удачных моментов с котиками."
        if language == "ru"
        else "A short collection of good cat moments."
    )
    return {
        "title": title,
        "hook": hook,
        "script": "cat reactions; cat play; cat movement; cat sounds; cat interactions",
        "visual_anchor": "cat",
        "search_terms": list(_GENERIC_SEARCH_TERMS),
        "caption": title,
        "hashtags": ["#cats", "#funnycats", "#catshorts"],
        "editorial_value": (
            "A broad cat compilation with original numbered cards, selected highlights, "
            "real source audio and human review; no narrow theme is promised."
        ),
        "fact_check_items": [],
        "ai_disclosure_recommended": False,
        "cat_compilation_mode": "generic",
    }
