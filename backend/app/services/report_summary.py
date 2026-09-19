"""Derived, human-readable findings about a report's judge evaluations -
which dimensions were strong, which need work, and the one-line summary -
computed once here so the in-app report and the PDF always agree.
"""

from typing import Protocol

from app.constants.judge import DIMENSION_STRONG_SCORE, MAX_STRENGTHS_SHOWN


class ScoredDimension(Protocol):
    judge_name: str
    dimension: str
    score: float


def strength_judges(evaluations: list[ScoredDimension]) -> list[str]:
    """Judge names of the best-scoring dimensions at or above the strong
    threshold, best first.
    """
    strong = sorted(
        (e for e in evaluations if float(e.score) >= DIMENSION_STRONG_SCORE),
        key=lambda e: float(e.score),
        reverse=True,
    )
    return [e.judge_name for e in strong[:MAX_STRENGTHS_SHOWN]]


def focus_judges(evaluations: list[ScoredDimension]) -> list[str]:
    """Judge names of every dimension below the strong threshold,
    weakest first.
    """
    weak = sorted(
        (e for e in evaluations if float(e.score) < DIMENSION_STRONG_SCORE),
        key=lambda e: float(e.score),
    )
    return [e.judge_name for e in weak]


def build_headline(evaluations: list[ScoredDimension]) -> str:
    """One sentence naming the strongest dimensions and the weakest one."""
    by_judge = {e.judge_name: e.dimension for e in evaluations}
    strengths = [by_judge[name] for name in strength_judges(evaluations)]
    focus = focus_judges(evaluations)

    parts = []
    if strengths:
        parts.append(f"Strongest in {' and '.join(strengths)}.")
    if focus:
        parts.append(f"Most room to grow in {by_judge[focus[0]]}.")
    else:
        parts.append("No dimension fell below the hiring bar.")
    return " ".join(parts)
