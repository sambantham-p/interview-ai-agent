INTERVIEW_PHASES = [
    "background_check",
    "project_drill_down",
    "technical_interview",
    "coding_challenge",
    "general_technical",
    "career_motivation",
    "candidate_questions",
]

HINT_LEVELS = [1, 2, 3]

# Score penalty applied when a hint is given, keyed by hint level:
# 1 -> 0.05 (nudge), 2 -> 0.15 (partial hint), 3 -> 0.3 (direct hint).
HINT_PENALTY_BY_LEVEL = {1: 0.05, 2: 0.15, 3: 0.3}

DEFAULT_RED_FLAG_THRESHOLD = 5

CODING_PHASE_ALLOWED_DIFFICULTIES = ["easy", "medium"]

LLM_TASK_INTERVIEWER = "interviewer"
