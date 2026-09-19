import { render, screen, fireEvent } from '@testing-library/react'
import { describe, it, expect } from 'vitest'
import { MemoryRouter, Route, Routes } from 'react-router'
import { AuthProvider } from '../../lib/AuthProvider'
import { checkPasswordStrength } from '../../lib/passwordRules'
import { LoginPage } from './LoginPage'
import { SignupPage } from './SignupPage'
import { VerifyOtpPage } from './VerifyOtpPage'
import { ForgotPasswordPage } from './ForgotPasswordPage'
import { ResetCodePage } from './ResetCodePage'
import { NewPasswordPage } from './NewPasswordPage'
import { PasswordStrengthMeter } from '../../components/ui/PasswordStrengthMeter'
import { OtpDigitBoxes } from '../../components/ui/OtpDigitBoxes'
import { renderWithQueryClient } from '../../test/renderWithQueryClient'

describe('PasswordStrengthMeter', () => {
  it('renders requirements and updates strength bar dynamically', () => {
    const { rerender } = render(<PasswordStrengthMeter password="weak" />)
    expect(screen.getByText(/Weak password/i)).toBeInTheDocument()
    expect(screen.getByText(/8\+ characters/i)).toBeInTheDocument()

    rerender(<PasswordStrengthMeter password="Prepwise#2026" />)
    expect(screen.getByText(/Strong password/i)).toBeInTheDocument()
  })

  it('shows Good password when exactly 3 of the 4 rules pass', () => {
    // Meets length/case/number but not special-character - 3 of 4.
    render(<PasswordStrengthMeter password="Prepwise2026" />)
    expect(screen.getByText(/Good password/i)).toBeInTheDocument()
  })

  it('shows a neutral prompt with no password entered', () => {
    render(<PasswordStrengthMeter />)
    expect(screen.getByText(/Enter password/i)).toBeInTheDocument()
  })
})

describe('OtpDigitBoxes', () => {
  it('renders 6 separate input boxes', () => {
    let value = ''
    render(
      <OtpDigitBoxes
        value={value}
        onChange={(val) => {
          value = val
        }}
      />
    )
    const inputs = screen.getAllByRole('textbox')
    expect(inputs).toHaveLength(6)
  })

  it('updates value when digits are entered', () => {
    let value = ''
    const handleChange = (val: string) => {
      value = val
    }
    render(<OtpDigitBoxes value={value} onChange={handleChange} />)
    const inputs = screen.getAllByRole('textbox')
    fireEvent.change(inputs[0], { target: { value: '4' } })
    expect(value).toBe('4')
  })
})

describe('LoginPage', () => {
  it('renders Welcome back heading and form inputs', () => {
    // The Google button itself (real widget vs. dev-only fallback,
    // including its poll/timeout race) has its own dedicated coverage in
    // GoogleSignInButton.test.tsx - not re-asserted here.
    renderWithQueryClient(
      <AuthProvider>
        <MemoryRouter>
          <LoginPage />
        </MemoryRouter>
      </AuthProvider>
    )

    expect(screen.getByText('Welcome back')).toBeInTheDocument()
    expect(screen.getByLabelText(/Email address/i)).toBeInTheDocument()
    expect(screen.getByLabelText(/^Password$/i)).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Sign in' })).toBeInTheDocument()
  })
})

describe('SignupPage', () => {
  it('renders Create your account heading and inputs', () => {
    renderWithQueryClient(
      <AuthProvider>
        <MemoryRouter>
          <SignupPage />
        </MemoryRouter>
      </AuthProvider>
    )

    expect(screen.getByText('Create your account')).toBeInTheDocument()
    expect(screen.getByLabelText(/Full name/i)).toBeInTheDocument()
    expect(screen.getByLabelText(/Email address/i)).toBeInTheDocument()
    expect(screen.getByLabelText('Password')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Create account' })).toBeInTheDocument()
  })

  it('only enables Create account once name, email, and a strong password are entered', () => {
    renderWithQueryClient(
      <AuthProvider>
        <MemoryRouter>
          <SignupPage />
        </MemoryRouter>
      </AuthProvider>
    )

    fireEvent.change(screen.getByLabelText(/Full name/i), {
      target: { value: 'Alex Chen' },
    })
    fireEvent.change(screen.getByLabelText(/Email address/i), {
      target: { value: 'alex@example.com' },
    })
    const submitButton = screen.getByRole('button', { name: 'Create account' })
    expect(submitButton).toBeDisabled()

    fireEvent.change(screen.getByLabelText('Password'), {
      target: { value: 'Prepwise#2026' },
    })
    expect(submitButton).not.toBeDisabled()
  })
})

describe('VerifyOtpPage', () => {
  it('renders Check your inbox heading and 6 digit boxes', () => {
    renderWithQueryClient(
      <AuthProvider>
        <MemoryRouter initialEntries={['/verify-email?email=test%40prepwise.ai']}>
          <VerifyOtpPage />
        </MemoryRouter>
      </AuthProvider>
    )

    expect(screen.getByText('Check your inbox')).toBeInTheDocument()
    expect(screen.getByText(/Verify your email/i)).toBeInTheDocument()
    expect(screen.getAllByRole('textbox')).toHaveLength(6)
    expect(screen.getByRole('button', { name: 'Verify email' })).toBeInTheDocument()
  })
})

describe('checkPasswordStrength', () => {
  it('is only valid once all four rules pass', () => {
    expect(checkPasswordStrength('weak').isValid).toBe(false)
    expect(checkPasswordStrength('Prepwise#2026').isValid).toBe(true)
  })
})

describe('ForgotPasswordPage', () => {
  it('renders Reset your password heading, email field, and back link', () => {
    renderWithQueryClient(
      <AuthProvider>
        <MemoryRouter>
          <ForgotPasswordPage />
        </MemoryRouter>
      </AuthProvider>
    )

    expect(screen.getByText('Reset your password')).toBeInTheDocument()
    expect(screen.getByLabelText(/Email address/i)).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Send reset code' })).toBeInTheDocument()
    expect(screen.getByText(/Back to sign in/i)).toBeInTheDocument()
  })
})

describe('ResetCodePage', () => {
  it('renders Reset code on its way heading and 6 digit boxes', () => {
    renderWithQueryClient(
      <AuthProvider>
        <MemoryRouter initialEntries={['/reset-password/verify?email=test%40prepwise.ai']}>
          <ResetCodePage />
        </MemoryRouter>
      </AuthProvider>
    )

    expect(screen.getByText('Reset code on its way')).toBeInTheDocument()
    expect(screen.getByText(/Check your inbox/i)).toBeInTheDocument()
    expect(screen.getAllByRole('textbox')).toHaveLength(6)
    expect(screen.getByRole('button', { name: 'Continue' })).toBeInTheDocument()
  })
})

describe('NewPasswordPage', () => {
  it('renders Choose a new password heading and both password fields', () => {
    renderWithQueryClient(
      <AuthProvider>
        <MemoryRouter initialEntries={['/reset-password/new?token=a-token']}>
          <Routes>
            <Route path="/reset-password/new" element={<NewPasswordPage />} />
          </Routes>
        </MemoryRouter>
      </AuthProvider>
    )

    expect(screen.getByText('Choose a new password')).toBeInTheDocument()
    expect(screen.getByLabelText(/^New password/i)).toBeInTheDocument()
    expect(screen.getByLabelText(/Confirm new password/i)).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Update password' })).toBeInTheDocument()
  })

  it('disables Update password until both fields match and meet requirements', () => {
    renderWithQueryClient(
      <AuthProvider>
        <MemoryRouter initialEntries={['/reset-password/new?token=a-token']}>
          <Routes>
            <Route path="/reset-password/new" element={<NewPasswordPage />} />
          </Routes>
        </MemoryRouter>
      </AuthProvider>
    )

    const submitButton = screen.getByRole('button', { name: 'Update password' })
    expect(submitButton).toBeDisabled()

    fireEvent.change(screen.getByLabelText(/^New password/i), {
      target: { value: 'Prepwise#2026' },
    })
    fireEvent.change(screen.getByLabelText(/Confirm new password/i), {
      target: { value: 'Prepwise#2026' },
    })

    expect(screen.getByText('Strong password')).toBeInTheDocument()
    expect(submitButton).not.toBeDisabled()
  })
})
