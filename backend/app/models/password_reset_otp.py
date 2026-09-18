from datetime import datetime

from sqlalchemy import Boolean, DateTime, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class PasswordResetOTP(Base):
    """A pending password-reset code for an existing, already-verified
    account - separate from EmailOTP (which covers new-account
    registration) so a signup code can never be replayed to reset an
    existing account's password, or vice versa.

    Insert-only, one row per /auth/forgot-password request:
    auth_service.verify_reset_code() always looks up the latest unused
    row for an email rather than mutating one in place.
    """

    __tablename__ = "password_reset_otps"

    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String, index=True, nullable=False)
    otp_code: Mapped[str] = mapped_column(String, nullable=False)
    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    is_used: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
