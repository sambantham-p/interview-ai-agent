import pytest
from pydantic import ValidationError

from app.schemas.jd import JobDescriptionInput


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
