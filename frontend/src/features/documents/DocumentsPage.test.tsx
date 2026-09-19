import { render, screen, waitFor, fireEvent } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { MemoryRouter } from 'react-router'
import { describe, it, expect, vi } from 'vitest'
import { DocumentsPage } from './DocumentsPage'
import { api } from '../../lib/api'

vi.mock('../../lib/api', () => ({
  api: { get: vi.fn<(path: string) => Promise<unknown>>() },
}))

vi.mock('../../lib/authContext', () => ({
  useAuth: () => ({ user: null, logout: vi.fn() }),
}))

function renderDocuments() {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  })
  return render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter>
        <DocumentsPage />
      </MemoryRouter>
    </QueryClientProvider>,
  )
}

describe('DocumentsPage', () => {
  it('shows empty states when the user has no resumes or JDs yet', async () => {
    vi.mocked(api.get).mockResolvedValue([])
    renderDocuments()

    await waitFor(() =>
      expect(screen.getByText('No resumes uploaded yet')).toBeInTheDocument(),
    )
    expect(screen.getByText('No job descriptions yet')).toBeInTheDocument()
  })

  it('lists resumes and job descriptions once loaded', async () => {
    vi.mocked(api.get).mockImplementation((path: string) => {
      if (path === '/resume') {
        return Promise.resolve([
          {
            id: 1,
            education: [],
            experience: [{ company: 'Acme', role: 'Engineer' }],
            projects: [],
            skills: ['Python', 'TypeScript'],
            github_url: null,
            created_at: '2026-01-01T00:00:00Z',
          },
        ])
      }
      return Promise.resolve([
        {
          id: 1,
          role: 'Backend Engineer',
          company_name: 'Acme Corp',
          seniority: 'senior',
          tech_stack: ['Python', 'FastAPI'],
          coding_assessment_expected: true,
          created_at: '2026-01-01T00:00:00Z',
        },
      ])
    })
    renderDocuments()

    await waitFor(() =>
      expect(screen.getByText('2 skills · Engineer')).toBeInTheDocument(),
    )
    expect(screen.getByText('Backend Engineer')).toBeInTheDocument()
  })

  it('shows an error state with retry when a query fails', async () => {
    vi.mocked(api.get).mockRejectedValue(new Error('network error'))
    renderDocuments()

    await waitFor(() =>
      expect(screen.getByText("Couldn't load your resumes.")).toBeInTheDocument(),
    )
    expect(screen.getByText("Couldn't load your job descriptions.")).toBeInTheDocument()
  })

  it('retry button on resume error calls refetch (covers line 95)', async () => {
    // First call rejects, second call resolves so the refetch has something to return.
    vi.mocked(api.get).mockRejectedValue(new Error('network error'))
    renderDocuments()

    await waitFor(() =>
      expect(screen.getByText("Couldn't load your resumes.")).toBeInTheDocument(),
    )

    // Now set up the mock to succeed on next call (the refetch).
    vi.mocked(api.get).mockResolvedValue([])

    // Click "Try again" for the resume error state.
    const retryButtons = screen.getAllByText('Try again')
    fireEvent.click(retryButtons[0])

    // After refetch the empty state should appear (no error any more).
    await waitFor(() =>
      expect(screen.getByText('No resumes uploaded yet')).toBeInTheDocument(),
    )
  })

  it('retry button on JD error calls refetch (covers line 123)', async () => {
    vi.mocked(api.get).mockRejectedValue(new Error('network error'))
    renderDocuments()

    await waitFor(() =>
      expect(screen.getByText("Couldn't load your job descriptions.")).toBeInTheDocument(),
    )

    vi.mocked(api.get).mockResolvedValue([])

    // "Try again" buttons appear for both resume and JD error states.
    const retryButtons = screen.getAllByText('Try again')
    // JD retry is the second button.
    fireEvent.click(retryButtons[1])

    await waitFor(() =>
      expect(screen.getByText('No job descriptions yet')).toBeInTheDocument(),
    )
  })

  it('shows loading skeletons while queries are in flight', () => {
    // Never resolve so the component stays in loading state.
    vi.mocked(api.get).mockReturnValue(new Promise(() => {}))
    const { container } = renderDocuments()

    // LoadingSkeleton renders pulse divs — just verify nothing errored and
    // no data or error text is shown yet.
    expect(container.querySelector('[aria-live]')).toBeNull()
    expect(screen.queryByText('No resumes uploaded yet')).not.toBeInTheDocument()
    expect(screen.queryByText("Couldn't load your resumes.")).not.toBeInTheDocument()
  })

  it('shows a resume with no experience or projects (0 skills, no role)', async () => {
    vi.mocked(api.get).mockImplementation((path: string) => {
      if (path === '/resume') {
        return Promise.resolve([
          {
            id: 2,
            education: [],
            experience: [],
            projects: [],
            skills: [],
            github_url: null,
            created_at: '2026-06-01T00:00:00Z',
          },
        ])
      }
      return Promise.resolve([])
    })
    renderDocuments()

    await waitFor(() => expect(screen.getByText('0 skills')).toBeInTheDocument())
    // No " · role" appended when there's no experience or project.
    expect(screen.queryByText(/0 skills ·/)).not.toBeInTheDocument()
  })

  it('shows a JD without a company name (no ` · ` prefix on date)', async () => {
    vi.mocked(api.get).mockImplementation((path: string) => {
      if (path === '/resume') return Promise.resolve([])
      return Promise.resolve([
        {
          id: 2,
          role: 'Frontend Engineer',
          company_name: null,
          seniority: 'mid',
          tech_stack: [],
          coding_assessment_expected: false,
          created_at: '2026-06-01T00:00:00Z',
        },
      ])
    })
    renderDocuments()

    await waitFor(() => expect(screen.getByText('Frontend Engineer')).toBeInTheDocument())
    // There should be no " · " company prefix in the subtitle.
    const dateEl = screen.getByText(/Jun 1, 2026/)
    expect(dateEl.textContent).not.toContain('·')
  })

  it('hides the tech stack row when a JD has an empty tech_stack', async () => {
    vi.mocked(api.get).mockImplementation((path: string) => {
      if (path === '/resume') return Promise.resolve([])
      return Promise.resolve([
        {
          id: 3,
          role: 'PM',
          company_name: 'Acme',
          seniority: 'senior',
          tech_stack: [],
          coding_assessment_expected: false,
          created_at: '2026-06-01T00:00:00Z',
        },
      ])
    })
    renderDocuments()

    await waitFor(() => expect(screen.getByText('PM')).toBeInTheDocument())
    // When tech_stack is empty, the tech-stack <p> element is not rendered at
    // all (the `jd.tech_stack.length > 0 &&` guard prevents it).
    const techStackParagraphs = document.querySelectorAll('p.text-xs.text-muted.mt-1.truncate')
    expect(techStackParagraphs.length).toBe(0)
  })
})
