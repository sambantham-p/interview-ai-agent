from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class LLMCall(Base):
    """One row per LLM Gateway call - every agent call (Interviewer,
    Judges, extraction) logs here. This is the only place that sees
    which of the ~7 agent roles is actually driving cost/latency, and is
    the mechanism the per-interview voice-cost cap reads from.
    """

    __tablename__ = "llm_calls"

    id: Mapped[int] = mapped_column(primary_key=True)
    task: Mapped[str] = mapped_column(String, index=True)
    model: Mapped[str] = mapped_column(String)
    session_id: Mapped[int | None] = mapped_column(
        ForeignKey("interview_sessions.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    prompt: Mapped[str] = mapped_column(String)
    response: Mapped[str] = mapped_column(String)
    prompt_token_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    candidates_token_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    total_token_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    latency_seconds: Mapped[float] = mapped_column(Float)
    error: Mapped[str | None] = mapped_column(String, nullable=True)
    extra: Mapped[dict] = mapped_column(JSONB, default=dict)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
