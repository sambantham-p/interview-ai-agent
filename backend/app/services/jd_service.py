from google.genai import types
from sqlalchemy.ext.asyncio import AsyncSession

from app.constants.gemini import GEMINI_JD_EXTRACTION_SEED
from app.constants.jd import MIN_FULL_TEXT_WORD_COUNT, MIN_SHORT_DESCRIPTION_WORD_COUNT
from app.core.config import get_settings
from app.core.gemini_client import extract_structured
from app.models.job_description import JobDescription
from app.schemas.jd import SENIORITY_LEVELS, JobDescriptionExtraction

EXTRACTION_INSTRUCTIONS = (
    "You will be given a job posting - a full job description or a short "
    "free-text role description (e.g. 'AI Engineer, mid-level'). "
    "Set extractable to false if the text is empty, gibberish, doesn't "
    "describe any job role, or doesn't give enough signal to determine "
    "role, seniority, and at least one tech_stack entry - then leave the "
    "other fields at their defaults and set rejection_reason to one plain "
    "sentence. All three of those fields are required for a usable "
    "extraction. "
    "Otherwise extract: role, the job title/category (stated or clearly "
    "implied, e.g. 'AI Engineer', 'Full Stack Developer', 'Backend "
    "Engineer'), normalized to a clear category even if the posting's own "
    "title is more specific; "
    f"seniority, exactly one of {', '.join(SENIORITY_LEVELS)} (infer from "
    "years of experience, title modifiers, or scope described; use "
    "'entry' only with no signal at all); tech_stack, every specific "
    "language/framework/tool named as required or preferred (never "
    "invent one); coding_assessment_expected, true for hands-on "
    "engineering roles or when a coding round is mentioned explicitly, "
    "false otherwise. "
    "Only return information explicitly present or clearly implied - no "
    "reasoning or alternatives in any field."
)

_REQUIRED_FIELDS = ("role", "seniority", "tech_stack")


class JobDescriptionExtractionError(Exception):
    """Raised when Gemini reports the input isn't a real job description
    (extractable=False) - distinct from GeminiResponseParseError, which
    means Gemini's response itself didn't parse.
    """


async def parse_and_persist_job_description(
    *, full_text: str | None, short_description: str | None, db: AsyncSession
) -> JobDescription:
    """Extract a JD via Gemini and persist it as a JobDescription row.

    Raises JobDescriptionExtractionError if the input isn't extractable -
    no row is created, so the candidate can't proceed to an interview
    built on fabricated JD data.
    """
    if full_text is not None and len(full_text.split()) < MIN_FULL_TEXT_WORD_COUNT:
        raise JobDescriptionExtractionError(
            "This looks like a bare title, not a full job description - "
            "add more detail (responsibilities, requirements) or submit it "
            "as short_description instead"
        )
    if (
        short_description is not None
        and len(short_description.split()) < MIN_SHORT_DESCRIPTION_WORD_COUNT
    ):
        raise JobDescriptionExtractionError(
            "short_description is too short to name a role - add a few "
            "more words (e.g. 'AI Engineer, mid-level')"
        )

    input_text = full_text if full_text is not None else short_description
    assert input_text is not None  # nosec B101

    extracted = await extract_structured(
        model=get_settings().gemini_jd_parsing_model,
        contents=[types.Part.from_text(text=input_text)],
        system_instruction=EXTRACTION_INSTRUCTIONS,
        text_format=JobDescriptionExtraction,
        thinking_level="medium",
        seed=GEMINI_JD_EXTRACTION_SEED,
    )

    if not extracted.extractable:
        raise JobDescriptionExtractionError(
            extracted.rejection_reason
            or "Gemini could not determine a job role from this input"
        )

    missing = [f for f in _REQUIRED_FIELDS if not getattr(extracted, f)]
    if missing:
        raise JobDescriptionExtractionError(
            f"Could not determine: {', '.join(missing)} - add more detail "
            "to the job description"
        )

    jd = JobDescription(
        role=extracted.role,
        seniority=extracted.seniority,
        tech_stack=extracted.tech_stack,
        coding_assessment_expected=bool(extracted.coding_assessment_expected),
    )
    db.add(jd)
    await db.commit()
    await db.refresh(jd)
    return jd
