import { useParams } from 'react-router'

// Placeholder — Monaco editor + 30-minute timer + paste-blocking/tab-blur
// detection land here once Stage 4 (backend) and the anti-cheating item on
// the Pre-Deployment Checklist are both done (see root CLAUDE.md).
export function CodingChallengePage() {
  const { sessionId } = useParams()

  return (
    <div className="mx-auto max-w-2xl p-8">
      <h2 className="text-xl font-semibold text-slate-900">
        Coding challenge — session {sessionId}
      </h2>
      <p className="mt-2 text-slate-600">
        Placeholder page. Will only render when the JD implied a coding
        assessment, once the Stage 4 backend orchestrator exists.
      </p>
    </div>
  )
}

export default CodingChallengePage
