from vv_knopka.cat_compilation import build_generic_cat_plan


def test_generic_cat_plan_does_not_promise_a_narrow_theme():
    ru = build_generic_cat_plan("ru")
    en = build_generic_cat_plan("en")

    assert ru["title"] == "Котики"
    assert en["title"] == "Cats"
    assert ru["visual_anchor"] == "cat"
    assert en["visual_anchor"] == "cat"
    assert ru["cat_compilation_mode"] == "generic"
    assert all("cat" in term.casefold() for term in ru["search_terms"])
    assert all("cat" in term.casefold() for term in en["search_terms"])
