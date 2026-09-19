from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

EMAIL_PATTERN = r"^[^@\s]+@[^@\s]+\.[^@\s]+$"

NAME_PATTERN = r"^[^<>&]+$"


class GoogleAuthRequest(BaseModel):
    credential: str = Field(
        ..., description="Google ID Token (JWT) from Google Identity Services"
    )


class RegisterRequest(BaseModel):
    email: str = Field(..., pattern=EMAIL_PATTERN)
    name: str = Field(..., min_length=1, max_length=100, pattern=NAME_PATTERN)
    password: str = Field(..., min_length=8)


class VerifyOtpRequest(BaseModel):
    email: str = Field(..., pattern=EMAIL_PATTERN)
    otp: str = Field(..., min_length=6, max_length=6)


class ResendOtpRequest(BaseModel):
    email: str = Field(..., pattern=EMAIL_PATTERN)


class LoginRequest(BaseModel):
    email: str = Field(..., pattern=EMAIL_PATTERN)
    password: str


class UserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    email: str
    name: str
    preferred_name: str | None = None
    picture: str | None = None
    auth_provider: str
    is_verified: bool
    created_at: datetime


class UpdateProfileRequest(BaseModel):
    # An empty or whitespace-only value clears the preferred name.
    preferred_name: str = Field(..., max_length=50, pattern=r"^[^<>&]*$")


class ForgotPasswordRequest(BaseModel):
    email: str = Field(..., pattern=EMAIL_PATTERN)


class VerifyResetCodeRequest(BaseModel):
    email: str = Field(..., pattern=EMAIL_PATTERN)
    otp: str = Field(..., min_length=6, max_length=6)


class ResetPasswordRequest(BaseModel):
    reset_token: str
    new_password: str = Field(..., min_length=8)


class AuthResponse(BaseModel):
    user: UserResponse
    token: str

    @classmethod
    def from_user(cls, user: object, token: str) -> "AuthResponse":
        return cls(user=UserResponse.model_validate(user), token=token)


class RegisterResponse(BaseModel):
    email: str
    otp_sent: bool = True
    message: str = "Verification code sent to your email address."


class ResendOtpResponse(BaseModel):
    email: str
    otp_sent: bool = True
    message: str = "A new verification code has been sent."


class VerifyResetCodeResponse(BaseModel):
    reset_token: str


class MessageResponse(BaseModel):
    message: str
