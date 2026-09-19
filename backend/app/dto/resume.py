from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, computed_field

DATE_FIELD_DESCRIPTION = (
    "The date exactly as written on the resume, character for character "
    "(e.g. 'Sept 2025', '2021', or 'Present'). Do not reformat, expand, "
    "or abbreviate month names, or infer any unstated month or year. "
    "Output only the date text itself, with no reasoning or units."
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
    repo_url: str | None = Field(
        default=None,
        description=(
            "This project's own repository link, if the resume shows one "
            "next to this specific project , distinct from the resume's "
            "general profile-level GitHub link (see github_url below). "
            "None if this project has no repo link of its own."
        ),
    )


RESUME_SECTION_LABELS = {
    "education": "Education",
    "experience": "Work experience",
    "projects": "Projects",
    "skills": "Skills",
    "github_url": "GitHub profile link",
}


def missing_resume_sections(profile: object) -> list[str]:
    """Labels for every section absent from a parsed resume."""
    return [
        label
        for attribute, label in RESUME_SECTION_LABELS.items()
        if not getattr(profile, attribute)
    ]


class ResumeExtraction(BaseModel):
    """Structured-output schema for resume parsing - fields must match
    CandidateProfile's JSONB columns, since this is persisted directly.

    looks_like_resume=False means the document isn't a resume/CV at all,
    so the caller can reject it with rejection_reason instead of saving
    whatever the model scraped out of it.
    """

    looks_like_resume: bool = Field(
        default=True,
        description=(
            "False if this document is not a resume or CV at all (an invoice, "
            "article, form, blank page, random text, another person's "
            "document ). True for any resume, however sparse."
        ),
    )
    rejection_reason: str | None = Field(
        default=None,
        description=(
            "Only when looks_like_resume is false: one plain, friendly "
            "sentence saying what the document appears to be instead."
        ),
    )

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

    @computed_field  # type: ignore[prop-decorator]
    @property
    def missing_sections(self) -> list[str]:
        """Sections the resume didn't contain, so the UI can say so."""
        return missing_resume_sections(self)
