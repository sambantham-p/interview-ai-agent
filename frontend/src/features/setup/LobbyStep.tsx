import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import { Button } from '../../components/ui/Button'
import { Card } from '../../components/ui/Card'
import { ErrorAlert } from '../../components/ui/ErrorAlert'
import { api } from '../../lib/api'
import { toErrorMessage } from '../../lib/errorMessage'
import type {
  InterviewPreset,
  InterviewStartRequest,
  InterviewStartResponse,
  JobDescription,
  Resume,
} from '../../types/api'
import { LobbyStarting } from './LobbyStarting'

export const LOBBY_COUNTDOWN_SECONDS = 3

export const PREPARING_STAGE_MS = 3500

function preparingStages(hasCompany: boolean): string[] {
  return [
    'Reading your resume',
    'Matching questions to the role',
    ...(hasCompany ? ['Researching the company'] : []),
    'Getting your interviewer ready',
  ]
}

interface LobbyStepProps {
  resume: Resume
  jobDescription: JobDescription
  preset: InterviewPreset
  duration: number
  onBack: () => void
}

export function LobbyStep({
  resume,
  jobDescription,
  preset,
  duration,
  onBack,
}: LobbyStepProps) {
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const [secondsLeft, setSecondsLeft] = useState<number | null>(null)
  const [activeStage, setActiveStage] = useState(0)
  const stages = preparingStages(Boolean(jobDescription.company_name))

  // The request starts the moment "Begin" is clicked, in parallel with the
  // countdown, so the wait is hidden behind it instead of added after it.
  const start = useMutation({
    mutationFn: (payload: InterviewStartRequest) =>
      api.post<InterviewStartResponse>('/interview/start', payload),
    onSuccess: () =>
      void queryClient.invalidateQueries({ queryKey: ['interviews'] }),
    onError: () => {
      setSecondsLeft(null)
      setActiveStage(0)
    },
  })

  const isStarting = secondsLeft !== null
  const countdownDone = secondsLeft === 0

  useEffect(() => {
    if (secondsLeft === null || secondsLeft === 0) return
    const timer = setTimeout(() => setSecondsLeft(secondsLeft - 1), 1000)
    return () => clearTimeout(timer)
  }, [secondsLeft])

  useEffect(() => {
    if (countdownDone && start.isSuccess)
      navigate(`/interview/${start.data.id}`)
  }, [countdownDone, start.isSuccess, start.data, navigate])

  useEffect(() => {
    if (!countdownDone || !start.isPending) return
    const timer = setInterval(
      () => setActiveStage((stage) => Math.min(stage + 1, stages.length - 1)),
      PREPARING_STAGE_MS,
    )
    return () => clearInterval(timer)
  }, [countdownDone, start.isPending, stages.length])

  function begin() {
    setActiveStage(0)
    setSecondsLeft(LOBBY_COUNTDOWN_SECONDS)
    start.mutate({
      candidate_profile_id: resume.id,
      job_description_id: jobDescription.id,
      preset_key: preset.key,
      duration_minutes: duration,
    })
  }

  return (
    <div className="space-y-6">
      {isStarting ? (
        <LobbyStarting
          secondsLeft={secondsLeft}
          countdownTotal={LOBBY_COUNTDOWN_SECONDS}
          stages={stages}
          activeStage={activeStage}
        />
      ) : (
        <>
          <div>
            <h2 className="text-lg font-semibold text-ink">
              Ready when you are
            </h2>
            <p className="mt-1 text-sm text-muted">
              The interviewer speaks first. Answer naturally, the way you would
              in person.
            </p>
          </div>

          <Card>
            <dl className="grid gap-4 sm:grid-cols-3 text-sm">
              <div>
                <dt className="text-xs font-semibold uppercase tracking-wide text-muted">
                  Role
                </dt>
                <dd className="mt-1 text-ink font-medium">
                  {jobDescription.role}
                  <span className="block text-xs text-muted font-normal">
                    {jobDescription.seniority}
                  </span>
                </dd>
              </div>
              <div>
                <dt className="text-xs font-semibold uppercase tracking-wide text-muted">
                  Format
                </dt>
                <dd className="mt-1 text-ink font-medium">
                  {preset.label}
                  <span className="block text-xs text-muted font-normal">
                    {duration} minutes
                  </span>
                </dd>
              </div>
              <div>
                <dt className="text-xs font-semibold uppercase tracking-wide text-muted">
                  Resume
                </dt>
                <dd className="mt-1 text-ink font-medium">
                  {new Date(resume.created_at).toLocaleDateString('en-GB')}
                </dd>
              </div>
            </dl>
          </Card>

          <ErrorAlert
            message={
              start.error
                ? toErrorMessage(start.error, 'Could not start the interview.')
                : null
            }
          />

          <div className="flex gap-3 sm:justify-between">
            <div className="sm:w-32">
              <Button variant="secondary" onClick={onBack}>
                Back
              </Button>
            </div>
            <div className="sm:w-56">
              <Button onClick={begin}>Begin interview</Button>
            </div>
          </div>
        </>
      )}
    </div>
  )
}
