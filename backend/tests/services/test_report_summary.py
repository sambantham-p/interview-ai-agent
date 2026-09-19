from types import SimpleNamespace

from app.services.report_summary import build_headline, focus_judges, strength_judges


def _dim(judge_name: str, dimension: str, score: float) -> SimpleNamespace:
    return SimpleNamespace(judge_name=judge_name, dimension=dimension, score=score)


def test_strength_judges_lists_best_first_and_caps_the_count() -> None:
    evaluations = [
        _dim("a", "A", 75),
        _dim("b", "B", 95),
        _dim("c", "C", 85),
        _dim("d", "D", 40),
    ]

    assert strength_judges(evaluations) == ["b", "c"]


def test_focus_judges_lists_weakest_first() -> None:
    evaluations = [_dim("a", "A", 60), _dim("b", "B", 30), _dim("c", "C", 90)]

    assert focus_judges(evaluations) == ["b", "a"]


def test_headline_names_strengths_and_the_weakest_dimension() -> None:
    evaluations = [_dim("a", "Alpha", 90), _dim("b", "Beta", 40)]

    assert build_headline(evaluations) == (
        "Strongest in Alpha. Most room to grow in Beta."
    )


def test_headline_says_nothing_fell_below_the_bar_when_all_are_strong() -> None:
    evaluations = [_dim("a", "Alpha", 90), _dim("b", "Beta", 80)]

    assert build_headline(evaluations) == (
        "Strongest in Alpha and Beta. No dimension fell below the hiring bar."
    )


def test_headline_with_only_weak_dimensions_has_no_strengths_sentence() -> None:
    assert build_headline([_dim("a", "Alpha", 30)]) == ("Most room to grow in Alpha.")
