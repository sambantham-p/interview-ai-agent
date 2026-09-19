import { render, screen } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { App } from './App'

const auth = vi.hoisted(() => ({
  current: { user: null, isAuthenticated: false, isLoading: false } as Record<string, unknown>,
}))

vi.mock('./lib/AuthProvider', () => ({
  AuthProvider: ({ children }: { children: React.ReactNode }) => <>{children}</>,
}))
vi.mock('./lib/authContext', () => ({ useAuth: () => auth.current }))
vi.mock('./components/Navigation', () => ({ Navigation: () => <nav>Navigation</nav> }))

vi.mock('./features/auth/LoginPage', () => ({ LoginPage: () => <p>Login page</p> }))
vi.mock('./features/auth/SignupPage', () => ({ SignupPage: () => <p>Signup page</p> }))
vi.mock('./features/auth/VerifyOtpPage', () => ({ VerifyOtpPage: () => <p>Verify page</p> }))
vi.mock('./features/auth/ForgotPasswordPage', () => ({
  ForgotPasswordPage: () => <p>Forgot page</p>,
}))
vi.mock('./features/auth/ResetCodePage', () => ({ ResetCodePage: () => <p>Reset code page</p> }))
vi.mock('./features/auth/NewPasswordPage', () => ({
  NewPasswordPage: () => <p>New password page</p>,
}))
vi.mock('./features/dashboard/DashboardPage', () => ({
  DashboardPage: () => <p>Dashboard page</p>,
}))
vi.mock('./features/documents/DocumentsPage', () => ({
  DocumentsPage: () => <p>Documents page</p>,
}))
vi.mock('./features/reports/ReportsPage', () => ({ ReportsPage: () => <p>Reports page</p> }))
vi.mock('./features/setup/SetupWizardPage', () => ({
  SetupWizardPage: () => <p>Setup page</p>,
}))
vi.mock('./features/interview-chat/InterviewChatPage', () => ({
  InterviewChatPage: () => <p>Interview page</p>,
}))
vi.mock('./features/report/ReportPage', () => ({ ReportPage: () => <p>Report page</p> }))
vi.mock('./features/settings/SettingsPage', () => ({
  SettingsPage: () => <p>Settings page</p>,
}))
vi.mock('./features/not-found/NotFoundPage', () => ({
  NotFoundPage: () => <p>Not found page</p>,
}))

function visit(path: string) {
  window.history.pushState({}, '', path)
  return render(<App />)
}

function signIn() {
  auth.current = {
    user: { id: 'u', name: 'Jane', email: 'j@example.com' },
    isAuthenticated: true,
    isLoading: false,
  }
}

describe('App routing', () => {
  beforeEach(() => {
    auth.current = { user: null, isAuthenticated: false, isLoading: false }
  })

  describe('landing page', () => {
    it('invites a guest to sign up or sign in', () => {
      visit('/')

      expect(screen.getByRole('link', { name: 'Get started free' })).toHaveAttribute('href', '/signup')
      expect(screen.getByRole('link', { name: 'Sign in' })).toHaveAttribute('href', '/login')
      expect(screen.getByText('Seven-phase interview loop')).toBeInTheDocument()
    })

    it('sends a signed-in user to the dashboard', () => {
      signIn()
      visit('/')

      expect(screen.getByRole('link', { name: 'Go to dashboard' })).toHaveAttribute('href', '/dashboard')
      expect(screen.queryByRole('link', { name: 'Get started free' })).not.toBeInTheDocument()
    })
  })

  it.each([
    ['/login', 'Login page'],
    ['/signup', 'Signup page'],
    ['/verify-email', 'Verify page'],
    ['/forgot-password', 'Forgot page'],
  ])('shows %s to a guest', (path, text) => {
    visit(path)

    expect(screen.getByText(text)).toBeInTheDocument()
  })

  it.each([
    ['/reset-password/verify', 'Reset code page'],
    ['/reset-password/new', 'New password page'],
  ])('shows %s to anyone', (path, text) => {
    visit(path)

    expect(screen.getByText(text)).toBeInTheDocument()
  })

  it.each([
    ['/dashboard', 'Dashboard page'],
    ['/documents', 'Documents page'],
    ['/reports', 'Reports page'],
    ['/setup', 'Setup page'],
    ['/interview/7', 'Interview page'],
    ['/interview/7/report', 'Report page'],
    ['/settings', 'Settings page'],
  ])('shows %s to a signed-in user', (path, text) => {
    signIn()
    visit(path)

    expect(screen.getByText(text)).toBeInTheDocument()
  })

  it.each(['/dashboard', '/documents', '/reports', '/setup', '/interview/7', '/settings'])(
    'does not show %s to a guest',
    (path) => {
      visit(path)

      expect(screen.queryByText(/page$/)).not.toBeInTheDocument()
    },
  )

  it('shows the not-found page for an unknown route', () => {
    visit('/nowhere')

    expect(screen.getByText('Not found page')).toBeInTheDocument()
  })
})
