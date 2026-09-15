from app.models.candidate_profile import CandidateProfile
from app.models.job_description import JobDescription
from app.services.interview_prompts import build_phase_system_instruction


def _fake_candidate_profile() -> CandidateProfile:
    return CandidateProfile(
        id=1,
        education=[],
        experience=[],
        projects=[{"name": "Foo"}],
        skills=["Python"],
        github_url=None,
    )


def _fake_job_description() -> JobDescription:
    return JobDescription(
        id=2,
        role="Backend Engineer",
        seniority="senior",
        tech_stack=["Python"],
        coding_assessment_expected=True,
    )


def test_no_github_tool_instructions_by_default() -> None:
    instruction = build_phase_system_instruction(
        "project_drill_down", _fake_candidate_profile(), _fake_job_description()
    )

    assert "list_repos" not in instruction


def test_github_tool_instructions_included_when_available() -> None:
    instruction = build_phase_system_instruction(
        "project_drill_down",
        _fake_candidate_profile(),
        _fake_job_description(),
        github_tools_available=True,
    )

    assert "list_repos" in instruction
    assert "already named" in instruction


def test_no_retrieved_questions_block_by_default() -> None:
    instruction = build_phase_system_instruction(
        "technical_interview", _fake_candidate_profile(), _fake_job_description()
    )

    assert "curated bank" not in instruction


def test_no_retrieved_questions_block_when_pool_is_empty() -> None:
    instruction = build_phase_system_instruction(
        "technical_interview",
        _fake_candidate_profile(),
        _fake_job_description(),
        retrieved_questions=[],
    )

    assert "curated bank" not in instruction


def test_retrieved_questions_block_included_when_present() -> None:
    instruction = build_phase_system_instruction(
        "technical_interview",
        _fake_candidate_profile(),
        _fake_job_description(),
        retrieved_questions=["What is ACID?", "Explain the GIL."],
    )

    assert "curated bank" in instruction
    assert "- What is ACID?" in instruction
    assert "- Explain the GIL." in instruction


def test_no_company_research_block_by_default() -> None:
    instruction = build_phase_system_instruction(
        "career_motivation", _fake_candidate_profile(), _fake_job_description()
    )

    assert "web search" not in instruction


def test_company_research_block_included_when_present() -> None:
    instruction = build_phase_system_instruction(
        "career_motivation",
        _fake_candidate_profile(),
        _fake_job_description(),
        company_research="Acme Corp recently launched a new product line.",
    )

    assert "web search" in instruction
    assert "Acme Corp recently launched a new product line." in instruction
