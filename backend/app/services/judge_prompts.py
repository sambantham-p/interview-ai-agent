"""Prompt/instruction text for the 5 post-hoc Judge agents.

Kept separate from judge_service.py so the orchestration logic (transcript
slicing, hint-penalty math, weighted aggregation) and the prompt text
(expected to see iteration as these judges are tuned) can be edited
independently - mirrors interview_prompts.py's split from
interview_service.py.
"""

from app.constants.interview import HINT_PENALTY_BY_LEVEL

JUDGE_COMMON_INSTRUCTIONS = (
    "You are an expert technical interview evaluator scoring one finished "
    "interview transcript on a single dimension. Score 0-100. You MUST "
    "cite at least one specific excerpt from the transcript as evidence "
    "for your score and never give a score with no supporting quote. Be "
    "calibrated and skeptical of a scripted or memorized-sounding answer, "
    "but do not penalize incomplete fine detail when the candidate "
    "clearly grasped the core idea."
)

PROJECT_DEPTH_INSTRUCTIONS = (
    "Score the candidate's demonstrated depth of understanding of the "
    "project(s) discussed in this Project Drill-Down transcript segment. "
    "Track where their answers broke down from surface-level to "
    "functional to deep to expert understanding, and cite the excerpt "
    "where that breaking point (or lack of one, for a strong answer) "
    "occurred. Reward getting the intent and core reasoning behind a "
    "decision right, even if a fine implementation detail is fuzzy and do "
    "not penalize incompleteness on its own."
)

CODING_INSTRUCTIONS = (
    "Score the candidate's coding discussion based on the transcript "
    "alone - there is no executed code to check, only what they said. "
    "Weigh: did they explain a workable approach, did they correctly "
    "state the time/space complexity, and could they justify why they "
    "chose that data structure or approach over alternatives. An answer "
    "that sounds correct but can't justify its own complexity or "
    "reasoning should score as memorized, not understood."
)

FUNDAMENTALS_INSTRUCTIONS = (
    "Score the candidate's technical/fundamentals answers across both "
    "the Technical Interview and General Technical transcript segments "
    "combined - role/domain-specific questions and core CS fundamentals. "
    "Calibrate to the seniority level given below."
)

ATTITUDE_INSTRUCTIONS = (
    "Score the candidate's attitude and communication across the ENTIRE "
    "interview: confidence, defensiveness, honesty, over-claiming, and "
    "empathy toward their own delivery signals (stammering, hesitation, "
    "nervousness) - do not penalize nervousness itself as if it were a "
    "wrong answer. Give ONE blended score, not separate sub-scores. You "
    "are given the session's ordinary red_flag_count, whether a severe "
    "red flag (abusive language) ended the interview, and per-phase hint "
    "counts as context below - factor red flag count into your "
    "qualitative judgment, but do NOT apply any hint-level penalty "
    "arithmetic yourself; that is handled separately after your score."
)

CAREER_FIT_INSTRUCTIONS = (
    "Score how consistent the candidate's stated career goals (from the "
    "Career Motivation and Candidate Questions transcript segments) are "
    "with both the job description below and their own behavior/answers "
    "earlier in the interview. Flag inconsistency with earlier phases as "
    "evidence, not just a mismatch with the JD."
)


def build_judge_system_instruction(
    dimension_instructions: str,
    *,
    job_description_summary: str,
    extra_context: str | None = None,
) -> str:
    parts = [JUDGE_COMMON_INSTRUCTIONS, dimension_instructions, job_description_summary]
    if extra_context:
        parts.append(extra_context)
    return "\n\n".join(parts)


def build_attitude_context(
    *, red_flag_count: int, severe_red_flag: bool, hint_counts: dict[str, int]
) -> str:
    hint_summary = (
        ", ".join(f"{phase}={count}" for phase, count in hint_counts.items()) or "none"
    )
    return (
        f"Ordinary red_flag_count for this session: {red_flag_count}. "
        f"Severe red flag (abusive language) ended the interview: {severe_red_flag}. "
        f"Hint counts by phase: {hint_summary}. Hint penalty reference "
        f"(applied separately, not by you): {HINT_PENALTY_BY_LEVEL}."
    )
