import json

import vv_knopka.youtube_clean_footage_v2 as clean_v2
import vv_knopka.youtube_cat_source_v6 as youtube_v6


def clean_decision(**overrides):
    decision = {
        "approved": True,
        "confidence": 0.95,
        "cat_visible": True,
        "creator_branding": False,
        "social_ui": False,
        "large_added_caption": False,
        "source_frame_collage": False,
        "multi_clip_sequence": False,
        "compilation_or_repost_style": False,
        "reason": "clean temporal samples",
    }
    decision.update(overrides)
    return decision


def test_v2_accepts_clean_temporal_samples():
    assert clean_v2.decision_passes_clean_gate(clean_decision()) is True


def test_v2_rejects_real_collage_inside_source_frame():
    assert clean_v2.decision_passes_clean_gate(clean_decision(source_frame_collage=True)) is False


def test_v2_rejects_clear_multi_clip_sequence():
    assert clean_v2.decision_passes_clean_gate(clean_decision(multi_clip_sequence=True)) is False


def test_reject_memory_expires_stale_collage_only_but_keeps_obvious_packaging(tmp_path):
    review_dir = tmp_path / "slots" / "02" / "youtube_clean_reviews"
    review_dir.mkdir(parents=True)

    (review_dir / "ambiguous.json").write_text(
        json.dumps(
            {
                "video_id": "ambiguous",
                "prompt_version": "youtube-clean-footage-v1",
                "clean_footage_approved": False,
                "decision": {
                    "creator_branding": False,
                    "social_ui": False,
                    "large_added_caption": False,
                    "compilation_or_repost_style": True,
                },
            }
        ),
        encoding="utf-8",
    )
    (review_dir / "pawcsu.json").write_text(
        json.dumps(
            {
                "video_id": "pawcsu",
                "prompt_version": "youtube-clean-footage-v1",
                "clean_footage_approved": False,
                "decision": {
                    "creator_branding": True,
                    "social_ui": False,
                    "large_added_caption": True,
                    "compilation_or_repost_style": True,
                },
            }
        ),
        encoding="utf-8",
    )
    (review_dir / "current.json").write_text(
        json.dumps(
            {
                "video_id": "current",
                "prompt_version": clean_v2.current_clean_prompt_version(),
                "clean_footage_approved": False,
                "decision": {
                    "creator_branding": False,
                    "social_ui": False,
                    "large_added_caption": False,
                    "source_frame_collage": False,
                    "multi_clip_sequence": True,
                    "compilation_or_repost_style": True,
                },
            }
        ),
        encoding="utf-8",
    )

    rejected = youtube_v6._known_rejected_video_ids_v2(tmp_path)
    assert "ambiguous" not in rejected
    assert "pawcsu" in rejected
    assert "current" in rejected
