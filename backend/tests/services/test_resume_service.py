from pytest_mock import MockerFixture

from app.schemas.resume import (
    EducationEntry,
    ExperienceEntry,
    ProjectEntry,
    ResumeExtraction,
)
from app.services.resume_service import parse_and_persist_resume


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
        "app.services.resume_service.get_settings",
        return_value=mocker.MagicMock(gemini_resume_parsing_model="gemini-3.8-flash"),
    )
    fake_db = mocker.AsyncMock()
    # AsyncSession.add() is sync, unlike commit/refresh
    fake_db.add = mocker.MagicMock()

    profile = await parse_and_persist_resume(b"pdf bytes", fake_db)

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
        {"name": "Widget", "description": None, "tech_stack": ["Python"]}
    ]
    fake_db.add.assert_called_once_with(profile)
    fake_db.commit.assert_awaited_once()
    fake_db.refresh.assert_awaited_once_with(profile)
    fake_extract_structured.assert_awaited_once()
