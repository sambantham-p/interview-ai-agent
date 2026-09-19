INTERVIEW_PHASES = [
    "background_check",
    "project_drill_down",
    "technical_interview",
    "coding_challenge",
    "general_technical",
    "career_motivation",
    "candidate_questions",
]

SESSION_STATUS_IN_PROGRESS = "in_progress"
SESSION_STATUS_COMPLETED = "completed"
SESSION_STATUS_ENDED_EARLY = "ended_early"
SESSION_STATUSES = [
    SESSION_STATUS_IN_PROGRESS,
    SESSION_STATUS_COMPLETED,
    SESSION_STATUS_ENDED_EARLY,
]
# Statuses of an interview that is over (no more turns, report allowed).
FINISHED_SESSION_STATUSES = [SESSION_STATUS_COMPLETED, SESSION_STATUS_ENDED_EARLY]

HINT_LEVELS = [1, 2, 3]

# Score penalty applied when a hint is given, keyed by hint level:
# 1 -> 0.05 (nudge), 2 -> 0.15 (partial hint), 3 -> 0.3 (direct hint).
HINT_PENALTY_BY_LEVEL = {1: 0.05, 2: 0.15, 3: 0.3}

DEFAULT_RED_FLAG_THRESHOLD = 5

CODING_PHASE_ALLOWED_DIFFICULTIES = ["easy", "medium"]

LLM_TASK_INTERVIEWER = "interviewer"

CODING_PHASE = "coding_challenge"

# Each preset ties an ordered subset of INTERVIEW_PHASES to the only
# durations (minutes) it may be run for.
INTERVIEW_PRESETS: dict[str, dict] = {
    "quick_project_deep_dive": {
        "label": "Quick Project Deep-Dive",
        "description": "A focused drill-down into one or two of your projects.",
        "phases": ["project_drill_down"],
        "durations": [5, 10],
    },
    "coding_only": {
        "label": "Coding Only",
        "description": "One algorithmic question, discussed end to end.",
        "phases": ["coding_challenge"],
        "durations": [5, 10],
    },
    "technical_round": {
        "label": "Technical Round",
        "description": "Role-specific technical, coding, and fundamentals questions.",
        "phases": ["technical_interview", "coding_challenge", "general_technical"],
        "durations": [15, 20, 25],
    },
    "project_coding_combo": {
        "label": "Project + Coding Combo",
        "description": "A project deep-dive followed by a coding discussion.",
        "phases": ["project_drill_down", "coding_challenge"],
        "durations": [15, 20],
    },
    "full_loop_no_coding": {
        "label": "Full Loop (no coding)",
        "description": "Every interview phase except the coding discussion.",
        "phases": [
            "background_check",
            "project_drill_down",
            "technical_interview",
            "general_technical",
            "career_motivation",
            "candidate_questions",
        ],
        "durations": [25, 30, 35],
    },
    "full_loop": {
        "label": "Full Loop (all 7 phases)",
        "description": "The complete interview, start to finish.",
        "phases": INTERVIEW_PHASES,
        "durations": [30, 35, 40],
    },
}

# Relative importance of each phase when a preset's duration is split.
PHASE_TIME_WEIGHTS = {
    "background_check": 1,
    "project_drill_down": 3,
    "technical_interview": 3,
    "coding_challenge": 3,
    "general_technical": 2,
    "career_motivation": 1,
    "candidate_questions": 1,
}

# Fractions of a phase's budget: at LOW the agent is told to ask only its
# single most important remaining question; at EXHAUSTED it must wrap up;
# at FORCE_COMPLETE the server ends the phase regardless of the agent.
PHASE_TIME_LOW_FRACTION = 0.7
PHASE_TIME_EXHAUSTED_FRACTION = 1.0
PHASE_TIME_FORCE_COMPLETE_FRACTION = 1.5

PHASE_LABELS = {
    "background_check": "Background Check",
    "project_drill_down": "Project Drill-Down",
    "technical_interview": "Technical Interview",
    "coding_challenge": "Coding Discussion",
    "general_technical": "General Technical",
    "career_motivation": "Career Motivation",
    "candidate_questions": "Candidate Questions",
}

# A spoken answer may use up to this fraction of the interview's total
# duration, bounded by the minimum and maximum values below. For interviews
# with no time limit, use the fixed default duration.
ANSWER_MAX_FRACTION_OF_INTERVIEW = 1 / 4
ANSWER_MAX_SECONDS_FLOOR = 180
ANSWER_MAX_SECONDS_CEILING = 480
ANSWER_MAX_SECONDS_UNTIMED = 300
