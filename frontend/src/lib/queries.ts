import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { api } from './api'
import type {
  InterviewPreset,
  InterviewSessionSummary,
  JobDescription,
  Resume,
} from '../types/api'

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
    gcTime: 0,
  })
}

export function useInterviewPresets(codingAssessmentExpected: boolean) {
  return useQuery({
    queryKey: ['interview-presets', codingAssessmentExpected],
    queryFn: () =>
      api.get<InterviewPreset[]>(
        `/interview/presets?coding_assessment_expected=${codingAssessmentExpected}`,
      ),
  })
}

export type DocumentKind = 'resume' | 'job description'

const DOCUMENT_ENDPOINTS = {
  resume: { path: '/resume', queryKey: 'resumes' },
  'job description': { path: '/jd', queryKey: 'job-descriptions' },
} as const


export function useDeleteDocument(kind: DocumentKind) {
  const queryClient = useQueryClient()
  const { path, queryKey } = DOCUMENT_ENDPOINTS[kind]

  return useMutation({
    mutationFn: (id: number) => api.delete<{ id: number }>(`${path}/${id}`),
    onSuccess: (_data, id) => {
      queryClient.setQueryData<{ id: number }[]>([queryKey], (old) =>
        old?.filter((doc) => doc.id !== id),
      )
      void queryClient.invalidateQueries({ queryKey: [queryKey] })
    },
  })
}
