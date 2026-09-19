
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

export interface InterviewStartResponse {
  id: number
  current_phase: InterviewPhase
  status: InterviewStatus
  reply: string
}
