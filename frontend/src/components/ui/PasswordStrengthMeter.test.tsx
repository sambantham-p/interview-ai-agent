import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import { PasswordStrengthMeter } from './PasswordStrengthMeter'

describe('PasswordStrengthMeter', () => {
  it.each([
    ['', 'Enter password'],
    ['abc', 'Weak password'],
    ['abcdefgh', 'Weak password'],
    ['Abcdefgh', 'Fair password'],
    ['Abcdefg1', 'Good password'],
    ['Abcdefg1!', 'Strong password'],
  ])('labels %j as "%s"', (password, label) => {
    render(<PasswordStrengthMeter password={password} />)

    expect(screen.getByText(label)).toBeInTheDocument()
  })

  it('treats a missing password as empty', () => {
    render(<PasswordStrengthMeter />)

    expect(screen.getByText('Enter password')).toBeInTheDocument()
  })
})
