import { act, renderHook } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { createElement } from 'react'
import { renderToString } from 'react-dom/server'
import { useOnlineStatus } from './useOnlineStatus'

describe('useOnlineStatus', () => {
  afterEach(() => {
    vi.restoreAllMocks()
  })

  it('reflects navigator.onLine and updates on online/offline events', () => {
    const onLine = vi.spyOn(window.navigator, 'onLine', 'get').mockReturnValue(true)
    const { result, unmount } = renderHook(() => useOnlineStatus())
    expect(result.current).toBe(true)

    onLine.mockReturnValue(false)
    act(() => {
      window.dispatchEvent(new Event('offline'))
    })
    expect(result.current).toBe(false)

    onLine.mockReturnValue(true)
    act(() => {
      window.dispatchEvent(new Event('online'))
    })
    expect(result.current).toBe(true)

    unmount()
  })

  it('assumes online when rendered on the server', () => {
    function Probe() {
      return createElement('span', null, String(useOnlineStatus()))
    }

    expect(renderToString(createElement(Probe))).toContain('true')
  })
})
