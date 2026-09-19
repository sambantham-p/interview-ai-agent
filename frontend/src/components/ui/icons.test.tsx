import { render } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import * as icons from './icons'

describe('icons', () => {
  const entries = Object.entries(icons).filter(([, value]) => typeof value === 'function')

  it('exports icons', () => {
    expect(entries.length).toBeGreaterThan(20)
  })

  it.each(entries)('%s renders an svg and accepts a className', (_name, Icon) => {
    const Component = Icon as (props: { className?: string }) => React.ReactElement
    const { container, unmount } = render(<Component className="custom-class" />)
    const svg = container.querySelector('svg')
    expect(svg).not.toBeNull()
    expect(svg?.getAttribute('class')).toContain('custom-class')
    unmount()
  })

  it.each(entries)('%s renders with its default className', (_name, Icon) => {
    const Component = Icon as (props: { className?: string }) => React.ReactElement
    const { container, unmount } = render(<Component />)
    expect(container.querySelector('svg')).not.toBeNull()
    unmount()
  })
})
