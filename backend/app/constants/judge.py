JUDGE_PROJECT_DEPTH = "project_depth"
JUDGE_CODING = "coding"
JUDGE_FUNDAMENTALS = "fundamentals"
JUDGE_ATTITUDE = "attitude"
JUDGE_CAREER_FIT = "career_fit"

JUDGE_NAMES = [
    JUDGE_PROJECT_DEPTH,
    JUDGE_CODING,
    JUDGE_FUNDAMENTALS,
    JUDGE_ATTITUDE,
    JUDGE_CAREER_FIT,
]

LLM_TASK_JUDGE_PROJECT_DEPTH = "judge_project_depth"
LLM_TASK_JUDGE_CODING = "judge_coding"
LLM_TASK_JUDGE_FUNDAMENTALS = "judge_fundamentals"
LLM_TASK_JUDGE_ATTITUDE = "judge_attitude"
LLM_TASK_JUDGE_CAREER_FIT = "judge_career_fit"

# Transcript phases each judge evaluates; None means the full transcript.
JUDGE_PHASES: dict[str, list[str] | None] = {
    JUDGE_PROJECT_DEPTH: ["project_drill_down"],
    JUDGE_CODING: ["coding_challenge"],
    JUDGE_FUNDAMENTALS: ["technical_interview", "general_technical"],
    JUDGE_ATTITUDE: None,
    JUDGE_CAREER_FIT: ["career_motivation", "candidate_questions"],
}

# Weights used for the overall score; must sum to 1.0.
JUDGE_WEIGHTS = {
    JUDGE_FUNDAMENTALS: 0.25,
    JUDGE_PROJECT_DEPTH: 0.25,
    JUDGE_CODING: 0.20,
    JUDGE_ATTITUDE: 0.15,
    JUDGE_CAREER_FIT: 0.15,
}

# Overall score thresholds, evaluated from highest to lowest.
RECOMMENDATION_TIERS = [
    (85, "strong_hire"),
    (70, "hire"),
    (55, "borderline"),
    (0, "no_hire"),
]

# Maximum attitude score when the session ends for abusive language.
ATTITUDE_ABUSIVE_LANGUAGE_SCORE_CAP = 10
