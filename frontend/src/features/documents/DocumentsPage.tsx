import { AppShell } from '../../components/AppShell'
import { Badge } from '../../components/ui/Badge'
import { EmptyState } from '../../components/ui/EmptyState'
import { ErrorState } from '../../components/ui/ErrorState'
import { LoadingSkeleton } from '../../components/ui/LoadingSkeleton'
import { BriefcaseIcon, DocumentIcon } from '../../components/ui/icons'
import { MissingNotice } from '../../components/ui/MissingNotice'
import { DocumentCard } from './DocumentCard'
import { useJobDescriptions, useResumes } from '../../lib/queries'
import type { JobDescription, Resume, Seniority } from '../../types/api'

function formatDate(value: string): string {
  return new Date(value).toLocaleDateString(undefined, {
    month: 'short',
    day: 'numeric',
    year: 'numeric',
  })
}

const SENIORITY_TONE: Record<Seniority, 'neutral' | 'brand' | 'navy'> = {
  intern: 'neutral',
  entry: 'neutral',
  fresher: 'neutral',
  mid: 'brand',
  senior: 'navy',
}

function ResumeCard({ resume }: { resume: Resume }) {
  const latestRole = resume.experience[0]?.role ?? resume.projects[0]?.name
  return (
    <DocumentCard
      id={resume.id}
      kind="resume"
      chip={
        <div className="w-10 h-10 rounded-xl bg-navy/10 text-navy flex items-center justify-center shrink-0">
          <DocumentIcon className="w-5 h-5" />
        </div>
      }
    >
      <p className="text-[14px] font-semibold text-ink">
        Resume · {formatDate(resume.created_at)}
      </p>
      <p className="text-xs text-muted mt-1">
        {resume.skills.length} skill{resume.skills.length === 1 ? '' : 's'}
        {latestRole ? ` · ${latestRole}` : ''}
      </p>
      <div className="mt-2">
        <MissingNotice subject="resume" items={resume.missing_sections} />
      </div>
    </DocumentCard>
  )
}

function JobDescriptionCard({ jd }: { jd: JobDescription }) {
  return (
    <DocumentCard
      id={jd.id}
      kind="job description"
      chip={
        <div className="w-10 h-10 rounded-xl bg-brand/10 text-brand flex items-center justify-center shrink-0">
          <BriefcaseIcon className="w-5 h-5" />
        </div>
      }
    >
      <div className="flex items-center gap-2">
        <p className="text-[14px] font-semibold text-ink truncate">{jd.role}</p>
        <Badge tone={SENIORITY_TONE[jd.seniority]} className="shrink-0">
          {jd.seniority}
        </Badge>
      </div>
      <p className="text-xs text-muted mt-1">
        {jd.company_name ? `${jd.company_name} · ` : ''}
        {formatDate(jd.created_at)}
      </p>
      {jd.tech_stack.length > 0 && (
        <p className="text-xs text-muted mt-1 truncate">
          {jd.tech_stack.join(', ')}
        </p>
      )}
      <div className="mt-2">
        <MissingNotice subject="job description" items={jd.missing_details} />
      </div>
    </DocumentCard>
  )
}

export function DocumentsPage() {
  const resumes = useResumes()
  const jds = useJobDescriptions()

  return (
    <AppShell>
      <h1 className="text-2xl font-bold text-ink">Documents</h1>
      <p className="mt-1 text-sm text-muted">
        Every resume and job description you've submitted. Deleting one also
        deletes the completed interviews that used it, and their reports.
      </p>

      <section className="mt-8">
        <h2 className="flex items-center gap-2 text-sm font-semibold text-muted uppercase tracking-wide mb-3">
          <DocumentIcon className="w-4 h-4" />
          Resumes
        </h2>
        {resumes.isLoading && <LoadingSkeleton rows={2} variant="grid" />}
        {resumes.isError && (
          <ErrorState
            message="Couldn't load your resumes."
            onRetry={() => resumes.refetch()}
          />
        )}
        {!resumes.isLoading &&
          !resumes.isError &&
          resumes.data?.length === 0 && (
            <EmptyState
              icon={<DocumentIcon className="w-5 h-5" />}
              title="No resumes uploaded yet"
              description="Upload a resume when you start your first interview."
            />
          )}
        {!resumes.isLoading &&
          !resumes.isError &&
          resumes.data &&
          resumes.data.length > 0 && (
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
              {resumes.data.map((resume) => (
                <ResumeCard key={resume.id} resume={resume} />
              ))}
            </div>
          )}
      </section>

      <section className="mt-8">
        <h2 className="flex items-center gap-2 text-sm font-semibold text-muted uppercase tracking-wide mb-3">
          <BriefcaseIcon className="w-4 h-4" />
          Job descriptions
        </h2>
        {jds.isLoading && <LoadingSkeleton rows={2} variant="grid" />}
        {jds.isError && (
          <ErrorState
            message="Couldn't load your job descriptions."
            onRetry={() => jds.refetch()}
          />
        )}
        {!jds.isLoading && !jds.isError && jds.data?.length === 0 && (
          <EmptyState
            icon={<BriefcaseIcon className="w-5 h-5" />}
            title="No job descriptions yet"
            description="Add a target job description when you start your first interview."
          />
        )}
        {!jds.isLoading && !jds.isError && jds.data && jds.data.length > 0 && (
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
            {jds.data.map((jd) => (
              <JobDescriptionCard key={jd.id} jd={jd} />
            ))}
          </div>
        )}
      </section>
    </AppShell>
  )
}
