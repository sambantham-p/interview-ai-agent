import { act, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter, Route, Routes } from 'react-router'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { ApiRequestError, api } from '../../lib/api'
import { buildDetail, buildEntry, buildReport, buildTurn } from '../../test/fixtures'
import { renderWithQueryClient } from '../../test/renderWithQueryClient'
import { InterviewChatPage } from './InterviewChatPage'

vi.mock('../../lib/api', async () => {
  const actual = await vi.importActual<typeof import('../../lib/api')>('../../lib/api')
  return { ...actual, api: { get: vi.fn<(...args: unknown[]) => unknown>(), post: vi.fn<(...args: unknown[]) => unknown>() } }
})

const online = vi.hoisted(() => {
  const listeners = new Set<() => void>()
  return {
    value: true,
    listeners,
    set(next: boolean) {
      online.value = next
      listeners.forEach((listener) => listener())
    },
  }
})
vi.mock('../../lib/useOnlineStatus', async () => {
  const { useSyncExternalStore } = await import('react')
  return {
    useOnlineStatus: () =>
      useSyncExternalStore(
        (listener) => {
          online.listeners.add(listener)
          return () => online.listeners.delete(listener)
        },
        () => online.value,
      ),
  }
})

const speech = vi.hoisted(() => ({
  load: vi.fn<(...args: unknown[]) => unknown>(),
  play: vi.fn<(...args: unknown[]) => unknown>(),
  speak: vi.fn<(...args: unknown[]) => unknown>(),
  stop: vi.fn<(...args: unknown[]) => unknown>(),
  playingKey: null as number | null,
}))
vi.mock('./useSpeechPlayback', () => ({ useSpeechPlayback: () => speech }))

const AUDIO = new Blob(['audio'])

function renderPage() {
  return renderWithQueryClient(
    <MemoryRouter initialEntries={['/interview/7']}>
      <Routes>
        <Route path="/interview/:sessionId" element={<InterviewChatPage />} />
        <Route path="/interview/:sessionId/report" element={<p>Report page</p>} />
      </Routes>
    </MemoryRouter>,
  )
}

function loadInterview(detail = buildDetail()) {
  vi.mocked(api.get).mockResolvedValue(detail)
}

async function typeAndSend(text: string) {
  const user = userEvent.setup()
  await user.type(await screen.findByLabelText('Your answer'), text)
  await user.click(screen.getByRole('button', { name: 'Send answer' }))
  return user
}

describe('InterviewChatPage', () => {
  beforeEach(() => {
    vi.mocked(api.get).mockReset()
    vi.mocked(api.post).mockReset()
    online.set(true)
    speech.load.mockReset().mockResolvedValue(AUDIO)
    speech.play.mockReset()
    speech.speak.mockReset().mockResolvedValue(undefined)
    speech.stop.mockReset()
    speech.playingKey = null
    Element.prototype.scrollIntoView = vi.fn<(...args: unknown[]) => unknown>()
  })

  it('shows a spinner, then the conversation', async () => {
    loadInterview()

    renderPage()

    expect(await screen.findByText('Welcome. Tell me about yourself.')).toBeInTheDocument()
    expect(screen.getByText('I build APIs.')).toBeInTheDocument()
  })

  it('shows an error with a retry when the interview cannot be loaded', async () => {
    const user = userEvent.setup()
    vi.mocked(api.get).mockRejectedValueOnce(new Error('boom')).mockResolvedValue(buildDetail())

    renderPage()
    await screen.findByText("Couldn't load this interview.")
    await user.click(screen.getByRole('button', { name: /try again|retry/i }))

    expect(await screen.findByText('I build APIs.')).toBeInTheDocument()
  })

  describe('opening greeting', () => {
    const opening = buildDetail({ transcript: [buildEntry({ index: 1 })] })

    it('holds the greeting back until its voice is ready, then shows and speaks it', async () => {
      let resolveAudio: (blob: Blob | null) => void = () => {}
      speech.load.mockReturnValue(new Promise((resolve) => (resolveAudio = resolve)))
      loadInterview(opening)

      renderPage()

      expect(await screen.findByText(/Your interviewer is getting ready/)).toBeInTheDocument()
      expect(screen.queryByText('Welcome. Tell me about yourself.')).not.toBeInTheDocument()

      await act(async () => resolveAudio(AUDIO))

      expect(await screen.findByText('Welcome. Tell me about yourself.')).toBeInTheDocument()
      expect(speech.play).toHaveBeenCalledWith(1, AUDIO)
    })

    it('shows the greeting without speaking when no voice is available', async () => {
      speech.load.mockResolvedValue(null)
      loadInterview(opening)

      renderPage()

      expect(await screen.findByText('Welcome. Tell me about yourself.')).toBeInTheDocument()
      expect(speech.play).not.toHaveBeenCalled()
    })

    it('shows the greeting immediately once the voice is muted', async () => {
      speech.load.mockReturnValue(new Promise(() => {}))
      loadInterview(opening)
      const user = userEvent.setup()

      renderPage()
      await screen.findByText(/Your interviewer is getting ready/)
      await user.click(screen.getByRole('button', { name: 'Mute interviewer voice' }))

      expect(await screen.findByText('Welcome. Tell me about yourself.')).toBeInTheDocument()
      expect(speech.stop).toHaveBeenCalled()
      expect(screen.getByRole('button', { name: 'Unmute interviewer voice' })).toBeInTheDocument()
    })
  })

  it('replays a message on request', async () => {
    loadInterview()
    const user = userEvent.setup()

    renderPage()
    await user.click(await screen.findByRole('button', { name: 'Play this message' }))

    expect(speech.speak).toHaveBeenCalledWith(1, 'Welcome. Tell me about yourself.')
  })

  describe('answering', () => {
    it('shows the answer straight away, then the interviewer reply, and speaks it', async () => {
      loadInterview()
      vi.mocked(api.post).mockResolvedValue(buildTurn({ reply: 'Next question.' }))

      await renderPageAndWait()
      await typeAndSend('My answer')

      expect(api.post).toHaveBeenCalledWith('/interview/7/turn', { message: 'My answer' })
      expect(await screen.findByText('Next question.')).toBeInTheDocument()
      expect(screen.getByText('My answer')).toBeInTheDocument()
      expect(speech.load).toHaveBeenCalledWith('Next question.')
      await waitFor(() => expect(speech.play).toHaveBeenCalledWith(4, AUDIO))
    })

    it('shows the pending answer and a responding indicator while waiting', async () => {
      loadInterview()
      vi.mocked(api.post).mockReturnValue(new Promise(() => {}))

      await renderPageAndWait()
      await typeAndSend('Pending answer')

      expect(await screen.findByText('Interviewer is responding…')).toBeInTheDocument()
      expect(screen.getByText('Pending answer')).toBeInTheDocument()
    })

    it('skips the voice when it is muted', async () => {
      loadInterview()
      vi.mocked(api.post).mockResolvedValue(buildTurn({ reply: 'Next question.' }))
      const user = userEvent.setup()

      renderPage()
      await user.click(await screen.findByRole('button', { name: 'Mute interviewer voice' }))
      await user.type(screen.getByLabelText('Your answer'), 'Hi')
      await user.click(screen.getByRole('button', { name: 'Send answer' }))

      expect(await screen.findByText('Next question.')).toBeInTheDocument()
      expect(speech.load).not.toHaveBeenCalled()
      expect(speech.play).not.toHaveBeenCalled()
    })

    it('does not play anything when the voice could not be produced in time', async () => {
      loadInterview()
      speech.load.mockResolvedValue(null)
      vi.mocked(api.post).mockResolvedValue(buildTurn({ reply: 'Next question.' }))

      await renderPageAndWait()
      await typeAndSend('Hi')

      expect(await screen.findByText('Next question.')).toBeInTheDocument()
      expect(speech.play).not.toHaveBeenCalled()
    })

    it('shows the server message and lets the candidate retry', async () => {
      loadInterview()
      vi.mocked(api.post)
        .mockRejectedValueOnce(new ApiRequestError('The model is busy', 503))
        .mockResolvedValue(buildTurn({ reply: 'Recovered.' }))

      await renderPageAndWait()
      const user = await typeAndSend('Try me')

      expect(await screen.findByText('The model is busy')).toBeInTheDocument()
      await user.click(screen.getByRole('button', { name: 'Retry' }))

      expect(await screen.findByText('Recovered.')).toBeInTheDocument()
    })

    it('explains a lost connection', async () => {
      loadInterview()
      vi.mocked(api.post).mockRejectedValue(new ApiRequestError('unreachable', 0))

      await renderPageAndWait()
      await typeAndSend('Hello')

      expect(
        await screen.findByText('Connection lost. Your answer is saved here, retry to send it.'),
      ).toBeInTheDocument()
    })

    it('refreshes the interview when it turns out to have ended elsewhere (409)', async () => {
      loadInterview()
      vi.mocked(api.post).mockRejectedValue(new ApiRequestError('Interview not active', 409))

      await renderPageAndWait()
      await typeAndSend('Hello')

      await waitFor(() => expect(vi.mocked(api.get).mock.calls.length).toBeGreaterThan(1))
    })
  })

  describe('connection', () => {
    it('shows an offline notice', async () => {
      online.set(false)
      loadInterview()

      renderPage()

      expect(await screen.findByText(/You're offline/)).toBeInTheDocument()
    })

    it('resends the unsent answer when the connection comes back', async () => {
      loadInterview()
      vi.mocked(api.post)
        .mockRejectedValueOnce(new ApiRequestError('unreachable', 0))
        .mockResolvedValue(buildTurn({ reply: 'Back online.' }))

      await renderPageAndWait()
      await typeAndSend('Sent while flaky')
      await screen.findByText(/Connection lost/)

      act(() => online.set(false))
      act(() => online.set(true))

      expect(await screen.findByText('Back online.')).toBeInTheDocument()
      expect(api.post).toHaveBeenCalledTimes(2)
    })

    it('does not resend when the connection returns and nothing failed', async () => {
      loadInterview()

      await renderPageAndWait()
      act(() => online.set(false))
      act(() => online.set(true))

      expect(api.post).not.toHaveBeenCalled()
    })
  })

  it('warns after a red-flag warning while the interview is running', async () => {
    loadInterview(buildDetail({ red_flag_warning_issued: true }))

    renderPage()

    expect(await screen.findByText(/Another one will end the interview/)).toBeInTheDocument()
  })

  describe('a finished interview', () => {
    it('replaces the composer with the ended panel and opens the report', async () => {
      loadInterview(buildDetail({ status: 'completed', red_flag_warning_issued: true }))
      vi.mocked(api.get).mockImplementation(async (path: string) =>
        path.endsWith('/report') ? buildReport() : buildDetail({ status: 'completed', red_flag_warning_issued: true }),
      )
      const user = userEvent.setup()

      renderPage()
      await user.click(await screen.findByRole('button', { name: 'View my report' }))

      expect(await screen.findByText('Report page')).toBeInTheDocument()
      expect(screen.queryByText(/Another one will end/)).not.toBeInTheDocument()
    })

    it('does not offer the answer box', async () => {
      loadInterview(buildDetail({ status: 'ended_early', end_reason: 'abusive_language' }))

      renderPage()

      expect(await screen.findByText('Interview ended')).toBeInTheDocument()
      expect(screen.queryByLabelText('Your answer')).not.toBeInTheDocument()
    })
  })
})

async function renderPageAndWait() {
  const result = renderPage()
  await screen.findByText('I build APIs.')
  return result
}
