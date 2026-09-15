from app.constants.judge import (
    JUDGE_NAMES,
    JUDGE_PHASES,
    JUDGE_WEIGHTS,
    RECOMMENDATION_TIERS,
)


def test_judge_weights_sum_to_one() -> None:
    assert sum(JUDGE_WEIGHTS.values()) == 1.0


def test_recommendation_tiers_are_strictly_descending() -> None:
    thresholds = [threshold for threshold, _tier in RECOMMENDATION_TIERS]
    assert thresholds == sorted(thresholds, reverse=True)
    assert thresholds[-1] == 0


def test_every_judge_name_has_phases_and_weight_entries() -> None:
    for name in JUDGE_NAMES:
        assert name in JUDGE_PHASES
        assert name in JUDGE_WEIGHTS


def test_judge_phases_use_known_interview_phases() -> None:
    from app.constants.interview import INTERVIEW_PHASES

    for phases in JUDGE_PHASES.values():
        if phases is None:
            continue
        for phase in phases:
            assert phase in INTERVIEW_PHASES
