from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.constants.interview import INTERVIEW_PHASES
from app.models.base import Base

SESSION_STATUSES = ["in_progress", "completed", "ended_early"]


class InterviewSession(Base):
    __tablename__ = "interview_sessions"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[str] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True
    )

    candidate_profile_id: Mapped[int] = mapped_column(
        ForeignKey("candidate_profiles.id", ondelete="CASCADE"), index=True
    )
    job_description_id: Mapped[int] = mapped_column(
        ForeignKey("job_descriptions.id", ondelete="CASCADE"), index=True
    )

    current_phase: Mapped[str] = mapped_column(String, default=INTERVIEW_PHASES[0])
    status: Mapped[str] = mapped_column(String, default=SESSION_STATUSES[0])
    transcript: Mapped[list] = mapped_column(JSONB, default=list)
    red_flag_count: Mapped[int] = mapped_column(Integer, default=0)
    red_flag_warning_issued: Mapped[bool] = mapped_column(default=False)
    hint_counts: Mapped[dict] = mapped_column(JSONB, default=dict)
    end_reason: Mapped[str | None] = mapped_column(String, nullable=True)
    question_pool: Mapped[list] = mapped_column(JSONB, default=list)
    asked_question_ids: Mapped[dict] = mapped_column(JSONB, default=dict)
    github_call_count: Mapped[int] = mapped_column(Integer, default=0)
    company_research: Mapped[str | None] = mapped_column(String, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    ended_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
