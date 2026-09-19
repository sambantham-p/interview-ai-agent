
export interface HealthCheck {
  service: string
  health: string
}

export interface EducationEntry {
  institution: string
  degree: string
  field_of_study: string | null
  start_date: string | null
  end_date: string | null
}

export interface ExperienceEntry {
  company: string
  role: string
  start_date: string | null
  end_date: string | null
  description: string | null
}

export interface ProjectEntry {
  name: string
  description: string | null
  tech_stack: string[]
  repo_url: string | null
}

export interface Resume {
  id: number
  education: EducationEntry[]
  experience: ExperienceEntry[]
  projects: ProjectEntry[]
  skills: string[]
  github_url: string | null
  missing_sections: string[]
  created_at: string
}

export type Seniority = 'intern' | 'entry' | 'mid' | 'senior' | 'fresher'

export interface JobDescription {
  id: number
  role: string
  company_name: string | null
  seniority: Seniority
  tech_stack: string[]
  coding_assessment_expected: boolean
  missing_details: string[]
  created_at: string
}

export type InterviewPhase =
  | 'background_check'
  | 'project_drill_down'
  | 'technical_interview'
  | 'coding_challenge'
  | 'general_technical'
  | 'career_motivation'
  | 'candidate_questions'

export type InterviewStatus = 'in_progress' | 'completed' | 'ended_early'

export type InterviewEndReason = 'abusive_language' | 'red_flag_threshold' | null

export interface InterviewSessionSummary {
  id: number
  candidate_profile_id: number
  job_description_id: number
  current_phase: InterviewPhase
  status: InterviewStatus
  end_reason: InterviewEndReason
  created_at: string
  ended_at: string | null
}

export interface InterviewPreset {
  key: string
  label: string
  description: string
  phases: InterviewPhase[]
  durations: number[]
  includes_coding: boolean
}

export interface InterviewStartRequest {
  candidate_profile_id: number
  job_description_id: number
  preset_key: string
  duration_minutes: number
}

export type PhaseTimeStatus = 'comfortable' | 'running_low' | 'exhausted'

export interface InterviewTurn {
  id: number
  current_phase: InterviewPhase
  status: InterviewStatus
  red_flag_count: number
  red_flag_warning_issued: boolean
  hint_counts: Record<string, number>
  end_reason: InterviewEndReason
  reply: string
  hint_level: number | null
  red_flag: boolean
  severe_red_flag: boolean
  anxiety_detected: boolean
  selected_phases: InterviewPhase[]
  duration_minutes: number | null
  phase_time_budget: Record<string, number>
  phase_started_at: string | null
  phase_time_status: PhaseTimeStatus | null
  max_answer_seconds: number
  server_time: string
  ended_at: string | null
}

export type InterviewStartResponse = InterviewTurn

export interface TranscriptEntry {
  index: number
  role: 'user' | 'model'
  text: string
  phase: InterviewPhase | null
  hint_level: number | null
  red_flag: boolean
  anxiety_detected: boolean
}

export interface InterviewDetail extends InterviewTurn {
  job_role: string
  company_name: string | null
  created_at: string
  transcript: TranscriptEntry[]
}

export interface SpeechToTextResult {
  text: string
}

export type RecommendationTier = 'strong_hire' | 'hire' | 'borderline' | 'no_hire'

export interface JudgeEvidenceItem {
  quote: string
  transcript_index: number | null
  reasoning: string
}

export interface JudgeEvaluation {
  id: number
  session_id: number
  judge_name: string
  dimension: string
  score: number
  summary: string
  evidence: JudgeEvidenceItem[]
}

export interface InterviewReport {
  id: number
  session_id: number
  overall_score: number
  recommendation_tier: RecommendationTier
  recommendation_label: string
  headline: string
  strength_dimensions: string[]
  focus_dimensions: string[]
  weights_used: Record<string, number>
  judge_evaluations: JudgeEvaluation[]
  hint_counts: Record<string, number>
  red_flag_count: number
  end_reason: InterviewEndReason
  end_reason_label: string | null
}

export interface ReportListItem {
  session_id: number
  status: InterviewStatus
  end_reason: InterviewEndReason
  end_reason_label: string | null
  job_role: string
  company_name: string | null
  created_at: string
  ended_at: string | null
  duration_minutes: number | null
  hint_count: number
  red_flag_count: number
  report_id: number | null
  overall_score: number | null
  recommendation_tier: RecommendationTier | null
  recommendation_label: string | null
}
