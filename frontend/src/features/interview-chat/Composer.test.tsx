import { act, render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { Composer } from './Composer'

const recorder = vi.hoisted(() => ({
  current: {
    state: 'idle' as 'idle' | 'recording' | 'transcribing',
    elapsedSeconds: 0,
    error: null as string | null,
    start: vi.fn<(...args: unknown[]) => unknown>(),
    stop: vi.fn<(...args: unknown[]) => unknown>(),
  },
  onTranscript: null as ((text: string) => void) | null,
}))

vi.mock('./useVoiceRecorder', () => ({
  useVoiceRecorder: (options: { onTranscript: (text: string) => void }) => {
    recorder.onTranscript = options.onTranscript
    return recorder.current
  },
}))

function renderComposer(props: Partial<React.ComponentProps<typeof Composer>> = {}) {
  const onSend = vi.fn<(...args: unknown[]) => unknown>()
  const onMicStart = vi.fn<(...args: unknown[]) => unknown>()
  render(
    <Composer
      sessionId={7}
      maxAnswerSeconds={300}
      isSending={false}
      onSend={onSend}
      onMicStart={onMicStart}
      {...props}
    />,
  )
  return { onSend, onMicStart }
}

describe('Composer', () => {
  beforeEach(() => {
    recorder.current = {
      state: 'idle',
      elapsedSeconds: 0,
      error: null,
      start: vi.fn<(...args: unknown[]) => unknown>(),
      stop: vi.fn<(...args: unknown[]) => unknown>(),
    }
  })

  it('keeps Send disabled until there is text', async () => {
    renderComposer()
    const send = screen.getByRole('button', { name: 'Send answer' })
    expect(send).toBeDisabled()

    await userEvent.type(screen.getByLabelText('Your answer'), '  hello  ')

    expect(send).toBeEnabled()
  })

  it('sends the trimmed answer and clears the box', async () => {
    const { onSend } = renderComposer()
    const box = screen.getByLabelText('Your answer')

    await userEvent.type(box, '  hello  ')
    await userEvent.click(screen.getByRole('button', { name: 'Send answer' }))

    expect(onSend).toHaveBeenCalledWith('hello')
    expect(box).toHaveValue('')
  })

  it('sends on Enter but adds a new line on Shift+Enter', async () => {
    const { onSend } = renderComposer()
    const box = screen.getByLabelText('Your answer')

    await userEvent.type(box, 'line one{Shift>}{Enter}{/Shift}line two')
    expect(onSend).not.toHaveBeenCalled()
    expect(box).toHaveValue('line one\nline two')

    await userEvent.type(box, '{Enter}')
    expect(onSend).toHaveBeenCalledWith('line one\nline two')
  })

  it('ignores Enter when there is nothing to send', async () => {
    const { onSend } = renderComposer()

    await userEvent.type(screen.getByLabelText('Your answer'), '{Enter}')

    expect(onSend).not.toHaveBeenCalled()
  })

  it('does not send while an answer is already being sent', async () => {
    const { onSend } = renderComposer({ isSending: true })

    await userEvent.type(screen.getByLabelText('Your answer'), 'hello{Enter}')

    expect(onSend).not.toHaveBeenCalled()
    expect(screen.getByRole('button', { name: 'Answer by voice' })).toBeDisabled()
  })

  it('starts recording from the mic button', async () => {
    renderComposer()

    await userEvent.click(screen.getByRole('button', { name: 'Answer by voice' }))

    expect(recorder.current.start).toHaveBeenCalled()
  })

  it('appends a transcript to what is already typed, or starts the draft with it', async () => {
    renderComposer()
    const box = screen.getByLabelText('Your answer')

    act(() => recorder.onTranscript?.('spoken words'))
    expect(box).toHaveValue('spoken words')

    act(() => recorder.onTranscript?.('and more'))
    expect(box).toHaveValue('spoken words and more')
  })

  it('shows a live timer while recording and stops on the stop button', async () => {
    recorder.current = { ...recorder.current, state: 'recording', elapsedSeconds: 65 }
    renderComposer()

    expect(screen.getByRole('status')).toHaveTextContent('Listening… 1:05 / 5:00')
    expect(screen.queryByText(/s left/)).not.toBeInTheDocument()
    expect(screen.queryByLabelText('Your answer')).not.toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Send answer' })).toBeDisabled()

    await userEvent.click(screen.getByRole('button', { name: 'Stop recording' }))
    expect(recorder.current.stop).toHaveBeenCalled()
  })

  it('warns when the recording is close to its limit', () => {
    recorder.current = { ...recorder.current, state: 'recording', elapsedSeconds: 280 }
    renderComposer()

    expect(screen.getByText('20s left')).toBeInTheDocument()
  })

  it('locks the box while a recording is being transcribed', () => {
    recorder.current = { ...recorder.current, state: 'transcribing' }
    renderComposer()

    expect(screen.getByLabelText('Your answer')).toBeDisabled()
    expect(screen.getByPlaceholderText('Transcribing your answer…')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Answer by voice' })).toBeDisabled()
  })

  it('shows a recorder error', () => {
    recorder.current = { ...recorder.current, error: 'Microphone access is unavailable.' }
    renderComposer()

    expect(screen.getByText('Microphone access is unavailable.')).toBeInTheDocument()
  })
})
