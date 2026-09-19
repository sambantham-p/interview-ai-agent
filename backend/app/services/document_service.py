"""Shared duplicate detection and deletion for the user-owned documents
(resumes and job descriptions).
"""

import hashlib
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.constants.interview import SESSION_STATUS_IN_PROGRESS
from app.models.interview_session import InterviewSession


class DuplicateDocumentError(Exception):
    """Raised when the user already has an identical resume/JD stored."""


class DocumentNotFoundError(Exception):
    """Raised when a document id doesn't exist or belongs to another user."""


class DocumentInUseError(Exception):
    """Raised when deleting a document that past interviews still use."""


def hash_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def hash_text(text: str) -> str:
    """Hash of text ignoring case and whitespace differences, so a
    re-paste that only differs in spacing still counts as identical.
    """
    return hash_bytes(" ".join(text.lower().split()).encode())


async def ensure_not_duplicate(
    model: Any, *, user_id: str, content_hash: str, db: AsyncSession, label: str
) -> None:
    existing_id = await db.scalar(
        select(model.id)
        .where(model.user_id == user_id, model.content_hash == content_hash)
        .limit(1)
    )
    if existing_id is not None:
        raise DuplicateDocumentError(
            f"This {label} has already been uploaded. Pick it from your "
            f"previous {label}s instead of uploading it again."
        )


async def delete_document(
    model: Any,
    session_fk: Any,
    *,
    document_id: int,
    user_id: str,
    db: AsyncSession,
    label: str,
) -> None:
    """Delete a user's document. A document belonging to another user is
    reported as not found, and one used by an in-progress interview is
    refused. Finished interviews don't block the delete: they cascade away
    with the document, along with their evaluations and reports.
    """
    document = await db.get(model, document_id)
    if document is None or document.user_id != user_id:
        raise DocumentNotFoundError(f"No {label} with id {document_id}")

    in_progress_count = await db.scalar(
        select(func.count())
        .select_from(InterviewSession)
        .where(
            session_fk == document_id,
            InterviewSession.status == SESSION_STATUS_IN_PROGRESS,
        )
    )
    if in_progress_count:
        plural = "interview" if in_progress_count == 1 else "interviews"
        raise DocumentInUseError(
            f"This {label} is used by {in_progress_count} in-progress {plural}. "
            "Finish or end it before deleting."
        )

    await db.delete(document)
    await db.commit()
