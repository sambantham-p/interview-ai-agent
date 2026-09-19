import type {
  InterviewDetail,
  InterviewReport,
  InterviewTurn,
  JudgeEvaluation,
  ReportListItem,
  TranscriptEntry,
} from '../types/api'

export function buildTurn(overrides: Partial<InterviewTurn> = {}): InterviewTurn {
  return {
    id: 7,
    current_phase: 'background_check',
    status: 'in_progress',
    red_flag_count: 0,
    red_flag_warning_issued: false,
    hint_counts: {},
    end_reason: null,
    reply: 'Welcome. Tell me about yourself.',
    hint_level: null,
    red_flag: false,
    severe_red_flag: false,
    anxiety_detected: false,
    selected_phases: ['background_check', 'technical_interview'],
    duration_minutes: 20,
    phase_time_budget: { background_check: 8, technical_interview: 12 },
    phase_started_at: '2026-01-01T10:00:00Z',
    phase_time_status: 'comfortable',
    max_answer_seconds: 300,
    server_time: '2026-01-01T10:01:00Z',
    ended_at: null,
    ...overrides,
  }
}

export function buildEntry(overrides: Partial<TranscriptEntry> = {}): TranscriptEntry {
  return {
    index: 1,
    role: 'model',
    text: 'Welcome. Tell me about yourself.',
    phase: 'background_check',
    hint_level: null,
    red_flag: false,
    anxiety_detected: false,
    ...overrides,
  }
}

export function buildDetail(overrides: Partial<InterviewDetail> = {}): InterviewDetail {
  return {
    ...buildTurn(),
    job_role: 'Backend Engineer',
    company_name: 'Acme',
    created_at: '2026-01-01T10:00:00Z',
    transcript: [
      buildEntry({ index: 1 }),
      buildEntry({ index: 2, role: 'user', text: 'I build APIs.' }),
    ],
    ...overrides,
  }
}

export function buildEvaluation(overrides: Partial<JudgeEvaluation> = {}): JudgeEvaluation {
  return {
    id: 1,
    session_id: 7,
    judge_name: 'project_depth',
    dimension: 'Project Depth',
    score: 82,
    summary: 'Solid understanding of the project.',
    evidence: [{ quote: 'I build APIs.', transcript_index: 2, reasoning: 'Concrete answer.' }],
    ...overrides,
  }
}

export function buildReport(overrides: Partial<InterviewReport> = {}): InterviewReport {
  return {
    id: 3,
    session_id: 7,
    overall_score: 74,
    recommendation_tier: 'hire',
    recommendation_label: 'Hire',
    headline: 'Strongest in Project Depth. Most room to grow in Coding.',
    strength_dimensions: ['project_depth'],
    focus_dimensions: ['coding'],
    weights_used: { project_depth: 0.25, coding: 0.2 },
    judge_evaluations: [
      buildEvaluation(),
      buildEvaluation({
        id: 2,
        judge_name: 'coding',
        dimension: 'Coding',
        score: 48,
        summary: 'Needs work on complexity.',
        evidence: [{ quote: 'no idea', transcript_index: null, reasoning: 'Vague.' }],
      }),
    ],
    hint_counts: { technical_interview: 2 },
    red_flag_count: 1,
    end_reason: null,
    end_reason_label: null,
    ...overrides,
  }
}

export function buildReportListItem(overrides: Partial<ReportListItem> = {}): ReportListItem {
  return {
    session_id: 7,
    status: 'completed',
    end_reason: null,
    end_reason_label: null,
    job_role: 'Backend Engineer',
    company_name: 'Acme',
    created_at: '2026-01-01T10:00:00Z',
    ended_at: '2026-01-01T10:30:00Z',
    duration_minutes: 30,
    hint_count: 2,
    red_flag_count: 1,
    report_id: 3,
    overall_score: 74,
    recommendation_tier: 'hire',
    recommendation_label: 'Hire',
    ...overrides,
  }
}
