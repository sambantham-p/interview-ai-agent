import { render, screen, fireEvent } from '@testing-library/react'
import { describe, it, expect } from 'vitest'
import { Avatar } from './Avatar'

describe('Avatar', () => {
  it('renders the initial when there is no picture', () => {
    render(<Avatar name="Sarah Chen" picture={null} className="w-9 h-9" />)
    expect(screen.getByText('S')).toBeInTheDocument()
    expect(screen.queryByRole('img')).not.toBeInTheDocument()
  })

  it('renders the picture with referrerPolicy set, for Google avatar URLs', () => {
    render(
      <Avatar
        name="Sarah Chen"
        picture="https://lh3.googleusercontent.com/a/photo.jpg"
        className="w-9 h-9"
      />
    )
    const img = screen.getByRole('img')
    expect(img).toHaveAttribute('src', 'https://lh3.googleusercontent.com/a/photo.jpg')
    expect(img).toHaveAttribute('referrerPolicy', 'no-referrer')
  })

  it('falls back to the initial if the picture fails to load', () => {
    render(
      <Avatar name="Sarah Chen" picture="https://lh3.googleusercontent.com/broken.jpg" />
    )
    fireEvent.error(screen.getByRole('img'))
    expect(screen.getByText('S')).toBeInTheDocument()
    expect(screen.queryByRole('img')).not.toBeInTheDocument()
  })
})
