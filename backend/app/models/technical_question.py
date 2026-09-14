from datetime import datetime

from pgvector.sqlalchemy import Vector
from sqlalchemy import DateTime, String, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.constants.question_bank import QUESTION_EMBEDDING_DIM
from app.models.base import Base


class TechnicalQuestion(Base):
    """Curated interview question, embedded for semantic retrieval
    against a JD's open-ended tech-stack text.
    """

    __tablename__ = "technical_questions"

    id: Mapped[int] = mapped_column(primary_key=True)
    question_text: Mapped[str] = mapped_column(String)
    topic: Mapped[str] = mapped_column(String, index=True)
    tech_stack: Mapped[list] = mapped_column(JSONB, default=list)
    difficulty: Mapped[str] = mapped_column(String, index=True)
    seniority: Mapped[str] = mapped_column(String, index=True)
    embedding: Mapped[list[float]] = mapped_column(Vector(QUESTION_EMBEDDING_DIM))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
