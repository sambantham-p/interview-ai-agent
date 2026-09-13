from sqlalchemy.ext.asyncio import AsyncSession

from app.models.interview_session import InterviewSession


class InterviewSessionNotFoundError(Exception):
    """Raised when a session_id doesn't correspond to a real interview session."""


async def get_interview_session_or_404(
    session_id: int, db: AsyncSession
) -> InterviewSession:
    session = await db.get(InterviewSession, session_id)
    if session is None:
        raise InterviewSessionNotFoundError(
            f"No interview session with id {session_id}"
        )
    return session
