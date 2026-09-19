import { screen, fireEvent, waitFor } from '@testing-library/react'
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { MemoryRouter, Route, Routes } from 'react-router'
import { ResetCodePage } from './ResetCodePage'
import { renderWithQueryClient } from '../../test/renderWithQueryClient'

const { mockVerifyResetCode, mockForgotPassword } = vi.hoisted(() => ({
  mockVerifyResetCode: vi.fn<(...args: unknown[]) => unknown>(),
  mockForgotPassword: vi.fn<(...args: unknown[]) => unknown>(),
}))

vi.mock('../../lib/authContext', () => ({
  useAuth: () => ({
    verifyResetCode: mockVerifyResetCode,
    forgotPassword: mockForgotPassword,
  }),
}))

// See VerifyOtpPage.manualClick.test.tsx for why this stub is needed -
// the real OtpDigitBoxes auto-triggers via onComplete before the page's
// own "Continue" button click handler could ever fire.
vi.mock('../../components/ui/OtpDigitBoxes', () => ({
  OtpDigitBoxes: ({ value, onChange }: { value: string; onChange: (v: string) => void }) => (
    <input
      aria-label="otp-stub"
      value={value}
      onChange={(e) => onChange(e.target.value)}
    />
  ),
}))

describe('ResetCodePage manual Continue click', () => {
  beforeEach(() => {
    mockVerifyResetCode.mockReset()
    mockForgotPassword.mockReset()
  })

  it('continues via the Continue button click handler itself', async () => {
    mockVerifyResetCode.mockResolvedValueOnce('a-reset-token')
    renderWithQueryClient(
      <MemoryRouter
        initialEntries={[
          { pathname: '/reset-password/verify', search: '?email=alex%40prepwise.ai' },
        ]}
      >
        <Routes>
          <Route path="/reset-password/verify" element={<ResetCodePage />} />
          <Route path="/reset-password/new" element={<div>New Password Page</div>} />
        </Routes>
      </MemoryRouter>
    )

    fireEvent.change(screen.getByLabelText('otp-stub'), { target: { value: '123456' } })
    fireEvent.click(screen.getByRole('button', { name: 'Continue' }))

    await waitFor(() => expect(screen.getByText('Code verified')).toBeInTheDocument())
    expect(mockVerifyResetCode).toHaveBeenCalledWith('alex@prepwise.ai', '123456')

    fireEvent.click(screen.getByRole('button', { name: 'Continue' }))
    expect(screen.getByText('New Password Page')).toBeInTheDocument()
  })
})
