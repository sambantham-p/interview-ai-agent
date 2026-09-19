import {
  AcademicCapIcon,
  BriefcaseIcon,
  CodeIcon,
  FolderIcon,
  LinkIcon,
  SparkleIcon,
} from '../../components/ui/icons'
import { MissingNotice } from '../../components/ui/MissingNotice'
import type { JobDescription, Resume } from '../../types/api'
import { Chips, PreviewSection, Timeline } from './DocumentPreviewCard'

function dateRange(start: string | null, end: string | null): string | null {
  if (!start && !end) return null
  return `${start ?? '?'} – ${end ?? 'Present'}`
}

export function ResumePreview({ resume }: { resume: Resume }) {
  return (
    <>
      <MissingNotice subject="resume" items={resume.missing_sections} />

      {resume.experience.length > 0 && (
        <PreviewSection icon={<BriefcaseIcon />} title="Experience">
          <Timeline
            items={resume.experience.map((e) => ({
              title: e.role,
              meta: e.company,
              dates: dateRange(e.start_date, e.end_date),
              description: e.description,
            }))}
          />
        </PreviewSection>
      )}

      {resume.education.length > 0 && (
        <PreviewSection icon={<AcademicCapIcon />} title="Education">
          <Timeline
            items={resume.education.map((e) => ({
              title: e.degree,
              meta: [e.institution, e.field_of_study].filter(Boolean).join(' · '),
              dates: dateRange(e.start_date, e.end_date),
            }))}
          />
        </PreviewSection>
      )}

      {resume.projects.length > 0 && (
        <PreviewSection icon={<FolderIcon />} title="Projects">
          <div className="grid gap-3 sm:grid-cols-2">
            {resume.projects.map((p, i) => (
              <div key={i} className="rounded-xl border border-mist bg-[#f8fafc] p-3.5">
                <p className="text-[14px] font-semibold text-ink">{p.name}</p>
                {p.description && (
                  <p className="text-xs text-muted mt-1 leading-relaxed line-clamp-2">{p.description}</p>
                )}
                {p.tech_stack.length > 0 && (
                  <div className="mt-2.5">
                    <Chips items={p.tech_stack} max={5} tone="navy" />
                  </div>
                )}
              </div>
            ))}
          </div>
        </PreviewSection>
      )}

      {resume.skills.length > 0 && (
        <PreviewSection icon={<SparkleIcon />} title="Skills">
          <Chips items={resume.skills} tone="brand" />
        </PreviewSection>
      )}

      {resume.github_url && (
        <PreviewSection icon={<LinkIcon />} title="GitHub">
          <p className="text-[13px] text-navy font-medium break-all">{resume.github_url}</p>
        </PreviewSection>
      )}
    </>
  )
}

export function JobDescriptionPreview({ jd }: { jd: JobDescription }) {
  return (
    <>
      <MissingNotice
        subject="job description"
        items={jd.missing_details}
        hint="Without a company, questions about why this company will be generic."
      />
      <PreviewSection icon={<CodeIcon />} title="Tech stack">
        {jd.tech_stack.length > 0 ? (
          <Chips items={jd.tech_stack} tone="brand" />
        ) : (
          <p className="text-sm text-muted">No specific technologies listed.</p>
        )}
      </PreviewSection>
    </>
  )
}
