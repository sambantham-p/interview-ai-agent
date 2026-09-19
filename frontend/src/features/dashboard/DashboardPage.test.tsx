import { render, screen, waitFor, fireEvent } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { MemoryRouter } from 'react-router'
import { describe, it, expect, vi } from 'vitest'
import type { ReactNode } from 'react'
import { DashboardPage } from './DashboardPage'
import { api } from '../../lib/api'

vi.mock('../../lib/api', () => ({
  api: { get: vi.fn<() => Promise<unknown>>() },
}))

vi.mock('../../lib/authContext', () => ({
  useAuth: () => ({
    user: { name: 'Sarah Chen', email: 'sarah@example.com', picture: null },
    logout: vi.fn(),
  }),
}))

function renderDashboard(children: ReactNode) {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  })
  return render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter>{children}</MemoryRouter>
    </QueryClientProvider>,
  )
}

describe('DashboardPage', () => {
  it('greets the signed-in user by first name', async () => {
    vi.mocked(api.get).mockResolvedValue([])
    renderDashboard(<DashboardPage />)

    expect(screen.getByText('Welcome back, Sarah')).toBeInTheDocument()
  })

  it('shows an empty state when there are no interviews yet', async () => {
    vi.mocked(api.get).mockResolvedValue([])
    renderDashboard(<DashboardPage />)

    await waitFor(() => expect(screen.getByText('No interviews yet')).toBeInTheDocument())
  })

  it('lists recent interviews once the query resolves', async () => {
    vi.mocked(api.get).mockResolvedValue([
      {
        id: 1,
        candidate_profile_id: 1,
        job_description_id: 1,
        current_phase: 'technical_interview',
        status: 'completed',
        end_reason: null,
        created_at: '2026-01-01T00:00:00Z',
        ended_at: '2026-01-01T00:30:00Z',
      },
    ])
    renderDashboard(<DashboardPage />)

    await waitFor(() =>
      expect(screen.getByText('Technical Interview')).toBeInTheDocument(),
    )
    // "Completed" appears twice — the stats row's label and the row's
    // status badge — so assert there's at least one, not exactly one.
    expect(screen.getAllByText('Completed').length).toBeGreaterThan(0)
  })

  it('shows an error state with retry when the interviews query fails', async () => {
    vi.mocked(api.get).mockRejectedValue(new Error('network error'))
    renderDashboard(<DashboardPage />)

    await waitFor(() =>
      expect(screen.getByText("Couldn't load your interviews.")).toBeInTheDocument(),
    )
  })

  it('retry button on interview error calls refetch (covers line 103)', async () => {
    // Initial call rejects so the error state is shown.
    vi.mocked(api.get).mockRejectedValue(new Error('network error'))
    renderDashboard(<DashboardPage />)

    await waitFor(() =>
      expect(screen.getByText("Couldn't load your interviews.")).toBeInTheDocument(),
    )

    // Next call succeeds so we can verify the refetch path executed.
    vi.mocked(api.get).mockResolvedValue([])

    fireEvent.click(screen.getByText('Try again'))

    await waitFor(() =>
      expect(screen.getByText('No interviews yet')).toBeInTheDocument(),
    )
  })

  it('shows stat tiles when there are interviews', async () => {
    vi.mocked(api.get).mockResolvedValue([
      {
        id: 1,
        candidate_profile_id: 1,
        job_description_id: 1,
        current_phase: 'technical_interview',
        status: 'in_progress',
        end_reason: null,
        created_at: '2026-01-01T00:00:00Z',
        ended_at: null,
      },
      {
        id: 2,
        candidate_profile_id: 1,
        job_description_id: 1,
        current_phase: 'career_motivation',
        status: 'completed',
        end_reason: null,
        created_at: '2026-02-01T00:00:00Z',
        ended_at: '2026-02-01T00:30:00Z',
      },
    ])
    renderDashboard(<DashboardPage />)

    await waitFor(() => expect(screen.getByText('Technical Interview')).toBeInTheDocument())

    // Stat tiles are shown for total, in-progress, and completed.
    expect(screen.getByText('Total interviews')).toBeInTheDocument()
    // "In progress" and "Completed" each appear in both a stat-tile label
    // and a status badge — use getAllByText to avoid the ambiguity error.
    expect(screen.getAllByText('In progress').length).toBeGreaterThan(0)
    expect(screen.getAllByText('Completed').length).toBeGreaterThan(0)
  })

  it('shows the end reason label for an early-ended interview', async () => {
    vi.mocked(api.get).mockResolvedValue([
      {
        id: 3,
        candidate_profile_id: 1,
        job_description_id: 1,
        current_phase: 'technical_interview',
        status: 'ended_early',
        end_reason: 'red_flag_threshold',
        created_at: '2026-03-01T00:00:00Z',
        ended_at: '2026-03-01T00:10:00Z',
      },
    ])
    renderDashboard(<DashboardPage />)

    // The end reason is rendered as a <span> inside the date <p> element,
    // so the full row text reads "Mar 1, 2026 · Ended: too many red flags".
    // Use a regex on the containing element instead of an exact text match.
    await waitFor(() => {
      const spans = document.querySelectorAll('span.text-amber-700')
      const found = Array.from(spans).some((el) =>
        el.textContent?.includes('Ended: too many red flags'),
      )
      expect(found).toBe(true)
    })
  })
})

describe('DashboardPage freshness', () => {
  const interview = (status: string) => ({
    id: 1,
    candidate_profile_id: 1,
    job_description_id: 1,
    current_phase: 'technical_interview',
    status,
    end_reason: null,
    created_at: '2026-01-01T00:00:00Z',
    ended_at: null,
  })

  it('shows loading, not the previous visit\'s list, when returning to the dashboard', async () => {
    const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } })
    const wrap = (node: ReactNode) => (
      <QueryClientProvider client={queryClient}>
        <MemoryRouter>{node}</MemoryRouter>
      </QueryClientProvider>
    )
    vi.mocked(api.get).mockResolvedValue([interview('in_progress')])
    const first = render(wrap(<DashboardPage />))
    await waitFor(() => expect(screen.getByText('In progress', { selector: 'span' })).toBeInTheDocument())
    first.unmount()
    await new Promise((resolve) => setTimeout(resolve, 10))

    // The interview finished while the user was elsewhere.
    let release: (value: unknown) => void = () => {}
    vi.mocked(api.get).mockReturnValue(new Promise((resolve) => { release = resolve }))
    render(wrap(<DashboardPage />))

    expect(screen.queryByText('In progress', { selector: 'span' })).not.toBeInTheDocument()
    release([interview('completed')])
    await waitFor(() => expect(screen.getByText('Completed', { selector: 'span' })).toBeInTheDocument())
  })
})
