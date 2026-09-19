from google.genai import types
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.constants.gemini import GEMINI_RESUME_EXTRACTION_SEED
from app.constants.resume import PDF_MIME_TYPE
from app.core.config import get_gemini_settings
from app.core.gemini_client import (
    FileInputRequest,
    build_file_input,
    extract_structured,
)
from app.core.pdf_links import (
    extract_pdf_link_targets,
    find_github_profile_url,
    is_github_profile_url,
)
from app.dto.resume import ResumeExtraction
from app.models.candidate_profile import CandidateProfile
from app.services.document_service import ensure_not_duplicate, hash_bytes


class ResumeExtractionError(Exception):
    """Raised when Gemini extracted nothing usable from the resume -
    distinct from GeminiResponseParseError, which means the response
    itself didn't parse.
    """


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
    "For every hyperlink, extract its actual target URL, not its visible "
    "display text. If the display text is needed for context, derive it "
    "from the URL where possible. If a URL is written as plain text rather "
    "than a hyperlink, extract it directly. Apply this to all links, "
    "including GitHub, LinkedIn, portfolios, projects, and websites. For "
    "example, if the display text is 'GitHub' but the target is "
    "'https://github.com/username/project', extract the target URL and use "
    "the URL to identify the relevant username or project when needed. "
    "Each project may have its own repository link shown directly next to "
    "it, separate from the resume's general profile-level GitHub link - "
    "extract that as the project's own repo_url when present, and leave it "
    "empty for a project with no link of its own. Do not use the "
    "profile-level GitHub link as a project's repo_url unless the resume "
    "itself points that specific project at it. "
    "Return only information explicitly present in the resume. Do not infer, "
    "summarize, omit, or add information. Every field value must contain raw "
    "extracted content only, without reasoning, uncertainty, or alternatives."
)


async def parse_and_persist_resume(
    file_bytes: bytes, db: AsyncSession, *, user_id: str
) -> CandidateProfile:
    """Parse a resume PDF via Gemini structured-output extraction and
    persist it as a new CandidateProfile row.

    Raises DuplicateDocumentError, before any Gemini call, if this exact
    file was already uploaded by this user.

    Raises ResumeExtractionError, with a reason the user can act on, if the
    file isn't a resume or nothing usable was extracted - no row is created, so the candidate can't proceed to an interview built on
    an empty profile (mirrors parse_and_persist_job_description's
    required-fields check in app/services/jd_service.py).
    """
    content_hash = hash_bytes(file_bytes)
    await ensure_not_duplicate(
        CandidateProfile,
        user_id=user_id,
        content_hash=content_hash,
        db=db,
        label="resume",
    )

    link_targets = extract_pdf_link_targets(file_bytes)
    contents = build_file_input(
        FileInputRequest(
            file_bytes=file_bytes,
            mime_type=PDF_MIME_TYPE,
            resolution="high",
        )
    )
    if link_targets:
        links_block = "\n".join(f"- {url}" for url in link_targets)
        contents.append(
            types.Part.from_text(
                text=(
                    "Hyperlink targets embedded in this PDF (the visible link "
                    "text on the page may differ from these). Use them as the "
                    "authoritative URLs for the GitHub profile and each "
                    f"project's repository link:\n{links_block}"
                )
            )
        )

    extracted = await extract_structured(
        model=get_gemini_settings().gemini_resume_parsing_model,
        contents=contents,
        system_instruction=EXTRACTION_INSTRUCTIONS,
        text_format=ResumeExtraction,
        thinking_level="medium",
        seed=GEMINI_RESUME_EXTRACTION_SEED,
    )

    if not extracted.looks_like_resume:
        detail = (
            f" It looks like {extracted.rejection_reason.rstrip('.')}."
            if extracted.rejection_reason
            else ""
        )
        raise ResumeExtractionError(
            f"This doesn't look like a resume.{detail} Please upload your "
            "own resume as a PDF."
        )

    if not (
        extracted.education
        or extracted.experience
        or extracted.projects
        or extracted.skills
    ):
        raise ResumeExtractionError(
            "We couldn't find any education, work experience, projects or "
            "skills in this file. It may be blank, a scanned image with no "
            "selectable text, or not a resume. Please upload a text-based "
            "PDF of your resume."
        )

    # The PDF's own link targets are authoritative. The model's value is
    # only used when the PDF has no GitHub link (a URL typed out as plain
    # text), and only if it is a real profile URL, never a link label.
    github_url = find_github_profile_url(link_targets)
    if github_url is None and is_github_profile_url(extracted.github_url):
        github_url = extracted.github_url

    profile = CandidateProfile(
        user_id=user_id,
        education=[entry.model_dump() for entry in extracted.education],
        experience=[entry.model_dump() for entry in extracted.experience],
        projects=[entry.model_dump() for entry in extracted.projects],
        skills=extracted.skills,
        github_url=github_url,
        content_hash=content_hash,
    )
    db.add(profile)
    await db.commit()
    await db.refresh(profile)
    return profile


async def list_resumes(user_id: str, db: AsyncSession) -> list[CandidateProfile]:
    """Every resume the given user has uploaded, newest first.

    candidate_profiles is insert-only , so this is a plain history list,
    not a "current resume" lookup.
    """
    result = await db.execute(
        select(CandidateProfile)
        .where(CandidateProfile.user_id == user_id)
        .order_by(CandidateProfile.created_at.desc())
    )
    return list(result.scalars().all())
