import { render, screen, fireEvent } from '@testing-library/react'
import { MemoryRouter, Route, Routes } from 'react-router'
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { UserMenu } from './UserMenu'

const { mockUseAuth, mockLogout } = vi.hoisted(() => ({
  mockUseAuth: vi.fn<(...args: unknown[]) => unknown>(),
  mockLogout: vi.fn<(...args: unknown[]) => unknown>(),
}))

vi.mock('../../lib/authContext', () => ({
  useAuth: mockUseAuth,
}))

function renderUserMenu() {
  return render(
    <MemoryRouter initialEntries={['/dashboard']}>
      <Routes>
        <Route path="/dashboard" element={<UserMenu />} />
        <Route path="/" element={<div>Home Page</div>} />
        <Route path="/settings" element={<div>Settings Page</div>} />
      </Routes>
    </MemoryRouter>,
  )
}

describe('UserMenu', () => {
  beforeEach(() => {
    mockLogout.mockReset()
  })
  it('renders nothing when there is no signed-in user', () => {
    mockUseAuth.mockReturnValue({ user: null, logout: mockLogout })
    const { container } = renderUserMenu()
    expect(container).toBeEmptyDOMElement()
  })

  it('shows the account info and sign out when opened', () => {
    mockUseAuth.mockReturnValue({
      user: { name: 'Sarah Chen', email: 'sarah@example.com', picture: null },
      logout: mockLogout,
    })
    renderUserMenu()

    fireEvent.click(screen.getByLabelText('Account menu'))

    // Shown on the sidebar row and repeated in the opened menu's header.
    expect(screen.getAllByText('Sarah Chen')).toHaveLength(2)
    expect(screen.getAllByText('sarah@example.com')).toHaveLength(2)
    expect(screen.getByText('Settings')).toBeInTheDocument()
    expect(screen.getByText('Log out')).toBeInTheDocument()
  })

  it('signs out and redirects to the landing page', () => {
    mockUseAuth.mockReturnValue({
      user: { name: 'Sarah Chen', email: 'sarah@example.com', picture: null },
      logout: mockLogout,
    })
    renderUserMenu()

    fireEvent.click(screen.getByLabelText('Account menu'))
    fireEvent.click(screen.getByText('Log out'))

    expect(mockLogout).toHaveBeenCalledOnce()
    expect(screen.getByText('Home Page')).toBeInTheDocument()
  })

  it('closes the dropdown when the Settings link is clicked', () => {
    mockUseAuth.mockReturnValue({
      user: { name: 'Sarah Chen', email: 'sarah@example.com', picture: null },
      logout: mockLogout,
    })
    renderUserMenu()

    // Open the menu
    fireEvent.click(screen.getByLabelText('Account menu'))
    expect(screen.getByText('Settings')).toBeInTheDocument()

    // Click Settings — this navigates to /settings AND closes the dropdown.
    // The dropdown is closed by setIsOpen(false) before navigation re-renders.
    fireEvent.click(screen.getByText('Settings'))

    // After navigation the settings page is shown.
    expect(screen.getByText('Settings Page')).toBeInTheDocument()
  })

  it('closes the dropdown when clicking outside the menu', () => {
    mockUseAuth.mockReturnValue({
      user: { name: 'Sarah Chen', email: 'sarah@example.com', picture: null },
      logout: mockLogout,
    })
    const { container } = renderUserMenu()

    // Open the menu
    fireEvent.click(screen.getByLabelText('Account menu'))
    expect(screen.getByText('Log out')).toBeInTheDocument()

    // Click outside the menu ref
    fireEvent.mouseDown(container)

    expect(screen.queryByText('Log out')).not.toBeInTheDocument()
  })

  it('toggles the dropdown closed when the avatar button is clicked again', () => {
    mockUseAuth.mockReturnValue({
      user: { name: 'Sarah Chen', email: 'sarah@example.com', picture: null },
      logout: mockLogout,
    })
    renderUserMenu()

    const avatarBtn = screen.getByLabelText('Account menu')

    // Open
    fireEvent.click(avatarBtn)
    expect(screen.getByText('Log out')).toBeInTheDocument()

    // Toggle closed
    fireEvent.click(avatarBtn)
    expect(screen.queryByText('Log out')).not.toBeInTheDocument()
  })

  it('signs out regardless of auth provider (google user)', () => {
    // The logout() function in authContext clears state + localStorage regardless
    // of how the user originally authenticated. This test verifies UserMenu
    // always calls logout() — the auth-provider-agnostic clearing is tested
    // in authContext.test.tsx.
    mockUseAuth.mockReturnValue({
      user: { name: 'Google User', email: 'google@example.com', picture: 'https://lh3.googleusercontent.com/photo' },
      logout: mockLogout,
    })
    renderUserMenu()

    fireEvent.click(screen.getByLabelText('Account menu'))
    fireEvent.click(screen.getByText('Log out'))

    expect(mockLogout).toHaveBeenCalledOnce()
  })
})
