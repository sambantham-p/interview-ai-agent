import { screen, fireEvent, waitFor } from '@testing-library/react'
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { MemoryRouter, Route, Routes } from 'react-router'
import { VerifyOtpPage } from './VerifyOtpPage'
import { renderWithQueryClient } from '../../test/renderWithQueryClient'

const { mockVerifyOtp, mockResendOtp } = vi.hoisted(() => ({
  mockVerifyOtp: vi.fn<(...args: unknown[]) => unknown>(),
  mockResendOtp: vi.fn<(...args: unknown[]) => unknown>(),
}))

vi.mock('../../lib/authContext', () => ({
  useAuth: () => ({
    verifyOtp: mockVerifyOtp,
    resendOtp: mockResendOtp,
  }),
}))

// A stub that only calls onChange, never onComplete - the real
// OtpDigitBoxes auto-triggers verification on the 6th digit, which makes
// the page's own "Verify email" button click handler unreachable through
// normal typing/pasting. This isolates that click handler specifically.
vi.mock('../../components/ui/OtpDigitBoxes', () => ({
  OtpDigitBoxes: ({ value, onChange }: { value: string; onChange: (v: string) => void }) => (
    <input
      aria-label="otp-stub"
      value={value}
      onChange={(e) => onChange(e.target.value)}
    />
  ),
}))

describe('VerifyOtpPage manual Verify click', () => {
  beforeEach(() => {
    mockVerifyOtp.mockReset()
    mockResendOtp.mockReset()
  })

  it('verifies via the Verify email button click handler itself', async () => {
    mockVerifyOtp.mockResolvedValueOnce(undefined)
    renderWithQueryClient(
      <MemoryRouter
        initialEntries={[{ pathname: '/verify-email', search: '?email=alex%40prepwise.ai' }]}
      >
        <Routes>
          <Route path="/verify-email" element={<VerifyOtpPage />} />
          <Route path="/setup" element={<div>Setup Page</div>} />
        </Routes>
      </MemoryRouter>
    )

    fireEvent.change(screen.getByLabelText('otp-stub'), { target: { value: '123456' } })
    fireEvent.click(screen.getByRole('button', { name: 'Verify email' }))

    await waitFor(() => expect(screen.getByText('Email verified')).toBeInTheDocument())
    expect(mockVerifyOtp).toHaveBeenCalledWith('alex@prepwise.ai', '123456')

    fireEvent.click(screen.getByRole('button', { name: 'Continue to Prepwise' }))
    expect(screen.getByText('Setup Page')).toBeInTheDocument()
  })
})
