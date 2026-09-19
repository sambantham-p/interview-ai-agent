import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import { JobDescriptionPreview, ResumePreview } from './DocumentPreviews'
import { jobDescriptionStats, resumeStats } from './documentStats'
import type { JobDescription, Resume } from '../../types/api'

const RESUME: Resume = {
  id: 1,
  education: [
    { institution: 'MIT', degree: 'BS', field_of_study: 'CS', start_date: '2018', end_date: '2022' },
  ],
  experience: [
    { company: 'Acme', role: 'Engineer', start_date: '2022', end_date: null, description: 'Built APIs' },
  ],
  projects: [{ name: 'Widget', description: 'A widget', tech_stack: ['Rust'], repo_url: null }],
  skills: ['Python', 'SQL'],
  github_url: 'https://github.com/example',
  missing_sections: [],
  created_at: '2026-01-01T00:00:00Z',
}

const JD: JobDescription = {
  id: 2,
  role: 'Backend Engineer',
  company_name: null,
  seniority: 'senior',
  tech_stack: ['Go', 'Postgres'],
  coding_assessment_expected: false,
  missing_details: ['Company name'],
  created_at: '2026-01-01T00:00:00Z',
}

describe('ResumePreview', () => {
  it('renders experience, education, projects, skills and GitHub', () => {
    render(<ResumePreview resume={RESUME} />)

    expect(screen.getByText('Engineer')).toBeInTheDocument()
    expect(screen.getByText('2022 – Present')).toBeInTheDocument()
    expect(screen.getByText('Built APIs')).toBeInTheDocument()
    expect(screen.getByText('MIT · CS')).toBeInTheDocument()
    expect(screen.getByText('Widget')).toBeInTheDocument()
    expect(screen.getByText('Rust')).toBeInTheDocument()
    expect(screen.getByText('SQL')).toBeInTheDocument()
    expect(screen.getByText('https://github.com/example')).toBeInTheDocument()
  })

  it('omits sections the resume does not have', () => {
    render(
      <ResumePreview
        resume={{ ...RESUME, education: [], experience: [], projects: [], github_url: null }}
      />,
    )

    expect(screen.queryByText('Experience')).not.toBeInTheDocument()
    expect(screen.queryByText('GitHub')).not.toBeInTheDocument()
    expect(screen.getByText('Skills')).toBeInTheDocument()
  })

  it('counts roles, projects and skills for the stats row', () => {
    expect(resumeStats(RESUME).map((s) => [s.label, s.value])).toEqual([
      ['Roles', 1],
      ['Projects', 1],
      ['Skills', 2],
    ])
  })
})

describe('JobDescriptionPreview', () => {
  it('shows the tech stack chips', () => {
    render(<JobDescriptionPreview jd={JD} />)

    expect(screen.getByText('Postgres')).toBeInTheDocument()
  })

  it('handles an empty tech stack', () => {
    render(<JobDescriptionPreview jd={{ ...JD, tech_stack: [] }} />)

    expect(screen.getByText('No specific technologies listed.')).toBeInTheDocument()
  })

  it('reports the coding round in the stats row', () => {
    const coding = jobDescriptionStats(JD).find((s) => s.label === 'Coding round')

    expect(coding?.value).toBe('Not expected')
  })
})


describe('missing-content notices', () => {
  it('lists what a partial resume is missing', () => {
    render(<ResumePreview resume={{ ...RESUME, missing_sections: ['Education', 'Projects'] }} />)

    expect(screen.getByRole('note')).toHaveTextContent('Not found in this resume: Education, Projects.')
  })

  it('shows no notice for a complete resume', () => {
    render(<ResumePreview resume={RESUME} />)

    expect(screen.queryByRole('note')).not.toBeInTheDocument()
  })

  it('explains what a missing company means for a JD', () => {
    render(<JobDescriptionPreview jd={JD} />)

    expect(screen.getByRole('note')).toHaveTextContent('Company name')
    expect(screen.getByRole('note')).toHaveTextContent('generic')
  })
})

describe('preview details', () => {
  it('shows partial date ranges with placeholders', () => {
    render(
      <ResumePreview
        resume={{
          ...RESUME,
          experience: [
            { company: 'A', role: 'Dev', start_date: null, end_date: '2020', description: null },
            { company: 'B', role: 'Lead', start_date: '2021', end_date: null, description: null },
            { company: 'C', role: 'Intern', start_date: null, end_date: null, description: null },
          ],
        }}
      />,
    )

    expect(screen.getByText('? – 2020')).toBeInTheDocument()
    expect(screen.getByText('2021 – Present')).toBeInTheDocument()
  })

  it('collapses a very long chip list behind a "+N more" note', () => {
    const skills = Array.from({ length: 20 }, (_, index) => `Skill ${index}`)

    render(<ResumePreview resume={{ ...RESUME, skills }} />)

    expect(screen.getByText('+4 more')).toBeInTheDocument()
    expect(screen.queryByText('Skill 19')).not.toBeInTheDocument()
  })
})
