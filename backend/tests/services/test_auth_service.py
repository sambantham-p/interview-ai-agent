from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest
from pytest_mock import MockerFixture

from app.core.security import create_password_reset_token, hash_password
from app.models.email_otp import EmailOTP
from app.models.password_reset_otp import PasswordResetOTP
from app.models.user import User
from app.services import auth_service


async def test_verify_google_token_provider_unreachable(mocker: MockerFixture) -> None:
    mocker.patch(
        "app.services.auth_service.httpx.AsyncClient.get",
        AsyncMock(side_effect=httpx.ConnectError("boom")),
    )

    with pytest.raises(auth_service.GoogleAuthProviderError):
        await auth_service.verify_google_token("real-token")


async def test_verify_google_token_rejected_by_tokeninfo(mocker: MockerFixture) -> None:
    mocker.patch(
        "app.services.auth_service.httpx.AsyncClient.get",
        AsyncMock(
            return_value=MagicMock(status_code=400, text="invalid_token", json=dict)
        ),
    )

    with pytest.raises(
        auth_service.GoogleTokenInvalidError, match="Invalid or expired"
    ):
        await auth_service.verify_google_token("bad-token")


def _mock_tokeninfo_response(mocker: MockerFixture, payload: dict) -> None:
    mocker.patch(
        "app.services.auth_service.httpx.AsyncClient.get",
        AsyncMock(
            return_value=MagicMock(
                status_code=200, json=lambda: payload, text="", headers={}
            )
        ),
    )


def _valid_tokeninfo_payload(**overrides) -> dict:
    defaults = {
        "sub": "real-sub-123",
        "email": "real@prepwise.ai",
        "name": "Real User",
        "picture": "https://pic.url",
        "aud": "test-client-id.apps.googleusercontent.com",
        "iss": "https://accounts.google.com",
        "email_verified": "true",
    }
    defaults.update(overrides)
    return defaults


async def test_verify_google_token_real_token_success(mocker: MockerFixture) -> None:
    _mock_tokeninfo_response(mocker, _valid_tokeninfo_payload())

    result = await auth_service.verify_google_token("a-real-id-token")

    assert result == {
        "sub": "real-sub-123",
        "email": "real@prepwise.ai",
        "name": "Real User",
        "picture": "https://pic.url",
    }


async def test_verify_google_token_rejects_wrong_audience(
    mocker: MockerFixture,
) -> None:
    _mock_tokeninfo_response(
        mocker,
        _valid_tokeninfo_payload(aud="some-other-app.apps.googleusercontent.com"),
    )

    with pytest.raises(auth_service.GoogleTokenInvalidError, match="not issued"):
        await auth_service.verify_google_token("a-real-id-token")


async def test_verify_google_token_rejects_unexpected_issuer(
    mocker: MockerFixture,
) -> None:
    _mock_tokeninfo_response(
        mocker, _valid_tokeninfo_payload(iss="https://evil.example")
    )

    with pytest.raises(auth_service.GoogleTokenInvalidError, match="issuer"):
        await auth_service.verify_google_token("a-real-id-token")


async def test_verify_google_token_rejects_unverified_email(
    mocker: MockerFixture,
) -> None:
    _mock_tokeninfo_response(mocker, _valid_tokeninfo_payload(email_verified="false"))

    with pytest.raises(auth_service.GoogleTokenInvalidError, match="not verified"):
        await auth_service.verify_google_token("a-real-id-token")


async def test_authenticate_or_create_google_user_new() -> None:
    session = AsyncMock()
    exec_result = MagicMock()
    exec_result.scalar_one_or_none.return_value = None
    session.execute.return_value = exec_result

    user = await auth_service.authenticate_or_create_google_user(
        session=session,
        google_id="gid-123",
        email="new@prepwise.ai",
        name="New User",
        picture="https://pic.url",
    )
    assert user.google_id == "gid-123"
    assert user.email == "new@prepwise.ai"
    assert user.name == "New User"
    assert user.is_verified is True
    session.add.assert_called_once()
    session.commit.assert_called_once()


async def test_authenticate_or_create_google_user_existing() -> None:
    session = AsyncMock()
    existing = User(
        id="usr_gid-123",
        google_id="gid-123",
        email="existing@prepwise.ai",
        name="Old Name",
        is_verified=True,
    )
    exec_result = MagicMock()
    exec_result.scalar_one_or_none.return_value = existing
    session.execute.return_value = exec_result

    user = await auth_service.authenticate_or_create_google_user(
        session=session,
        google_id="gid-123",
        email="existing@prepwise.ai",
        name="Updated Name",
        picture="https://new.url",
    )
    assert user.name == "Updated Name"
    assert user.picture == "https://new.url"
    session.commit.assert_called_once()


async def test_authenticate_or_create_google_user_refuses_to_link_by_email() -> None:
    session = AsyncMock()
    no_google_match = MagicMock()
    no_google_match.scalar_one_or_none.return_value = None
    existing_email_user = MagicMock()
    existing_email_user.scalar_one_or_none.return_value = User(
        id="usr_existing",
        email="taken@prepwise.ai",
        name="Existing",
        password_hash="some_hash",
        is_verified=True,
    )
    session.execute.side_effect = [no_google_match, existing_email_user]

    with pytest.raises(auth_service.GoogleAccountLinkingRequiredError):
        await auth_service.authenticate_or_create_google_user(
            session=session,
            google_id="new-google-id",
            email="taken@prepwise.ai",
            name="Attacker-controlled name",
            picture=None,
        )
    session.add.assert_not_called()
    session.commit.assert_not_called()


async def test_create_pending_registration_existing_verified_user_fails() -> None:
    session = AsyncMock()
    existing = User(
        id="usr_123", email="taken@prepwise.ai", name="Taken", is_verified=True
    )
    exec_result = MagicMock()
    exec_result.scalar_one_or_none.return_value = existing
    session.execute.return_value = exec_result

    with pytest.raises(auth_service.EmailAlreadyRegisteredError):
        await auth_service.create_pending_registration(
            session=session,
            email="taken@prepwise.ai",
            name="Taken",
            password="StrongPass#2026",
        )


async def test_create_pending_registration_weak_password_fails() -> None:
    session = AsyncMock()
    exec_result = MagicMock()
    exec_result.scalar_one_or_none.return_value = None
    session.execute.return_value = exec_result

    with pytest.raises(auth_service.WeakPasswordError):
        await auth_service.create_pending_registration(
            session=session, email="new@prepwise.ai", name="New", password="weak"
        )


async def test_create_pending_registration_success() -> None:
    session = AsyncMock()
    exec_result = MagicMock()
    exec_result.scalar_one_or_none.return_value = None
    session.execute.return_value = exec_result

    with patch(
        "app.services.auth_service.send_verification_email",
        AsyncMock(return_value=True),
    ):
        email, otp = await auth_service.create_pending_registration(
            session=session,
            email="valid@prepwise.ai",
            name="Valid User",
            password="StrongPassword#2026",
        )
    assert email == "valid@prepwise.ai"
    assert len(otp) == 6
    session.add.assert_called_once()
    session.commit.assert_called_once()


async def test_verify_otp_no_pending_record() -> None:
    session = AsyncMock()
    exec_result = MagicMock()
    exec_result.scalar_one_or_none.return_value = None
    session.execute.return_value = exec_result

    with pytest.raises(auth_service.PendingRegistrationNotFoundError):
        await auth_service.verify_otp_and_create_user(
            session, "none@prepwise.ai", "123456"
        )


async def test_verify_otp_expired() -> None:
    session = AsyncMock()
    expired_otp = EmailOTP(
        email="exp@prepwise.ai",
        name="Expired",
        password_hash="hash",
        otp_code="123456",
        expires_at=datetime.now(UTC) - timedelta(minutes=5),
        is_used=False,
    )
    exec_result = MagicMock()
    exec_result.scalar_one_or_none.return_value = expired_otp
    session.execute.return_value = exec_result

    with pytest.raises(auth_service.OtpExpiredError, match="expired"):
        await auth_service.verify_otp_and_create_user(
            session, "exp@prepwise.ai", "123456"
        )


async def test_verify_otp_incorrect_code() -> None:
    session = AsyncMock()
    otp_record = EmailOTP(
        email="test@prepwise.ai",
        name="Test",
        password_hash="hash",
        otp_code="123456",
        expires_at=datetime.now(UTC) + timedelta(minutes=5),
        is_used=False,
    )
    exec_result = MagicMock()
    exec_result.scalar_one_or_none.return_value = otp_record
    session.execute.return_value = exec_result

    with pytest.raises(auth_service.IncorrectOtpError, match="[Ii]ncorrect"):
        await auth_service.verify_otp_and_create_user(
            session, "test@prepwise.ai", "999999"
        )


async def test_verify_otp_success_inserts_user() -> None:
    session = AsyncMock()
    otp_record = EmailOTP(
        email="success@prepwise.ai",
        name="Success User",
        password_hash="hashed_pw_123",
        otp_code="123456",
        expires_at=datetime.now(UTC) + timedelta(minutes=5),
        is_used=False,
    )
    otp_res = MagicMock()
    otp_res.scalar_one_or_none.return_value = otp_record

    user_res = MagicMock()
    user_res.scalar_one_or_none.return_value = None

    session.execute.side_effect = [otp_res, user_res]

    user = await auth_service.verify_otp_and_create_user(
        session, "success@prepwise.ai", "123456"
    )
    assert otp_record.is_used is True
    assert user.email == "success@prepwise.ai"
    assert user.name == "Success User"
    assert user.is_verified is True
    session.add.assert_called_once()
    session.commit.assert_called_once()


async def test_verify_otp_success_updates_existing_unverified_user() -> None:
    otp_record = EmailOTP(
        email="existing@prepwise.ai",
        name="Existing User",
        password_hash="new_hashed_pw",
        otp_code="123456",
        expires_at=datetime.now(UTC) + timedelta(minutes=5),
        is_used=False,
    )
    existing_user = User(
        id="usr_existing",
        email="existing@prepwise.ai",
        name="Old Name",
        password_hash="stale_hash",
        is_verified=False,
    )

    session = AsyncMock()
    otp_res = MagicMock()
    otp_res.scalar_one_or_none.return_value = otp_record
    user_res = MagicMock()
    user_res.scalar_one_or_none.return_value = existing_user
    session.execute.side_effect = [otp_res, user_res]

    user = await auth_service.verify_otp_and_create_user(
        session, "existing@prepwise.ai", "123456"
    )

    assert user is existing_user
    assert user.name == "Existing User"
    assert user.password_hash == "new_hashed_pw"
    assert user.is_verified is True
    session.add.assert_not_called()


async def test_resend_registration_otp_no_pending_record() -> None:
    session = AsyncMock()
    exec_result = MagicMock()
    exec_result.scalar_one_or_none.return_value = None
    session.execute.return_value = exec_result

    with pytest.raises(auth_service.PendingRegistrationNotFoundError):
        await auth_service.resend_registration_otp(session, "none@prepwise.ai")


async def test_resend_registration_otp_success() -> None:
    session = AsyncMock()
    otp_record = EmailOTP(
        email="resend@prepwise.ai",
        name="Resend",
        password_hash="hash",
        otp_code="111111",
        expires_at=datetime.now(UTC) + timedelta(minutes=5),
        is_used=False,
    )
    exec_result = MagicMock()
    exec_result.scalar_one_or_none.return_value = otp_record
    session.execute.return_value = exec_result

    with patch(
        "app.services.auth_service.send_verification_email",
        AsyncMock(return_value=True),
    ):
        new_otp = await auth_service.resend_registration_otp(
            session, "resend@prepwise.ai"
        )

    assert new_otp == otp_record.otp_code
    assert new_otp != "111111"


async def test_authenticate_email_user_success() -> None:
    session = AsyncMock()
    pw_hash = hash_password("Correct#2026")
    fake_user = User(
        id="usr_abc",
        email="login@prepwise.ai",
        name="Login User",
        password_hash=pw_hash,
        is_verified=True,
    )
    exec_result = MagicMock()
    exec_result.scalar_one_or_none.return_value = fake_user
    session.execute.return_value = exec_result

    user = await auth_service.authenticate_email_user(
        session, "login@prepwise.ai", "Correct#2026"
    )
    assert user.id == "usr_abc"


async def test_authenticate_email_user_normalizes_email_case() -> None:
    session = AsyncMock()
    pw_hash = hash_password("Correct#2026")
    fake_user = User(
        id="usr_abc",
        email="mixed@prepwise.ai",
        name="Mixed Case",
        password_hash=pw_hash,
        is_verified=True,
    )
    exec_result = MagicMock()
    exec_result.scalar_one_or_none.return_value = fake_user
    session.execute.return_value = exec_result

    await auth_service.authenticate_email_user(
        session, "  Mixed@Prepwise.AI  ", "Correct#2026"
    )

    stmt = session.execute.call_args.args[0]
    compiled = str(stmt.compile(compile_kwargs={"literal_binds": True}))
    assert "mixed@prepwise.ai" in compiled
    assert "Mixed@Prepwise.AI" not in compiled


async def test_authenticate_email_user_unverified_fails() -> None:
    session = AsyncMock()
    pw_hash = hash_password("Correct#2026")
    fake_user = User(
        id="usr_abc",
        email="unverified@prepwise.ai",
        name="Unverified",
        password_hash=pw_hash,
        is_verified=False,
    )
    exec_result = MagicMock()
    exec_result.scalar_one_or_none.return_value = fake_user
    session.execute.return_value = exec_result

    with pytest.raises(auth_service.EmailNotVerifiedError):
        await auth_service.authenticate_email_user(
            session, "unverified@prepwise.ai", "Correct#2026"
        )


async def test_authenticate_email_user_wrong_password_fails() -> None:
    session = AsyncMock()
    pw_hash = hash_password("Correct#2026")
    fake_user = User(
        id="usr_abc",
        email="login@prepwise.ai",
        name="Login User",
        password_hash=pw_hash,
        is_verified=True,
    )
    exec_result = MagicMock()
    exec_result.scalar_one_or_none.return_value = fake_user
    session.execute.return_value = exec_result

    with pytest.raises(auth_service.InvalidCredentialsError):
        await auth_service.authenticate_email_user(
            session, "login@prepwise.ai", "WrongPassword#2026"
        )


async def test_authenticate_email_user_unknown_email_fails() -> None:
    session = AsyncMock()
    exec_result = MagicMock()
    exec_result.scalar_one_or_none.return_value = None
    session.execute.return_value = exec_result

    with pytest.raises(auth_service.InvalidCredentialsError):
        await auth_service.authenticate_email_user(
            session, "nobody@prepwise.ai", "Whatever#2026"
        )


async def test_request_password_reset_for_unknown_email_returns_none_but_no_error() -> (
    None
):
    session = AsyncMock()
    exec_result = MagicMock()
    exec_result.scalar_one_or_none.return_value = None
    session.execute.return_value = exec_result

    otp = await auth_service.request_password_reset(session, "nobody@prepwise.ai")

    assert otp is None
    session.add.assert_not_called()


async def test_request_password_reset_for_unverified_user_returns_none() -> None:
    session = AsyncMock()
    exec_result = MagicMock()
    exec_result.scalar_one_or_none.return_value = User(
        id="usr_1", email="pending@prepwise.ai", name="Pending", is_verified=False
    )
    session.execute.return_value = exec_result

    otp = await auth_service.request_password_reset(session, "pending@prepwise.ai")

    assert otp is None
    session.add.assert_not_called()


async def test_request_password_reset_for_verified_user_creates_code() -> None:
    session = AsyncMock()
    exec_result = MagicMock()
    exec_result.scalar_one_or_none.return_value = User(
        id="usr_1", email="jane@prepwise.ai", name="Jane", is_verified=True
    )
    session.execute.return_value = exec_result

    with patch(
        "app.services.auth_service.send_password_reset_email",
        AsyncMock(return_value=True),
    ):
        otp = await auth_service.request_password_reset(session, "jane@prepwise.ai")

    assert otp is not None
    assert len(otp) == 6
    session.add.assert_called_once()
    session.commit.assert_called_once()


async def test_verify_reset_code_no_pending_record() -> None:
    session = AsyncMock()
    exec_result = MagicMock()
    exec_result.scalar_one_or_none.return_value = None
    session.execute.return_value = exec_result

    with pytest.raises(auth_service.InvalidOrExpiredResetCodeError):
        await auth_service.verify_reset_code(session, "nobody@prepwise.ai", "123456")


async def test_verify_reset_code_expired() -> None:
    session = AsyncMock()
    record = PasswordResetOTP(
        email="jane@prepwise.ai",
        otp_code="123456",
        expires_at=datetime.now(UTC) - timedelta(minutes=1),
        is_used=False,
    )
    exec_result = MagicMock()
    exec_result.scalar_one_or_none.return_value = record
    session.execute.return_value = exec_result

    with pytest.raises(auth_service.InvalidOrExpiredResetCodeError):
        await auth_service.verify_reset_code(session, "jane@prepwise.ai", "123456")


async def test_verify_reset_code_incorrect_code() -> None:
    session = AsyncMock()
    record = PasswordResetOTP(
        email="jane@prepwise.ai",
        otp_code="123456",
        expires_at=datetime.now(UTC) + timedelta(minutes=5),
        is_used=False,
    )
    exec_result = MagicMock()
    exec_result.scalar_one_or_none.return_value = record
    session.execute.return_value = exec_result

    with pytest.raises(auth_service.InvalidOrExpiredResetCodeError):
        await auth_service.verify_reset_code(session, "jane@prepwise.ai", "999999")


async def test_verify_reset_code_success_returns_reset_token() -> None:
    session = AsyncMock()
    record = PasswordResetOTP(
        email="jane@prepwise.ai",
        otp_code="123456",
        expires_at=datetime.now(UTC) + timedelta(minutes=5),
        is_used=False,
    )
    exec_result = MagicMock()
    exec_result.scalar_one_or_none.return_value = record
    session.execute.return_value = exec_result

    reset_token = await auth_service.verify_reset_code(
        session, "jane@prepwise.ai", "123456"
    )

    assert reset_token
    assert record.is_used is True
    session.commit.assert_called_once()


async def test_reset_password_invalid_token() -> None:
    session = AsyncMock()

    with pytest.raises(auth_service.PasswordResetTokenInvalidError):
        await auth_service.reset_password(session, "not-a-real-token", "NewPass#2026")


async def test_reset_password_weak_password_fails() -> None:
    session = AsyncMock()
    reset_token = create_password_reset_token("jane@prepwise.ai")

    with pytest.raises(auth_service.WeakPasswordError):
        await auth_service.reset_password(session, reset_token, "weak")


async def test_reset_password_unknown_user_fails() -> None:
    session = AsyncMock()
    exec_result = MagicMock()
    exec_result.scalar_one_or_none.return_value = None
    session.execute.return_value = exec_result
    reset_token = create_password_reset_token("nobody@prepwise.ai")

    with pytest.raises(auth_service.PasswordResetTokenInvalidError):
        await auth_service.reset_password(session, reset_token, "NewPass#2026")


async def test_reset_password_success_updates_hash_and_bumps_token_version() -> None:
    session = AsyncMock()
    user = User(
        id="usr_1",
        email="jane@prepwise.ai",
        name="Jane",
        password_hash="old_hash",
        is_verified=True,
        token_version=0,
    )
    exec_result = MagicMock()
    exec_result.scalar_one_or_none.return_value = user
    session.execute.return_value = exec_result
    reset_token = create_password_reset_token("jane@prepwise.ai")

    await auth_service.reset_password(session, reset_token, "NewPassword#2026")

    assert user.password_hash != "old_hash"
    assert user.token_version == 1
    session.commit.assert_called_once()
