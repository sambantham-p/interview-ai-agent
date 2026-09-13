from app.constants.interview import INTERVIEW_PHASES


def test_interview_phases_has_seven_phases_in_order() -> None:
    assert INTERVIEW_PHASES == [
        "background_check",
        "project_drill_down",
        "technical_interview",
        "coding_challenge",
        "general_technical",
        "career_motivation",
        "candidate_questions",
    ]
