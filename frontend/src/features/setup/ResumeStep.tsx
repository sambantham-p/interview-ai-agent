import { useRef, useState } from 'react'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import { Button } from '../../components/ui/Button'
import { Card } from '../../components/ui/Card'
import { ErrorAlert } from '../../components/ui/ErrorAlert'
import { LoadingSkeleton } from '../../components/ui/LoadingSkeleton'
import { DocumentIcon } from '../../components/ui/icons'
import { api } from '../../lib/api'
import { toErrorMessage } from '../../lib/errorMessage'
import { useResumes } from '../../lib/queries'
import type { Resume } from '../../types/api'
import { DocumentPreviewCard } from './DocumentPreviewCard'
import { ResumePreview, resumeStats } from './DocumentPreviews'

export const MAX_RESUME_SIZE_BYTES = 10 * 1024 * 1024

interface ResumeStepProps {
  selected: Resume | null
  onSelect: (resume: Resume | null) => void
  onContinue: () => void
}

function resumeTitle(resume: Resume): string {
  const job = resume.experience[0]
  if (job) return `${job.role} at ${job.company}`
  return resume.education[0]?.institution ?? 'Resume'
}

export function ResumeStep({ selected, onSelect, onContinue }: ResumeStepProps) {
  const resumes = useResumes()
  const queryClient = useQueryClient()
  const fileInput = useRef<HTMLInputElement>(null)
  const [fileError, setFileError] = useState<string | null>(null)

  const upload = useMutation({
    mutationFn: (file: File) => {
      const form = new FormData()
      form.append('file', file)
      return api.upload<Resume>('/resume/upload', form)
    },
    onSuccess: (resume) => {
      void queryClient.invalidateQueries({ queryKey: ['resumes'] })
      onSelect(resume)
    },
  })


  function handleFile(file: File | undefined) {
    setFileError(null)
    if (!file) return
    if (file.type !== 'application/pdf') {
      setFileError('Please choose a PDF file.')
      return
    }
    if (file.size > MAX_RESUME_SIZE_BYTES) {
      setFileError('That file is over the 10 MB limit.')
      return
    }
    upload.mutate(file)
  }

  const uploadError = fileError ?? (upload.error ? toErrorMessage(upload.error, 'Could not upload that resume.') : null)
  const previous = (resumes.data ?? []).filter((r) => r.id !== selected?.id)

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-lg font-semibold text-ink">Your resume</h2>
        <p className="mt-1 text-sm text-muted">
          Every question is grounded in it. Upload a PDF, or reuse one you've already submitted.
        </p>
      </div>

      {selected ? (
        <DocumentPreviewCard
          icon={<DocumentIcon className="w-5 h-5" />}
          title={resumeTitle(selected)}
          subtitle={`Uploaded ${new Date(selected.created_at).toLocaleDateString()}`}
          id={selected.id}
          kind="resume"
          stats={resumeStats(selected)}
          onDeleted={() => onSelect(null)}
          onChange={() => onSelect(null)}
        >
          <ResumePreview resume={selected} />
        </DocumentPreviewCard>
      ) : (
        <>
          <Card className="flex flex-col sm:flex-row sm:items-center gap-4 justify-between">
            <div>
              <p className="text-[14px] font-semibold text-ink">Upload a new resume</p>
              <p className="text-xs text-muted mt-1">PDF, up to 10 MB.</p>
            </div>
            <div className="sm:w-48">
              <input
                ref={fileInput}
                type="file"
                accept="application/pdf"
                aria-label="Resume PDF"
                className="sr-only"
                onChange={(e) => {
                  handleFile(e.target.files?.[0])
                  e.target.value = ''
                }}
              />
              <Button variant="outline" isLoading={upload.isPending} onClick={() => fileInput.current?.click()}>
                Choose PDF
              </Button>
            </div>
          </Card>
          <ErrorAlert message={uploadError} />

          {resumes.isLoading && <LoadingSkeleton variant="grid" />}
          {previous.length > 0 && (
            <div>
              <h3 className="text-xs font-semibold uppercase tracking-wide text-muted mb-3">
                Or pick a previous resume
              </h3>
              <div className="grid gap-3 sm:grid-cols-2">
                {previous.map((resume) => (
                  <button
                    key={resume.id}
                    type="button"
                    onClick={() => onSelect(resume)}
                    className="text-left rounded-2xl border border-mist bg-white hover:border-hairline p-4 flex items-start gap-3.5 transition-colors cursor-pointer"
                  >
                    <div className="w-10 h-10 rounded-xl bg-navy/10 text-navy flex items-center justify-center shrink-0">
                      <DocumentIcon className="w-5 h-5" />
                    </div>
                    <div className="min-w-0 flex-1">
                      <p className="text-[14px] font-semibold text-ink truncate">{resumeTitle(resume)}</p>
                      <p className="text-xs text-muted mt-1">
                        {new Date(resume.created_at).toLocaleDateString()} · {resume.skills.length} skills
                      </p>
                    </div>
                  </button>
                ))}
              </div>
            </div>
          )}
        </>
      )}

      <div className="sm:w-48 sm:ml-auto">
        <Button disabled={!selected} onClick={onContinue}>
          Continue
        </Button>
      </div>
    </div>
  )
}
