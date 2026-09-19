import { render, screen } from '@testing-library/react'
import { describe, it, expect, vi } from 'vitest'
import { MemoryRouter, Route, Routes } from 'react-router'
import { GuestOnlyRoute } from './GuestOnlyRoute'

const { mockUseAuth } = vi.hoisted(() => ({
  mockUseAuth: vi.fn<(...args: unknown[]) => unknown>(),
}))

vi.mock('../lib/authContext', () => ({
  useAuth: mockUseAuth,
}))

function renderGuestRoute() {
  render(
    <MemoryRouter initialEntries={['/login']}>
      <Routes>
        <Route
          path="/login"
          element={
            <GuestOnlyRoute>
              <div>Login Form</div>
            </GuestOnlyRoute>
          }
        />
        <Route path="/dashboard" element={<div>Dashboard Page</div>} />
      </Routes>
    </MemoryRouter>
  )
}

describe('GuestOnlyRoute', () => {
  it('renders nothing while auth state is still loading', () => {
    mockUseAuth.mockReturnValue({ isAuthenticated: false, isLoading: true })
    const { container } = render(
      <MemoryRouter initialEntries={['/login']}>
        <GuestOnlyRoute>
          <div>Login Form</div>
        </GuestOnlyRoute>
      </MemoryRouter>
    )
    expect(container).toBeEmptyDOMElement()
  })

  it('redirects to the dashboard when the visitor is already authenticated', () => {
    mockUseAuth.mockReturnValue({ isAuthenticated: true, isLoading: false })
    renderGuestRoute()
    expect(screen.getByText('Dashboard Page')).toBeInTheDocument()
    expect(screen.queryByText('Login Form')).not.toBeInTheDocument()
  })

  it('renders the page when the visitor is not authenticated', () => {
    mockUseAuth.mockReturnValue({ isAuthenticated: false, isLoading: false })
    renderGuestRoute()
    expect(screen.getByText('Login Form')).toBeInTheDocument()
  })
})
