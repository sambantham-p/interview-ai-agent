from pydantic import BaseModel, ConfigDict, Field


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
    weights_used: dict[str, float]
    judge_evaluations: list[JudgeEvaluationResponse]
    hint_counts: dict[str, int]
    red_flag_count: int
    end_reason: str | None
