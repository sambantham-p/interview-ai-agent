import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { ApiRequestError, api } from './api'
import { toErrorMessage } from './errorMessage'
import { useToast } from './toastContext'
import type {
  InterviewDetail,
  InterviewPreset,
  InterviewReport,
  InterviewSessionSummary,
  JobDescription,
  ReportListItem,
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

export function useInterview(sessionId: string | undefined) {
  return useQuery({
    queryKey: ['interview', sessionId],
    queryFn: () => api.get<InterviewDetail>(`/interview/${sessionId}`),
    enabled: Boolean(sessionId),
    staleTime: Infinity,
  })
}

export function useReports() {
  return useQuery({
    queryKey: ['reports'],
    queryFn: () => api.get<ReportListItem[]>('/reports'),
    gcTime: 0,
  })
}

export function useInterviewReport(sessionId: string | undefined) {
  return useQuery({
    queryKey: ['interview-report', sessionId],
    queryFn: () => api.get<InterviewReport>(`/interview/${sessionId}/report`),
    enabled: Boolean(sessionId),
    retry: (failureCount, error) =>
      !(error instanceof ApiRequestError && error.statusCode === 404) && failureCount < 2,
  })
}


export function useGenerateReport(sessionId: string | undefined) {
  const queryClient = useQueryClient()
  const { showToast } = useToast()

  return useMutation({
    mutationFn: async () => {
      try {
        return await api.get<InterviewReport>(`/interview/${sessionId}/report`)
      } catch (error) {
        if (!(error instanceof ApiRequestError && error.statusCode === 404)) throw error
        return api.post<InterviewReport>(`/interview/${sessionId}/report`, {})
      }
    },
    onSuccess: (report) => {
      queryClient.setQueryData(['interview-report', sessionId], report)
      void queryClient.invalidateQueries({ queryKey: ['interviews'] })
      void queryClient.invalidateQueries({ queryKey: ['reports'] })
    },
    onError: (error) => showToast(toErrorMessage(error, 'Could not generate the report.'), 'error'),
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
  const { showToast } = useToast()
  const { path, queryKey } = DOCUMENT_ENDPOINTS[kind]

  return useMutation({
    mutationFn: (id: number) => api.delete<{ id: number }>(`${path}/${id}`),
    onSuccess: (_data, id) => {
      queryClient.setQueryData<{ id: number }[]>([queryKey], (old) =>
        old?.filter((doc) => doc.id !== id),
      )
      void queryClient.invalidateQueries({ queryKey: [queryKey] })
      showToast(`${kind.charAt(0).toUpperCase()}${kind.slice(1)} deleted`)
    },
  })
}
