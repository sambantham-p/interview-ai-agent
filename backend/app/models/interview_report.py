from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Numeric, String, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class InterviewReport(Base):
    """Store each generated evaluation report as an immutable snapshot.
    Reports are insert-only, and judge_evaluation_ids records the exact
    evaluations used to generate each report.
    """

    __tablename__ = "interview_reports"

    id: Mapped[int] = mapped_column(primary_key=True)
    session_id: Mapped[int] = mapped_column(
        ForeignKey("interview_sessions.id", ondelete="CASCADE"), index=True
    )
    overall_score: Mapped[float] = mapped_column(Numeric(5, 2))
    recommendation_tier: Mapped[str] = mapped_column(String)
    weights_used: Mapped[dict] = mapped_column(JSONB, default=dict)
    judge_evaluation_ids: Mapped[list] = mapped_column(JSONB, default=list)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
