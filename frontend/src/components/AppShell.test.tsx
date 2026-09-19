import { render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router'
import { describe, it, expect, vi } from 'vitest'
import { AppShell } from './AppShell'

vi.mock('../lib/authContext', () => ({
  useAuth: () => ({ user: null, logout: vi.fn<(...args: unknown[]) => unknown>() }),
}))

describe('AppShell', () => {
  it('renders the nav items and the page content', () => {
    render(
      <MemoryRouter initialEntries={['/dashboard']}>
        <AppShell
          title="Test page"
          parent={{ label: 'Reports', to: '/reports' }}
        >
          <div>Page Content</div>
        </AppShell>
      </MemoryRouter>,
    )

    expect(screen.getByText('Dashboard')).toBeInTheDocument()
    expect(screen.getByText('Documents')).toBeInTheDocument()
    expect(screen.getByText('Page Content')).toBeInTheDocument()
    expect(
      screen.getByRole('navigation', { name: 'Breadcrumb' }),
    ).toHaveTextContent('Test page')
  })

  it('highlights the active nav item', () => {
    render(
      <MemoryRouter initialEntries={['/documents']}>
        <AppShell title="Test page">
          <div>Page Content</div>
        </AppShell>
      </MemoryRouter>,
    )

    expect(screen.getByText('Documents').className).toContain('bg-brand/15')
    expect(screen.getByText('Dashboard').className).not.toContain('bg-brand/15')
  })
})
