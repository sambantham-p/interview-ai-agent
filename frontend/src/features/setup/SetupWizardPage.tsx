import { useState } from 'react'
import { AppShell } from '../../components/AppShell'
import { PageIntro } from '../../components/ui/PageIntro'
import { Stepper } from '../../components/ui/Stepper'
import { useInterviewPresets } from '../../lib/queries'
import type { JobDescription, Resume } from '../../types/api'
import { JobDescriptionStep } from './JobDescriptionStep'
import { LobbyStep } from './LobbyStep'
import { MicCheckStep } from './MicCheckStep'
import { PresetStep } from './PresetStep'
import { ResumeStep } from './ResumeStep'

const STEPS = ['Resume', 'Role', 'Format', 'Mic check', 'Lobby'] as const

export function SetupWizardPage() {
  const [step, setStep] = useState(0)
  const [resume, setResume] = useState<Resume | null>(null)
  const [jd, setJd] = useState<JobDescription | null>(null)
  const [presetKey, setPresetKey] = useState<string | null>(null)
  const [duration, setDuration] = useState<number | null>(null)
  const presets = useInterviewPresets(jd?.coding_assessment_expected ?? true)
  const preset = presets.data?.find((p) => p.key === presetKey) ?? null

  function selectJd(next: JobDescription | null) {
    if (next?.id !== jd?.id) {
      setPresetKey(null)
      setDuration(null)
    }
    setJd(next)
  }

  return (
    <AppShell title="New interview">
      <PageIntro
        title="Set up your interview"
        description="Choose your resume, the role you're targeting and a format. The questions are tailored to you."
      />
      <div className="mt-8 mb-8">
        <Stepper steps={STEPS} current={step} />
      </div>

      {step === 0 && (
        <ResumeStep selected={resume} onSelect={setResume} onContinue={() => setStep(1)} />
      )}
      {step === 1 && (
        <JobDescriptionStep
          selected={jd}
          onSelect={selectJd}
          onBack={() => setStep(0)}
          onContinue={() => setStep(2)}
        />
      )}
      {step === 2 && jd && (
        <PresetStep
          jobDescription={jd}
          presetKey={presetKey}
          duration={duration}
          onChange={(key, minutes) => {
            setPresetKey(key)
            setDuration(minutes)
          }}
          onBack={() => setStep(1)}
          onContinue={() => setStep(3)}
        />
      )}
      {step === 3 && <MicCheckStep onBack={() => setStep(2)} onContinue={() => setStep(4)} />}
      {step === 4 && resume && jd && preset && duration && (
        <LobbyStep
          resume={resume}
          jobDescription={jd}
          preset={preset}
          duration={duration}
          onBack={() => setStep(3)}
        />
      )}
    </AppShell>
  )
}

export default SetupWizardPage
