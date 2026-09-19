import pytest
from pytest_mock import MockerFixture

from app.dto.resume import (
    EducationEntry,
    ExperienceEntry,
    ProjectEntry,
    ResumeExtraction,
)
from app.models.candidate_profile import CandidateProfile
from app.services.resume_service import (
    ResumeExtractionError,
    list_resumes,
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
    fake_db.scalar.return_value = None

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
    fake_db.scalar.return_value = None

    with pytest.raises(ResumeExtractionError, match="couldn't find any education"):
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
    fake_db.scalar.return_value = None

    profile = await parse_and_persist_resume(
        b"pdf bytes", fake_db, user_id="usr_test123"
    )

    assert profile.skills == ["Python"]
    fake_db.add.assert_called_once_with(profile)


def _mock_db_with_profiles(mocker: MockerFixture, profiles: list[CandidateProfile]):
    fake_result = mocker.MagicMock()
    fake_result.scalars.return_value.all.return_value = profiles
    fake_db = mocker.AsyncMock()
    fake_db.execute = mocker.AsyncMock(return_value=fake_result)
    return fake_db


async def test_list_resumes_returns_profiles_for_the_given_user(
    mocker: MockerFixture,
) -> None:
    profiles = [
        CandidateProfile(
            id=1,
            user_id="usr_a",
            education=[],
            experience=[],
            projects=[],
            skills=[],
        ),
    ]
    fake_db = _mock_db_with_profiles(mocker, profiles)

    result = await list_resumes("usr_a", fake_db)

    assert result == profiles
    fake_db.execute.assert_awaited_once()


async def test_list_resumes_returns_empty_list_when_user_has_none(
    mocker: MockerFixture,
) -> None:
    fake_db = _mock_db_with_profiles(mocker, [])

    result = await list_resumes("usr_a", fake_db)

    assert result == []


async def test_parse_and_persist_resume_rejects_a_duplicate_before_calling_gemini(
    mocker: MockerFixture,
) -> None:
    from app.services.document_service import DuplicateDocumentError

    fake_extract = mocker.patch(
        "app.services.resume_service.extract_structured",
        new_callable=mocker.AsyncMock,
    )
    fake_db = mocker.AsyncMock()
    fake_db.scalar.return_value = 1

    with pytest.raises(DuplicateDocumentError):
        await parse_and_persist_resume(b"pdf bytes", fake_db, user_id="usr_test123")

    fake_extract.assert_not_called()


def _persist_with_links(mocker: MockerFixture, *, github_url, links):
    extracted = ResumeExtraction(
        education=[],
        experience=[],
        projects=[],
        skills=["Python"],
        github_url=github_url,
    )
    fake_extract = mocker.patch(
        "app.services.resume_service.extract_structured",
        return_value=extracted,
        new_callable=mocker.AsyncMock,
    )
    mocker.patch(
        "app.services.resume_service.get_gemini_settings",
        return_value=mocker.MagicMock(gemini_resume_parsing_model="m"),
    )
    mocker.patch(
        "app.services.resume_service.extract_pdf_link_targets", return_value=links
    )
    fake_db = mocker.AsyncMock()
    fake_db.add = mocker.MagicMock()
    fake_db.scalar.return_value = None
    return fake_extract, fake_db


async def test_resume_upload_stores_the_github_url_from_the_pdf_links(
    mocker: MockerFixture,
) -> None:
    _, fake_db = _persist_with_links(
        mocker, github_url="github.com", links=["https://github.com/sam"]
    )

    profile = await parse_and_persist_resume(b"pdf", fake_db, user_id="u")

    assert profile.github_url == "https://github.com/sam"


async def test_resume_upload_prefers_the_pdf_link_over_the_models_url(
    mocker: MockerFixture,
) -> None:
    _, fake_db = _persist_with_links(
        mocker,
        github_url="https://github.com/from-llm",
        links=["https://github.com/from-pdf"],
    )

    profile = await parse_and_persist_resume(b"pdf", fake_db, user_id="u")

    assert profile.github_url == "https://github.com/from-pdf"


async def test_resume_upload_uses_a_valid_model_url_when_pdf_has_no_github_link(
    mocker: MockerFixture,
) -> None:
    _, fake_db = _persist_with_links(
        mocker, github_url="https://github.com/typed-out", links=[]
    )

    profile = await parse_and_persist_resume(b"pdf", fake_db, user_id="u")

    assert profile.github_url == "https://github.com/typed-out"


async def test_resume_upload_never_stores_a_bare_link_label(
    mocker: MockerFixture,
) -> None:
    _, fake_db = _persist_with_links(mocker, github_url="github.com", links=[])

    profile = await parse_and_persist_resume(b"pdf", fake_db, user_id="u")

    assert profile.github_url is None


async def test_resume_upload_sends_embedded_links_to_gemini(
    mocker: MockerFixture,
) -> None:
    fake_extract, fake_db = _persist_with_links(
        mocker, github_url=None, links=["https://github.com/sam/project"]
    )

    await parse_and_persist_resume(b"pdf", fake_db, user_id="u")

    parts = fake_extract.call_args.kwargs["contents"]
    assert len(parts) == 2
    assert "https://github.com/sam/project" in parts[1].text


async def test_resume_upload_sends_no_link_block_when_pdf_has_none(
    mocker: MockerFixture,
) -> None:
    fake_extract, fake_db = _persist_with_links(mocker, github_url=None, links=[])

    await parse_and_persist_resume(b"pdf", fake_db, user_id="u")

    assert len(fake_extract.call_args.kwargs["contents"]) == 1


async def test_parse_and_persist_resume_rejects_a_non_resume_with_a_friendly_reason(
    mocker: MockerFixture,
) -> None:
    extracted = ResumeExtraction(
        looks_like_resume=False,
        rejection_reason="an electricity bill.",
        education=[],
        experience=[],
        projects=[],
        skills=["Python"],  # junk scraped from a non-resume must not save it
        github_url=None,
    )
    _mock_extraction(mocker, extracted)
    fake_db = mocker.AsyncMock()
    fake_db.add = mocker.MagicMock()
    fake_db.scalar.return_value = None

    with pytest.raises(ResumeExtractionError) as exc_info:
        await parse_and_persist_resume(b"pdf", fake_db, user_id="u")

    message = str(exc_info.value)
    assert "doesn't look like a resume" in message
    assert "electricity bill" in message
    assert ".." not in message
    fake_db.add.assert_not_called()


async def test_parse_and_persist_resume_rejects_a_non_resume_without_a_reason(
    mocker: MockerFixture,
) -> None:
    extracted = ResumeExtraction(
        looks_like_resume=False,
        education=[],
        experience=[],
        projects=[],
        skills=[],
        github_url=None,
    )
    _mock_extraction(mocker, extracted)
    fake_db = mocker.AsyncMock()
    fake_db.scalar.return_value = None

    with pytest.raises(ResumeExtractionError, match="Please upload your own resume"):
        await parse_and_persist_resume(b"pdf", fake_db, user_id="u")
