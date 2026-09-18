import hashlib
import re
import secrets
import string
from datetime import UTC, datetime, timedelta
from typing import NamedTuple

import jwt

from app.constants.auth import (
    PASSWORD_RESET_EXPIRY_MINUTES,
    PASSWORD_RESET_TOKEN_PURPOSE,
)
from app.core.config import get_auth_settings

# OWASP-recommended minimum for PBKDF2-HMAC-SHA256 as of the 2023
# Password Storage Cheat Sheet .
PBKDF2_ITERATIONS = 600_000
PBKDF2_ALGORITHM = "sha256"
PBKDF2_HASH_PREFIX = "pbkdf2_sha256"


def hash_password(password: str) -> str:
    salt = secrets.token_hex(16)
    key = hashlib.pbkdf2_hmac(
        PBKDF2_ALGORITHM,
        password.encode("utf-8"),
        salt.encode("utf-8"),
        PBKDF2_ITERATIONS,
    )
    # Iteration count travels with the hash so a future bump to
    # PBKDF2_ITERATIONS doesn't strand already-hashed passwords.
    return f"{PBKDF2_HASH_PREFIX}${PBKDF2_ITERATIONS}${salt}${key.hex()}"


def verify_password(plain_password: str, hashed_password: str) -> bool:
    try:
        algorithm, iterations, salt, expected_hex = hashed_password.split("$")
        if algorithm != PBKDF2_HASH_PREFIX:
            return False
        key = hashlib.pbkdf2_hmac(
            PBKDF2_ALGORITHM,
            plain_password.encode("utf-8"),
            salt.encode("utf-8"),
            int(iterations),
        )
        return secrets.compare_digest(key.hex(), expected_hex)
    except ValueError:
        return False


def validate_password_strength(password: str) -> tuple[bool, str]:
    if len(password) < 8:
        return False, "Password must be at least 8 characters long."
    if not re.search(r"[A-Z]", password):
        return False, "Password must contain at least one uppercase letter."
    if not re.search(r"[a-z]", password):
        return False, "Password must contain at least one lowercase letter."
    if not re.search(r"\d", password):
        return False, "Password must contain at least one number."
    if not any(char in string.punctuation for char in password):
        return False, "Password must contain at least one special character."
    return True, ""


def generate_otp_code() -> str:
    # 6-digit string, 100000-999999 - secrets.randbelow() is a CSPRNG,
    return str(secrets.randbelow(900_000) + 100_000)


class AccessTokenSubject(NamedTuple):
    """The identity carried by a session token: which user, and which
    "generation" of that user's sessions - see `token_version` below.
    """

    user_id: str
    token_version: int


def create_access_token(user_id: str, token_version: int) -> str:
    """Signs a JWT identifying `user_id`, verifiable by decode_access_token
    without a DB round-trip. Session identity, not authorization - route
    handlers still load the User row themselves (see
    app/routes/auth.py's get_current_user).

    `token_version` is echoed from User.token_version at issue time.
    get_current_user() rejects a token whose `ver` claim no longer matches
    the User row's current token_version - the mechanism reset_password()
    uses to invalidate every session token issued before a password
    change (matches the Figma "Choose a new password" copy: "You'll be
    signed out of other sessions").
    """
    settings = get_auth_settings()
    now = datetime.now(UTC)
    payload = {
        "sub": user_id,
        "ver": token_version,
        "iat": now,
        "exp": now + timedelta(minutes=settings.jwt_expiry_minutes),
    }
    return jwt.encode(
        payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm
    )


class InvalidSessionTokenError(Exception):
    """Raised when a bearer token fails to decode/verify - missing,
    malformed, expired, wrong signature, or a token_version that's been
    superseded by a password reset. Registered as a global exception
    handler (see app/core/exception_handlers.py) rather than caught
    locally, since it's raised from inside a FastAPI dependency
    (app/routes/auth.py's get_current_user) that runs before a route
    body's own try/except would see it.
    """


def decode_access_token(token: str) -> AccessTokenSubject:
    """Returns the (user id, token_version) embedded in a valid, unexpired
    token. Does not check the version against the current User row itself -
    that comparison needs a DB lookup, done by the caller (get_current_user).
    """
    settings = get_auth_settings()
    try:
        payload = jwt.decode(
            token, settings.jwt_secret_key, algorithms=[settings.jwt_algorithm]
        )
    except jwt.PyJWTError as exc:
        raise InvalidSessionTokenError("Invalid or expired session token.") from exc
    user_id = payload.get("sub")
    if user_id is None:
        raise InvalidSessionTokenError("Invalid or expired session token.")
    return AccessTokenSubject(user_id=user_id, token_version=payload.get("ver", 0))


class PasswordResetTokenInvalidError(Exception):
    """Raised when a password-reset token fails to decode/verify, or was
    issued for a different purpose (i.e. it's a session access token, not
    a reset token) - kept distinct from InvalidSessionTokenError since
    the two token types are never interchangeable.
    """


def create_password_reset_token(email: str) -> str:
    """Signs a short-lived, single-purpose JWT proving the holder already
    verified a password-reset code for `email` (see
    app/services/auth_service.py's verify_reset_code) - handed back to
    the client so the final "choose a new password" step doesn't need to
    resubmit the code, without granting a real session.
    """
    settings = get_auth_settings()
    now = datetime.now(UTC)
    payload = {
        "email": email,
        "purpose": PASSWORD_RESET_TOKEN_PURPOSE,
        "iat": now,
        "exp": now + timedelta(minutes=PASSWORD_RESET_EXPIRY_MINUTES),
    }
    return jwt.encode(
        payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm
    )


def decode_password_reset_token(token: str) -> str:
    """Returns the email a valid, unexpired password-reset token was
    issued for. Rejects a well-signed session access token too - it has
    no "purpose" claim, so it fails the check below.
    """
    settings = get_auth_settings()
    try:
        payload = jwt.decode(
            token, settings.jwt_secret_key, algorithms=[settings.jwt_algorithm]
        )
    except jwt.PyJWTError as exc:
        raise PasswordResetTokenInvalidError("Invalid or expired reset token.") from exc
    if payload.get("purpose") != PASSWORD_RESET_TOKEN_PURPOSE:
        raise PasswordResetTokenInvalidError("Invalid or expired reset token.")
    return payload["email"]
