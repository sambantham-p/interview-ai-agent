import { useState } from 'react'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import { Button } from '../../components/ui/Button'
import { ErrorAlert } from '../../components/ui/ErrorAlert'
import { LoadingSkeleton } from '../../components/ui/LoadingSkeleton'
import { BriefcaseIcon } from '../../components/ui/icons'
import { api } from '../../lib/api'
import { toErrorMessage } from '../../lib/errorMessage'
import { useJobDescriptions } from '../../lib/queries'
import type { JobDescription } from '../../types/api'
import { DocumentPreviewCard } from './DocumentPreviewCard'
import { JobDescriptionPreview, jobDescriptionStats } from './DocumentPreviews'

type JdMode = 'full_text' | 'short_description'

const MODE_COPY: Record<JdMode, { tab: string; label: string; placeholder: string }> = {
  full_text: {
    tab: 'Full job description',
    label: 'Paste the job description',
    placeholder: 'Paste the full posting: responsibilities, requirements, tech stack…',
  },
  short_description: {
    tab: 'Short description',
    label: 'Describe the role',
    placeholder: 'e.g. AI Engineer, mid-level, Python and TensorFlow',
  },
}

interface JobDescriptionStepProps {
  selected: JobDescription | null
  onSelect: (jd: JobDescription | null) => void
  onBack: () => void
  onContinue: () => void
}

export function JobDescriptionStep({
  selected,
  onSelect,
  onBack,
  onContinue,
}: JobDescriptionStepProps) {
  const jds = useJobDescriptions()
  const queryClient = useQueryClient()
  const [mode, setMode] = useState<JdMode>('full_text')
  // One draft per tab, so switching tabs never carries text across modes.
  const [drafts, setDrafts] = useState<Record<JdMode, string>>({
    full_text: '',
    short_description: '',
  })
  const text = drafts[mode]

  const submit = useMutation({
    mutationFn: (payload: Partial<Record<JdMode, string>>) =>
      api.post<JobDescription>('/jd', payload),
    onSuccess: (jd) => {
      void queryClient.invalidateQueries({ queryKey: ['job-descriptions'] })
      onSelect(jd)
      setDrafts({ full_text: '', short_description: '' })
    },
  })


  const copy = MODE_COPY[mode]
  const previous = (jds.data ?? []).filter((jd) => jd.id !== selected?.id)

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-lg font-semibold text-ink">The role you're targeting</h2>
        <p className="mt-1 text-sm text-muted">
          Paste a job description, or just describe the role in a sentence.
        </p>
      </div>

      {selected ? (
        <DocumentPreviewCard
          icon={<BriefcaseIcon className="w-5 h-5" />}
          title={selected.role}
          subtitle={`${selected.company_name ? `${selected.company_name} · ` : ''}Added ${new Date(selected.created_at).toLocaleDateString()}`}
          id={selected.id}
          kind="job description"
          stats={jobDescriptionStats(selected)}
          onDeleted={() => onSelect(null)}
          onChange={() => onSelect(null)}
        >
          <JobDescriptionPreview jd={selected} />
        </DocumentPreviewCard>
      ) : (
        <>
      <div className="rounded-2xl bg-white border border-mist p-5 sm:p-6 space-y-4">
        <div role="tablist" className="inline-flex rounded-lg bg-[#f4f7fa] p-1 gap-1">
          {(Object.keys(MODE_COPY) as JdMode[]).map((key) => (
            <button
              key={key}
              type="button"
              role="tab"
              aria-selected={mode === key}
              onClick={() => {
                // The error belongs to the tab it happened in.
                submit.reset()
                setMode(key)
              }}
              className={`px-3 py-1.5 rounded-md text-[13px] font-medium cursor-pointer ${
                mode === key ? 'bg-white text-ink shadow-sm' : 'text-muted'
              }`}
            >
              {MODE_COPY[key].tab}
            </button>
          ))}
        </div>

        <div className="flex flex-col gap-1.5">
          <label htmlFor="jd-text" className="text-[14px] font-semibold text-ink">
            {copy.label}
          </label>
          <textarea
            id="jd-text"
            value={text}
            onChange={(e) => setDrafts({ ...drafts, [mode]: e.target.value })}
            rows={mode === 'full_text' ? 8 : 3}
            placeholder={copy.placeholder}
            className="w-full rounded-[10px] border border-mist p-3 text-[14px] text-ink focus:outline-none focus:border-brand"
          />
        </div>

        <ErrorAlert message={submit.error ? toErrorMessage(submit.error, 'Could not analyze that role.') : null} />

        <div className="sm:w-56 sm:ml-auto">
          <Button
            variant="outline"
            isLoading={submit.isPending}
            disabled={text.trim() === ''}
            onClick={() => submit.mutate({ [mode]: text.trim() })}
          >
            Analyze role
          </Button>
        </div>
      </div>

      {jds.isLoading && <LoadingSkeleton variant="grid" />}
      {previous.length > 0 && (
        <div>
          <h3 className="text-xs font-semibold uppercase tracking-wide text-muted mb-3">
            Or pick a previous role
          </h3>
          <div className="grid gap-3 sm:grid-cols-2">
            {previous.map((jd) => {
              return (
                <button
                  key={jd.id}
                  type="button"
                  onClick={() => onSelect(jd)}
                  className="text-left rounded-2xl border border-mist bg-white hover:border-hairline p-4 flex items-start gap-3.5 transition-colors cursor-pointer"
                >
                  <div className="w-10 h-10 rounded-xl bg-brand/10 text-brand flex items-center justify-center shrink-0">
                    <BriefcaseIcon className="w-5 h-5" />
                  </div>
                  <div className="min-w-0 flex-1">
                    <p className="text-[14px] font-semibold text-ink truncate">{jd.role}</p>
                    <p className="text-xs text-muted mt-1 truncate">
                      {jd.company_name ? `${jd.company_name} · ` : ''}
                      {jd.seniority} · {jd.tech_stack.join(', ')}
                    </p>
                  </div>
                </button>
              )
            })}
          </div>
        </div>
      )}
        </>
      )}

      <div className="flex gap-3 sm:justify-between">
        <div className="sm:w-32">
          <Button variant="secondary" onClick={onBack}>
            Back
          </Button>
        </div>
        <div className="sm:w-48">
          <Button disabled={!selected} onClick={onContinue}>
            Continue
          </Button>
        </div>
      </div>
    </div>
  )
}
