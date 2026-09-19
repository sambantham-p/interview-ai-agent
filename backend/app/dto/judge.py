from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.constants.judge import END_REASON_LABELS, RECOMMENDATION_LABELS
from app.services.report_summary import build_headline, focus_judges, strength_judges


class JudgeEvidenceItem(BaseModel):
    """One cited transcript excerpt backing a judge's score."""

    quote: str = Field(description="A short, verbatim or near-verbatim excerpt.")
    transcript_index: int | None = Field(
        default=None,
        description=(
            "Index into the session's transcript list this quote came from, "
            "if identifiable. None if the judge can't pin one down."
        ),
    )
    reasoning: str = Field(description="Why this excerpt supports the score.")


class JudgeOutput(BaseModel):
    """Structured-output schema every Judge agent returns via
    generate_structured(). score is the judge's own 0-100 assessment
    before any deterministic post-processing - the Attitude judge's hint
    penalty deduction and abusive-language cap are applied afterward in
    Python, not by the model itself (see judge_service.py).
    """

    score: float = Field(ge=0, le=100)
    summary: str = Field(description="2-4 sentence rationale for the score.")
    evidence: list[JudgeEvidenceItem] = Field(
        min_length=1,
        description="At least one cited transcript excerpt is required.",
    )


class JudgeEvaluationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    session_id: int
    judge_name: str
    dimension: str
    score: float
    summary: str
    evidence: list[JudgeEvidenceItem]


class InterviewReportResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    session_id: int
    overall_score: float
    recommendation_tier: str
    recommendation_label: str
    headline: str
    strength_dimensions: list[str]
    focus_dimensions: list[str]
    weights_used: dict[str, float]
    judge_evaluations: list[JudgeEvaluationResponse]
    hint_counts: dict[str, int]
    red_flag_count: int
    end_reason: str | None
    end_reason_label: str | None

    @classmethod
    def from_report_and_evaluations(
        cls,
        report: object,
        evaluations: list[object],
        session: object,
    ) -> "InterviewReportResponse":
        return cls(
            id=report.id,
            session_id=report.session_id,
            overall_score=float(report.overall_score),
            recommendation_tier=report.recommendation_tier,
            recommendation_label=RECOMMENDATION_LABELS.get(
                report.recommendation_tier, report.recommendation_tier
            ),
            headline=build_headline(evaluations),
            strength_dimensions=strength_judges(evaluations),
            focus_dimensions=focus_judges(evaluations),
            weights_used=report.weights_used,
            judge_evaluations=[
                JudgeEvaluationResponse.model_validate(e) for e in evaluations
            ],
            hint_counts=session.hint_counts,
            red_flag_count=session.red_flag_count,
            end_reason=session.end_reason,
            end_reason_label=END_REASON_LABELS.get(session.end_reason or ""),
        )


class ReportListItem(BaseModel):
    """One finished interview in the reports collection: what it was for,
    how it went, and - once its report has been generated - the score and
    verdict.
    """

    session_id: int
    status: str
    end_reason: str | None
    end_reason_label: str | None
    job_role: str
    company_name: str | None
    created_at: datetime
    ended_at: datetime | None
    duration_minutes: int | None
    hint_count: int
    red_flag_count: int
    report_id: int | None
    overall_score: float | None
    recommendation_tier: str | None
    recommendation_label: str | None

    @classmethod
    def from_parts(
        cls, session: object, job_description: object, report: object | None
    ) -> "ReportListItem":
        duration_minutes = (
            max(1, round((session.ended_at - session.created_at).total_seconds() / 60))
            if session.ended_at
            else None
        )
        return cls(
            session_id=session.id,
            status=session.status,
            end_reason=session.end_reason,
            end_reason_label=END_REASON_LABELS.get(session.end_reason or ""),
            job_role=job_description.role,
            company_name=job_description.company_name,
            created_at=session.created_at,
            ended_at=session.ended_at,
            duration_minutes=duration_minutes,
            hint_count=sum(session.hint_counts.values()),
            red_flag_count=session.red_flag_count,
            report_id=report.id if report else None,
            overall_score=float(report.overall_score) if report else None,
            recommendation_tier=report.recommendation_tier if report else None,
            recommendation_label=(
                RECOMMENDATION_LABELS.get(
                    report.recommendation_tier, report.recommendation_tier
                )
                if report
                else None
            ),
        )
