import { render, screen, waitFor } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { describe, expect, it, vi } from 'vitest'
import type { ReactNode } from 'react'
import { HealthStatus } from './HealthStatus'
import { api } from '../../lib/api'

vi.mock('../../lib/api', () => ({
  api: { get: vi.fn<() => Promise<unknown>>() },
}))

function renderWithQueryClient(children: ReactNode) {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  })
  return render(
    <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>,
  )
}

describe('HealthStatus', () => {
  it('shows the backend health once the query resolves', async () => {
    vi.mocked(api.get).mockResolvedValue({
      service: 'interview-ai-agent',
      health: 'healthy',
    })

    renderWithQueryClient(<HealthStatus />)

    await waitFor(() =>
      expect(
        screen.getByText(/interview-ai-agent is healthy/i),
      ).toBeInTheDocument(),
    )
  })

  it('shows an error message when the backend is unreachable', async () => {
    vi.mocked(api.get).mockRejectedValue(new Error('Failed to fetch'))

    renderWithQueryClient(<HealthStatus />)

    await waitFor(() =>
      expect(screen.getByText(/backend unreachable/i)).toBeInTheDocument(),
    )
  })
})
