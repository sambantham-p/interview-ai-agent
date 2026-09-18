from datetime import UTC, datetime, timedelta

import jwt
import pytest
from pytest_mock import MockerFixture

from app.core.config import AuthSettings
from app.core.security import (
    InvalidSessionTokenError,
    PasswordResetTokenInvalidError,
    create_access_token,
    create_password_reset_token,
    decode_access_token,
    decode_password_reset_token,
    generate_otp_code,
    hash_password,
    validate_password_strength,
    verify_password,
)


def test_hash_and_verify_password() -> None:
    password = "MySecurePassword#2026"
    hashed = hash_password(password)

    assert "$" in hashed
    assert verify_password(password, hashed) is True
    assert verify_password("WrongPassword#2026", hashed) is False
    assert verify_password(password, "invalid_hash_string") is False


def test_validate_password_strength() -> None:
    # Too short
    valid, msg = validate_password_strength("Short1!")
    assert valid is False
    assert "8 characters" in msg

    # No uppercase
    valid, msg = validate_password_strength("nouppercase123!")
    assert valid is False
    assert "uppercase" in msg

    # No lowercase
    valid, msg = validate_password_strength("NOLOWERCASE123!")
    assert valid is False
    assert "lowercase" in msg

    # No number
    valid, msg = validate_password_strength("NoNumberSpecial!")
    assert valid is False
    assert "number" in msg

    # No special character
    valid, msg = validate_password_strength("NoSpecialChar123")
    assert valid is False
    assert "special character" in msg

    # Valid strong password
    valid, msg = validate_password_strength("Prepwise#2026")
    assert valid is True
    assert msg == ""


def test_validate_password_strength_accepts_quote_and_backslash_specials() -> None:
    # Regression: the old hand-listed regex char class omitted `"`, `'`,
    # and `\`, so a password whose only special character was one of
    # these was wrongly rejected.
    for password in ('NoOtherSpecial123"', "NoOtherSpecial123'", "NoOtherSpecial123\\"):
        valid, msg = validate_password_strength(password)
        assert valid is True
        assert msg == ""


def test_generate_otp_code() -> None:
    otp = generate_otp_code()
    assert len(otp) == 6
    assert otp.isdigit()
    assert 100000 <= int(otp) <= 999999


def test_create_and_decode_access_token_round_trips(mocker: MockerFixture) -> None:
    mocker.patch(
        "app.core.security.get_auth_settings",
        return_value=AuthSettings(jwt_secret_key="a" * 32, jwt_expiry_minutes=60),
    )

    token = create_access_token("usr_123", 0)

    subject = decode_access_token(token)
    assert subject.user_id == "usr_123"
    assert subject.token_version == 0


def test_decode_access_token_rejects_bad_signature(mocker: MockerFixture) -> None:
    mocker.patch(
        "app.core.security.get_auth_settings",
        return_value=AuthSettings(jwt_secret_key="a" * 32),
    )
    token = create_access_token("usr_123", 0)

    mocker.patch(
        "app.core.security.get_auth_settings",
        return_value=AuthSettings(jwt_secret_key="b" * 32),
    )

    with pytest.raises(InvalidSessionTokenError):
        decode_access_token(token)


def test_decode_access_token_rejects_expired_token(mocker: MockerFixture) -> None:
    settings = AuthSettings(jwt_secret_key="a" * 32)
    mocker.patch("app.core.security.get_auth_settings", return_value=settings)

    now = datetime.now(UTC)
    expired_token = jwt.encode(
        {
            "sub": "usr_123",
            "iat": now - timedelta(hours=1),
            "exp": now - timedelta(minutes=1),
        },
        settings.jwt_secret_key,
        algorithm=settings.jwt_algorithm,
    )

    with pytest.raises(InvalidSessionTokenError):
        decode_access_token(expired_token)


def test_decode_access_token_rejects_malformed_token(mocker: MockerFixture) -> None:
    mocker.patch(
        "app.core.security.get_auth_settings",
        return_value=AuthSettings(jwt_secret_key="a" * 32),
    )

    with pytest.raises(InvalidSessionTokenError):
        decode_access_token("not-a-real-token")


def test_decode_access_token_rejects_a_well_signed_token_missing_sub(
    mocker: MockerFixture,
) -> None:
    settings = AuthSettings(jwt_secret_key="a" * 32)
    mocker.patch("app.core.security.get_auth_settings", return_value=settings)

    now = datetime.now(UTC)
    token_without_sub = jwt.encode(
        {"purpose": "password_reset", "iat": now, "exp": now + timedelta(minutes=5)},
        settings.jwt_secret_key,
        algorithm=settings.jwt_algorithm,
    )

    with pytest.raises(InvalidSessionTokenError):
        decode_access_token(token_without_sub)


def test_create_and_decode_password_reset_token_round_trips(
    mocker: MockerFixture,
) -> None:
    mocker.patch(
        "app.core.security.get_auth_settings",
        return_value=AuthSettings(jwt_secret_key="a" * 32),
    )

    token = create_password_reset_token("jane@example.com")

    assert decode_password_reset_token(token) == "jane@example.com"


def test_decode_password_reset_token_rejects_malformed_token(
    mocker: MockerFixture,
) -> None:
    mocker.patch(
        "app.core.security.get_auth_settings",
        return_value=AuthSettings(jwt_secret_key="a" * 32),
    )

    with pytest.raises(PasswordResetTokenInvalidError):
        decode_password_reset_token("not-a-real-token")


def test_decode_password_reset_token_rejects_a_session_access_token(
    mocker: MockerFixture,
) -> None:
    mocker.patch(
        "app.core.security.get_auth_settings",
        return_value=AuthSettings(jwt_secret_key="a" * 32),
    )
    session_token = create_access_token("usr_123", 0)

    with pytest.raises(PasswordResetTokenInvalidError):
        decode_password_reset_token(session_token)
