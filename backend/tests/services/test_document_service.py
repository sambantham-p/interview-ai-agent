import re

import pytest
from pytest_mock import MockerFixture

from app.models.candidate_profile import CandidateProfile
from app.models.interview_session import InterviewSession
from app.services.document_service import (
    DocumentInUseError,
    DocumentNotFoundError,
    DuplicateDocumentError,
    delete_document,
    ensure_not_duplicate,
    hash_bytes,
    hash_text,
)


def test_hash_text_ignores_case_and_whitespace() -> None:
    assert hash_text("Backend  Engineer\nPython") == hash_text(
        "backend engineer python"
    )
    assert hash_text("backend engineer") != hash_text("frontend engineer")


def test_hash_bytes_is_stable() -> None:
    assert hash_bytes(b"abc") == hash_bytes(b"abc")
    assert hash_bytes(b"abc") != hash_bytes(b"abd")


async def test_ensure_not_duplicate_raises_readable_error_when_hash_exists(
    mocker: MockerFixture,
) -> None:
    db = mocker.AsyncMock()
    db.scalar.return_value = 5

    with pytest.raises(DuplicateDocumentError, match="already been uploaded"):
        await ensure_not_duplicate(
            CandidateProfile, user_id="u", content_hash="h", db=db, label="resume"
        )


async def test_ensure_not_duplicate_passes_when_hash_is_new(
    mocker: MockerFixture,
) -> None:
    db = mocker.AsyncMock()
    db.scalar.return_value = None

    await ensure_not_duplicate(
        CandidateProfile, user_id="u", content_hash="h", db=db, label="resume"
    )


async def _delete(db, **overrides):
    kwargs = {
        "document_id": 3,
        "user_id": "u",
        "db": db,
        "label": "resume",
    }
    kwargs.update(overrides)
    await delete_document(
        CandidateProfile, InterviewSession.candidate_profile_id, **kwargs
    )


async def test_delete_document_deletes_an_unused_document(
    mocker: MockerFixture,
) -> None:
    db = mocker.AsyncMock()
    db.get.return_value = CandidateProfile(id=3, user_id="u")
    db.scalar.return_value = 0

    await _delete(db)

    db.delete.assert_awaited_once()
    db.commit.assert_awaited_once()


@pytest.mark.parametrize("found", [None, CandidateProfile(id=3, user_id="other")])
async def test_delete_document_treats_missing_or_foreign_as_not_found(
    mocker: MockerFixture, found
) -> None:
    db = mocker.AsyncMock()
    db.get.return_value = found

    with pytest.raises(DocumentNotFoundError):
        await _delete(db)

    db.delete.assert_not_called()


@pytest.mark.parametrize(
    ("count", "word"),
    [(1, "1 in-progress interview."), (2, "2 in-progress interviews.")],
)
async def test_delete_document_refuses_when_in_progress_interviews_use_it(
    mocker: MockerFixture, count: int, word: str
) -> None:
    db = mocker.AsyncMock()
    db.get.return_value = CandidateProfile(id=3, user_id="u")
    db.scalar.return_value = count

    with pytest.raises(DocumentInUseError, match=re.escape(word)):
        await _delete(db)

    db.delete.assert_not_called()
