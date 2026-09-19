import { screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter, Route, Routes, useLocation } from 'react-router'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { renderWithQueryClient } from '../../test/renderWithQueryClient'
import { SettingsPage } from './SettingsPage'

const auth = vi.hoisted(() => ({
  current: null as Record<string, unknown> | null,
}))

vi.mock('../../lib/authContext', () => ({
  useAuth: () => auth.current,
}))

function Landing() {
  const location = useLocation()
  return <p>Landed on {location.pathname + location.search}</p>
}

function setAuth(overrides: Record<string, unknown> = {}) {
  auth.current = {
    user: {
      id: 'usr_1',
      name: 'Jane Doe',
      email: 'jane@example.com',
      picture: null,
      preferred_name: 'Jay',
    },
    logout: vi.fn<(...args: unknown[]) => unknown>(),
    updatePreferredName: vi.fn<(...args: unknown[]) => unknown>().mockResolvedValue({}),
    forgotPassword: vi.fn<(...args: unknown[]) => unknown>().mockResolvedValue({}),
    deleteAccount: vi.fn<(...args: unknown[]) => unknown>().mockResolvedValue(undefined),
    ...overrides,
  }
  return auth.current
}

function renderPage() {
  return renderWithQueryClient(
    <MemoryRouter initialEntries={['/settings']}>
      <Routes>
        <Route path="/settings" element={<SettingsPage />} />
        <Route path="*" element={<Landing />} />
      </Routes>
    </MemoryRouter>,
  )
}

describe('SettingsPage', () => {
  beforeEach(() => {
    setAuth()
  })

  it('shows the email read-only and the current profile name', () => {
    renderPage()

    expect(screen.getByLabelText('Email')).toBeDisabled()
    expect(screen.getByLabelText('Email')).toHaveValue('jane@example.com')
    expect(screen.getByLabelText('Profile name')).toHaveValue('Jay')
  })

  it('keeps Save disabled until the name changes, then saves it', async () => {
    const user = userEvent.setup()
    renderPage()
    const save = screen.getByRole('button', { name: 'Save changes' })
    expect(save).toBeDisabled()

    await user.clear(screen.getByLabelText('Profile name'))
    await user.type(screen.getByLabelText('Profile name'), 'Sam')
    expect(save).toBeEnabled()
    await user.click(save)

    await waitFor(() =>
      expect((auth.current?.updatePreferredName as ReturnType<typeof vi.fn>)).toHaveBeenCalledWith('Sam'),
    )
    expect(await screen.findByText('Profile name updated')).toBeInTheDocument()
  })

  it('starts empty when there is no profile name yet', () => {
    setAuth({
      user: { id: 'u', name: 'Jane Doe', email: 'j@example.com', picture: null },
    })
    renderPage()

    expect(screen.getByLabelText('Profile name')).toHaveValue('')
  })

  it('shows a readable error when saving fails', async () => {
    const user = userEvent.setup()
    setAuth({ updatePreferredName: vi.fn<(...args: unknown[]) => unknown>().mockRejectedValue(new Error('Server said no')) })
    renderPage()

    await user.type(screen.getByLabelText('Profile name'), 'x')
    await user.click(screen.getByRole('button', { name: 'Save changes' }))

    expect(await screen.findByText('Server said no')).toBeInTheDocument()
  })

  it('falls back to a generic message when the failure is not an Error', async () => {
    const user = userEvent.setup()
    setAuth({ updatePreferredName: vi.fn<(...args: unknown[]) => unknown>().mockRejectedValue('nope') })
    renderPage()

    await user.type(screen.getByLabelText('Profile name'), 'x')
    await user.click(screen.getByRole('button', { name: 'Save changes' }))

    expect(await screen.findByText("Couldn't save your name. Please try again.")).toBeInTheDocument()
  })

  it('emails a reset code and moves to the code page', async () => {
    const user = userEvent.setup()
    renderPage()

    await user.click(screen.getByRole('button', { name: 'Send reset email' }))

    await waitFor(() =>
      expect(screen.getByText('Landed on /reset-password/verify?email=jane%40example.com')).toBeInTheDocument(),
    )
    expect(auth.current?.forgotPassword).toHaveBeenCalledWith('jane@example.com')
  })

  it('shows an error when the reset email cannot be sent', async () => {
    const user = userEvent.setup()
    setAuth({ forgotPassword: vi.fn<(...args: unknown[]) => unknown>().mockRejectedValue(new Error('Mail is down')) })
    renderPage()

    await user.click(screen.getByRole('button', { name: 'Send reset email' }))

    expect(await screen.findByText('Mail is down')).toBeInTheDocument()
  })

  it('asks for confirmation before deleting, and can be cancelled', async () => {
    const user = userEvent.setup()
    renderPage()

    await user.click(screen.getByRole('button', { name: 'Delete account' }))
    expect(screen.getByRole('button', { name: 'Yes, delete everything' })).toBeInTheDocument()

    await user.click(screen.getByRole('button', { name: 'Cancel' }))
    expect(screen.queryByRole('button', { name: 'Yes, delete everything' })).not.toBeInTheDocument()
    expect(auth.current?.deleteAccount).not.toHaveBeenCalled()
  })

  it('deletes the account and returns to the landing page', async () => {
    const user = userEvent.setup()
    renderPage()

    await user.click(screen.getByRole('button', { name: 'Delete account' }))
    await user.click(screen.getByRole('button', { name: 'Yes, delete everything' }))

    await waitFor(() => expect(screen.getByText('Landed on /')).toBeInTheDocument())
    expect(auth.current?.deleteAccount).toHaveBeenCalled()
  })

  it('shows why a deletion failed and stays on the page', async () => {
    const user = userEvent.setup()
    setAuth({ deleteAccount: vi.fn<(...args: unknown[]) => unknown>().mockRejectedValue(new Error('Delete blocked')) })
    renderPage()

    await user.click(screen.getByRole('button', { name: 'Delete account' }))
    await user.click(screen.getByRole('button', { name: 'Yes, delete everything' }))

    expect(await screen.findByText('Delete blocked')).toBeInTheDocument()
  })

  it('renders only the delete section when there is no signed-in user', () => {
    setAuth({ user: null })
    renderPage()

    expect(screen.queryByLabelText('Email')).not.toBeInTheDocument()
    expect(screen.queryByRole('button', { name: 'Send reset email' })).not.toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Delete account' })).toBeInTheDocument()
  })
})
