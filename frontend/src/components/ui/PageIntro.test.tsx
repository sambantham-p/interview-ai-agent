import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import { MeshGradientBackground } from './MeshGradientBackground'
import { PageIntro } from './PageIntro'

describe('PageIntro', () => {
  it('renders a title, description and action', () => {
    render(<PageIntro title="Reports" description="Your interviews." action={<button>Go</button>} />)

    expect(screen.getByRole('heading', { name: 'Reports' })).toBeInTheDocument()
    expect(screen.getByText('Your interviews.')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Go' })).toBeInTheDocument()
  })

  it('renders only the description when there is no title', () => {
    render(<PageIntro description="Just text." />)

    expect(screen.queryByRole('heading')).not.toBeInTheDocument()
    expect(screen.getByText('Just text.')).not.toHaveClass('mt-2')
  })
})

describe('MeshGradientBackground', () => {
  it('renders decoratively and dims when muted', () => {
    const { container, rerender } = render(<MeshGradientBackground />)
    const normal = (container.firstElementChild as HTMLElement).style.backgroundImage
    expect(container.firstElementChild).toHaveAttribute('aria-hidden', 'true')

    rerender(<MeshGradientBackground muted />)
    const muted = (container.firstElementChild as HTMLElement).style.backgroundImage
    expect(muted).not.toBe(normal)
  })
})
