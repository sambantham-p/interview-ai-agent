import { act, fireEvent, render, screen, waitFor } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { MemoryRouter, Route, Routes } from 'react-router'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { SetupWizardPage } from './SetupWizardPage'
import { api } from '../../lib/api'

vi.mock('../../lib/api', () => ({
  api: {
    get: vi.fn<(path: string) => Promise<unknown>>(),
    post: vi.fn<(path: string, payload: unknown) => Promise<unknown>>(),
    upload: vi.fn<(path: string, form: FormData) => Promise<unknown>>(),
    delete: vi.fn<(path: string) => Promise<unknown>>(),
  },
}))

vi.mock('../../lib/authContext', () => ({
  useAuth: () => ({
    user: { name: 'Sarah Chen', email: 'sarah@example.com', picture: null },
    logout: vi.fn<() => void>(),
  }),
}))

const RESUME = {
  id: 1,
  education: [],
  experience: [{ company: 'Acme', role: 'Backend Dev', start_date: null, end_date: null, description: null }],
  projects: [],
  skills: ['Python'],
  github_url: null,
  missing_sections: [],
  created_at: '2026-01-01T00:00:00Z',
}

const JD = {
  id: 7,
  role: 'Backend Engineer',
  company_name: 'Acme',
  seniority: 'mid',
  tech_stack: ['Python'],
  coding_assessment_expected: true,
  missing_details: [],
  created_at: '2026-01-02T00:00:00Z',
}

const PRESETS = [
  {
    key: 'coding_only',
    label: 'Coding Only',
    description: 'One question.',
    phases: ['coding_challenge'],
    durations: [5, 10],
    includes_coding: true,
  },
  {
    key: 'full_loop',
    label: 'Full Loop (all 7 phases)',
    description: 'Everything.',
    phases: ['background_check', 'coding_challenge'],
    durations: [30, 35, 40],
    includes_coding: true,
  },
]

function mockGets(overrides: Record<string, unknown> = {}) {
  vi.mocked(api.get).mockImplementation((path: string) => {
    if (path in overrides) return Promise.resolve(overrides[path])
    if (path === '/resume') return Promise.resolve([RESUME])
    if (path === '/jd') return Promise.resolve([JD])
    if (path.startsWith('/interview/presets')) return Promise.resolve(PRESETS)
    return Promise.reject(new Error(`unexpected GET ${path}`))
  })
}

function renderWizard() {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter initialEntries={['/setup']}>
        <Routes>
          <Route path="/setup" element={<SetupWizardPage />} />
          <Route path="/interview/:id" element={<p>Interview room</p>} />
        </Routes>
      </MemoryRouter>
    </QueryClientProvider>,
  )
}

async function pickResumeAndJd() {
  fireEvent.click(await screen.findByRole('button', { name: /Backend Dev/ }))
  fireEvent.click(screen.getByRole('button', { name: 'Continue' }))
  fireEvent.click(await screen.findByRole('button', { name: /Backend Engineer/ }))
  fireEvent.click(screen.getByRole('button', { name: 'Continue' }))
}

beforeEach(() => {
  vi.mocked(api.get).mockReset()
  vi.mocked(api.post).mockReset()
  vi.mocked(api.upload).mockReset()
  vi.mocked(api.delete).mockReset()
  mockGets()
})

afterEach(() => {
  vi.useRealTimers()
  vi.unstubAllGlobals()
})

describe('resume step', () => {
  it('keeps Continue disabled until a resume is chosen', async () => {
    renderWizard()

    await screen.findByRole('button', { name: /Backend Dev/ })
    expect(screen.getByRole('button', { name: 'Continue' })).toBeDisabled()
  })

  it('uploads a PDF as multipart and selects the parsed resume', async () => {
    vi.mocked(api.upload).mockResolvedValue({ ...RESUME, id: 2 })
    renderWizard()

    const file = new File(['%PDF-1.4'], 'cv.pdf', { type: 'application/pdf' })
    fireEvent.change(screen.getByLabelText('Resume PDF'), { target: { files: [file] } })

    await waitFor(() => expect(api.upload).toHaveBeenCalled())
    const [path, form] = vi.mocked(api.upload).mock.calls[0]
    expect(path).toBe('/resume/upload')
    expect((form as FormData).get('file')).toBe(file)
    await waitFor(() =>
      expect(screen.getByRole('button', { name: 'Continue' })).toBeEnabled(),
    )
  })

  it('rejects a non-PDF file without calling the backend', async () => {
    renderWizard()

    const file = new File(['hi'], 'notes.txt', { type: 'text/plain' })
    fireEvent.change(screen.getByLabelText('Resume PDF'), { target: { files: [file] } })

    expect(await screen.findByRole('alert')).toHaveTextContent('PDF')
    expect(api.upload).not.toHaveBeenCalled()
  })

  it('shows the backend error when parsing fails', async () => {
    vi.mocked(api.upload).mockRejectedValue(new Error('Resume looks empty'))
    renderWizard()

    const file = new File(['%PDF-1.4'], 'cv.pdf', { type: 'application/pdf' })
    fireEvent.change(screen.getByLabelText('Resume PDF'), { target: { files: [file] } })

    expect(await screen.findByText('Resume looks empty')).toBeInTheDocument()
  })
})

describe('rejection reasons', () => {
  it('shows the backend reason when the file is not a resume', async () => {
    vi.mocked(api.upload).mockRejectedValue(
      new Error("This doesn't look like a resume. It looks like an electricity bill. Please upload your own resume as a PDF."),
    )
    renderWizard()

    const file = new File(['%PDF-1.4'], 'bill.pdf', { type: 'application/pdf' })
    fireEvent.change(screen.getByLabelText('Resume PDF'), { target: { files: [file] } })

    expect(await screen.findByRole('alert')).toHaveTextContent('electricity bill')
    expect(screen.getByLabelText('Resume PDF')).toBeInTheDocument()
  })

  it('shows the backend reason when the text is not a job description', async () => {
    vi.mocked(api.post).mockRejectedValue(
      new Error("This doesn't look like a job description: it's a recipe. Please paste a job posting."),
    )
    renderWizard()
    fireEvent.click(await screen.findByRole('button', { name: /Backend Dev/ }))
    fireEvent.click(screen.getByRole('button', { name: 'Continue' }))

    fireEvent.change(await screen.findByLabelText('Paste the job description'), {
      target: { value: 'Mix flour and eggs.' },
    })
    fireEvent.click(screen.getByRole('button', { name: 'Analyze role' }))

    expect(await screen.findByRole('alert')).toHaveTextContent("it's a recipe")
  })

  it('shows what a partial resume lacks right after upload', async () => {
    vi.mocked(api.upload).mockResolvedValue({ ...RESUME, id: 3, missing_sections: ['Education', 'Projects'] })
    renderWizard()

    const file = new File(['%PDF-1.4'], 'cv.pdf', { type: 'application/pdf' })
    fireEvent.change(screen.getByLabelText('Resume PDF'), { target: { files: [file] } })

    expect(await screen.findByRole('note')).toHaveTextContent('Education, Projects')
  })
})

describe('job description step', () => {
  it('submits a pasted JD as full_text and selects the result', async () => {
    vi.mocked(api.post).mockResolvedValue({ ...JD, id: 8 })
    renderWizard()
    fireEvent.click(await screen.findByRole('button', { name: /Backend Dev/ }))
    fireEvent.click(screen.getByRole('button', { name: 'Continue' }))

    fireEvent.change(await screen.findByLabelText('Paste the job description'), {
      target: { value: 'We need a backend engineer.' },
    })
    fireEvent.click(screen.getByRole('button', { name: 'Analyze role' }))

    await waitFor(() =>
      expect(api.post).toHaveBeenCalledWith('/jd', {
        full_text: 'We need a backend engineer.',
      }),
    )
  })

  it('submits the short-description mode under its own field', async () => {
    vi.mocked(api.post).mockResolvedValue(JD)
    renderWizard()
    fireEvent.click(await screen.findByRole('button', { name: /Backend Dev/ }))
    fireEvent.click(screen.getByRole('button', { name: 'Continue' }))

    fireEvent.click(await screen.findByRole('tab', { name: 'Short description' }))
    fireEvent.change(screen.getByLabelText('Describe the role'), {
      target: { value: 'AI Engineer, mid, Python' },
    })
    fireEvent.click(screen.getByRole('button', { name: 'Analyze role' }))

    await waitFor(() =>
      expect(api.post).toHaveBeenCalledWith('/jd', {
        short_description: 'AI Engineer, mid, Python',
      }),
    )
  })

  it('does not carry a rejected draft or its error over to the other tab', async () => {
    vi.mocked(api.post).mockRejectedValue(new Error("This doesn't look like a job description: junk."))
    renderWizard()
    fireEvent.click(await screen.findByRole('button', { name: /Backend Dev/ }))
    fireEvent.click(screen.getByRole('button', { name: 'Continue' }))

    fireEvent.change(await screen.findByLabelText('Paste the job description'), {
      target: { value: 'asdf junk' },
    })
    fireEvent.click(screen.getByRole('button', { name: 'Analyze role' }))
    expect(await screen.findByRole('alert')).toHaveTextContent('junk')

    fireEvent.click(screen.getByRole('tab', { name: 'Short description' }))

    expect(screen.queryByRole('alert')).not.toBeInTheDocument()
    expect(screen.getByLabelText('Describe the role')).toHaveValue('')
  })

  it('keeps each tab\'s own draft when switching back and forth', async () => {
    renderWizard()
    fireEvent.click(await screen.findByRole('button', { name: /Backend Dev/ }))
    fireEvent.click(screen.getByRole('button', { name: 'Continue' }))

    fireEvent.change(await screen.findByLabelText('Paste the job description'), {
      target: { value: 'my full posting' },
    })
    fireEvent.click(screen.getByRole('tab', { name: 'Short description' }))
    fireEvent.change(screen.getByLabelText('Describe the role'), {
      target: { value: 'AI Engineer, mid' },
    })
    fireEvent.click(screen.getByRole('tab', { name: 'Full job description' }))

    expect(screen.getByLabelText('Paste the job description')).toHaveValue('my full posting')
  })

  it('disables Analyze role while the text is empty', async () => {
    renderWizard()
    fireEvent.click(await screen.findByRole('button', { name: /Backend Dev/ }))
    fireEvent.click(screen.getByRole('button', { name: 'Continue' }))

    expect(await screen.findByRole('button', { name: 'Analyze role' })).toBeDisabled()
  })
})

describe('preset step', () => {
  it('asks the backend for presets matching the JD coding flag', async () => {
    mockGets({ '/jd': [{ ...JD, coding_assessment_expected: false }] })
    renderWizard()
    await pickResumeAndJd()

    await screen.findByRole('radiogroup', { name: 'Interview presets' })
    expect(api.get).toHaveBeenCalledWith(
      '/interview/presets?coding_assessment_expected=false',
    )
  })

  it("selecting a preset picks its shortest duration, and durations can be changed", async () => {
    renderWizard()
    await pickResumeAndJd()

    fireEvent.click(await screen.findByRole('radio', { name: /Full Loop/ }))
    expect(screen.getByRole('button', { name: '30 min' })).toHaveAttribute('aria-pressed', 'true')

    fireEvent.click(screen.getByRole('button', { name: '40 min' }))
    expect(screen.getByRole('button', { name: '40 min' })).toHaveAttribute('aria-pressed', 'true')
    expect(screen.getByRole('button', { name: '30 min' })).toHaveAttribute('aria-pressed', 'false')
  })

  it('switching preset resets to that preset\'s first duration', async () => {
    renderWizard()
    await pickResumeAndJd()

    fireEvent.click(await screen.findByRole('radio', { name: /Full Loop/ }))
    fireEvent.click(screen.getByRole('button', { name: '40 min' }))
    fireEvent.click(screen.getByRole('radio', { name: /Coding Only/ }))

    expect(screen.getByRole('button', { name: '5 min' })).toHaveAttribute('aria-pressed', 'true')
  })

  it('requires a preset before continuing', async () => {
    renderWizard()
    await pickResumeAndJd()

    await screen.findByRole('radio', { name: /Full Loop/ })
    expect(screen.getByRole('button', { name: 'Continue' })).toBeDisabled()
  })
})

describe('mic check step', () => {
  async function goToMicCheck() {
    renderWizard()
    await pickResumeAndJd()
    fireEvent.click(await screen.findByRole('radio', { name: /Coding Only/ }))
    fireEvent.click(screen.getByRole('button', { name: 'Continue' }))
  }

  it('lets the candidate skip to text without granting access', async () => {
    await goToMicCheck()

    expect(await screen.findByText('Check your microphone')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Skip, use text' })).toBeEnabled()
  })

  it('explains a denied microphone without blocking progress', async () => {
    vi.stubGlobal('navigator', {
      mediaDevices: { getUserMedia: vi.fn().mockRejectedValue(new Error('denied')) },
    })
    await goToMicCheck()

    fireEvent.click(await screen.findByRole('button', { name: 'Test microphone' }))

    expect(await screen.findByRole('alert')).toHaveTextContent('blocked')
    expect(screen.getByRole('button', { name: 'Skip, use text' })).toBeEnabled()
  })

  it('reports an unsupported browser', async () => {
    vi.stubGlobal('navigator', { mediaDevices: undefined })
    await goToMicCheck()

    fireEvent.click(await screen.findByRole('button', { name: 'Test microphone' }))

    expect(await screen.findByRole('alert')).toHaveTextContent("can't access a microphone")
  })

  it('shows a live level meter once the microphone is granted', async () => {
    const stop = vi.fn<() => void>()
    vi.stubGlobal('navigator', {
      mediaDevices: {
        getUserMedia: vi.fn().mockResolvedValue({ getTracks: () => [{ stop }] }),
      },
    })
    class FakeAudioContext {
      createAnalyser() {
        return {
          fftSize: 0,
          frequencyBinCount: 4,
          getByteFrequencyData: (a: Uint8Array) => a.fill(120),
        }
      }
      createMediaStreamSource() {
        return { connect: vi.fn<() => void>() }
      }
      close() {
        return Promise.resolve()
      }
    }
    vi.stubGlobal('AudioContext', FakeAudioContext)
    vi.stubGlobal('requestAnimationFrame', () => 0)
    vi.stubGlobal('cancelAnimationFrame', () => undefined)
    await goToMicCheck()

    fireEvent.click(await screen.findByRole('button', { name: 'Test microphone' }))

    expect(await screen.findByRole('meter')).toBeInTheDocument()
    expect(screen.getByRole('status')).toHaveTextContent('working')
    expect(screen.getByRole('button', { name: 'Continue' })).toBeEnabled()
  })
})

describe('lobby step', () => {
  async function goToLobby() {
    renderWizard()
    await pickResumeAndJd()
    fireEvent.click(await screen.findByRole('radio', { name: /Full Loop/ }))
    fireEvent.click(screen.getByRole('button', { name: 'Continue' }))
    fireEvent.click(await screen.findByRole('button', { name: 'Skip, use text' }))
  }

  // Steps of at most 1s so React re-renders (and schedules the next
  // countdown tick) between them, like real time does.
  async function advance(ms: number) {
    let remaining = ms
    do {
      const step = Math.min(1000, remaining)
      await act(async () => {
        await vi.advanceTimersByTimeAsync(step)
      })
      remaining -= step
    } while (remaining > 0)
  }

  const START_PAYLOAD = {
    candidate_profile_id: 1,
    job_description_id: 7,
    preset_key: 'full_loop',
    duration_minutes: 30,
  }

  it('recaps the choices made', async () => {
    await goToLobby()

    expect(await screen.findByText('Ready when you are')).toBeInTheDocument()
    expect(screen.getByText('Backend Engineer')).toBeInTheDocument()
    expect(screen.getByText('Full Loop (all 7 phases)')).toBeInTheDocument()
    expect(screen.getByText('30 minutes')).toBeInTheDocument()
  })

  it('starts the request immediately, counts down, then opens the interview', async () => {
    vi.mocked(api.post).mockResolvedValue({ id: 42 })
    await goToLobby()
    vi.useFakeTimers()

    fireEvent.click(screen.getByRole('button', { name: 'Begin interview' }))
    await advance(0)

    // Request fired at once, not after the countdown.
    expect(api.post).toHaveBeenCalledWith('/interview/start', START_PAYLOAD)
    expect(screen.getByRole('timer')).toHaveTextContent('3')
    // Even though the response is already back, the countdown finishes first.
    await advance(1000)
    expect(screen.getByRole('timer')).toHaveTextContent('2')
    expect(screen.queryByText('Interview room')).not.toBeInTheDocument()

    await advance(2000)

    expect(screen.getByText('Interview room')).toBeInTheDocument()
  })

  it('shows what is being prepared while the interviewer loads, then opens the interview', async () => {
    let respond: (value: unknown) => void = () => {}
    vi.mocked(api.post).mockReturnValue(new Promise((resolve) => { respond = resolve }))
    await goToLobby()
    vi.useFakeTimers()

    fireEvent.click(screen.getByRole('button', { name: 'Begin interview' }))
    await advance(3000)

    expect(screen.getByText('Preparing your interviewer')).toBeInTheDocument()
    const first = screen.getByText('Reading your resume').closest('li')
    expect(first).toHaveAttribute('aria-current', 'step')
    // The company step appears because this JD names a company.
    expect(screen.getByText('Researching the company')).toBeInTheDocument()

    await advance(3500)
    expect(screen.getByText('Matching questions to the role').closest('li')).toHaveAttribute('aria-current', 'step')

    respond({ id: 42 })
    await advance(0)

    expect(screen.getByText('Interview room')).toBeInTheDocument()
  })

  it('skips the company step when the JD has no company', async () => {
    mockGets({ '/jd': [{ ...JD, company_name: null }] })
    vi.mocked(api.post).mockReturnValue(new Promise(() => {}))
    await goToLobby()
    vi.useFakeTimers()

    fireEvent.click(screen.getByRole('button', { name: 'Begin interview' }))
    await advance(3000)

    expect(screen.getByText('Reading your resume')).toBeInTheDocument()
    expect(screen.queryByText('Researching the company')).not.toBeInTheDocument()
  })

  it('returns to the ready state with the error if starting fails', async () => {
    vi.mocked(api.post).mockRejectedValue(new Error('Gemini is down'))
    await goToLobby()

    fireEvent.click(screen.getByRole('button', { name: 'Begin interview' }))

    expect(await screen.findByText('Gemini is down')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Begin interview' })).toBeEnabled()
    expect(screen.queryByRole('timer')).not.toBeInTheDocument()
  })
})

describe('navigation', () => {
  it('goes back a step and still shows the chosen JD preview', async () => {
    renderWizard()
    await pickResumeAndJd()

    fireEvent.click(await screen.findByRole('button', { name: 'Back' }))

    expect(await screen.findByRole('button', { name: 'Delete job description' })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Continue' })).toBeEnabled()
  })
})

describe('stepper', () => {
  it('marks the current step and completed steps', async () => {
    renderWizard()
    expect(screen.getByRole('listitem', { current: 'step' })).toHaveTextContent('Resume')

    fireEvent.click(await screen.findByRole('button', { name: /Backend Dev/ }))
    fireEvent.click(screen.getByRole('button', { name: 'Continue' }))

    expect(await screen.findByText('(completed)')).toBeInTheDocument()
    expect(screen.getByRole('listitem', { current: 'step' })).toHaveTextContent('Role')
  })
})

describe('resume preview and delete', () => {
  it('shows a preview and hides the upload once a resume is chosen', async () => {
    renderWizard()

    fireEvent.click(await screen.findByRole('button', { name: /Backend Dev/ }))

    expect(screen.getByText('Backend Dev at Acme')).toBeInTheDocument()
    expect(screen.getByText('Python')).toBeInTheDocument()
    expect(screen.queryByLabelText('Resume PDF')).not.toBeInTheDocument()
    expect(screen.queryByText('Upload a new resume')).not.toBeInTheDocument()
  })

  it('shows the preview right after an upload', async () => {
    vi.mocked(api.upload).mockResolvedValue({ ...RESUME, id: 2, skills: ['Go'] })
    renderWizard()

    const file = new File(['%PDF-1.4'], 'cv.pdf', { type: 'application/pdf' })
    fireEvent.change(screen.getByLabelText('Resume PDF'), { target: { files: [file] } })

    expect(await screen.findByText('Go')).toBeInTheDocument()
    expect(screen.queryByLabelText('Resume PDF')).not.toBeInTheDocument()
  })

  it('shows the backend message when the resume is a duplicate', async () => {
    vi.mocked(api.upload).mockRejectedValue(
      new Error('This resume has already been uploaded. Pick it from your previous resumes instead of uploading it again.'),
    )
    renderWizard()

    const file = new File(['%PDF-1.4'], 'cv.pdf', { type: 'application/pdf' })
    fireEvent.change(screen.getByLabelText('Resume PDF'), { target: { files: [file] } })

    expect(await screen.findByText(/already been uploaded/)).toBeInTheDocument()
    expect(screen.getByLabelText('Resume PDF')).toBeInTheDocument()
  })

  it('deletes only after confirmation, then brings the upload back', async () => {
    vi.mocked(api.delete).mockResolvedValue({ id: 1 })
    renderWizard()
    fireEvent.click(await screen.findByRole('button', { name: /Backend Dev/ }))

    fireEvent.click(screen.getByRole('button', { name: 'Delete resume' }))
    expect(api.delete).not.toHaveBeenCalled()
    fireEvent.click(screen.getByRole('button', { name: 'Delete' }))

    await waitFor(() => expect(api.delete).toHaveBeenCalledWith('/resume/1'))
    expect(await screen.findByLabelText('Resume PDF')).toBeInTheDocument()
  })

  it('cancelling the confirmation keeps the resume', async () => {
    renderWizard()
    fireEvent.click(await screen.findByRole('button', { name: /Backend Dev/ }))

    fireEvent.click(screen.getByRole('button', { name: 'Delete resume' }))
    fireEvent.click(screen.getByRole('button', { name: 'Cancel' }))

    expect(api.delete).not.toHaveBeenCalled()
    expect(screen.getByRole('button', { name: 'Delete resume' })).toBeInTheDocument()
  })

  it('shows Deleting… on the preview while the request is pending', async () => {
    let finishDelete: () => void = () => {}
    vi.mocked(api.delete).mockImplementation(
      () => new Promise((resolve) => { finishDelete = () => resolve({ id: 1 }) }),
    )
    renderWizard()
    fireEvent.click(await screen.findByRole('button', { name: /Backend Dev/ }))

    fireEvent.click(screen.getByRole('button', { name: 'Delete resume' }))
    fireEvent.click(screen.getByRole('button', { name: 'Delete' }))

    expect(await screen.findByRole('status')).toHaveTextContent('Deleting resume…')

    finishDelete()

    expect(await screen.findByLabelText('Resume PDF')).toBeInTheDocument()
  })

  it('keeps the preview and shows the reason when delete is refused', async () => {
    vi.mocked(api.delete).mockRejectedValue(
      new Error("This resume is used by 1 in-progress interview. Finish or end it before deleting."),
    )
    renderWizard()
    fireEvent.click(await screen.findByRole('button', { name: /Backend Dev/ }))

    fireEvent.click(screen.getByRole('button', { name: 'Delete resume' }))
    fireEvent.click(screen.getByRole('button', { name: 'Delete' }))

    expect(await screen.findByText(/used by 1 in-progress interview/)).toBeInTheDocument()
    expect(screen.getByText('Backend Dev at Acme')).toBeInTheDocument()
  })

  it('Change clears the choice without deleting anything', async () => {
    renderWizard()
    fireEvent.click(await screen.findByRole('button', { name: /Backend Dev/ }))

    fireEvent.click(screen.getByRole('button', { name: 'Change' }))

    expect(await screen.findByLabelText('Resume PDF')).toBeInTheDocument()
    expect(api.delete).not.toHaveBeenCalled()
  })
})

describe('job description preview and delete', () => {
  async function goToRole() {
    renderWizard()
    fireEvent.click(await screen.findByRole('button', { name: /Backend Dev/ }))
    fireEvent.click(screen.getByRole('button', { name: 'Continue' }))
  }

  it('shows a preview and hides the paste form once a JD is chosen', async () => {
    await goToRole()

    fireEvent.click(await screen.findByRole('button', { name: /Backend Engineer/ }))

    expect(screen.getByText('Expected')).toBeInTheDocument()
    expect(screen.queryByLabelText('Paste the job description')).not.toBeInTheDocument()
  })

  it('shows the preview right after analyzing a new JD', async () => {
    vi.mocked(api.post).mockResolvedValue({ ...JD, id: 8, role: 'Data Engineer' })
    await goToRole()

    fireEvent.change(await screen.findByLabelText('Paste the job description'), {
      target: { value: 'We need a data engineer.' },
    })
    fireEvent.click(screen.getByRole('button', { name: 'Analyze role' }))

    expect(await screen.findByText('Data Engineer')).toBeInTheDocument()
    expect(screen.queryByLabelText('Paste the job description')).not.toBeInTheDocument()
  })

  it('shows the backend message when the JD is a duplicate', async () => {
    vi.mocked(api.post).mockRejectedValue(
      new Error('This job description has already been uploaded. Pick it from your previous job descriptions instead of uploading it again.'),
    )
    await goToRole()

    fireEvent.change(await screen.findByLabelText('Paste the job description'), {
      target: { value: 'We need a backend engineer.' },
    })
    fireEvent.click(screen.getByRole('button', { name: 'Analyze role' }))

    expect(await screen.findByText(/already been uploaded/)).toBeInTheDocument()
  })

  it('deletes a JD after confirmation and brings the form back', async () => {
    vi.mocked(api.delete).mockResolvedValue({ id: 7 })
    await goToRole()
    fireEvent.click(await screen.findByRole('button', { name: /Backend Engineer/ }))

    fireEvent.click(screen.getByRole('button', { name: 'Delete job description' }))
    fireEvent.click(screen.getByRole('button', { name: 'Delete' }))

    await waitFor(() => expect(api.delete).toHaveBeenCalledWith('/jd/7'))
    expect(await screen.findByLabelText('Paste the job description')).toBeInTheDocument()
  })
})
