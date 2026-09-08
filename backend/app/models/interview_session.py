from datetime import datetime

from sqlalchemy import Boolean, DateTime, String, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.constants.app import DEFAULT_USER_ID
from app.models.base import Base


class InterviewSession(Base):
    __tablename__ = "interview_sessions"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[str] = mapped_column(String, default=DEFAULT_USER_ID, index=True)

    role_title: Mapped[str] = mapped_column(String)
    seniority: Mapped[str] = mapped_column(String)
    tech_stack: Mapped[list] = mapped_column(JSONB, default=list)
    coding_assessment_expected: Mapped[bool] = mapped_column(Boolean, default=False)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
