import { fireEvent, render, screen } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'
import { DeleteControls } from './DeleteControls'

function setup(
  props: Partial<React.ComponentProps<typeof DeleteControls>> = {},
) {
  const onConfirm = vi.fn<() => void>()
  render(
    <div className="flex flex-wrap">
      <DeleteControls
        label="resume"
        isDeleting={false}
        errorMessage={null}
        onConfirm={onConfirm}
        {...props}
      />
    </div>,
  )
  return onConfirm
}

describe('DeleteControls', () => {
  it('only confirms after the inline confirmation', () => {
    const onConfirm = setup()

    fireEvent.click(screen.getByRole('button', { name: 'Delete resume' }))
    expect(onConfirm).not.toHaveBeenCalled()
    fireEvent.click(screen.getByRole('button', { name: 'Delete' }))

    expect(onConfirm).toHaveBeenCalledOnce()
  })

  it('warns that completed interviews and their reports are deleted too', () => {
    setup()

    fireEvent.click(screen.getByRole('button', { name: 'Delete resume' }))

    expect(screen.getByRole('group')).toHaveTextContent(
      'Any completed interviews that used it, along with their reports, will be deleted too.',
    )
  })

  it('cancel returns to the idle state', () => {
    const onConfirm = setup()

    fireEvent.click(screen.getByRole('button', { name: 'Delete resume' }))
    fireEvent.click(screen.getByRole('button', { name: 'Cancel' }))

    expect(onConfirm).not.toHaveBeenCalled()
    expect(
      screen.getByRole('button', { name: 'Delete resume' }),
    ).toBeInTheDocument()
  })

  it('shows a deleting status instead of any buttons while pending', () => {
    setup({ isDeleting: true })

    expect(screen.getByRole('status')).toHaveTextContent('Deleting resume…')
    expect(screen.queryByRole('button')).not.toBeInTheDocument()
  })

  it('shows the error and the idle actions again after a failure', () => {
    setup({ errorMessage: 'Used by 1 in-progress interview' })

    expect(screen.getByRole('alert')).toHaveTextContent(
      'Used by 1 in-progress interview',
    )
    expect(
      screen.getByRole('button', { name: 'Delete resume' }),
    ).toBeInTheDocument()
  })

  it('renders extra idle actions', () => {
    setup({ children: <button>Change</button> })

    expect(screen.getByRole('button', { name: 'Change' })).toBeInTheDocument()
  })
})
