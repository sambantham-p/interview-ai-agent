import { screen } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'
import { renderWithQueryClient } from '../../test/renderWithQueryClient'
import { DocumentPreviewCard } from './DocumentPreviewCard'

vi.mock('../../lib/api', () => ({ api: { delete: vi.fn<(...args: unknown[]) => unknown>() } }))

describe('DocumentPreviewCard', () => {
  it('shows stats that do not specify a tone', () => {
    renderWithQueryClient(
      <DocumentPreviewCard
        icon={<span />}
        title="Backend Dev"
        id={1}
        kind="resume"
        stats={[{ icon: <span />, value: 3, label: 'Roles' }]}
        onDeleted={vi.fn<(...args: unknown[]) => unknown>()}
        onChange={vi.fn<(...args: unknown[]) => unknown>()}
      >
        <p>Body</p>
      </DocumentPreviewCard>,
    )

    expect(screen.getByText('Roles')).toBeInTheDocument()
    expect(screen.getByText('3')).toBeInTheDocument()
  })

  it('renders without stats or a subtitle', () => {
    renderWithQueryClient(
      <DocumentPreviewCard
        icon={<span />}
        title="Backend Dev"
        id={1}
        kind="resume"
        onDeleted={vi.fn<(...args: unknown[]) => unknown>()}
        onChange={vi.fn<(...args: unknown[]) => unknown>()}
      >
        <p>Body</p>
      </DocumentPreviewCard>,
    )

    expect(screen.getByText('Body')).toBeInTheDocument()
  })
})
