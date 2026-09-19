from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Numeric, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class JudgeEvaluation(Base):
    """Store each Judge scoring pass over a session transcript.

    Insert-only: each run creates a new row, preserving previous evaluations.
    """

    __tablename__ = "judge_evaluations"

    id: Mapped[int] = mapped_column(primary_key=True)
    session_id: Mapped[int] = mapped_column(
        ForeignKey("interview_sessions.id", ondelete="CASCADE"), index=True
    )
    judge_name: Mapped[str] = mapped_column(String, index=True)
    dimension: Mapped[str] = mapped_column(String)
    score: Mapped[float] = mapped_column(Numeric(5, 2))
    summary: Mapped[str] = mapped_column(Text)
    evidence: Mapped[list] = mapped_column(JSONB, default=list)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
