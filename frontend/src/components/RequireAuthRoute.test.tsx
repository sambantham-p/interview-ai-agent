import { render, screen } from '@testing-library/react'
import { describe, it, expect, vi } from 'vitest'
import { MemoryRouter, Route, Routes } from 'react-router'
import { RequireAuthRoute } from './RequireAuthRoute'

const { mockUseAuth } = vi.hoisted(() => ({
  mockUseAuth: vi.fn<(...args: unknown[]) => unknown>(),
}))

vi.mock('../lib/authContext', () => ({
  useAuth: mockUseAuth,
}))

function renderProtectedRoute() {
  render(
    <MemoryRouter initialEntries={['/setup']}>
      <Routes>
        <Route
          path="/setup"
          element={
            <RequireAuthRoute>
              <div>Setup Page</div>
            </RequireAuthRoute>
          }
        />
        <Route path="/" element={<div>Home Page</div>} />
      </Routes>
    </MemoryRouter>
  )
}

describe('RequireAuthRoute', () => {
  it('renders nothing while auth state is still loading', () => {
    mockUseAuth.mockReturnValue({ isAuthenticated: false, isLoading: true })
    const { container } = render(
      <MemoryRouter initialEntries={['/setup']}>
        <RequireAuthRoute>
          <div>Setup Page</div>
        </RequireAuthRoute>
      </MemoryRouter>
    )
    expect(container).toBeEmptyDOMElement()
  })

  it('redirects to home when the visitor is signed out', () => {
    mockUseAuth.mockReturnValue({ isAuthenticated: false, isLoading: false })
    renderProtectedRoute()
    expect(screen.getByText('Home Page')).toBeInTheDocument()
    expect(screen.queryByText('Setup Page')).not.toBeInTheDocument()
  })

  it('renders the page when the visitor is signed in', () => {
    mockUseAuth.mockReturnValue({ isAuthenticated: true, isLoading: false })
    renderProtectedRoute()
    expect(screen.getByText('Setup Page')).toBeInTheDocument()
  })
})
