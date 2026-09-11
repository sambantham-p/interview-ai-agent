from sqlalchemy.ext.asyncio import AsyncSession

from app.constants.gemini import GEMINI_RESUME_EXTRACTION_SEED
from app.constants.resume import PDF_MIME_TYPE
from app.core.config import get_settings
from app.core.gemini_client import (
    FileInputRequest,
    build_file_input,
    extract_structured,
)
from app.models.candidate_profile import CandidateProfile
from app.schemas.resume import ResumeExtraction

EXTRACTION_INSTRUCTIONS = (
    "Extract structured data from the entire resume. Read all pages and all "
    "content before answering, including every column in multi-column layouts. "
    "Do not stop after the first section, page, or column. "
    "Extract: education history; work experience, including every role and "
    "company listed; projects, including academic and personal projects; "
    "technical skills across all skill categories; and the GitHub profile URL "
    "or GitHub reference if present. "
    "Search the entire document for each category and include every relevant "
    "item. Only leave a section empty if it is genuinely absent from the "
    "resume. "
    "Return only information explicitly present in the resume. Do not infer, "
    "summarize, omit, or add information. Every field value must contain raw "
    "extracted content only, without reasoning, uncertainty, or alternatives."
)


async def parse_and_persist_resume(
    file_bytes: bytes, db: AsyncSession
) -> CandidateProfile:
    """Parse a resume PDF via Gemini structured-output extraction and
    persist it as a new CandidateProfile row.
    """
    extracted = await extract_structured(
        model=get_settings().gemini_resume_parsing_model,
        contents=build_file_input(
            FileInputRequest(
                file_bytes=file_bytes,
                mime_type=PDF_MIME_TYPE,
                resolution="high",
            )
        ),
        system_instruction=EXTRACTION_INSTRUCTIONS,
        text_format=ResumeExtraction,
        thinking_level="high",
        seed=GEMINI_RESUME_EXTRACTION_SEED,
    )

    profile = CandidateProfile(
        education=[entry.model_dump() for entry in extracted.education],
        experience=[entry.model_dump() for entry in extracted.experience],
        projects=[entry.model_dump() for entry in extracted.projects],
        skills=extracted.skills,
        github_url=extracted.github_url,
    )
    db.add(profile)
    await db.commit()
    await db.refresh(profile)
    return profile
