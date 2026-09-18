import { render, screen, fireEvent } from '@testing-library/react'
import { describe, it, expect, vi } from 'vitest'
import { Input } from './Input'

describe('Input', () => {
  it('derives an id from the label when no id is given', () => {
    render(<Input label="Email address" />)
    const input = screen.getByLabelText('Email address')
    expect(input).toHaveAttribute('id', 'email-address')
  })

  it('uses an explicit id over the derived one', () => {
    render(<Input label="Email address" id="custom-id" />)
    expect(screen.getByLabelText('Email address')).toHaveAttribute('id', 'custom-id')
  })

  it('renders without a label and without an id', () => {
    render(<Input placeholder="no label" />)
    expect(screen.getByPlaceholderText('no label')).not.toHaveAttribute('id')
  })

  it('shows the error message when error is set', () => {
    render(<Input label="Email" error="Invalid email" />)
    expect(screen.getByText('Invalid email')).toBeInTheDocument()
  })

  it('defaults to a password field and toggles visibility on click', () => {
    render(<Input label="Password" isPassword value="secret" onChange={() => {}} />)
    const input = screen.getByLabelText('Password')
    expect(input).toHaveAttribute('type', 'password')

    fireEvent.click(screen.getByText('Show'))
    expect(input).toHaveAttribute('type', 'text')
    expect(screen.getByText('Hide')).toBeInTheDocument()

    fireEvent.click(screen.getByText('Hide'))
    expect(input).toHaveAttribute('type', 'password')
  })

  it('forwards onChange and other input props', () => {
    const handleChange = vi.fn()
    render(<Input label="Name" onChange={handleChange} placeholder="Your name" />)
    fireEvent.change(screen.getByPlaceholderText('Your name'), {
      target: { value: 'Alex' },
    })
    expect(handleChange).toHaveBeenCalled()
  })
})
