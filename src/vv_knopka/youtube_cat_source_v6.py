from __future__ import annotations

import json
from pathlib import Path

from . import youtube_cat_source_v4 as _v4
from . import youtube_cc_preflight as _preflight
from . import youtube_clean_footage_v2 as _clean_v2


# Patch only the clean-review dependency points before v5 is imported.
# The established API/search/download implementation remains unchanged.
_v4.review_clean_youtube_footage = _clean_v2.review_clean_youtube_footage
_v4.clean_review_clip_metadata = _clean_v2.clean_review_clip_metadata
_preflight.review_clean_youtube_footage = _clean_v2.review_clean_youtube_footage
_preflight.clean_review_clip_metadata = _clean_v2.clean_review_clip_metadata


def _known_rejected_video_ids_v2(runtime_dir: Path) -> set[str]:
    """Keep durable obvious packaging rejects, but expire ambiguous v1 collage-only decisions."""
    rejected: set[str] = set()
    current_prompt = _clean_v2.current_clean_prompt_version()
    for path in runtime_dir.glob("slots/*/youtube_clean_reviews/*.json"):
        try:
            raw = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        if raw.get("clean_footage_approved") is not False:
            continue
        video_id = str(raw.get("video_id") or "").strip()
        if not video_id:
            continue
        decision = raw.get("decision") or {}
        obvious_packaging = any(
            bool(decision.get(field))
            for field in ("creator_branding", "social_ui", "large_added_caption")
        )
        if raw.get("prompt_version") == current_prompt or obvious_packaging:
            rejected.add(video_id)
    return rejected


_preflight.known_rejected_video_ids = _known_rejected_video_ids_v2

# Import after dependency patching so v5 binds the patched helpers.
from . import youtube_cat_source_v5 as _v5  # noqa: E402


def main() -> None:
    _v5.main()


if __name__ == "__main__":
    main()
