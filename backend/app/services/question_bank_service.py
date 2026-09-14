from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.constants.question_bank import QUESTION_POOL_TOP_K
from app.core.embeddings import embed_text
from app.models.job_description import JobDescription
from app.models.technical_question import TechnicalQuestion


async def prefetch_question_pool(
    *,
    job_description: JobDescription,
    db: AsyncSession,
    top_k: int = QUESTION_POOL_TOP_K,
) -> list[dict]:
    """Retrieves the top-k technical questions semantically matching this
    JD's role/seniority/tech stack, for a single prefetch at
    start_interview time (see RAG Architecture in CLAUDE.md: no
    background top-up, no live per-question search on a live turn).

    Returns [] when the bank is empty or nothing matches well enough to
    be useful - never raises just because the bank is thin for a given
    JD, so an empty/early-stage bank degrades to Stage 2's original
    free-generation behavior rather than breaking the interview.
    """
    query_text = (
        f"{job_description.role} {job_description.seniority} "
        f"{' '.join(job_description.tech_stack)}"
    )
    query_embedding = await embed_text(query_text)

    result = await db.execute(
        select(TechnicalQuestion)
        .order_by(TechnicalQuestion.embedding.cosine_distance(query_embedding))
        .limit(top_k)
    )
    questions = result.scalars().all()

    return [
        {
            "id": question.id,
            "question_text": question.question_text,
            "topic": question.topic,
            "difficulty": question.difficulty,
        }
        for question in questions
    ]
