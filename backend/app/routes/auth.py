import httpx
from fastapi import APIRouter, Depends, Header
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_db
from app.core.responses import error_response, success_response
from app.core.security import (
    InvalidSessionTokenError,
    create_access_token,
    decode_access_token,
)
from app.dto.auth import (
    AuthResponse,
    ForgotPasswordRequest,
    GoogleAuthRequest,
    LoginRequest,
    MessageResponse,
    RegisterRequest,
    RegisterResponse,
    ResendOtpRequest,
    ResendOtpResponse,
    ResetPasswordRequest,
    UserResponse,
    VerifyOtpRequest,
    VerifyResetCodeRequest,
    VerifyResetCodeResponse,
)
from app.models.user import User
from app.services import auth_service

router = APIRouter(tags=["auth"])


async def get_current_user(
    authorization: str | None = Header(default=None),
    db: AsyncSession = Depends(get_db),
) -> User:
    """Resolves the signed-in User from a `Bearer <token>` Authorization
    header. Raises InvalidSessionTokenError (handled globally, see
    app/core/exception_handlers.py) for a missing header, an unverifiable
    token, a token whose subject no longer has a User row, or a token
    whose `ver` claim has been superseded by a password reset.
    """
    if authorization is None or not authorization.startswith("Bearer "):
        raise InvalidSessionTokenError("Missing or malformed Authorization header.")

    subject = decode_access_token(authorization.removeprefix("Bearer "))
    user = await auth_service.get_user_by_id(db, subject.user_id)
    if user is None or user.token_version != subject.token_version:
        raise InvalidSessionTokenError("Invalid or expired session token.")
    return user


@router.post(
    "/auth/google",
    response_model=AuthResponse,
    summary="Authenticate with Google and insert user object",
)
async def google_auth(
    payload: GoogleAuthRequest,
    db: AsyncSession = Depends(get_db),
) -> JSONResponse:
    try:
        google_data = await auth_service.verify_google_token(
            credential=payload.credential
        )
    except auth_service.GoogleTokenInvalidError as exc:
        return error_response(message=str(exc), status_code=httpx.codes.UNAUTHORIZED)
    except auth_service.GoogleAuthProviderError as exc:
        return error_response(message=str(exc), status_code=httpx.codes.BAD_GATEWAY)

    try:
        user = await auth_service.authenticate_or_create_google_user(
            session=db,
            google_id=google_data["sub"],
            email=google_data["email"],
            name=google_data["name"],
            picture=google_data.get("picture"),
        )
    except auth_service.GoogleAccountLinkingRequiredError as exc:
        return error_response(message=str(exc), status_code=httpx.codes.CONFLICT)

    token = create_access_token(user.id, user.token_version)
    return success_response(data=AuthResponse.from_user(user, token))


@router.post(
    "/auth/register",
    response_model=RegisterResponse,
    summary="Initiate email registration and send 6-digit OTP",
)
async def register(
    payload: RegisterRequest,
    db: AsyncSession = Depends(get_db),
) -> JSONResponse:
    try:
        email, _ = await auth_service.create_pending_registration(
            session=db,
            email=payload.email,
            name=payload.name,
            password=payload.password,
        )
    except auth_service.EmailAlreadyRegisteredError as exc:
        return error_response(message=str(exc), status_code=httpx.codes.BAD_REQUEST)
    except auth_service.WeakPasswordError as exc:
        return error_response(
            message=str(exc), status_code=httpx.codes.UNPROCESSABLE_ENTITY
        )

    return success_response(data=RegisterResponse(email=email))


@router.post(
    "/auth/verify-otp",
    response_model=AuthResponse,
    summary="Verify 6-digit OTP and insert/activate user object",
)
async def verify_otp(
    payload: VerifyOtpRequest,
    db: AsyncSession = Depends(get_db),
) -> JSONResponse:
    try:
        user = await auth_service.verify_otp_and_create_user(
            session=db,
            email=payload.email,
            otp=payload.otp,
        )
    except auth_service.PendingRegistrationNotFoundError as exc:
        return error_response(message=str(exc), status_code=httpx.codes.BAD_REQUEST)
    except auth_service.OtpExpiredError as exc:
        return error_response(message=str(exc), status_code=httpx.codes.BAD_REQUEST)
    except auth_service.IncorrectOtpError as exc:
        return error_response(message=str(exc), status_code=httpx.codes.BAD_REQUEST)

    token = create_access_token(user.id, user.token_version)
    return success_response(data=AuthResponse.from_user(user, token))


@router.post(
    "/auth/resend-otp",
    response_model=ResendOtpResponse,
    summary="Resend a fresh 6-digit OTP code",
)
async def resend_otp(
    payload: ResendOtpRequest,
    db: AsyncSession = Depends(get_db),
) -> JSONResponse:
    try:
        await auth_service.resend_registration_otp(
            session=db,
            email=payload.email,
        )
    except auth_service.PendingRegistrationNotFoundError as exc:
        return error_response(message=str(exc), status_code=httpx.codes.BAD_REQUEST)

    return success_response(data=ResendOtpResponse(email=payload.email))


@router.post(
    "/auth/login",
    response_model=AuthResponse,
    summary="Sign in with email and password",
)
async def login(
    payload: LoginRequest,
    db: AsyncSession = Depends(get_db),
) -> JSONResponse:
    try:
        user = await auth_service.authenticate_email_user(
            session=db,
            email=payload.email,
            password=payload.password,
        )
    except auth_service.InvalidCredentialsError as exc:
        return error_response(message=str(exc), status_code=httpx.codes.UNAUTHORIZED)
    except auth_service.EmailNotVerifiedError as exc:
        return error_response(message=str(exc), status_code=httpx.codes.FORBIDDEN)

    token = create_access_token(user.id, user.token_version)
    return success_response(data=AuthResponse.from_user(user, token))


@router.post(
    "/auth/forgot-password",
    response_model=MessageResponse,
    summary="Request a password reset code by email",
)
async def forgot_password(
    payload: ForgotPasswordRequest,
    db: AsyncSession = Depends(get_db),
) -> JSONResponse:
    """Always returns the same generic response whether or not `email` has
    an account - see request_password_reset()'s anti-enumeration note.
    """
    await auth_service.request_password_reset(session=db, email=payload.email)
    data = MessageResponse(
        message=(
            "If an account exists for this email address, you'll "
            "receive a secure reset code shortly."
        )
    )
    return success_response(data=data)


@router.post(
    "/auth/verify-reset-code",
    response_model=VerifyResetCodeResponse,
    summary="Verify a password reset code",
)
async def verify_reset_code(
    payload: VerifyResetCodeRequest,
    db: AsyncSession = Depends(get_db),
) -> JSONResponse:
    try:
        reset_token = await auth_service.verify_reset_code(
            session=db, email=payload.email, otp=payload.otp
        )
    except auth_service.InvalidOrExpiredResetCodeError as exc:
        return error_response(message=str(exc), status_code=httpx.codes.BAD_REQUEST)

    return success_response(data=VerifyResetCodeResponse(reset_token=reset_token))


@router.post(
    "/auth/reset-password",
    response_model=MessageResponse,
    summary="Set a new password using a verified reset token",
)
async def reset_password(
    payload: ResetPasswordRequest,
    db: AsyncSession = Depends(get_db),
) -> JSONResponse:
    try:
        await auth_service.reset_password(
            session=db,
            reset_token=payload.reset_token,
            new_password=payload.new_password,
        )
    except auth_service.PasswordResetTokenInvalidError as exc:
        return error_response(message=str(exc), status_code=httpx.codes.UNAUTHORIZED)
    except auth_service.WeakPasswordError as exc:
        return error_response(
            message=str(exc), status_code=httpx.codes.UNPROCESSABLE_ENTITY
        )

    return success_response(
        data=MessageResponse(
            message="Your password has been updated. Please sign in again."
        )
    )


@router.get("/auth/me", summary="Get profile of the authenticated user")
async def get_current_user_profile(
    user: User = Depends(get_current_user),
) -> JSONResponse:
    return success_response(data={"user": UserResponse.model_validate(user)})
