import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter } from 'react-router'
import { describe, expect, it, vi } from 'vitest'
import { EndedPanel } from './EndedPanel'

function renderPanel(props: Partial<React.ComponentProps<typeof EndedPanel>> = {}) {
  const onGenerateReport = vi.fn<(...args: unknown[]) => unknown>()
  render(
    <MemoryRouter>
      <EndedPanel endReason={null} isGenerating={false} onGenerateReport={onGenerateReport} {...props} />
    </MemoryRouter>,
  )
  return { onGenerateReport }
}

describe('EndedPanel', () => {
  it.each([
    [null, 'Interview complete'],
    ['abusive_language', 'Interview ended'],
    ['red_flag_threshold', 'Interview ended early'],
  ] as const)('shows the right headline for %s', (endReason, title) => {
    renderPanel({ endReason })

    expect(screen.getByRole('heading', { name: title })).toBeInTheDocument()
  })

  it('generates the report and links back to the dashboard', async () => {
    const { onGenerateReport } = renderPanel()

    await userEvent.click(screen.getByRole('button', { name: 'View my report' }))

    expect(onGenerateReport).toHaveBeenCalledOnce()
    expect(screen.getByRole('link', { name: 'Back to dashboard' })).toHaveAttribute('href', '/dashboard')
  })

  it('disables the button while the report is being generated', () => {
    renderPanel({ isGenerating: true })

    expect(screen.getByRole('button', { name: /Evaluating your interview/ })).toBeDisabled()
  })
})
