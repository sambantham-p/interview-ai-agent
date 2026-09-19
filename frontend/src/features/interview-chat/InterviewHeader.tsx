import { Link } from 'react-router'
import { PrepwiseLogo } from '../../components/ui/PrepwiseLogo'
import { ArrowLeftIcon, ClockIcon, SpeakerIcon, SpeakerMutedIcon } from '../../components/ui/icons'
import { phaseLabel } from '../../lib/interviewLabels'
import type { InterviewDetail } from '../../types/api'
import { formatClock, usePhaseRemainingSeconds } from './usePhaseClock'

interface InterviewHeaderProps {
  interview: InterviewDetail
  voiceOn: boolean
  onToggleVoice: () => void
}

function PhaseTimerChip({ interview }: { interview: InterviewDetail }) {
  const remainingSeconds = usePhaseRemainingSeconds(interview)
  if (remainingSeconds === null) return null

  const isRunningLow = interview.phase_time_status && interview.phase_time_status !== 'comfortable'
  return (
    <span
      className={`inline-flex items-center gap-1.5 rounded-full px-3 py-1.5 text-xs font-semibold tabular-nums ${
        isRunningLow ? 'bg-amber-400/15 text-amber-200' : 'bg-white/10 text-slate-200'
      }`}
      aria-label="Time left in this phase"
    >
      <ClockIcon className="w-3.5 h-3.5" />
      {remainingSeconds === 0 ? 'Wrapping up' : formatClock(remainingSeconds)}
    </span>
  )
}

export function InterviewHeader({ interview, voiceOn, onToggleVoice }: InterviewHeaderProps) {
  const phases = interview.selected_phases
  const phaseNumber = phases.indexOf(interview.current_phase) + 1

  return (
    <header className="border-b border-white/10 bg-hero">
      <div className="mx-auto max-w-3xl flex items-center justify-between gap-3 px-4 sm:px-6 py-3">
        <div className="flex items-center gap-3 min-w-0">
          <Link
            to="/dashboard"
            aria-label="Leave the interview"
            className="p-2 -ml-2 rounded-lg text-slate-300 hover:bg-white/10 hover:text-white transition-colors"
          >
            <ArrowLeftIcon className="w-5 h-5" />
          </Link>
          <div className="min-w-0">
            <p className="text-sm font-semibold text-white truncate">
              {interview.job_role}
              {interview.company_name ? ` · ${interview.company_name}` : ''}
            </p>
            <p className="text-xs text-slate-400 truncate">
              {phaseNumber > 0 ? `Phase ${phaseNumber} of ${phases.length} · ` : ''}
              {phaseLabel(interview.current_phase)}
            </p>
          </div>
        </div>

        <div className="flex items-center gap-2 shrink-0">
          <PhaseTimerChip key={interview.server_time} interview={interview} />
          <button
            type="button"
            onClick={onToggleVoice}
            aria-pressed={voiceOn}
            aria-label={voiceOn ? 'Mute interviewer voice' : 'Unmute interviewer voice'}
            className="p-2 rounded-lg text-slate-300 hover:bg-white/10 hover:text-white transition-colors cursor-pointer"
          >
            {voiceOn ? <SpeakerIcon className="w-5 h-5" /> : <SpeakerMutedIcon className="w-5 h-5" />}
          </button>
          <span className="hidden sm:block">
            <PrepwiseLogo size="sm" showWordmark={false} />
          </span>
        </div>
      </div>

      {phases.length > 1 && (
        <div className="mx-auto max-w-3xl flex gap-1.5 px-4 sm:px-6 pb-3" aria-hidden="true">
          {phases.map((phase, index) => (
            <span
              key={phase}
              className={`h-1 flex-1 rounded-full ${
                index + 1 < phaseNumber
                  ? 'bg-brand'
                  : index + 1 === phaseNumber
                    ? 'bg-brand/60'
                    : 'bg-white/10'
              }`}
            />
          ))}
        </div>
      )}
    </header>
  )
}
