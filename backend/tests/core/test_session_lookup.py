import pytest
from pytest_mock import MockerFixture

from app.core.session_lookup import (
    InterviewSessionNotFoundError,
    get_interview_session_or_404,
)
from app.models.interview_session import InterviewSession


def _db_returning(mocker: MockerFixture, session: InterviewSession | None):
    db = mocker.MagicMock()
    db.get = mocker.AsyncMock(return_value=session)
    return db


async def test_for_update_takes_a_key_share_lock_that_does_not_block_llm_call_logging(
    mocker: MockerFixture,
) -> None:
    """The LLM Gateway logs each call on its own connection while a turn's
    transaction holds this lock; a plain FOR UPDATE would block that log
    row's foreign-key check and deadlock the turn against itself.
    """
    session = InterviewSession(id=1, user_id="usr_a")
    db = _db_returning(mocker, session)

    await get_interview_session_or_404(1, db, user_id="usr_a", for_update=True)

    assert db.get.call_args.kwargs["with_for_update"] == {"key_share": True}


async def test_without_for_update_no_row_lock_is_taken(mocker: MockerFixture) -> None:
    db = _db_returning(mocker, InterviewSession(id=1, user_id="usr_a"))

    await get_interview_session_or_404(1, db, user_id="usr_a")

    assert "with_for_update" not in db.get.call_args.kwargs


async def test_another_users_session_reads_as_not_found(mocker: MockerFixture) -> None:
    db = _db_returning(mocker, InterviewSession(id=1, user_id="usr_a"))

    with pytest.raises(InterviewSessionNotFoundError):
        await get_interview_session_or_404(1, db, user_id="usr_b")
