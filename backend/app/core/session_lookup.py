from sqlalchemy.ext.asyncio import AsyncSession

from app.models.interview_session import InterviewSession


class InterviewSessionNotFoundError(Exception):
    """Raised when a session_id doesn't correspond to a real interview session."""


async def get_interview_session_or_404(
    session_id: int, db: AsyncSession, *, for_update: bool = False
) -> InterviewSession:
    """Fetch a session by id, or raise `InterviewSessionNotFoundError`.

    `for_update=True` row-locks the session for the rest of the transaction and
    needed by the turn-processing path, where two concurrent turns for the
    same session would otherwise both read the same `github_call_count`
    (or transcript) before either writes it back.
    """
    session = (
        await db.get(InterviewSession, session_id, with_for_update=True)
        if for_update
        else await db.get(InterviewSession, session_id)
    )
    if session is None:
        raise InterviewSessionNotFoundError(
            f"No interview session with id {session_id}"
        )
    return session
