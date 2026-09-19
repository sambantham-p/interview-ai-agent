import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { act, renderHook, waitFor } from '@testing-library/react'
import type { ReactNode } from 'react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { useVoiceRecorder } from './useVoiceRecorder'

const { mockUpload } = vi.hoisted(() => ({ mockUpload: vi.fn<(...args: unknown[]) => unknown>() }))
vi.mock('../../lib/api', () => ({ api: { upload: mockUpload } }))

class FakeRecorder {
  static instances: FakeRecorder[] = []
  state: 'inactive' | 'recording' = 'inactive'
  mimeType = 'audio/webm'
  ondataavailable: ((event: { data: Blob }) => void) | null = null
  onstop: (() => void) | null = null
  constructor(
    public stream: MediaStream,
    public options: unknown,
  ) {
    FakeRecorder.instances.push(this)
  }
  start() {
    this.state = 'recording'
  }
  stop() {
    this.state = 'inactive'
    this.onstop?.()
  }
}

function makeStream() {
  const track = { stop: vi.fn<(...args: unknown[]) => unknown>() }
  return { track, stream: { getTracks: () => [track] } as unknown as MediaStream }
}

function wrapper({ children }: { children: ReactNode }) {
  const client = new QueryClient({ defaultOptions: { mutations: { retry: false } } })
  return <QueryClientProvider client={client}>{children}</QueryClientProvider>
}

function setup(options: { maxSeconds?: number } = {}) {
  const onTranscript = vi.fn<(...args: unknown[]) => unknown>()
  const onRecordingStart = vi.fn<(...args: unknown[]) => unknown>()
  const hook = renderHook(
    () =>
      useVoiceRecorder({
        sessionId: 7,
        maxSeconds: options.maxSeconds ?? 300,
        onTranscript,
        onRecordingStart,
      }),
    { wrapper },
  )
  return { ...hook, onTranscript, onRecordingStart }
}

describe('useVoiceRecorder', () => {
  let getUserMedia: ReturnType<typeof vi.fn>

  beforeEach(() => {
    mockUpload.mockReset()
    FakeRecorder.instances = []
    getUserMedia = vi.fn<(...args: unknown[]) => unknown>()
    Object.defineProperty(navigator, 'mediaDevices', {
      value: { getUserMedia },
      configurable: true,
    })
    vi.stubGlobal('MediaRecorder', FakeRecorder)
  })
  afterEach(() => {
    vi.unstubAllGlobals()
    vi.useRealTimers()
  })

  it('reports that the microphone is unavailable when the browser has no recorder', async () => {
    vi.stubGlobal('MediaRecorder', undefined)
    const { result } = setup()

    await act(async () => result.current.start())

    expect(result.current.error).toMatch(/Microphone access is unavailable/)
    expect(result.current.state).toBe('idle')
  })

  it('reports that the microphone is unavailable when getUserMedia is missing', async () => {
    Object.defineProperty(navigator, 'mediaDevices', { value: undefined, configurable: true })
    const { result } = setup()

    await act(async () => result.current.start())

    expect(result.current.error).toMatch(/Microphone access is unavailable/)
  })

  it('reports that the microphone is unavailable when permission is denied', async () => {
    getUserMedia.mockRejectedValue(new Error('denied'))
    const { result } = setup()

    await act(async () => result.current.start())

    expect(result.current.error).toMatch(/Microphone access is unavailable/)
  })

  it('records, then transcribes the recording and hands back the text', async () => {
    const { stream, track } = makeStream()
    getUserMedia.mockResolvedValue(stream)
    mockUpload.mockResolvedValue({ text: 'I used a hash map' })
    const { result, onTranscript, onRecordingStart } = setup()

    await act(async () => result.current.start())
    expect(result.current.state).toBe('recording')
    expect(onRecordingStart).toHaveBeenCalledOnce()

    const recorder = FakeRecorder.instances[0]
    act(() => recorder.ondataavailable?.({ data: new Blob(['audio-bytes']) }))
    act(() => result.current.stop())

    await waitFor(() => expect(onTranscript).toHaveBeenCalledWith('I used a hash map'))
    expect(track.stop).toHaveBeenCalled()
    const [path, formData] = mockUpload.mock.calls[0]
    expect(path).toBe('/voice/stt')
    expect((formData as FormData).get('session_id')).toBe('7')
    expect((formData as FormData).get('audio')).toBeInstanceOf(Blob)
    expect(result.current.state).toBe('idle')
  })

  it('shows the transcribing state while the recording is uploaded', async () => {
    getUserMedia.mockResolvedValue(makeStream().stream)
    mockUpload.mockReturnValue(new Promise(() => {}))
    const { result } = setup()

    await act(async () => result.current.start())
    act(() => FakeRecorder.instances[0].ondataavailable?.({ data: new Blob(['x']) }))
    act(() => result.current.stop())

    await waitFor(() => expect(result.current.state).toBe('transcribing'))
  })

  it('does not upload an empty recording', async () => {
    getUserMedia.mockResolvedValue(makeStream().stream)
    const { result } = setup()

    await act(async () => result.current.start())
    act(() => FakeRecorder.instances[0].ondataavailable?.({ data: new Blob([]) }))
    act(() => result.current.stop())

    expect(mockUpload).not.toHaveBeenCalled()
    expect(result.current.state).toBe('idle')
  })

  it('surfaces a transcription failure', async () => {
    getUserMedia.mockResolvedValue(makeStream().stream)
    mockUpload.mockRejectedValue(new Error('Could not hear that'))
    const { result } = setup()

    await act(async () => result.current.start())
    act(() => FakeRecorder.instances[0].ondataavailable?.({ data: new Blob(['x']) }))
    act(() => result.current.stop())

    await waitFor(() => expect(result.current.error).toBe('Could not hear that'))
  })

  it('stop() does nothing when nothing is recording', () => {
    const { result } = setup()

    act(() => result.current.stop())

    expect(result.current.state).toBe('idle')
  })

  it('counts elapsed seconds and stops automatically at the limit', async () => {
    vi.useFakeTimers()
    getUserMedia.mockResolvedValue(makeStream().stream)
    const { result } = setup({ maxSeconds: 2 })

    await act(async () => result.current.start())
    act(() => FakeRecorder.instances[0].ondataavailable?.({ data: new Blob(['x']) }))
    expect(result.current.elapsedSeconds).toBe(0)

    await act(async () => {
      await vi.advanceTimersByTimeAsync(1000)
    })
    expect(result.current.elapsedSeconds).toBe(1)
    expect(result.current.state).toBe('recording')

    await act(async () => {
      await vi.advanceTimersByTimeAsync(1000)
    })
    expect(FakeRecorder.instances[0].state).toBe('inactive')
  })

  it('releases the microphone when the page is left mid-recording', async () => {
    const { stream, track } = makeStream()
    getUserMedia.mockResolvedValue(stream)
    const { result, unmount } = setup()

    await act(async () => result.current.start())
    unmount()

    expect(track.stop).toHaveBeenCalled()
    expect(mockUpload).not.toHaveBeenCalled()
  })

  it('cleans up quietly when unmounted without ever recording', () => {
    const { unmount } = setup()

    expect(() => unmount()).not.toThrow()
  })
})
