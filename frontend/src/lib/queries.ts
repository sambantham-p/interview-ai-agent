import { useQuery } from '@tanstack/react-query'
import { api } from './api'
import type { InterviewSessionSummary, JobDescription, Resume } from '../types/api'

export function useResumes() {
  return useQuery({
    queryKey: ['resumes'],
    queryFn: () => api.get<Resume[]>('/resume'),
  })
}

export function useJobDescriptions() {
  return useQuery({
    queryKey: ['job-descriptions'],
    queryFn: () => api.get<JobDescription[]>('/jd'),
  })
}

export function useInterviews() {
  return useQuery({
    queryKey: ['interviews'],
    queryFn: () => api.get<InterviewSessionSummary[]>('/interview'),
  })
}
