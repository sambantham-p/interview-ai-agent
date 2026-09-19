import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { act, renderHook, waitFor } from '@testing-library/react'
import type { ReactNode } from 'react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { ToastProvider } from '../../lib/ToastProvider'
import { useReportPdfDownload } from './useReportPdfDownload'

const { mockPostForBlob } = vi.hoisted(() => ({ mockPostForBlob: vi.fn<(...args: unknown[]) => unknown>() }))

vi.mock('../../lib/api', () => ({ api: { postForBlob: mockPostForBlob } }))

function wrapper({ children }: { children: ReactNode }) {
  const client = new QueryClient({ defaultOptions: { mutations: { retry: false } } })
  return (
    <QueryClientProvider client={client}>
      <ToastProvider>{children}</ToastProvider>
    </QueryClientProvider>
  )
}

describe('useReportPdfDownload', () => {
  beforeEach(() => {
    mockPostForBlob.mockReset()
    URL.createObjectURL = vi.fn<() => string>(() => 'blob:pdf')
    URL.revokeObjectURL = vi.fn<(...args: unknown[]) => unknown>()
  })
  afterEach(() => {
    vi.restoreAllMocks()
  })

  it('downloads the PDF through a temporary link', async () => {
    mockPostForBlob.mockResolvedValue(new Blob(['%PDF']))
    const click = vi.spyOn(HTMLAnchorElement.prototype, 'click').mockImplementation(() => {})
    const { result } = renderHook(() => useReportPdfDownload('7'), { wrapper })

    await act(async () => {
      await result.current.mutateAsync()
    })

    expect(mockPostForBlob).toHaveBeenCalledWith('/interview/7/report/pdf', {})
    expect(click).toHaveBeenCalledOnce()
    expect(URL.revokeObjectURL).toHaveBeenCalledWith('blob:pdf')
  })

  it('reports a failure', async () => {
    mockPostForBlob.mockRejectedValue(new Error('No report yet'))
    const { result } = renderHook(() => useReportPdfDownload('7'), { wrapper })

    await act(async () => {
      await result.current.mutateAsync().catch(() => undefined)
    })

    await waitFor(() => expect(result.current.isError).toBe(true))
  })
})
