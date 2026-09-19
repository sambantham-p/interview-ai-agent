import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { act, renderHook, waitFor } from '@testing-library/react'
import type { ReactNode } from 'react'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { ApiRequestError } from './api'
import {
  useDeleteDocument,
  useGenerateReport,
  useInterview,
  useInterviewPresets,
  useInterviewReport,
  useInterviews,
  useJobDescriptions,
  useReports,
  useResumes,
} from './queries'
import { ToastProvider } from './ToastProvider'

const { mockGet, mockPost, mockDelete } = vi.hoisted(() => ({
  mockGet: vi.fn<(...args: unknown[]) => unknown>(),
  mockPost: vi.fn<(...args: unknown[]) => unknown>(),
  mockDelete: vi.fn<(...args: unknown[]) => unknown>(),
}))

vi.mock('./api', async () => {
  const actual = await vi.importActual<typeof import('./api')>('./api')
  return { ...actual, api: { get: mockGet, post: mockPost, delete: mockDelete } }
})

function setup() {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  const wrapper = ({ children }: { children: ReactNode }) => (
    <QueryClientProvider client={client}>
      <ToastProvider>{children}</ToastProvider>
    </QueryClientProvider>
  )
  return { client, wrapper }
}

describe('queries', () => {
  beforeEach(() => {
    mockGet.mockReset()
    mockPost.mockReset()
    mockDelete.mockReset()
  })

  it.each([
    ['useResumes', useResumes, '/resume'],
    ['useJobDescriptions', useJobDescriptions, '/jd'],
    ['useInterviews', useInterviews, '/interview'],
    ['useReports', useReports, '/reports'],
  ])('%s fetches its list endpoint', async (_name, hook, path) => {
    mockGet.mockResolvedValue([{ id: 1 }])
    const { wrapper } = setup()

    const { result } = renderHook(() => hook(), { wrapper })

    await waitFor(() => expect(result.current.data).toEqual([{ id: 1 }]))
    expect(mockGet).toHaveBeenCalledWith(path)
  })

  it('useInterview and useInterviewReport are disabled without a session id', () => {
    const { wrapper } = setup()

    const interview = renderHook(() => useInterview(undefined), { wrapper })
    const report = renderHook(() => useInterviewReport(undefined), { wrapper })

    expect(interview.result.current.fetchStatus).toBe('idle')
    expect(report.result.current.fetchStatus).toBe('idle')
    expect(mockGet).not.toHaveBeenCalled()
  })

  it('useInterview and useInterviewReport fetch by session id', async () => {
    mockGet.mockResolvedValue({ id: 5 })
    const { wrapper } = setup()

    const interview = renderHook(() => useInterview('5'), { wrapper })
    const report = renderHook(() => useInterviewReport('5'), { wrapper })

    await waitFor(() => expect(interview.result.current.data).toEqual({ id: 5 }))
    await waitFor(() => expect(report.result.current.data).toEqual({ id: 5 }))
    expect(mockGet).toHaveBeenCalledWith('/interview/5')
    expect(mockGet).toHaveBeenCalledWith('/interview/5/report')
  })

  it('useInterviewPresets passes the coding filter', async () => {
    mockGet.mockResolvedValue([])
    const { wrapper } = setup()

    renderHook(() => useInterviewPresets(false), { wrapper })

    await waitFor(() =>
      expect(mockGet).toHaveBeenCalledWith('/interview/presets?coding_assessment_expected=false'),
    )
  })

  it('useInterviewReport does not retry a 404 (no report yet)', async () => {
    mockGet.mockRejectedValue(new ApiRequestError('none', 404))
    const { wrapper } = setup()

    const { result } = renderHook(() => useInterviewReport('5'), { wrapper })

    await waitFor(() => expect(result.current.isError).toBe(true))
    expect(mockGet).toHaveBeenCalledTimes(1)
  })

  it('useInterviewReport keeps retrying other failures', async () => {
    mockGet.mockRejectedValue(new ApiRequestError('server down', 500))
    const { wrapper } = setup()

    const { result } = renderHook(() => useInterviewReport('5'), { wrapper })

    await waitFor(() => expect(result.current.failureCount).toBe(1))
    expect(result.current.isError).toBe(false)
  })

  describe('useGenerateReport', () => {
    it('reuses an existing report without creating another', async () => {
      const report = { id: 9 }
      mockGet.mockResolvedValue(report)
      const { client, wrapper } = setup()
      const { result } = renderHook(() => useGenerateReport('5'), { wrapper })

      await act(async () => {
        await result.current.mutateAsync()
      })

      expect(mockPost).not.toHaveBeenCalled()
      expect(client.getQueryData(['interview-report', '5'])).toEqual(report)
    })

    it('generates a report when none exists yet (404)', async () => {
      mockGet.mockRejectedValue(new ApiRequestError('none', 404))
      mockPost.mockResolvedValue({ id: 10 })
      const { client, wrapper } = setup()
      const { result } = renderHook(() => useGenerateReport('5'), { wrapper })

      await act(async () => {
        await result.current.mutateAsync()
      })

      expect(mockPost).toHaveBeenCalledWith('/interview/5/report', {})
      expect(client.getQueryData(['interview-report', '5'])).toEqual({ id: 10 })
    })

    it('shows an error toast for any other failure', async () => {
      mockGet.mockRejectedValue(new ApiRequestError('server down', 500))
      const { wrapper } = setup()
      const { result } = renderHook(() => useGenerateReport('5'), { wrapper })

      await act(async () => {
        await result.current.mutateAsync().catch(() => undefined)
      })

      expect(mockPost).not.toHaveBeenCalled()
      await waitFor(() => expect(result.current.isError).toBe(true))
    })
  })

  describe('useDeleteDocument', () => {
    it('removes the deleted row from the cached list', async () => {
      mockDelete.mockResolvedValue({ id: 2 })
      const { client, wrapper } = setup()
      client.setQueryData(['resumes'], [{ id: 1 }, { id: 2 }])
      const { result } = renderHook(() => useDeleteDocument('resume'), { wrapper })

      await act(async () => {
        await result.current.mutateAsync(2)
      })

      expect(mockDelete).toHaveBeenCalledWith('/resume/2')
      expect(client.getQueryData(['resumes'])).toEqual([{ id: 1 }])
    })

    it('targets the job description endpoint', async () => {
      mockDelete.mockResolvedValue({ id: 4 })
      const { wrapper } = setup()
      const { result } = renderHook(() => useDeleteDocument('job description'), { wrapper })

      await act(async () => {
        await result.current.mutateAsync(4)
      })

      expect(mockDelete).toHaveBeenCalledWith('/jd/4')
    })
  })
})
