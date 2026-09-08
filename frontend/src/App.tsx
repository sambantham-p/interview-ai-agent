import { BrowserRouter, Link, Route, Routes } from 'react-router'
import { HealthStatus } from './features/health-check/HealthStatus'
import { ResumeUploadPage } from './features/resume-upload/ResumeUploadPage'
import { InterviewChatPage } from './features/interview-chat/InterviewChatPage'
import { CodingChallengePage } from './features/coding-challenge/CodingChallengePage'
import { ReportPage } from './features/report/ReportPage'

function HomePage() {
  return (
    <div className="mx-auto max-w-2xl p-8">
      <h1 className="text-2xl font-semibold text-slate-900">
        interview-ai-agent
      </h1>
      <HealthStatus />
      <nav className="mt-6 flex flex-col gap-2 text-blue-600 underline">
        <Link to="/setup">Resume + JD setup</Link>
        <Link to="/interview/demo-session">Interview chat (placeholder)</Link>
        <Link to="/interview/demo-session/coding">
          Coding challenge (placeholder)
        </Link>
        <Link to="/interview/demo-session/report">
          Report (placeholder)
        </Link>
      </nav>
    </div>
  )
}

export function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<HomePage />} />
        <Route path="/setup" element={<ResumeUploadPage />} />
        <Route path="/interview/:sessionId" element={<InterviewChatPage />} />
        <Route
          path="/interview/:sessionId/coding"
          element={<CodingChallengePage />}
        />
        <Route
          path="/interview/:sessionId/report"
          element={<ReportPage />}
        />
      </Routes>
    </BrowserRouter>
  )
}

export default App
