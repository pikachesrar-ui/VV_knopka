from vv_knopka.youtube_cc_prescreen import diversify_channels, prescreen_decision_passes


def test_diversify_channels_keeps_only_one_candidate_per_uploader():
    candidates = [
        {"video_id": "a", "channel_id": "same", "view_count": 100},
        {"video_id": "b", "channel_id": "same", "view_count": 90},
        {"video_id": "c", "channel_id": "other", "view_count": 80},
    ]
    selected = diversify_channels(candidates)
    assert [item["video_id"] for item in selected] == ["a", "c"]


def test_prescreen_rejects_creator_branding_even_if_model_says_approved():
    decision = {
        "approved": True,
        "confidence": 0.99,
        "domestic_cat": True,
        "creator_branding": True,
        "social_ui": False,
        "large_added_caption": False,
        "compilation_or_repost_style": False,
    }
    assert prescreen_decision_passes(decision) is False


def test_prescreen_rejects_large_caption_and_non_domestic_cat():
    captioned = {
        "approved": True,
        "confidence": 0.95,
        "domestic_cat": True,
        "creator_branding": False,
        "social_ui": False,
        "large_added_caption": True,
        "compilation_or_repost_style": False,
    }
    big_cat = dict(captioned)
    big_cat["large_added_caption"] = False
    big_cat["domestic_cat"] = False
    assert prescreen_decision_passes(captioned) is False
    assert prescreen_decision_passes(big_cat) is False


def test_prescreen_accepts_clean_domestic_cat_thumbnail():
    decision = {
        "approved": True,
        "confidence": 0.91,
        "domestic_cat": True,
        "creator_branding": False,
        "social_ui": False,
        "large_added_caption": False,
        "compilation_or_repost_style": False,
    }
    assert prescreen_decision_passes(decision) is True
