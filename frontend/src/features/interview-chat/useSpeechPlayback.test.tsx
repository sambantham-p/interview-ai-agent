import { act, renderHook, waitFor } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { useSpeechPlayback } from './useSpeechPlayback'

const { mockPostForBlob } = vi.hoisted(() => ({ mockPostForBlob: vi.fn<(...args: unknown[]) => unknown>() }))
vi.mock('../../lib/api', () => ({ api: { postForBlob: mockPostForBlob } }))

class FakeAudio {
  static instances: FakeAudio[] = []
  static playResult: Promise<void> = Promise.resolve()
  onended: (() => void) | null = null
  pause = vi.fn<(...args: unknown[]) => unknown>()
  play = vi.fn<() => Promise<void>>(() => FakeAudio.playResult)
  constructor(public src: string) {
    FakeAudio.instances.push(this)
  }
}

describe('useSpeechPlayback', () => {
  beforeEach(() => {
    mockPostForBlob.mockReset()
    FakeAudio.instances = []
    FakeAudio.playResult = Promise.resolve()
    vi.stubGlobal('Audio', FakeAudio)
    URL.createObjectURL = vi.fn<() => string>(() => 'blob:speech')
    URL.revokeObjectURL = vi.fn<(...args: unknown[]) => unknown>()
  })
  afterEach(() => {
    vi.unstubAllGlobals()
  })

  it('loads the audio for a message, scoped to the session', async () => {
    const blob = new Blob(['a'])
    mockPostForBlob.mockResolvedValue(blob)
    const { result } = renderHook(() => useSpeechPlayback(7))

    let loaded: Blob | null = null
    await act(async () => {
      loaded = await result.current.load('Hello')
    })

    expect(loaded).toBe(blob)
    expect(mockPostForBlob).toHaveBeenCalledWith(
      '/voice/tts',
      { text: 'Hello', session_id: 7 },
      expect.any(AbortSignal),
    )
  })

  it('returns null when the voice cannot be produced', async () => {
    mockPostForBlob.mockRejectedValue(new Error('down'))
    const { result } = renderHook(() => useSpeechPlayback(7))

    let loaded: Blob | null = new Blob()
    await act(async () => {
      loaded = await result.current.load('Hello')
    })

    expect(loaded).toBeNull()
  })

  it('plays audio, tracks what is speaking and clears when it ends', () => {
    const { result } = renderHook(() => useSpeechPlayback(7))

    act(() => result.current.play(3, new Blob(['a'])))

    expect(result.current.playingKey).toBe(3)
    expect(FakeAudio.instances[0].play).toHaveBeenCalled()

    act(() => FakeAudio.instances[0].onended?.())

    expect(result.current.playingKey).toBeNull()
    expect(URL.revokeObjectURL).toHaveBeenCalledWith('blob:speech')
  })

  it('stops when the browser refuses to play', async () => {
    FakeAudio.playResult = Promise.reject(new Error('blocked'))
    const { result } = renderHook(() => useSpeechPlayback(7))

    act(() => result.current.play(3, new Blob(['a'])))

    await waitFor(() => expect(result.current.playingKey).toBeNull())
  })

  it('replaces the current audio when new audio starts', () => {
    const { result } = renderHook(() => useSpeechPlayback(7))

    act(() => result.current.play(1, new Blob(['a'])))
    act(() => result.current.play(2, new Blob(['b'])))

    expect(FakeAudio.instances[0].pause).toHaveBeenCalled()
    expect(result.current.playingKey).toBe(2)
  })

  it('speak loads then plays a message on demand', async () => {
    mockPostForBlob.mockResolvedValue(new Blob(['a']))
    const { result } = renderHook(() => useSpeechPlayback(7))

    await act(async () => {
      await result.current.speak(4, 'Replay me')
    })

    expect(result.current.playingKey).toBe(4)
    expect(FakeAudio.instances).toHaveLength(1)
  })

  it('speak clears the indicator when no voice could be produced', async () => {
    mockPostForBlob.mockRejectedValue(new Error('down'))
    const { result } = renderHook(() => useSpeechPlayback(7))

    await act(async () => {
      await result.current.speak(4, 'Replay me')
    })

    expect(result.current.playingKey).toBeNull()
    expect(FakeAudio.instances).toHaveLength(0)
  })

  it('ignores a slow load that was superseded by stop()', async () => {
    let resolveBlob: (blob: Blob) => void = () => {}
    mockPostForBlob.mockReturnValue(new Promise<Blob>((resolve) => (resolveBlob = resolve)))
    const { result } = renderHook(() => useSpeechPlayback(7))

    let speaking: Promise<void> = Promise.resolve()
    act(() => {
      speaking = result.current.speak(4, 'Slow')
    })
    act(() => result.current.stop())
    await act(async () => {
      resolveBlob(new Blob(['late']))
      await speaking
    })

    expect(FakeAudio.instances).toHaveLength(0)
    expect(result.current.playingKey).toBeNull()
  })

  it('stops playback when the component unmounts', () => {
    const { result, unmount } = renderHook(() => useSpeechPlayback(7))
    act(() => result.current.play(1, new Blob(['a'])))

    unmount()

    expect(FakeAudio.instances[0].pause).toHaveBeenCalled()
  })
})
