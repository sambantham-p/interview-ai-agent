from datetime import UTC, datetime

from app.dto.interview import InterviewSessionDetail, TranscriptEntry
from app.dto.judge import (
    InterviewReportResponse,
    JudgeEvaluationResponse,
    JudgeEvidenceItem,
)
from app.services.report_pdf import (
    _citations_by_index,
    _markup,
    _score_color,
    build_report_pdf,
)


def _evaluation(**overrides) -> JudgeEvaluationResponse:
    defaults = {
        "id": 1,
        "session_id": 10,
        "judge_name": "project_depth",
        "dimension": "Project Depth",
        "score": 82.0,
        "summary": "Solid & clear <reasoning>.",
        "evidence": [
            JudgeEvidenceItem(
                quote="I used Redis", transcript_index=1, reasoning="Specific"
            ),
            JudgeEvidenceItem(
                quote="no index", transcript_index=None, reasoning="Vague"
            ),
        ],
    }
    defaults.update(overrides)
    return JudgeEvaluationResponse(**defaults)


def _report(**overrides) -> InterviewReportResponse:
    defaults = {
        "id": 1,
        "session_id": 10,
        "overall_score": 74.0,
        "recommendation_tier": "hire",
        "recommendation_label": "Hire",
        "headline": "Strong on projects.",
        "strength_dimensions": ["Project Depth"],
        "focus_dimensions": ["Coding"],
        "weights_used": {"project_depth": 0.25, "coding": 0.2},
        "judge_evaluations": [
            _evaluation(),
            _evaluation(
                id=2,
                judge_name="coding",
                dimension="Coding",
                score=40.0,
                evidence=[
                    JudgeEvidenceItem(quote="q", transcript_index=1, reasoning="Weak")
                ],
            ),
            _evaluation(id=3, judge_name="attitude", dimension="Attitude", score=60.0),
        ],
        "hint_counts": {"technical_interview": 2, "unknown_phase": 1},
        "red_flag_count": 1,
        "end_reason": None,
        "end_reason_label": None,
    }
    defaults.update(overrides)
    return InterviewReportResponse(**defaults)


def _detail(**overrides) -> InterviewSessionDetail:
    entries = [
        TranscriptEntry(
            index=1,
            role="model",
            text="Tell me <more> & more",
            phase="background_check",
        ),
        TranscriptEntry(
            index=2,
            role="user",
            text="I used Redis\nsecond line",
            phase="background_check",
        ),
        TranscriptEntry(
            index=3,
            role="model",
            text="Next",
            phase="technical_interview",
            hint_level=2,
        ),
    ]
    defaults = {
        "current_phase": "technical_interview",
        "status": "completed",
        "reply": "Next",
        "job_role": "Backend Engineer",
        "company_name": "Acme",
        "created_at": datetime(2026, 1, 1, tzinfo=UTC),
        "ended_at": None,
        "transcript": entries,
    }
    defaults.update(overrides)
    return InterviewSessionDetail.model_construct(**defaults)


def test_build_report_pdf_returns_a_pdf_document() -> None:
    pdf = build_report_pdf(_report(), _detail())

    assert pdf.startswith(b"%PDF")


def test_build_report_pdf_handles_ended_early_and_no_company_or_hints() -> None:
    report = _report(
        end_reason="abusive_language",
        end_reason_label="Ended early: abusive language",
        hint_counts={},
        recommendation_tier="mystery_tier",
    )

    pdf = build_report_pdf(report, _detail(company_name=None))

    assert pdf.startswith(b"%PDF")


def test_markup_escapes_tags_and_converts_newlines() -> None:
    assert _markup("a <b> & c\nd") == "a &lt;b&gt; &amp; c<br/>d"


def test_score_color_bands() -> None:
    assert _score_color(90) == _score_color(70)
    assert _score_color(60) == _score_color(55)
    assert _score_color(90) != _score_color(60)
    assert _score_color(60) != _score_color(10)


def test_citations_by_index_skips_evidence_without_an_index() -> None:
    citations = _citations_by_index(_report())

    assert set(citations) == {1}
    assert ("Project Depth", "Specific") in citations[1]
    assert all(reasoning != "Vague" for _, reasoning in citations[1])
