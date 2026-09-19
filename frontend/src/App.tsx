import { BrowserRouter, Link, Route, Routes } from 'react-router'
import { useAuth } from './lib/authContext'
import { AuthProvider } from './lib/AuthProvider'
import { Navigation } from './components/Navigation'
import { GuestOnlyRoute } from './components/GuestOnlyRoute'
import { RequireAuthRoute } from './components/RequireAuthRoute'
import { ShieldCheckIcon } from './components/ui/ShieldCheckIcon'
import { MeshGradientBackground } from './components/ui/MeshGradientBackground'
import { LoginPage } from './features/auth/LoginPage'
import { SignupPage } from './features/auth/SignupPage'
import { VerifyOtpPage } from './features/auth/VerifyOtpPage'
import { ForgotPasswordPage } from './features/auth/ForgotPasswordPage'
import { SettingsPage } from './features/settings/SettingsPage'
import { ResetCodePage } from './features/auth/ResetCodePage'
import { NewPasswordPage } from './features/auth/NewPasswordPage'
import { DashboardPage } from './features/dashboard/DashboardPage'
import { DocumentsPage } from './features/documents/DocumentsPage'
import { SetupWizardPage } from './features/setup/SetupWizardPage'
import { InterviewChatPage } from './features/interview-chat/InterviewChatPage'
import { ReportPage } from './features/report/ReportPage'
import { ReportsPage } from './features/reports/ReportsPage'
import { NotFoundPage } from './features/not-found/NotFoundPage'
import { STARTUP_ROUTE } from './lib/routes'

const HIGHLIGHTS = [
  {
    title: 'Seven-phase interview loop',
    body: 'From background checks to career fit, mirroring a real full-loop technical interview.',
  },
  {
    title: 'Grounded in your resume + the JD',
    body: 'Every question is calibrated to what you actually built and the role you’re targeting.',
  },
  {
    title: 'Evidence-backed report',
    body: 'A scored evaluation that cites the exact moment in the transcript behind every score.',
  },
]

function HomePage() {
  const { user, isAuthenticated } = useAuth()

  return (
    <div className="min-h-screen flex flex-col bg-hero">
      <div className="relative isolate overflow-hidden flex-1 flex flex-col">
        <MeshGradientBackground />

        <Navigation transparent />

        <main className="mx-auto max-w-4xl w-full px-6 sm:px-10 flex-1 flex flex-col items-center justify-center text-center py-20 sm:py-28">
          <span className="inline-flex items-center gap-2 px-3.5 py-1.5 rounded-full bg-white/10 border border-white/15 text-teal-200 text-xs font-semibold tracking-wide uppercase backdrop-blur-sm">
            AI-powered mock interviews
          </span>

          <h1 className="mt-6 text-4xl sm:text-6xl font-bold tracking-tight text-white text-balance">
            Walk into your next interview{' '}
            <span className="bg-linear-to-r from-brand to-[#5eead4] bg-clip-text text-transparent">
              already having done it once.
            </span>
          </h1>

          <p className="mt-5 max-w-2xl text-lg text-slate-300 text-balance">
            Prepwise runs a full-loop technical interview driven entirely by
            your resume and a target job description, then hands you an
            evidence-backed evaluation at the end.
          </p>

          <div className="mt-9 flex flex-col sm:flex-row items-center gap-3">
            {isAuthenticated && user ? (
              <Link
                to="/dashboard"
                className="px-7 py-3.5 rounded-[10px] bg-brand text-[#06251f] text-[15px] font-semibold shadow-lg shadow-teal-900/30 hover:bg-[#14c3a8] active:scale-[0.99] transition-all"
              >
                Go to dashboard
              </Link>
            ) : (
              <>
                <Link
                  to="/signup"
                  className="px-7 py-3.5 rounded-[10px] bg-brand text-[#06251f] text-[15px] font-semibold shadow-lg shadow-teal-900/30 hover:bg-[#14c3a8] active:scale-[0.99] transition-all"
                >
                  Get started free
                </Link>
                <Link
                  to="/login"
                  className="px-7 py-3.5 rounded-[10px] bg-white/5 border border-white/20 text-white text-[15px] font-semibold hover:bg-white/10 active:scale-[0.99] transition-all backdrop-blur-sm"
                >
                  Sign in
                </Link>
              </>
            )}
          </div>

          <dl className="mt-20 grid grid-cols-1 sm:grid-cols-3 gap-6 w-full text-left">
            {HIGHLIGHTS.map((item) => (
              <div
                key={item.title}
                className="rounded-2xl bg-white/4 border border-white/10 p-5 backdrop-blur-sm"
              >
                <ShieldCheckIcon className="w-5 h-5 mb-3" />
                <dt className="text-sm font-semibold text-white">
                  {item.title}
                </dt>
                <dd className="mt-1.5 text-sm text-slate-400 leading-relaxed">
                  {item.body}
                </dd>
              </div>
            ))}
          </dl>
        </main>
      </div>
    </div>
  )
}

export function App() {
  return (
    <AuthProvider>
      <BrowserRouter>
        <Routes>
          <Route path={STARTUP_ROUTE} element={<HomePage />} />
          <Route
            path="/login"
            element={
              <GuestOnlyRoute>
                <LoginPage />
              </GuestOnlyRoute>
            }
          />
          <Route
            path="/signup"
            element={
              <GuestOnlyRoute>
                <SignupPage />
              </GuestOnlyRoute>
            }
          />
          <Route
            path="/verify-email"
            element={
              <GuestOnlyRoute>
                <VerifyOtpPage />
              </GuestOnlyRoute>
            }
          />
          <Route
            path="/forgot-password"
            element={
              <GuestOnlyRoute>
                <ForgotPasswordPage />
              </GuestOnlyRoute>
            }
          />
          <Route
            path="/reset-password/verify"
            element={<ResetCodePage />}
          />
          <Route
            path="/reset-password/new"
            element={<NewPasswordPage />}
          />
          <Route
            path="/dashboard"
            element={
              <RequireAuthRoute>
                <DashboardPage />
              </RequireAuthRoute>
            }
          />
          <Route
            path="/documents"
            element={
              <RequireAuthRoute>
                <DocumentsPage />
              </RequireAuthRoute>
            }
          />
          <Route
            path="/reports"
            element={
              <RequireAuthRoute>
                <ReportsPage />
              </RequireAuthRoute>
            }
          />
          <Route
            path="/setup"
            element={
              <RequireAuthRoute>
                <SetupWizardPage />
              </RequireAuthRoute>
            }
          />
          <Route
            path="/interview/:sessionId"
            element={
              <RequireAuthRoute>
                <InterviewChatPage />
              </RequireAuthRoute>
            }
          />
          <Route
            path="/interview/:sessionId/report"
            element={
              <RequireAuthRoute>
                <ReportPage />
              </RequireAuthRoute>
            }
          />
          <Route
            path="/settings"
            element={
              <RequireAuthRoute>
                <SettingsPage />
              </RequireAuthRoute>
            }
          />
          <Route path="*" element={<NotFoundPage />} />
        </Routes>
      </BrowserRouter>
    </AuthProvider>
  )
}

export default App
