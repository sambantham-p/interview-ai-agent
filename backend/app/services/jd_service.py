from google.genai import types
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.constants.gemini import GEMINI_JD_EXTRACTION_SEED
from app.constants.jd import MIN_FULL_TEXT_WORD_COUNT, MIN_SHORT_DESCRIPTION_WORD_COUNT
from app.core.config import get_gemini_settings
from app.core.gemini_client import extract_structured
from app.dto.jd import SENIORITY_LEVELS, JobDescriptionExtraction
from app.models.job_description import JobDescription
from app.services.document_service import ensure_not_duplicate, hash_text

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
    "title is more specific; company_name, the hiring company's name if "
    "stated (leave it null if not named - this field is always optional "
    "and never affects extractable); "
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

_MISSING_FIELD_HINTS = {
    "role": 'the job title (e.g. "Backend Engineer")',
    "seniority": "the experience level (e.g. intern, entry, mid, senior)",
    "tech_stack": "at least one required technology or skill",
}


class JobDescriptionExtractionError(Exception):
    """Raised when Gemini reports the input isn't a real job description
    (extractable=False) - distinct from GeminiResponseParseError, which
    means Gemini's response itself didn't parse.
    """


async def parse_and_persist_job_description(
    *,
    full_text: str | None,
    short_description: str | None,
    db: AsyncSession,
    user_id: str,
) -> JobDescription:
    """Extract a JD via Gemini and persist it as a JobDescription row.

    Raises DuplicateDocumentError, before any Gemini call, if this user
    already submitted the same text.

    Raises JobDescriptionExtractionError if the input isn't extractable -
    no row is created, so the candidate can't proceed to an interview
    built on fabricated JD data.
    """
    if full_text is not None and len(full_text.split()) < MIN_FULL_TEXT_WORD_COUNT:
        raise JobDescriptionExtractionError(
            "This is too short to be a full job description. Paste the whole "
            "posting (responsibilities, requirements, tech stack), or switch "
            'to "Short description" and name the role, e.g. "AI Engineer, '
            'mid-level, Python".'
        )
    if (
        short_description is not None
        and len(short_description.split()) < MIN_SHORT_DESCRIPTION_WORD_COUNT
    ):
        raise JobDescriptionExtractionError(
            "That's too short to identify a role. Add a few more words, e.g. "
            '"AI Engineer, mid-level, Python".'
        )

    input_text = full_text if full_text is not None else short_description
    assert input_text is not None  # nosec B101

    content_hash = hash_text(input_text)
    await ensure_not_duplicate(
        JobDescription,
        user_id=user_id,
        content_hash=content_hash,
        db=db,
        label="job description",
    )

    extracted = await extract_structured(
        model=get_gemini_settings().gemini_jd_parsing_model,
        contents=[types.Part.from_text(text=input_text)],
        system_instruction=EXTRACTION_INSTRUCTIONS,
        text_format=JobDescriptionExtraction,
        thinking_level="medium",
        seed=GEMINI_JD_EXTRACTION_SEED,
    )

    if not extracted.extractable:
        reason = (
            extracted.rejection_reason.rstrip(".")
            if extracted.rejection_reason
            else "no job role could be identified in it"
        )
        raise JobDescriptionExtractionError(
            f"This doesn't look like a job description: {reason}. Please "
            "paste a job posting, or describe the role you're targeting."
        )

    missing = [f for f in _REQUIRED_FIELDS if not getattr(extracted, f)]
    if missing:
        needed = "; ".join(_MISSING_FIELD_HINTS[f] for f in missing)
        raise JobDescriptionExtractionError(
            f"This job description is missing details we need: {needed}. "
            "Please add them and try again."
        )

    if extracted.seniority not in SENIORITY_LEVELS:
        raise JobDescriptionExtractionError(
            "We couldn't map the experience level in this posting to one of: "
            f"{', '.join(SENIORITY_LEVELS)}. Please state it more plainly, "
            'e.g. "senior" or "2 years of experience".'
        )

    jd = JobDescription(
        user_id=user_id,
        role=extracted.role,
        company_name=extracted.company_name,
        seniority=extracted.seniority,
        tech_stack=extracted.tech_stack,
        coding_assessment_expected=bool(extracted.coding_assessment_expected),
        content_hash=content_hash,
    )
    db.add(jd)
    await db.commit()
    await db.refresh(jd)
    return jd


async def list_job_descriptions(user_id: str, db: AsyncSession) -> list[JobDescription]:
    """Every job description the given user has submitted, newest first.

    job_descriptions is insert-only , so this is a plain history list,
    not a "current JD" lookup.
    """
    result = await db.execute(
        select(JobDescription)
        .where(JobDescription.user_id == user_id)
        .order_by(JobDescription.created_at.desc())
    )
    return list(result.scalars().all())
