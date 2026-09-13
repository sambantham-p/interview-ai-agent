from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, model_validator

SENIORITY_LEVELS = ["intern", "entry", "mid", "senior", "fresher"]


class JobDescriptionInput(BaseModel):
    """Request DTO for POST /jd - exactly one of full_text (a full JD
    paste) or short_description (a short role/target description).
    """

    full_text: str | None = Field(default=None, min_length=1)
    short_description: str | None = Field(default=None, min_length=1)

    @model_validator(mode="after")
    def check_exactly_one_input_mode(self) -> "JobDescriptionInput":
        if bool(self.full_text) == bool(self.short_description):
            raise ValueError("Provide exactly one of full_text or short_description")
        return self


class JobDescriptionExtraction(BaseModel):
    """Structured-output schema for JD extraction.

    extractable=False means the input didn't describe a real job role
    (empty, gibberish, unrelated) - other fields stay empty and
    rejection_reason explains why, so the caller can stop instead of
    persisting fabricated data.
    """

    extractable: bool
    rejection_reason: str | None = None
    role: str | None = Field(
        default=None,
        description=(
            "The job title/role, normalized to a clear job category even if the "
            "posting uses a more specific title. For example, 'SDE II - Payments' "
            "should be normalized to 'Backend Engineer'."
        ),
    )
    seniority: str | None = Field(
        default=None,
        description=f"One of: {', '.join(SENIORITY_LEVELS)}.",
    )
    tech_stack: list[str] = []
    coding_assessment_expected: bool | None = None


class JobDescriptionResponse(BaseModel):
    """Response DTO for POST /jd - build via `model_validate(jd)`, not a
    hand-built dict.
    """

    model_config = ConfigDict(from_attributes=True)

    id: int
    role: str
    seniority: str
    tech_stack: list[str]
    coding_assessment_expected: bool
    created_at: datetime
