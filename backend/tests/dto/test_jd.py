import pytest
from pydantic import ValidationError

from app.dto.jd import JobDescriptionInput


def test_accepts_full_text_alone() -> None:
    payload = JobDescriptionInput(full_text="We are hiring a Senior Backend Engineer")

    assert payload.full_text == "We are hiring a Senior Backend Engineer"
    assert payload.short_description is None


def test_accepts_short_description_alone() -> None:
    payload = JobDescriptionInput(short_description="AI Engineer, mid-level")

    assert payload.short_description == "AI Engineer, mid-level"
    assert payload.full_text is None


def test_rejects_neither_input_mode_given() -> None:
    with pytest.raises(ValidationError):
        JobDescriptionInput()


def test_rejects_both_input_modes_given() -> None:
    with pytest.raises(ValidationError):
        JobDescriptionInput(full_text="full JD text", short_description="short version")


def test_rejects_blank_full_text() -> None:
    with pytest.raises(ValidationError):
        JobDescriptionInput(full_text="")


def _jd_response(**overrides):
    from datetime import UTC, datetime

    from app.dto.jd import JobDescriptionResponse

    data = {
        "id": 1,
        "role": "Backend Engineer",
        "company_name": "Acme",
        "seniority": "mid",
        "tech_stack": ["Python"],
        "coding_assessment_expected": True,
        "created_at": datetime(2026, 1, 1, tzinfo=UTC),
    }
    data.update(overrides)
    return JobDescriptionResponse(**data)


def test_missing_details_flags_an_unstated_company() -> None:
    assert _jd_response(company_name=None).missing_details == ["Company name"]


def test_missing_details_is_empty_when_company_is_named() -> None:
    assert _jd_response().missing_details == []
