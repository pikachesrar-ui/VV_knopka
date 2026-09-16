from vv_knopka.pexels_curator import (
    choose_pixabay_file,
    infer_visual_anchor,
    pexels_page_matches_anchor,
    select_vision_approved_candidates,
)


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


def test_slug_is_only_a_metadata_signal():
    assert pexels_page_matches_anchor(
        "https://www.pexels.com/video/close-up-video-of-an-octopus-17836505/",
        "octopus",
    )
    assert not pexels_page_matches_anchor(
        "https://www.pexels.com/video/skin-texture-close-up-7477545/",
        "octopus",
    )


def test_vision_gate_rejects_unrelated_and_low_confidence_candidates():
    candidates = [
        {"id": 1, "metadata_mentions_anchor": False},
        {"id": 2, "metadata_mentions_anchor": True},
        {"id": 3, "metadata_mentions_anchor": False},
    ]
    decisions = [
        {"id": 1, "accepted": True, "confidence": 0.96, "reason": "octopus clearly visible"},
        {"id": 2, "accepted": False, "confidence": 0.99, "reason": "only coral and fish"},
        {"id": 3, "accepted": True, "confidence": 0.50, "reason": "ambiguous shape"},
    ]
    approved = select_vision_approved_candidates(
        candidates,
        decisions,
        minimum_confidence=0.72,
    )
    assert [item["id"] for item in approved] == [1]
    assert approved[0]["vision_confidence"] == 0.96


def test_pixabay_file_prefers_portrait_rendition():
    video = {
        "videos": {
            "large": {
                "url": "https://cdn.example/landscape.mp4",
                "width": 1920,
                "height": 1080,
                "size": 100,
                "thumbnail": "https://cdn.example/landscape.jpg",
            },
            "medium": {
                "url": "https://cdn.example/portrait.mp4",
                "width": 720,
                "height": 1280,
                "size": 80,
                "thumbnail": "https://cdn.example/portrait.jpg",
            },
        }
    }
    chosen = choose_pixabay_file(video)
    assert chosen is not None
    assert chosen["link"].endswith("portrait.mp4")
    assert chosen["thumbnail"].endswith("portrait.jpg")
