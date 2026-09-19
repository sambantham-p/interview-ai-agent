import { describe, expect, it } from 'vitest'
import { ApiRequestError } from '../lib/api'
import { queryClient } from './queryClient'

describe('queryClient retry policy', () => {
  const retry = queryClient.getDefaultOptions().queries?.retry as (
    failureCount: number,
    error: Error,
  ) => boolean

  it('never retries an unauthorized response', () => {
    expect(retry(0, new ApiRequestError('nope', 401))).toBe(false)
  })

  it('retries other errors once', () => {
    expect(retry(0, new ApiRequestError('boom', 500))).toBe(true)
    expect(retry(1, new ApiRequestError('boom', 500))).toBe(false)
    expect(retry(0, new Error('network'))).toBe(true)
  })
})
