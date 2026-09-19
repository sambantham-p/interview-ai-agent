import { render, screen, fireEvent } from '@testing-library/react'
import { MemoryRouter, Route, Routes } from 'react-router'
import { describe, it, expect, vi } from 'vitest'
import { Navigation } from './Navigation'

const { mockUseAuth, mockLogout } = vi.hoisted(() => ({
  mockUseAuth: vi.fn(),
  mockLogout: vi.fn(),
}))

vi.mock('../lib/authContext', () => ({
  useAuth: mockUseAuth,
}))

function renderNavigation({
  transparent = false,
  initialPath = '/dashboard',
}: {
  transparent?: boolean
  initialPath?: string
} = {}) {
  return render(
    <MemoryRouter initialEntries={[initialPath]}>
      <Routes>
        <Route path={initialPath} element={<Navigation transparent={transparent} />} />
        <Route path="/login" element={<div>Login Page</div>} />
        <Route path="/" element={<div>Home Page</div>} />
      </Routes>
    </MemoryRouter>,
  )
}

describe('Navigation — unauthenticated', () => {
  it('renders Sign in and Sign up links when no user is signed in', () => {
    mockUseAuth.mockReturnValue({ user: null, isAuthenticated: false, logout: mockLogout })
    renderNavigation()

    expect(screen.getByText('Sign in')).toBeInTheDocument()
    expect(screen.getByText('Sign up')).toBeInTheDocument()
    expect(screen.queryByText('Sign out')).not.toBeInTheDocument()
  })

  it('Sign in links to /login', () => {
    mockUseAuth.mockReturnValue({ user: null, isAuthenticated: false, logout: mockLogout })
    renderNavigation()

    const signInLink = screen.getByText('Sign in').closest('a')
    expect(signInLink).toHaveAttribute('href', '/login')
  })

  it('Sign up links to /signup', () => {
    mockUseAuth.mockReturnValue({ user: null, isAuthenticated: false, logout: mockLogout })
    renderNavigation()

    const signUpLink = screen.getByText('Sign up').closest('a')
    expect(signUpLink).toHaveAttribute('href', '/signup')
  })
})

describe('Navigation — authenticated', () => {
  it('renders the user name, email, and Sign out button', () => {
    mockUseAuth.mockReturnValue({
      user: { name: 'Sarah Chen', email: 'sarah@example.com', picture: null },
      isAuthenticated: true,
      logout: mockLogout,
    })
    renderNavigation()

    expect(screen.getByText('Sarah Chen')).toBeInTheDocument()
    expect(screen.getByText('sarah@example.com')).toBeInTheDocument()
    expect(screen.getByText('Sign out')).toBeInTheDocument()
    expect(screen.queryByText('Sign in')).not.toBeInTheDocument()
  })

  it('calls logout() and navigates to /login when Sign out is clicked', () => {
    mockUseAuth.mockReturnValue({
      user: { name: 'Sarah Chen', email: 'sarah@example.com', picture: null },
      isAuthenticated: true,
      logout: mockLogout,
    })
    renderNavigation()

    fireEvent.click(screen.getByText('Sign out'))

    expect(mockLogout).toHaveBeenCalledOnce()
    expect(screen.getByText('Login Page')).toBeInTheDocument()
  })
})

describe('Navigation — transparent variant', () => {
  it('applies bg-transparent class to the header', () => {
    mockUseAuth.mockReturnValue({ user: null, isAuthenticated: false, logout: mockLogout })
    const { container } = renderNavigation({ transparent: true })

    const header = container.querySelector('header')
    expect(header?.className).toContain('bg-transparent')
    expect(header?.className).not.toContain('bg-white')
  })

  it('renders the logo link (navigates to /)', () => {
    mockUseAuth.mockReturnValue({ user: null, isAuthenticated: false, logout: mockLogout })
    renderNavigation({ transparent: true })
    // The logo link wraps PrepwiseLogo which renders "Prepwise" text.
    const logoLink = screen.getByRole('link', { name: /prepwise/i })
    expect(logoLink).toHaveAttribute('href', '/')
  })

  it('applies white text to the unauthenticated Sign in link when transparent', () => {
    mockUseAuth.mockReturnValue({ user: null, isAuthenticated: false, logout: mockLogout })
    renderNavigation({ transparent: true })

    const signInEl = screen.getByText('Sign in')
    expect(signInEl.className).toContain('text-white')
  })
})

describe('Navigation — opaque (default) variant', () => {
  it('applies sticky bg-white border class to the header', () => {
    mockUseAuth.mockReturnValue({ user: null, isAuthenticated: false, logout: mockLogout })
    const { container } = renderNavigation({ transparent: false })

    const header = container.querySelector('header')
    expect(header?.className).toContain('bg-white')
    expect(header?.className).toContain('sticky')
  })

  it('applies navy text to the Sign in link when opaque', () => {
    mockUseAuth.mockReturnValue({ user: null, isAuthenticated: false, logout: mockLogout })
    renderNavigation({ transparent: false })

    const signInEl = screen.getByText('Sign in')
    expect(signInEl.className).toContain('text-navy')
  })
})
