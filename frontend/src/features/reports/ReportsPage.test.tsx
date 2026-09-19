import { screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter } from 'react-router'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { api } from '../../lib/api'
import { renderWithQueryClient } from '../../test/renderWithQueryClient'
import { buildReportListItem } from '../../test/fixtures'
import { ReportCard } from './ReportCard'
import { ReportsPage } from './ReportsPage'

vi.mock('../../lib/api', () => ({ api: { get: vi.fn<() => Promise<unknown>>() } }))
vi.mock('../../lib/authContext', () => ({
  useAuth: () => ({ user: null, logout: vi.fn<(...args: unknown[]) => unknown>() }),
}))

function renderPage() {
  return renderWithQueryClient(
    <MemoryRouter>
      <ReportsPage />
    </MemoryRouter>,
  )
}

describe('ReportsPage', () => {
  beforeEach(() => {
    vi.mocked(api.get).mockReset()
  })

  it('shows the summary tiles and a card per interview', async () => {
    vi.mocked(api.get).mockResolvedValue([
      buildReportListItem({ session_id: 1, overall_score: 80 }),
      buildReportListItem({ session_id: 2, overall_score: 60, job_role: 'Data Engineer' }),
      buildReportListItem({
        session_id: 3,
        overall_score: null,
        recommendation_tier: null,
        report_id: null,
        job_role: 'Unscored role',
      }),
    ])

    renderPage()

    await waitFor(() => expect(screen.getByText('Average score')).toBeInTheDocument())
    expect(screen.getByText('70')).toBeInTheDocument()
    expect(screen.getByText('Best score')).toBeInTheDocument()
    expect(screen.getByText('Data Engineer')).toBeInTheDocument()
    expect(screen.getByText('Unscored role')).toBeInTheDocument()
  })

  it('shows an empty state when there are no finished interviews', async () => {
    vi.mocked(api.get).mockResolvedValue([])

    renderPage()

    await waitFor(() => expect(screen.getByText('No reports yet')).toBeInTheDocument())
    expect(screen.getByRole('link', { name: /Start an interview/ })).toHaveAttribute('href', '/setup')
    expect(screen.queryByText('Average score')).not.toBeInTheDocument()
  })

  it('shows an error with a retry', async () => {
    const user = userEvent.setup()
    vi.mocked(api.get).mockRejectedValueOnce(new Error('boom')).mockResolvedValue([])

    renderPage()

    await waitFor(() => expect(screen.getByText("Couldn't load your reports.")).toBeInTheDocument())
    await user.click(screen.getByRole('button', { name: /try again|retry/i }))

    await waitFor(() => expect(screen.getByText('No reports yet')).toBeInTheDocument())
  })
})

describe('ReportCard', () => {
  function renderCard(overrides = {}) {
    return renderWithQueryClient(
      <MemoryRouter>
        <ReportCard item={buildReportListItem(overrides)} />
      </MemoryRouter>,
    )
  }

  it('links to the report with score, verdict, counts and duration', () => {
    renderCard({ end_reason_label: 'Ended: abusive language' })

    expect(screen.getByRole('link')).toHaveAttribute('href', '/interview/7/report')
    expect(screen.getByText('Hire')).toBeInTheDocument()
    expect(screen.getByText('2 hints')).toBeInTheDocument()
    expect(screen.getByText('1 flag')).toBeInTheDocument()
    expect(screen.getByText('Ended: abusive language')).toBeInTheDocument()
    expect(screen.getByText(/Acme/)).toHaveTextContent('30 min')
    expect(screen.getByText('View report →')).toBeInTheDocument()
  })

  it('offers to generate a missing report and hides absent details', () => {
    renderCard({
      overall_score: null,
      recommendation_tier: null,
      report_id: null,
      company_name: null,
      duration_minutes: null,
      hint_count: 1,
      red_flag_count: 2,
    })

    expect(screen.getByText('Report not generated')).toBeInTheDocument()
    expect(screen.getByText('Generate →')).toBeInTheDocument()
    expect(screen.getByText('1 hint')).toBeInTheDocument()
    expect(screen.getByText('2 flags')).toBeInTheDocument()
    expect(screen.queryByText(/Acme/)).not.toBeInTheDocument()
    expect(screen.queryByText(/ min/)).not.toBeInTheDocument()
  })

  it('omits the hint and flag badges when there are none', () => {
    renderCard({ hint_count: 0, red_flag_count: 0 })

    expect(screen.queryByText(/hint/)).not.toBeInTheDocument()
    expect(screen.queryByText(/flag/)).not.toBeInTheDocument()
  })
})
