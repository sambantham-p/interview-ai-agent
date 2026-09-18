from datetime import datetime

from sqlalchemy import Boolean, DateTime, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.constants.auth import AUTH_PROVIDER_EMAIL
from app.models.base import Base


class User(Base):
    """A registered candidate account (email/password or Google sign-in).

    `id` is an app-generated string ("usr_<google id>" or
    "usr_<random hex>"), not an autoincrement integer, so a Google-linked
    account's id is stable and derivable without a DB round-trip - see
    authenticate_or_create_google_user() in app/services/auth_service.py.
    """

    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    email: Mapped[str] = mapped_column(String, unique=True, index=True, nullable=False)
    name: Mapped[str] = mapped_column(String, nullable=False)
    picture: Mapped[str | None] = mapped_column(String, nullable=True)
    password_hash: Mapped[str | None] = mapped_column(String, nullable=True)
    auth_provider: Mapped[str] = mapped_column(
        String, default=AUTH_PROVIDER_EMAIL, nullable=False
    )
    google_id: Mapped[str | None] = mapped_column(
        String, unique=True, index=True, nullable=True
    )
    is_verified: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    token_version: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
