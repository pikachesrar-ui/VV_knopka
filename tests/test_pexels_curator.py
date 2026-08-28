from vv_knopka.pexels_curator import infer_visual_anchor, pexels_page_matches_anchor


def test_infer_visual_anchor_from_existing_slot_one_plan():
    plan = {
        "search_terms": [
            "octopus sleeping close up aquarium",
            "octopus changing color underwater",
            "octopus camouflage coral reef",
            "octopus skin texture macro",
            "octopus tentacles underwater",
        ]
    }
    assert infer_visual_anchor(plan) == "octopus"


def test_pexels_anchor_filter_rejects_unrelated_filler():
    assert pexels_page_matches_anchor(
        "https://www.pexels.com/video/close-up-video-of-an-octopus-17836505/",
        "octopus",
    )
    assert not pexels_page_matches_anchor(
        "https://www.pexels.com/video/skin-texture-close-up-7477545/",
        "octopus",
    )
    assert not pexels_page_matches_anchor(
        "https://www.pexels.com/video/tropical-fish-on-coral-reef-37906980/",
        "octopus",
    )
