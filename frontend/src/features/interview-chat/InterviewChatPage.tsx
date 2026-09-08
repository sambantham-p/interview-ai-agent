import { useParams } from 'react-router'

// Placeholder — one continuous view across Interview Phases 1,2,3,5,6,7,
// matching the backend's single persistent Interviewer agent (no route
// change per phase — see root CLAUDE.md's Agent Architecture). Wired to
// streamed chat turns once the Stage 2 backend endpoints exist.
export function InterviewChatPage() {
  const { sessionId } = useParams()

  return (
    <div className="mx-auto max-w-2xl p-8">
      <h2 className="text-xl font-semibold text-slate-900">
        Interview session {sessionId}
      </h2>
      <p className="mt-2 text-slate-600">
        Placeholder page. Will stream the Interviewer agent's replies once
        the Stage 2 chat-turn endpoints exist.
      </p>
    </div>
  )
}

export default InterviewChatPage
