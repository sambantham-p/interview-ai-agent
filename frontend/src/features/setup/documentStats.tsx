import {
  BriefcaseIcon,
  CheckCircleIcon,
  CodeIcon,
  FolderIcon,
  SparkleIcon,
} from '../../components/ui/icons'
import type { JobDescription, Resume } from '../../types/api'
import type { PreviewStat } from './DocumentPreviewCard'

export function resumeStats(resume: Resume): PreviewStat[] {
  return [
    { icon: <BriefcaseIcon className="w-4.5 h-4.5" />, value: resume.experience.length, label: 'Roles', tone: 'navy' },
    { icon: <FolderIcon className="w-4.5 h-4.5" />, value: resume.projects.length, label: 'Projects', tone: 'brand' },
    { icon: <SparkleIcon className="w-4.5 h-4.5" />, value: resume.skills.length, label: 'Skills', tone: 'amber' },
  ]
}

export function jobDescriptionStats(jd: JobDescription): PreviewStat[] {
  return [
    {
      icon: <BriefcaseIcon className="w-4.5 h-4.5" />,
      value: <span className="capitalize">{jd.seniority}</span>,
      label: 'Level',
      tone: 'navy',
    },
    { icon: <CodeIcon className="w-4.5 h-4.5" />, value: jd.tech_stack.length, label: 'Technologies', tone: 'brand' },
    {
      icon: <CheckCircleIcon className="w-4.5 h-4.5" />,
      value: jd.coding_assessment_expected ? 'Expected' : 'Not expected',
      label: 'Coding round',
      tone: 'amber',
    },
  ]
}
