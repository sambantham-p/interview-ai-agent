import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it, vi } from 'vitest'
import { MemoryRouter, Route, Routes } from 'react-router'
import { NotFoundPage } from './NotFoundPage'
import { STARTUP_ROUTE } from '../../lib/routes'

const { mockUseAuth } = vi.hoisted(() => ({
  mockUseAuth: vi.fn(),
}))

vi.mock('../../lib/authContext', () => ({
  useAuth: mockUseAuth,
}))

function renderUnknownRoute() {
  return render(
    <MemoryRouter initialEntries={['/missing-page']}>
      <Routes>
        <Route path={STARTUP_ROUTE} element={<div>Home Page</div>} />
        <Route path="/setup" element={<div>Setup Page</div>} />
        <Route path="*" element={<NotFoundPage />} />
      </Routes>
    </MemoryRouter>,
  )
}

describe('NotFoundPage', () => {
  describe('signed out', () => {
    it('renders a clear 404 message pointing back to the public homepage', () => {
      mockUseAuth.mockReturnValue({ isAuthenticated: false })
      renderUnknownRoute()

      expect(screen.getByText('404')).toBeInTheDocument()
      expect(
        screen.getByRole('heading', {
          name: /the page you’re looking for doesn’t exist or has been moved/i,
        }),
      ).toBeInTheDocument()
      expect(screen.getByRole('link', { name: /go home/i })).toHaveAttribute(
        'href',
        STARTUP_ROUTE,
      )
    })

    it('navigates back to the startup page from the primary action', async () => {
      mockUseAuth.mockReturnValue({ isAuthenticated: false })
      const user = userEvent.setup()
      renderUnknownRoute()

      await user.click(screen.getByRole('link', { name: /go home/i }))

      expect(screen.getByText('Home Page')).toBeInTheDocument()
    })
  })

  describe('signed in', () => {
    it('points the primary action at starting a new interview, not the marketing homepage', () => {
      mockUseAuth.mockReturnValue({ isAuthenticated: true })
      renderUnknownRoute()

      expect(
        screen.getByRole('link', { name: /start an interview/i }),
      ).toHaveAttribute('href', '/setup')
    })

    it('navigates to the setup page from the primary action', async () => {
      mockUseAuth.mockReturnValue({ isAuthenticated: true })
      const user = userEvent.setup()
      renderUnknownRoute()

      await user.click(screen.getByRole('link', { name: /start an interview/i }))

      expect(screen.getByText('Setup Page')).toBeInTheDocument()
    })
  })
})
