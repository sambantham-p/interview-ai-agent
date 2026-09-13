import pytest
from pytest_mock import MockerFixture

from app.schemas.jd import JobDescriptionExtraction
from app.services.jd_service import (
    JobDescriptionExtractionError,
    parse_and_persist_job_description,
)


def _mock_gemini(mocker: MockerFixture, extracted: JobDescriptionExtraction):
    fake_extract_structured = mocker.patch(
        "app.services.jd_service.extract_structured",
        return_value=extracted,
        new_callable=mocker.AsyncMock,
    )
    mocker.patch(
        "app.services.jd_service.get_settings",
        return_value=mocker.MagicMock(gemini_jd_parsing_model="gemini-3.8-flash"),
    )
    return fake_extract_structured


async def test_parse_and_persist_job_description_builds_and_persists_a_jd(
    mocker: MockerFixture,
) -> None:
    extracted = JobDescriptionExtraction(
        extractable=True,
        role="Backend Engineer",
        seniority="senior",
        tech_stack=["Python", "FastAPI"],
        coding_assessment_expected=True,
    )
    fake_extract_structured = _mock_gemini(mocker, extracted)
    fake_db = mocker.AsyncMock()
    fake_db.add = mocker.MagicMock()

    jd = await parse_and_persist_job_description(
        full_text=(
            "We are hiring a Senior Backend Engineer to design and build "
            "scalable backend services. Requirements include strong Python "
            "and FastAPI experience, PostgreSQL, and AWS."
        ),
        short_description=None,
        db=fake_db,
    )

    assert jd.role == "Backend Engineer"
    assert jd.seniority == "senior"
    assert jd.tech_stack == ["Python", "FastAPI"]
    assert jd.coding_assessment_expected is True
    fake_db.add.assert_called_once_with(jd)
    fake_db.commit.assert_awaited_once()
    fake_db.refresh.assert_awaited_once_with(jd)
    fake_extract_structured.assert_awaited_once()


async def test_parse_and_persist_job_description_uses_short_description_when_given(
    mocker: MockerFixture,
) -> None:
    extracted = JobDescriptionExtraction(
        extractable=True,
        role="AI Engineer",
        seniority="mid",
        tech_stack=["Python", "TensorFlow"],
        coding_assessment_expected=False,
    )
    _mock_gemini(mocker, extracted)
    fake_db = mocker.AsyncMock()
    fake_db.add = mocker.MagicMock()

    jd = await parse_and_persist_job_description(
        full_text=None,
        short_description="AI Engineer, mid-level, Python and TensorFlow",
        db=fake_db,
    )

    assert jd.role == "AI Engineer"


async def test_parse_and_persist_job_description_defaults_coding_assessment_to_false(
    mocker: MockerFixture,
) -> None:
    # extracted.coding_assessment_expected is nullable, the DB column isn't.
    extracted = JobDescriptionExtraction(
        extractable=True,
        role="Product Manager",
        seniority="mid",
        tech_stack=["SQL"],
        coding_assessment_expected=None,
    )
    _mock_gemini(mocker, extracted)
    fake_db = mocker.AsyncMock()
    fake_db.add = mocker.MagicMock()

    jd = await parse_and_persist_job_description(
        full_text=(
            "We are hiring a Product Manager to own the roadmap for our "
            "consumer app, work closely with engineering and design, and "
            "define success metrics using SQL for analysis."
        ),
        short_description=None,
        db=fake_db,
    )

    assert jd.coding_assessment_expected is False


async def test_parse_and_persist_job_description_raises_when_input_is_not_extractable(
    mocker: MockerFixture,
) -> None:
    # extractable=False must stop here - no DB row gets created.
    extracted = JobDescriptionExtraction(
        extractable=False,
        rejection_reason="the text doesn't describe any job role",
    )
    _mock_gemini(mocker, extracted)
    fake_db = mocker.AsyncMock()
    fake_db.add = mocker.MagicMock()

    with pytest.raises(
        JobDescriptionExtractionError, match="doesn't describe any job role"
    ):
        await parse_and_persist_job_description(
            full_text="asdkjaslkdj " * 20, short_description=None, db=fake_db
        )

    fake_db.add.assert_not_called()
    fake_db.commit.assert_not_awaited()


@pytest.mark.parametrize(
    "extracted_kwargs",
    [
        {"role": None},
        {"seniority": None},
        {"tech_stack": []},
    ],
)
async def test_parse_and_persist_job_description_raises_when_a_required_field_is_missing(
    mocker: MockerFixture, extracted_kwargs: dict
) -> None:
    # extractable=True but incomplete must still stop here - a candidate
    # can't proceed to an interview missing role/seniority/tech_stack data.
    base = {
        "extractable": True,
        "role": "Backend Engineer",
        "seniority": "senior",
        "tech_stack": ["Python"],
        "coding_assessment_expected": True,
    }
    extracted = JobDescriptionExtraction(**{**base, **extracted_kwargs})
    _mock_gemini(mocker, extracted)
    fake_db = mocker.AsyncMock()
    fake_db.add = mocker.MagicMock()

    with pytest.raises(JobDescriptionExtractionError, match="Could not determine"):
        await parse_and_persist_job_description(
            full_text="A real job description with plenty of detail " * 3,
            short_description=None,
            db=fake_db,
        )

    fake_db.add.assert_not_called()


async def test_parse_and_persist_job_description_rejects_a_bare_title_as_full_text(
    mocker: MockerFixture,
) -> None:
    # A bare title given as full_text (e.g. "Senior Software Engineer.")
    # must be rejected before ever calling Gemini - not enough content
    # for a real extraction (see MIN_FULL_TEXT_WORD_COUNT).
    fake_extract_structured = mocker.patch(
        "app.services.jd_service.extract_structured", new_callable=mocker.AsyncMock
    )
    fake_db = mocker.AsyncMock()

    with pytest.raises(JobDescriptionExtractionError, match="bare title"):
        await parse_and_persist_job_description(
            full_text="Senior Software Engineer.",
            short_description=None,
            db=fake_db,
        )

    fake_extract_structured.assert_not_awaited()
    fake_db.add.assert_not_called()


async def test_parse_and_persist_job_description_rejects_a_too_short_short_description(
    mocker: MockerFixture,
) -> None:
    # Same guard as full_text, lower bar (see MIN_SHORT_DESCRIPTION_WORD_COUNT).
    fake_extract_structured = mocker.patch(
        "app.services.jd_service.extract_structured", new_callable=mocker.AsyncMock
    )
    fake_db = mocker.AsyncMock()

    with pytest.raises(JobDescriptionExtractionError, match="too short"):
        await parse_and_persist_job_description(
            full_text=None, short_description="Engineer", db=fake_db
        )

    fake_extract_structured.assert_not_awaited()
    fake_db.add.assert_not_called()


async def test_parse_and_persist_job_description_allows_a_short_short_description(
    mocker: MockerFixture,
) -> None:
    # At/above MIN_SHORT_DESCRIPTION_WORD_COUNT with all required fields
    # present must still succeed.
    extracted = JobDescriptionExtraction(
        extractable=True,
        role="AI Engineer",
        seniority="mid",
        tech_stack=["Python"],
        coding_assessment_expected=False,
    )
    _mock_gemini(mocker, extracted)
    fake_db = mocker.AsyncMock()
    fake_db.add = mocker.MagicMock()

    jd = await parse_and_persist_job_description(
        full_text=None, short_description="AI Engineer, mid-level", db=fake_db
    )

    assert jd.role == "AI Engineer"
