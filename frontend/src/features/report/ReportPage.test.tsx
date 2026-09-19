import { screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter, Route, Routes } from 'react-router'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { ApiRequestError, api } from '../../lib/api'
import { buildDetail, buildReport } from '../../test/fixtures'
import { renderWithQueryClient } from '../../test/renderWithQueryClient'
import { ReportPage } from './ReportPage'

const { mockPostForBlob } = vi.hoisted(() => ({ mockPostForBlob: vi.fn<(...args: unknown[]) => unknown>() }))

vi.mock('../../lib/api', async () => {
  const actual = await vi.importActual<typeof import('../../lib/api')>('../../lib/api')
  return {
    ...actual,
    api: { get: vi.fn<(...args: unknown[]) => unknown>(), post: vi.fn<(...args: unknown[]) => unknown>(), postForBlob: mockPostForBlob },
  }
})
vi.mock('../../lib/authContext', () => ({
  useAuth: () => ({ user: null, logout: vi.fn<(...args: unknown[]) => unknown>() }),
}))

function respond({
  detail,
  report,
}: {
  detail?: unknown
  report?: unknown | Error
}) {
  vi.mocked(api.get).mockImplementation(async (path: string) => {
    if (path.endsWith('/report')) {
      if (report instanceof Error) throw report
      return report
    }
    if (detail instanceof Error) throw detail
    return detail
  })
}

function renderPage() {
  return renderWithQueryClient(
    <MemoryRouter initialEntries={['/interview/7/report']}>
      <Routes>
        <Route path="/interview/:sessionId/report" element={<ReportPage />} />
      </Routes>
    </MemoryRouter>,
  )
}

describe('ReportPage', () => {
  beforeEach(() => {
    vi.mocked(api.get).mockReset()
    vi.mocked(api.post).mockReset()
    mockPostForBlob.mockReset()
  })

  it('shows the report with tabs and downloads the PDF', async () => {
    const user = userEvent.setup()
    respond({ detail: buildDetail({ ended_at: '2026-01-01T10:30:00Z' }), report: buildReport() })
    mockPostForBlob.mockResolvedValue(new Blob(['%PDF']))
    URL.createObjectURL = vi.fn<() => string>(() => 'blob:pdf')
    URL.revokeObjectURL = vi.fn<(...args: unknown[]) => unknown>()
    const click = vi.spyOn(HTMLAnchorElement.prototype, 'click').mockImplementation(() => {})

    renderPage()

    await waitFor(() => expect(screen.getByText('Overall result')).toBeInTheDocument())
    expect(screen.getByRole('heading', { name: 'Backend Engineer' })).toBeInTheDocument()

    await user.click(screen.getByRole('tab', { name: 'Performance insights' }))
    expect(screen.getByText('Strengths')).toBeInTheDocument()
    await user.click(screen.getByRole('tab', { name: 'Phase review' }))
    expect(screen.getByText(/phase by phase/)).toBeInTheDocument()
    await user.click(screen.getByRole('tab', { name: 'Action plan' }))
    expect(screen.getByText('Focus on these first')).toBeInTheDocument()

    await user.click(screen.getByRole('button', { name: /Download PDF/ }))
    await waitFor(() => expect(click).toHaveBeenCalled())
    for (const link of screen.getAllByRole('link', { name: 'Practice again' })) {
      expect(link).toHaveAttribute('href', '/setup')
    }
  })

  it('omits the company when the job has none', async () => {
    respond({ detail: buildDetail({ company_name: null }), report: buildReport() })

    renderPage()

    await waitFor(() => expect(screen.getByText('Overall result')).toBeInTheDocument())
    expect(screen.queryByText(/Acme/)).not.toBeInTheDocument()
  })

  it('tells the candidate an unfinished interview has no report yet', async () => {
    respond({
      detail: buildDetail({ status: 'in_progress' }),
      report: new ApiRequestError('none', 404),
    })

    renderPage()

    await waitFor(() =>
      expect(screen.getByText("This interview isn't finished yet")).toBeInTheDocument(),
    )
    expect(screen.getByRole('link', { name: /Continue the interview/ })).toHaveAttribute(
      'href',
      '/interview/7',
    )
  })

  it('generates a report for a finished interview that has none', async () => {
    const user = userEvent.setup()
    respond({
      detail: buildDetail({ status: 'completed' }),
      report: new ApiRequestError('none', 404),
    })
    vi.mocked(api.post).mockResolvedValue(buildReport())

    renderPage()
    await user.click(await screen.findByRole('button', { name: 'Generate my report' }))

    await waitFor(() => expect(api.post).toHaveBeenCalledWith('/interview/7/report', {}))
    await waitFor(() => expect(screen.getByText('Overall result')).toBeInTheDocument())
  })

  it('shows a pending state while the report is generating', async () => {
    const user = userEvent.setup()
    respond({
      detail: buildDetail({ status: 'completed' }),
      report: new ApiRequestError('none', 404),
    })
    vi.mocked(api.post).mockReturnValue(new Promise(() => {}))

    renderPage()
    await user.click(await screen.findByRole('button', { name: 'Generate my report' }))

    await waitFor(() => expect(screen.getByText(/Evaluating your interview/)).toBeInTheDocument())
  })

  it('shows an error when the interview itself cannot be loaded', async () => {
    respond({ detail: new Error('boom'), report: new ApiRequestError('none', 404) })

    renderPage()

    await waitFor(() => expect(screen.getByText("Couldn't load this interview.")).toBeInTheDocument())
  })

  it('shows an error when the report fails for a reason other than not existing', async () => {
    respond({ detail: buildDetail(), report: new ApiRequestError('down', 500) })

    renderPage()

    await waitFor(() => expect(screen.getByText("Couldn't load the report.")).toBeInTheDocument(), {
      timeout: 5000,
    })
  })

  it('retries loading the interview', async () => {
    const user = userEvent.setup()
    vi.mocked(api.get).mockImplementation(async (path: string) => {
      if (path.endsWith('/report')) return buildReport()
      throw new Error('boom')
    })

    renderPage()
    await screen.findByText("Couldn't load this interview.")
    const calls = vi.mocked(api.get).mock.calls.length
    await user.click(screen.getByRole('button', { name: /try again|retry/i }))

    await waitFor(() => expect(vi.mocked(api.get).mock.calls.length).toBeGreaterThan(calls))
  })

  it('retries loading the report', async () => {
    const user = userEvent.setup()
    respond({ detail: buildDetail(), report: new ApiRequestError('down', 500) })

    renderPage()
    await screen.findByText("Couldn't load the report.", undefined, { timeout: 5000 })
    const calls = vi.mocked(api.get).mock.calls.length
    await user.click(screen.getByRole('button', { name: /try again|retry/i }))

    await waitFor(() => expect(vi.mocked(api.get).mock.calls.length).toBeGreaterThan(calls))
  })
})
