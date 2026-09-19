from datetime import UTC, datetime

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.services.interview_presets import max_answer_seconds, session_phase_time_status


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
        ge=1,
        le=3,
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
    """preset_key and duration_minutes go together; omitting both runs
    the full seven-phase interview with no time budget.
    """

    candidate_profile_id: int
    job_description_id: int
    preset_key: str | None = None
    duration_minutes: int | None = Field(default=None, gt=0)

    @model_validator(mode="after")
    def check_preset_and_duration_together(self) -> "InterviewStartRequest":
        if (self.preset_key is None) != (self.duration_minutes is None):
            raise ValueError("Provide preset_key and duration_minutes together")
        return self


class InterviewPresetResponse(BaseModel):
    key: str
    label: str
    description: str
    phases: list[str]
    durations: list[int]
    includes_coding: bool


class InterviewTurnRequest(BaseModel):
    message: str = Field(min_length=1)


class InterviewTurnResponse(BaseModel):
    """The interviewer's latest reply plus the session state the live
    interview screen needs: this turn's judgment flags and the phase
    timing, alongside the running aggregates.
    """

    model_config = ConfigDict(from_attributes=True)

    id: int
    current_phase: str
    status: str
    red_flag_count: int
    red_flag_warning_issued: bool
    hint_counts: dict[str, int]
    end_reason: str | None
    reply: str
    hint_level: int | None
    red_flag: bool
    severe_red_flag: bool
    anxiety_detected: bool
    selected_phases: list[str]
    duration_minutes: int | None
    phase_time_budget: dict[str, float]
    phase_started_at: datetime | None
    phase_time_status: str | None
    max_answer_seconds: int
    server_time: datetime
    ended_at: datetime | None

    @classmethod
    def from_session(cls, session: object) -> "InterviewTurnResponse":
        latest = session.transcript[-1]
        now = datetime.now(UTC)
        time_status, _ = session_phase_time_status(session, now)
        return cls(
            id=session.id,
            current_phase=session.current_phase,
            status=session.status,
            red_flag_count=session.red_flag_count,
            red_flag_warning_issued=session.red_flag_warning_issued,
            hint_counts=session.hint_counts,
            end_reason=session.end_reason,
            reply=latest["text"],
            hint_level=latest.get("hint_level"),
            red_flag=latest.get("red_flag", False),
            severe_red_flag=latest.get("severe_red_flag", False),
            anxiety_detected=latest.get("anxiety_detected", False),
            selected_phases=session.selected_phases,
            duration_minutes=session.duration_minutes,
            phase_time_budget=session.phase_time_budget,
            phase_started_at=session.phase_started_at,
            phase_time_status=time_status,
            max_answer_seconds=max_answer_seconds(session.duration_minutes),
            server_time=now,
            ended_at=session.ended_at,
        )


def build_turn_response(session: object) -> InterviewTurnResponse:
    """Build the API DTO for the latest interviewer reply in a session."""
    return InterviewTurnResponse.from_session(session)


class TranscriptEntry(BaseModel):
    """One displayable transcript message. `index` is its position in the
    session's full stored transcript - the same index the Judges cite as
    `transcript_index` in their evidence.
    """

    index: int
    role: str
    text: str
    phase: str | None = None
    hint_level: int | None = None
    red_flag: bool = False
    anxiety_detected: bool = False


class InterviewSessionDetail(InterviewTurnResponse):
    """A full session for the live interview and report screens: the
    turn-response state plus the displayable transcript and the job it
    was run for.
    """

    job_role: str
    company_name: str | None
    created_at: datetime
    transcript: list[TranscriptEntry]


def build_session_detail(
    session: object, job_description: object
) -> InterviewSessionDetail:
    """Build the detail DTO, leaving out the synthetic opening prompt
    (the only stored user entry that isn't a candidate answer).
    """
    entries = [
        TranscriptEntry(
            index=index,
            role=entry["role"],
            text=entry["text"],
            phase=entry.get("phase"),
            hint_level=entry.get("hint_level"),
            red_flag=entry.get("red_flag", False),
            anxiety_detected=entry.get("anxiety_detected", False),
        )
        for index, entry in enumerate(session.transcript)
        if "phase" in entry
    ]
    turn = InterviewTurnResponse.from_session(session)
    return InterviewSessionDetail(
        **turn.model_dump(),
        job_role=job_description.role,
        company_name=job_description.company_name,
        created_at=session.created_at,
        transcript=entries,
    )


class InterviewSessionSummary(BaseModel):
    """Response DTO for GET /interview (list) - lighter than
    InterviewTurnResponse, no reply/transcript content, just enough to
    render a dashboard/documents list row.
    """

    model_config = ConfigDict(from_attributes=True)

    id: int
    candidate_profile_id: int
    job_description_id: int
    current_phase: str
    status: str
    end_reason: str | None
    created_at: datetime
    ended_at: datetime | None
