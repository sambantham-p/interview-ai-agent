import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it, vi } from 'vitest'
import { buildEntry } from '../../test/fixtures'
import { MessageBubble } from './MessageBubble'

describe('MessageBubble', () => {
  it('renders a candidate message without a replay control', () => {
    render(
      <MessageBubble
        entry={buildEntry({ role: 'user', text: 'My answer' })}
        isSpeaking={false}
        onReplay={vi.fn<(...args: unknown[]) => unknown>()}
      />,
    )

    expect(screen.getByText('My answer')).toBeInTheDocument()
    expect(screen.queryByRole('button')).not.toBeInTheDocument()
  })

  it('lets the candidate replay an interviewer message', async () => {
    const onReplay = vi.fn<(...args: unknown[]) => unknown>()
    render(<MessageBubble entry={buildEntry()} isSpeaking={false} onReplay={onReplay} />)

    await userEvent.click(screen.getByRole('button', { name: 'Play this message' }))

    expect(onReplay).toHaveBeenCalledOnce()
  })

  it('marks the message that is being spoken', () => {
    render(<MessageBubble entry={buildEntry()} isSpeaking onReplay={vi.fn<(...args: unknown[]) => unknown>()} />)

    expect(screen.getByRole('button', { name: 'Play this message' })).toHaveClass('text-brand')
  })

  it.each([
    [1, 'Small nudge'],
    [2, 'Hint'],
    [3, 'Bigger hint'],
    [9, 'Hint'],
  ])('labels hint level %i as "%s"', (level, label) => {
    render(
      <MessageBubble entry={buildEntry({ hint_level: level })} isSpeaking={false} onReplay={vi.fn<(...args: unknown[]) => unknown>()} />,
    )

    expect(screen.getByText(label)).toBeInTheDocument()
  })

  it('reassures an anxious candidate', () => {
    render(
      <MessageBubble
        entry={buildEntry({ anxiety_detected: true })}
        isSpeaking={false}
        onReplay={vi.fn<(...args: unknown[]) => unknown>()}
      />,
    )

    expect(screen.getByText('Take your time')).toBeInTheDocument()
  })
})
