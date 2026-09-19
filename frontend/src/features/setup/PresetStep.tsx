import { Button } from '../../components/ui/Button'
import { ErrorAlert } from '../../components/ui/ErrorAlert'
import { LoadingSkeleton } from '../../components/ui/LoadingSkeleton'
import { toErrorMessage } from '../../lib/errorMessage'
import { phaseLabel } from '../../lib/interviewLabels'
import { useInterviewPresets } from '../../lib/queries'
import type { InterviewPreset, JobDescription } from '../../types/api'

interface PresetStepProps {
  jobDescription: JobDescription
  presetKey: string | null
  duration: number | null
  onChange: (presetKey: string, duration: number) => void
  onBack: () => void
  onContinue: () => void
}

export function PresetStep({
  jobDescription,
  presetKey,
  duration,
  onChange,
  onBack,
  onContinue,
}: PresetStepProps) {
  const presets = useInterviewPresets(jobDescription.coding_assessment_expected)

  // Picking a different preset resets to its shortest allowed duration,
  // since a duration valid for one preset may not exist on another.
  function choosePreset(preset: InterviewPreset) {
    if (preset.key === presetKey) return
    onChange(preset.key, preset.durations[0])
  }

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-lg font-semibold text-ink">Choose your interview</h2>
        <p className="mt-1 text-sm text-muted">
          Each format has its own set of durations. Time is weighted toward the
          phases that matter most.
        </p>
      </div>

      {presets.isLoading && <LoadingSkeleton variant="grid" />}
      <ErrorAlert message={presets.error ? toErrorMessage(presets.error, 'Could not load interview formats.') : null} />

      {presets.data && (
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3" role="radiogroup" aria-label="Interview presets">
          {presets.data.map((preset) => {
            const isSelected = preset.key === presetKey
            return (
              <div
                key={preset.key}
                className={`rounded-2xl border p-5 flex flex-col gap-3 transition-colors ${
                  isSelected ? 'border-brand bg-brand/5' : 'border-mist bg-white'
                }`}
              >
                <button
                  type="button"
                  role="radio"
                  aria-checked={isSelected}
                  onClick={() => choosePreset(preset)}
                  className="text-left cursor-pointer"
                >
                  <p className="text-[15px] font-semibold text-ink">{preset.label}</p>
                  <p className="text-xs text-muted mt-1">{preset.description}</p>
                  <p className="text-xs text-muted mt-2">
                    {preset.phases.map(phaseLabel).join(' · ')}
                  </p>
                </button>
                <div className="flex gap-2 mt-auto" role="group" aria-label={`${preset.label} duration`}>
                  {preset.durations.map((minutes) => {
                    const isActive = isSelected && duration === minutes
                    return (
                      <button
                        key={minutes}
                        type="button"
                        aria-pressed={isActive}
                        onClick={() => onChange(preset.key, minutes)}
                        className={`flex-1 rounded-lg border py-1.5 text-[13px] font-semibold cursor-pointer ${
                          isActive
                            ? 'bg-navy text-white border-navy'
                            : 'bg-white text-ink border-mist hover:border-hairline'
                        }`}
                      >
                        {minutes} min
                      </button>
                    )
                  })}
                </div>
              </div>
            )
          })}
        </div>
      )}

      <div className="flex gap-3 sm:justify-between">
        <div className="sm:w-32">
          <Button variant="secondary" onClick={onBack}>
            Back
          </Button>
        </div>
        <div className="sm:w-48">
          <Button disabled={!presetKey || !duration} onClick={onContinue}>
            Continue
          </Button>
        </div>
      </div>
    </div>
  )
}
