import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter } from 'react-router'
import { describe, expect, it } from 'vitest'
import {
  buildDetail,
  buildEntry,
  buildEvaluation,
  buildReport,
} from '../../test/fixtures'
import { ActionPlanTab } from './ActionPlanTab'
import { InsightsTab } from './InsightsTab'
import { OverviewTab } from './OverviewTab'
import { PhaseReviewTab } from './PhaseReviewTab'

const cleanReport = buildReport({
  strength_dimensions: ['project_depth', 'coding'],
  focus_dimensions: [],
  hint_counts: {},
  red_flag_count: 0,
})

describe('OverviewTab', () => {
  it('shows the verdict, headline, stats and per-dimension scores', () => {
    render(
      <OverviewTab
        report={buildReport({ end_reason_label: 'Ended: too many red flags' })}
        detail={buildDetail({ ended_at: '2026-01-01T10:30:00Z' })}
      />,
    )

    expect(screen.getByText('Overall result')).toBeInTheDocument()
    expect(screen.getByText('Ended: too many red flags')).toBeInTheDocument()
    expect(screen.getByText('30')).toBeInTheDocument()
    expect(screen.getByText('Project Depth')).toBeInTheDocument()
    expect(screen.getByText('25% of overall')).toBeInTheDocument()
  })

  it('shows dashes for length when unfinished and 0% for a dimension with no weight', () => {
    render(
      <OverviewTab
        report={buildReport({
          weights_used: {},
          red_flag_count: 0,
          judge_evaluations: [buildEvaluation()],
        })}
        detail={buildDetail({ ended_at: null })}
      />,
    )

    expect(screen.getByText('-')).toBeInTheDocument()
    expect(screen.getByText('0% of overall')).toBeInTheDocument()
  })
})

describe('InsightsTab', () => {
  it('lists strengths, areas to improve, contribution and hints by phase', () => {
    render(<InsightsTab report={buildReport({ hint_counts: { technical_interview: 1 } })} />)

    expect(screen.getByText('Strengths')).toBeInTheDocument()
    expect(screen.getByText('Areas to improve')).toBeInTheDocument()
    expect(screen.getByText('20.5 of 25 pts')).toBeInTheDocument()
    expect(screen.getByText('1 hint')).toBeInTheDocument()
    expect(screen.getByText('Technical Interview')).toBeInTheDocument()
  })

  it('pluralises hints and handles dimensions missing a weight', () => {
    render(
      <InsightsTab
        report={buildReport({
          weights_used: {},
          hint_counts: { technical_interview: 3, general_technical: 0 },
        })}
      />,
    )

    expect(screen.getByText('3 hints')).toBeInTheDocument()
    expect(screen.queryByText('General Technical')).not.toBeInTheDocument()
  })

  it('shows encouraging empty states', () => {
    render(<InsightsTab report={buildReport({ strength_dimensions: [], focus_dimensions: [], hint_counts: {} })} />)

    expect(screen.getByText('No dimension reached the hiring bar this time.')).toBeInTheDocument()
    expect(screen.getByText('Every dimension cleared the hiring bar.')).toBeInTheDocument()
    expect(screen.getByText("You didn't need any hints. Nicely done.")).toBeInTheDocument()
  })
})

describe('ActionPlanTab', () => {
  it('lists focus areas with evidence, habits to watch and a practice link', () => {
    render(
      <MemoryRouter>
        <ActionPlanTab report={buildReport({ red_flag_count: 2 })} />
      </MemoryRouter>,
    )

    expect(screen.getByText('Focus on these first')).toBeInTheDocument()
    expect(screen.getByText('Vague.')).toBeInTheDocument()
    expect(screen.getByText(/You needed hints in/)).toBeInTheDocument()
    expect(screen.getByText(/2 answers conflicted/)).toBeInTheDocument()
    expect(screen.getByRole('link', { name: 'Practice again' })).toHaveAttribute('href', '/setup')
  })

  it('uses the singular for one flagged answer and skips evidence when there is none', () => {
    render(
      <MemoryRouter>
        <ActionPlanTab
          report={buildReport({
            hint_counts: {},
            red_flag_count: 1,
            focus_dimensions: ['coding'],
            judge_evaluations: [
              buildEvaluation({ judge_name: 'coding', dimension: 'Coding', score: 40, evidence: [] }),
            ],
          })}
        />
      </MemoryRouter>,
    )

    expect(screen.getByText(/1 answer conflicted/)).toBeInTheDocument()
  })

  it('congratulates when nothing needs work', () => {
    render(
      <MemoryRouter>
        <ActionPlanTab report={cleanReport} />
      </MemoryRouter>,
    )

    expect(screen.getByText("You're in good shape")).toBeInTheDocument()
    expect(screen.queryByText('Habits to watch')).not.toBeInTheDocument()
  })
})

describe('PhaseReviewTab', () => {
  const detail = buildDetail({
    transcript: [
      buildEntry({ index: 1, role: 'model', phase: 'background_check', text: 'Intro question' }),
      buildEntry({ index: 2, role: 'user', phase: 'background_check', text: 'I build APIs.' }),
      buildEntry({
        index: 3,
        role: 'model',
        phase: 'technical_interview',
        text: 'Explain indexes',
        hint_level: 2,
      }),
    ],
  })

  it('opens the first phase, highlights cited messages and toggles other phases', async () => {
    const user = userEvent.setup()
    render(
      <PhaseReviewTab
        report={buildReport({ hint_counts: { technical_interview: 1 } })}
        detail={detail}
      />,
    )

    expect(screen.getByText('Intro question')).toBeInTheDocument()
    expect(screen.getByText(/Cited for Project Depth/)).toBeInTheDocument()
    expect(screen.getByText('1 cited')).toBeInTheDocument()
    expect(screen.queryByText('Explain indexes')).not.toBeInTheDocument()

    await user.click(screen.getByRole('button', { name: /Technical Interview/ }))
    expect(screen.getByText('Explain indexes')).toBeInTheDocument()
    expect(screen.getByText('· hint 2')).toBeInTheDocument()

    await user.click(screen.getByRole('button', { name: /Technical Interview/ }))
    expect(screen.queryByText('Explain indexes')).not.toBeInTheDocument()
  })

  it('groups several citations of the same message and pluralises hints', () => {
    const report = buildReport({
      hint_counts: { background_check: 2 },
      judge_evaluations: [
        buildEvaluation({
          evidence: [{ quote: 'q', transcript_index: 2, reasoning: 'First point' }],
        }),
        buildEvaluation({
          id: 2,
          judge_name: 'coding',
          dimension: 'Coding',
          evidence: [{ quote: 'q', transcript_index: 2, reasoning: 'Second point' }],
        }),
      ],
    })

    render(<PhaseReviewTab report={report} detail={detail} />)

    expect(screen.getByText('2 hints')).toBeInTheDocument()
    expect(screen.getByText(/First point/)).toBeInTheDocument()
    expect(screen.getByText(/Second point/)).toBeInTheDocument()
  })
})
