from datetime import UTC, datetime

from app.models.candidate_profile import CandidateProfile
from app.schemas.resume import ResumeExtraction, ResumeUploadResponse


def test_resume_upload_response_validates_from_a_candidate_profile_orm_object() -> None:
    # from_attributes=True means this must work straight off an ORM
    # object's attributes, not just a dict - that's the whole point of
    # ResumeUploadResponse.model_validate(profile) in the route.
    profile = CandidateProfile(
        id=1,
        education=[],
        experience=[],
        projects=[],
        skills=["Python", "SQL"],
        github_url="https://github.com/example",
        created_at=datetime(2026, 1, 1, tzinfo=UTC),
    )

    response = ResumeUploadResponse.model_validate(profile)

    assert response.id == 1
    assert response.skills == ["Python", "SQL"]
    assert response.github_url == "https://github.com/example"
    assert response.created_at == datetime(2026, 1, 1, tzinfo=UTC)


def test_resume_upload_response_allows_github_url_to_be_none() -> None:
    profile = CandidateProfile(
        id=2,
        education=[],
        experience=[],
        projects=[],
        skills=[],
        github_url=None,
        created_at=datetime(2026, 1, 1, tzinfo=UTC),
    )

    response = ResumeUploadResponse.model_validate(profile)

    assert response.github_url is None


def test_resume_extraction_schema_tells_gemini_the_date_format() -> None:
    # This is the actual mechanism by which the date-format rule reaches
    # Gemini: model_json_schema() feeds response_format["schema"] in
    # extract_structured() (see gemini_client.py), independent of the
    # prose in EXTRACTION_INSTRUCTIONS. Losing this description would
    # silently reopen the garbled-date bug it was added to fix.
    schema = ResumeExtraction.model_json_schema()
    education_defs = schema["$defs"]["EducationEntry"]["properties"]

    assert "YYYY-MM" in education_defs["start_date"]["description"]


def test_resume_extraction_schema_tells_gemini_not_to_split_one_date_range() -> None:
    # Regression test for a real bug: one "2020 - 2025" range on the
    # resume came back as two separate EducationEntry objects (one per
    # year, each with end_date null) because nothing told the model a
    # range belongs on a single entry. Fixed via the class docstring,
    # which model_json_schema() surfaces as this $defs entry's own
    # "description" - the same channel Field(description=...) uses for
    # per-property rules.
    schema = ResumeExtraction.model_json_schema()
    education_description = schema["$defs"]["EducationEntry"]["description"]
    experience_description = schema["$defs"]["ExperienceEntry"]["description"]

    assert "SAME" in education_description and "never split" in education_description
    assert "SAME" in experience_description and "never split" in experience_description
