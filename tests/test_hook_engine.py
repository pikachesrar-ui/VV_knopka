from vv_knopka.hook_engine import assess_hooks, score_hook


def test_hook_engine_penalizes_generic_opening_and_keeps_three_candidates() -> None:
    strong = "Why does your cat blink so slowly?"
    generic = "Did you know that cats can blink slowly?"

    assert score_hook(strong) > score_hook(generic)
    audit = assess_hooks(strong, [strong, generic, "Your cat's blink is a social signal."])
    assert audit["selected"] == strong
    assert audit["selected_style"] == "question"
    assert len(audit["candidates"]) == 3
    assert audit["selection_method"] == "single_planner_call_plus_local_audit"
