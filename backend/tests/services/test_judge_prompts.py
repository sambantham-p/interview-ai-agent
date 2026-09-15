from app.services.judge_prompts import (
    JUDGE_COMMON_INSTRUCTIONS,
    build_attitude_context,
    build_judge_system_instruction,
)


def test_build_judge_system_instruction_concatenates_pieces_in_order() -> None:
    instruction = build_judge_system_instruction(
        "Score coding.", job_description_summary="Job description: role='Backend'."
    )

    assert instruction.index(JUDGE_COMMON_INSTRUCTIONS) < instruction.index(
        "Score coding."
    )
    assert instruction.index("Score coding.") < instruction.index(
        "Job description: role='Backend'."
    )


def test_build_judge_system_instruction_omits_extra_context_when_not_given() -> None:
    instruction = build_judge_system_instruction(
        "Score coding.", job_description_summary="Job description: role='Backend'."
    )

    assert "red_flag_count" not in instruction


def test_build_judge_system_instruction_includes_extra_context_when_given() -> None:
    instruction = build_judge_system_instruction(
        "Score attitude.",
        job_description_summary="Job description: role='Backend'.",
        extra_context="Ordinary red_flag_count for this session: 2.",
    )

    assert "red_flag_count for this session: 2" in instruction


def test_build_attitude_context_includes_red_flag_count_and_severe_flag() -> None:
    context = build_attitude_context(
        red_flag_count=3, severe_red_flag=True, hint_counts={"technical_interview": 2}
    )

    assert "red_flag_count for this session: 3" in context
    assert "abusive language) ended the interview: True" in context
    assert "technical_interview=2" in context


def test_build_attitude_context_defaults_hint_summary_to_none_when_empty() -> None:
    context = build_attitude_context(
        red_flag_count=0, severe_red_flag=False, hint_counts={}
    )

    assert "Hint counts by phase: none" in context
