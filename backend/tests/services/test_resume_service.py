import pytest
from pytest_mock import MockerFixture

from app.schemas.resume import (
    EducationEntry,
    ExperienceEntry,
    ProjectEntry,
    ResumeExtraction,
)
from app.services.resume_service import (
    ResumeExtractionError,
    parse_and_persist_resume,
)


async def test_parse_and_persist_resume_builds_and_persists_a_candidate_profile(
    mocker: MockerFixture,
) -> None:
    extracted = ResumeExtraction(
        education=[EducationEntry(institution="MIT", degree="BS", field_of_study="CS")],
        experience=[ExperienceEntry(company="Acme", role="Engineer")],
        projects=[ProjectEntry(name="Widget", tech_stack=["Python"])],
        skills=["Python", "SQL"],
        github_url="https://github.com/example",
    )
    fake_extract_structured = mocker.patch(
        "app.services.resume_service.extract_structured",
        return_value=extracted,
        new_callable=mocker.AsyncMock,
    )
    mocker.patch(
        "app.services.resume_service.get_gemini_settings",
        return_value=mocker.MagicMock(gemini_resume_parsing_model="gemini-3.8-flash"),
    )
    fake_db = mocker.AsyncMock()
    # AsyncSession.add() is sync, unlike commit/refresh
    fake_db.add = mocker.MagicMock()

    profile = await parse_and_persist_resume(
        b"pdf bytes", fake_db, user_id="usr_test123"
    )

    assert profile.user_id == "usr_test123"
    assert profile.skills == ["Python", "SQL"]
    assert profile.github_url == "https://github.com/example"
    assert profile.education == [
        {
            "institution": "MIT",
            "degree": "BS",
            "field_of_study": "CS",
            "start_date": None,
            "end_date": None,
        }
    ]
    assert profile.projects == [
        {
            "name": "Widget",
            "description": None,
            "tech_stack": ["Python"],
            "repo_url": None,
        }
    ]
    fake_db.add.assert_called_once_with(profile)
    fake_db.commit.assert_awaited_once()
    fake_db.refresh.assert_awaited_once_with(profile)
    fake_extract_structured.assert_awaited_once()


def _mock_extraction(mocker: MockerFixture, extracted: ResumeExtraction):
    mocker.patch(
        "app.services.resume_service.extract_structured",
        return_value=extracted,
        new_callable=mocker.AsyncMock,
    )
    mocker.patch(
        "app.services.resume_service.get_gemini_settings",
        return_value=mocker.MagicMock(gemini_resume_parsing_model="gemini-3.8-flash"),
    )


async def test_parse_and_persist_resume_rejects_a_completely_empty_extraction(
    mocker: MockerFixture,
) -> None:
    # Mirrors parse_and_persist_job_description's required-fields check -
    # a "successful" Gemini call that extracted nothing usable (blank or
    # image-only PDF) must not persist an empty CandidateProfile row.
    extracted = ResumeExtraction(
        education=[], experience=[], projects=[], skills=[], github_url=None
    )
    _mock_extraction(mocker, extracted)
    fake_db = mocker.AsyncMock()
    fake_db.add = mocker.MagicMock()

    with pytest.raises(ResumeExtractionError, match="Could not extract"):
        await parse_and_persist_resume(b"pdf bytes", fake_db, user_id="usr_test123")

    fake_db.add.assert_not_called()
    fake_db.commit.assert_not_awaited()


async def test_parse_and_persist_resume_accepts_a_sparse_but_non_empty_extraction(
    mocker: MockerFixture,
) -> None:
    # Only one non-empty field is enough - this isn't a "how complete is
    # the resume" quality bar, just a "was anything real extracted" bar.
    extracted = ResumeExtraction(
        education=[], experience=[], projects=[], skills=["Python"], github_url=None
    )
    _mock_extraction(mocker, extracted)
    fake_db = mocker.AsyncMock()
    fake_db.add = mocker.MagicMock()

    profile = await parse_and_persist_resume(
        b"pdf bytes", fake_db, user_id="usr_test123"
    )

    assert profile.skills == ["Python"]
    fake_db.add.assert_called_once_with(profile)
