from pydantic import BaseModel, ConfigDict, Field


class InterviewTurnOutput(BaseModel):
    """Structured-output schema for one Interviewer agent turn.

    The agent makes every live judgment call itself in this single
    payload, no separate watcher agent - reply is the natural-language
    text shown to the candidate, everything else is a mechanical flag
    the service layer acts on (hint penalty, red-flag counting, phase
    advancement).
    """

    reply: str = Field(description="The interviewer's next message to the candidate.")
    phase_complete: bool = Field(
        description="True once this phase has covered enough ground to move on."
    )
    hint_level: int | None = Field(
        default=None,
        description=(
            "1, 2, or 3 if this reply gave a hint because the candidate seemed "
            "stuck (silence, 'I don't know', stammering, long hesitation) - "
            "escalate the level only after a prior hint at a lower level didn't "
            "help. None if no hint was given."
        ),
    )
    red_flag: bool = Field(
        description=(
            "True if this turn revealed an ordinary red flag: a claim "
            "contradicting the candidate's resume/profile, or fundamentals far "
            "below the seniority claimed. Do NOT use this for abusive/vulgar "
            "language - use severe_red_flag for that instead."
        ),
    )
    red_flag_reason: str | None = Field(
        default=None, description="One sentence, required when red_flag is true."
    )
    severe_red_flag: bool = Field(
        default=False,
        description=(
            "True ONLY if the candidate's message itself contained abusive, "
            "vulgar, harassing, or deliberately insulting language directed at "
            "the interviewer or the process - not for a merely wrong, dishonest, "
            "or low-quality answer (use red_flag for those). This ends the "
            "interview immediately, with no warning step, so only set it for "
            "genuine profanity/harassment, never as a stronger version of an "
            "ordinary red flag."
        ),
    )
    severe_red_flag_reason: str | None = Field(
        default=None,
        description="One sentence, required when severe_red_flag is true.",
    )
    anxiety_detected: bool = Field(
        description=(
            "True if the candidate's answer showed high anxiety (stammering, "
            "hesitation, rushed/garbled phrasing) - when true, reply should "
            "pause and reassure before continuing, not just note it."
        )
    )


class InterviewStartRequest(BaseModel):
    candidate_profile_id: int
    job_description_id: int


class InterviewTurnRequest(BaseModel):
    message: str = Field(min_length=1)


class InterviewTurnResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    current_phase: str
    status: str
    red_flag_count: int
    hint_counts: dict[str, int]
    end_reason: str | None
    reply: str
