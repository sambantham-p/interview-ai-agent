import secrets
import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

import httpx
import structlog
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.constants.auth import (
    AUTH_PROVIDER_EMAIL,
    AUTH_PROVIDER_GOOGLE,
    OTP_EXPIRY_MINUTES,
    PASSWORD_RESET_EXPIRY_MINUTES,
)
from app.core.config import get_auth_settings
from app.core.security import (
    PasswordResetTokenInvalidError,
    create_password_reset_token,
    decode_password_reset_token,
    generate_otp_code,
    hash_password,
    validate_password_strength,
    verify_password,
)
from app.models.email_otp import EmailOTP
from app.models.password_reset_otp import PasswordResetOTP
from app.models.user import User
from app.services.email_service import (
    send_password_reset_email,
    send_verification_email,
)

__all__ = [
    "EmailAlreadyRegisteredError",
    "EmailNotVerifiedError",
    "GoogleAccountLinkingRequiredError",
    "GoogleAuthProviderError",
    "GoogleTokenInvalidError",
    "IncorrectOtpError",
    "InvalidCredentialsError",
    "InvalidOrExpiredResetCodeError",
    "OtpExpiredError",
    "PasswordResetTokenInvalidError",
    "PendingRegistrationNotFoundError",
    "WeakPasswordError",
    "authenticate_email_user",
    "authenticate_or_create_google_user",
    "create_pending_registration",
    "get_user_by_id",
    "request_password_reset",
    "resend_registration_otp",
    "reset_password",
    "verify_google_token",
    "verify_otp_and_create_user",
    "verify_reset_code",
]

logger = structlog.get_logger(__name__)

GOOGLE_TOKENINFO_URL = "https://oauth2.googleapis.com/tokeninfo"
GOOGLE_TOKEN_ISSUERS = {"accounts.google.com", "https://accounts.google.com"}


class GoogleTokenInvalidError(Exception):
    """Raised when Google rejects the credential, or its payload is
    missing the subject/email a User record needs.
    """


class GoogleAuthProviderError(Exception):
    """Raised when Google's tokeninfo endpoint itself can't be reached -
    a provider-side failure, not a bad credential.
    """


class GoogleAccountLinkingRequiredError(Exception):
    """Raised when a Google sign-in's verified email matches an existing
    account that has no google_id linked yet. Auto-linking purely on a
    matching email claim would let anyone who can produce a Google-
    verified token for that address sign into an existing password-
    protected account without ever proving they know the password - so
    this is surfaced to the candidate as "sign in with your existing
    method first" instead of silently merging the accounts.
    """


class EmailAlreadyRegisteredError(Exception):
    """Raised when /register targets an email with an existing, already-
    verified account - it should sign in instead.
    """


class WeakPasswordError(Exception):
    """Raised when a registration password fails validate_password_strength().
    str(exc) is the specific rule that failed, safe to show the candidate.
    """


class PendingRegistrationNotFoundError(Exception):
    """Raised when verify_otp/resend_otp target an email with no unused
    EmailOTP row - either it was never registered, or it's already verified.
    """


class OtpExpiredError(Exception):
    """Raised when the matched EmailOTP row's expires_at has passed."""


class IncorrectOtpError(Exception):
    """Raised when the submitted code doesn't match the pending row's."""


class InvalidCredentialsError(Exception):
    """Raised by /login for an unknown email, a Google-only account with
    no password_hash, or a wrong password - one message for all three, so
    a caller can't use the error to enumerate which emails are registered.
    """


class EmailNotVerifiedError(Exception):
    """Raised by /login for an account that never completed OTP
    verification.
    """


class InvalidOrExpiredResetCodeError(Exception):
    """Raised by verify_reset_code for a missing, expired, or incorrect
    code - one message for all three so a caller can't use the
    difference to learn whether an email has an account (see
    request_password_reset's anti-enumeration note).
    """


def _normalize_email(email: str) -> str:
    return email.strip().lower()


async def verify_google_token(credential: str) -> dict[str, Any]:
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(
                GOOGLE_TOKENINFO_URL, params={"id_token": credential}
            )
    except httpx.HTTPError as exc:
        logger.exception("google_verification_connection_error", error=str(exc))
        raise GoogleAuthProviderError(
            "Unable to communicate with Google authentication servers."
        ) from exc

    if resp.status_code != httpx.codes.OK:
        logger.warning(
            "google_token_verification_failed",
            status_code=resp.status_code,
            body=resp.text,
        )
        raise GoogleTokenInvalidError("Invalid or expired Google authentication token.")

    data = resp.json()
    sub = data.get("sub")
    email = _normalize_email(data["email"]) if data.get("email") else None
    name = data.get("name", email.split("@")[0] if email else "Candidate")
    picture = data.get("picture")

    if not sub or not email:
        raise GoogleTokenInvalidError("Google token payload missing subject or email.")

    # aud: rejects a genuine Google ID token minted for a *different*
    # Google OAuth app being replayed against this one. iss/email_verified:
    # tokeninfo will happily echo back an unverified email claim, which
    # would otherwise let anyone claim an address they don't actually
    # control - see authenticate_or_create_google_user()'s linking guard
    # for why that email claim has to be trustworthy before it's used.
    if data.get("aud") != get_auth_settings().google_oauth_client_id:
        raise GoogleTokenInvalidError(
            "Google token was not issued for this application."
        )
    if data.get("iss") not in GOOGLE_TOKEN_ISSUERS:
        raise GoogleTokenInvalidError("Google token has an unexpected issuer.")
    if data.get("email_verified") not in ("true", True):
        raise GoogleTokenInvalidError("Google account email is not verified.")

    return {"sub": sub, "email": email, "name": name, "picture": picture}


async def authenticate_or_create_google_user(
    session: AsyncSession,
    google_id: str,
    email: str,
    name: str,
    picture: str | None,
) -> User:
    email = _normalize_email(email)
    stmt = select(User).where(User.google_id == google_id)
    res = await session.execute(stmt)
    user = res.scalar_one_or_none()

    if user is None:
        email_stmt = select(User).where(User.email == email)
        email_res = await session.execute(email_stmt)
        if email_res.scalar_one_or_none() is not None:
            raise GoogleAccountLinkingRequiredError(
                "An account with this email address already exists. Sign in "
                "with your existing method first, then link Google from "
                "account settings."
            )

    if user:
        user.name = name
        if picture:
            user.picture = picture
        user.is_verified = True
        logger.info("google_user_logged_in", user_id=user.id, email=email)
    else:
        user = User(
            id=f"usr_{google_id}",
            email=email,
            name=name,
            picture=picture,
            auth_provider=AUTH_PROVIDER_GOOGLE,
            google_id=google_id,
            is_verified=True,
        )
        session.add(user)
        logger.info("google_user_inserted", user_id=user.id, email=email)

    await session.commit()
    await session.refresh(user)
    return user


async def create_pending_registration(
    session: AsyncSession,
    email: str,
    name: str,
    password: str,
) -> tuple[str, str]:
    email = _normalize_email(email)
    stmt = select(User).where(User.email == email)
    res = await session.execute(stmt)
    existing_user = res.scalar_one_or_none()
    if existing_user and existing_user.is_verified:
        raise EmailAlreadyRegisteredError(
            "An account with this email address already exists. Please sign in."
        )

    is_valid, err_msg = validate_password_strength(password)
    if not is_valid:
        raise WeakPasswordError(err_msg)

    hashed = hash_password(password)
    otp = generate_otp_code()
    expires_at = datetime.now(UTC) + timedelta(minutes=OTP_EXPIRY_MINUTES)

    otp_record = EmailOTP(
        email=email,
        name=name,
        password_hash=hashed,
        otp_code=otp,
        expires_at=expires_at,
        is_used=False,
    )
    session.add(otp_record)
    await session.commit()

    await send_verification_email(email, name, otp)
    logger.info(
        "pending_registration_otp_created", email=email, expires_at=str(expires_at)
    )
    return email, otp


async def verify_otp_and_create_user(
    session: AsyncSession,
    email: str,
    otp: str,
) -> User:
    email = _normalize_email(email)
    stmt = (
        select(EmailOTP)
        .where(EmailOTP.email == email, ~EmailOTP.is_used)
        .order_by(desc(EmailOTP.created_at))
        .limit(1)
    )
    res = await session.execute(stmt)
    otp_record = res.scalar_one_or_none()

    if not otp_record:
        raise PendingRegistrationNotFoundError(
            "No pending verification found for this email address."
        )

    record_expiry = otp_record.expires_at
    if record_expiry.tzinfo is None:
        record_expiry = record_expiry.replace(tzinfo=UTC)
    if datetime.now(UTC) > record_expiry:
        raise OtpExpiredError(
            "Verification code has expired. Please request a new code."
        )

    if not secrets.compare_digest(otp_record.otp_code, otp.strip()):
        raise IncorrectOtpError(
            "Incorrect verification code. Please check your email and try again."
        )

    otp_record.is_used = True

    user_stmt = select(User).where(User.email == email)
    user_res = await session.execute(user_stmt)
    user = user_res.scalar_one_or_none()

    if user:
        user.name = otp_record.name
        user.password_hash = otp_record.password_hash
        user.is_verified = True
        logger.info("existing_user_verified_via_otp", user_id=user.id, email=email)
    else:
        new_id = f"usr_{uuid.uuid4().hex[:16]}"
        user = User(
            id=new_id,
            email=email,
            name=otp_record.name,
            password_hash=otp_record.password_hash,
            auth_provider=AUTH_PROVIDER_EMAIL,
            is_verified=True,
        )
        session.add(user)
        logger.info("new_user_inserted_via_otp", user_id=user.id, email=email)

    await session.commit()
    await session.refresh(user)
    return user


async def resend_registration_otp(
    session: AsyncSession,
    email: str,
) -> str:
    email = _normalize_email(email)
    stmt = (
        select(EmailOTP)
        .where(EmailOTP.email == email, ~EmailOTP.is_used)
        .order_by(desc(EmailOTP.created_at))
        .limit(1)
    )
    res = await session.execute(stmt)
    latest = res.scalar_one_or_none()

    if not latest:
        raise PendingRegistrationNotFoundError(
            "No pending registration found for this email address."
        )

    new_otp = generate_otp_code()
    latest.otp_code = new_otp
    latest.expires_at = datetime.now(UTC) + timedelta(minutes=OTP_EXPIRY_MINUTES)

    await session.commit()
    await send_verification_email(email, latest.name, new_otp)
    logger.info("registration_otp_resent", email=email)
    return new_otp


async def authenticate_email_user(
    session: AsyncSession,
    email: str,
    password: str,
) -> User:
    email = _normalize_email(email)
    stmt = select(User).where(User.email == email)
    res = await session.execute(stmt)
    user = res.scalar_one_or_none()

    if (
        not user
        or not user.password_hash
        or not verify_password(password, user.password_hash)
    ):
        raise InvalidCredentialsError("Invalid email or password.")

    if not user.is_verified:
        raise EmailNotVerifiedError(
            "Please verify your email address before signing in."
        )

    logger.info("email_user_authenticated", user_id=user.id, email=email)
    return user


async def get_user_by_id(session: AsyncSession, user_id: str) -> User | None:
    """Loads a User by id - used by app/routes/auth.py's get_current_user
    dependency to resolve the subject of a verified session token.
    """
    return await session.get(User, user_id)


async def request_password_reset(session: AsyncSession, email: str) -> str | None:
    """Starts a password reset for `email` if, and only if, it belongs to
    a verified account - but the caller (app/routes/auth.py) always sends
    the same generic response either way ("If an account exists for ..."),
    so an unregistered email is indistinguishable from a registered one in
    the response.
    """
    email = _normalize_email(email)
    stmt = select(User).where(User.email == email)
    res = await session.execute(stmt)
    user = res.scalar_one_or_none()
    if user is None or not user.is_verified:
        return None

    otp = generate_otp_code()
    expires_at = datetime.now(UTC) + timedelta(minutes=PASSWORD_RESET_EXPIRY_MINUTES)

    record = PasswordResetOTP(
        email=email, otp_code=otp, expires_at=expires_at, is_used=False
    )
    session.add(record)
    await session.commit()

    await send_password_reset_email(email, user.name, otp)
    logger.info("password_reset_otp_created", email=email, expires_at=str(expires_at))
    return otp


async def verify_reset_code(session: AsyncSession, email: str, otp: str) -> str:
    """Returns a short-lived password-reset token on success, consumed by
    reset_password() below - see create_password_reset_token().
    """
    email = _normalize_email(email)
    stmt = (
        select(PasswordResetOTP)
        .where(PasswordResetOTP.email == email, ~PasswordResetOTP.is_used)
        .order_by(desc(PasswordResetOTP.created_at))
        .limit(1)
    )
    res = await session.execute(stmt)
    record = res.scalar_one_or_none()

    if record is None:
        raise InvalidOrExpiredResetCodeError("Invalid or expired reset code.")

    expiry = record.expires_at
    if expiry.tzinfo is None:
        expiry = expiry.replace(tzinfo=UTC)
    if datetime.now(UTC) > expiry or not secrets.compare_digest(
        record.otp_code, otp.strip()
    ):
        raise InvalidOrExpiredResetCodeError("Invalid or expired reset code.")

    record.is_used = True
    await session.commit()

    logger.info("password_reset_code_verified", email=email)
    return create_password_reset_token(email)


async def reset_password(
    session: AsyncSession, reset_token: str, new_password: str
) -> None:
    """Sets a new password for the reset token's email. Bumps
    User.token_version, which invalidates every access token already
    issued for that user - see create_access_token()'s docstring for why.
    """
    email = decode_password_reset_token(reset_token)

    is_valid, err_msg = validate_password_strength(new_password)
    if not is_valid:
        raise WeakPasswordError(err_msg)

    stmt = select(User).where(User.email == email)
    res = await session.execute(stmt)
    user = res.scalar_one_or_none()
    if user is None:
        raise PasswordResetTokenInvalidError("Invalid or expired reset token.")

    user.password_hash = hash_password(new_password)
    user.token_version += 1
    await session.commit()

    logger.info("password_reset_completed", user_id=user.id, email=email)
