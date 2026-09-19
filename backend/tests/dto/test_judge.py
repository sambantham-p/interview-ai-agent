import pytest
from pydantic import ValidationError

from app.dto.judge import JudgeEvidenceItem, JudgeOutput


def test_judge_output_accepts_a_valid_score_and_evidence() -> None:
    output = JudgeOutput(
        score=72.5,
        summary="Solid grasp of the core approach, fuzzy on edge cases.",
        evidence=[
            JudgeEvidenceItem(
                quote="I'd use a hash map for O(1) lookups",
                transcript_index=4,
                reasoning="Correctly justified the data structure choice.",
            )
        ],
    )

    assert output.score == 72.5
    assert len(output.evidence) == 1


def test_judge_output_rejects_score_above_100() -> None:
    with pytest.raises(ValidationError):
        JudgeOutput(
            score=101,
            summary="x",
            evidence=[JudgeEvidenceItem(quote="q", reasoning="r")],
        )


def test_judge_output_rejects_score_below_zero() -> None:
    with pytest.raises(ValidationError):
        JudgeOutput(
            score=-1,
            summary="x",
            evidence=[JudgeEvidenceItem(quote="q", reasoning="r")],
        )


def test_judge_output_rejects_empty_evidence_list() -> None:
    with pytest.raises(ValidationError):
        JudgeOutput(score=50, summary="x", evidence=[])


def test_judge_evidence_item_transcript_index_defaults_to_none() -> None:
    item = JudgeEvidenceItem(quote="q", reasoning="r")

    assert item.transcript_index is None
