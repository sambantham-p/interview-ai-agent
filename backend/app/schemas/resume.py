from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

DATE_FIELD_DESCRIPTION = (
    "Date as YYYY-MM, or YYYY if the resume doesn't state a month. Never "
    "guess a month/day that isn't stated, and never include units, "
    "reasoning, or alternate formats - output only the date string itself."
)


class EducationEntry(BaseModel):
    """One entry per institution/degree. A single date range shown on the
    resume (e.g. "2020 - 2025") is start_date and end_date on this SAME
    entry - never split one range across two separate entries.
    """

    institution: str
    degree: str
    field_of_study: str | None = None
    start_date: str | None = Field(default=None, description=DATE_FIELD_DESCRIPTION)
    end_date: str | None = Field(default=None, description=DATE_FIELD_DESCRIPTION)


class ExperienceEntry(BaseModel):
    """One entry per distinct role/company period. A single date range
    shown on the resume (e.g. "Jan 2021 - Present") is start_date and
    end_date on this SAME entry - never split one range, or duplicate
    the same company/role, across two separate entries.
    """

    company: str
    role: str
    start_date: str | None = Field(default=None, description=DATE_FIELD_DESCRIPTION)
    end_date: str | None = Field(default=None, description=DATE_FIELD_DESCRIPTION)
    description: str | None = None


class ProjectEntry(BaseModel):
    name: str
    description: str | None = None
    tech_stack: list[str] = []


class ResumeExtraction(BaseModel):
    """Structured-output schema for resume parsing - fields must match
    CandidateProfile's JSONB columns, since this is persisted directly.
    """

    education: list[EducationEntry]
    experience: list[ExperienceEntry]
    projects: list[ProjectEntry]
    skills: list[str]
    github_url: str | None


class ResumeUploadResponse(BaseModel):
    """Response DTO for POST /resume/upload - build via
    `model_validate(profile)`, not a hand-built dict.
    """

    model_config = ConfigDict(from_attributes=True)

    id: int
    education: list[EducationEntry]
    experience: list[ExperienceEntry]
    projects: list[ProjectEntry]
    skills: list[str]
    github_url: str | None
    created_at: datetime
