import { describe, expect, it } from 'vitest'
import { getDisplayName } from './displayName'

describe('getDisplayName', () => {
  it('prefers the preferred name', () => {
    expect(getDisplayName({ name: 'Jane Doe', preferred_name: '  Jay ' })).toBe('Jay')
  })

  it('falls back to the first word of the account name', () => {
    expect(getDisplayName({ name: 'Jane Doe', preferred_name: null })).toBe('Jane')
    expect(getDisplayName({ name: 'Jane Doe', preferred_name: '   ' })).toBe('Jane')
  })

  it('returns an empty string for an empty account name', () => {
    expect(getDisplayName({ name: '   ', preferred_name: null })).toBe('')
  })
})
