import { useEffect, useRef, useState } from 'react'
import { Button } from '../../components/ui/Button'
import { Card } from '../../components/ui/Card'

type MicState = 'idle' | 'requesting' | 'listening' | 'denied' | 'unsupported'

interface MicCheckStepProps {
  onBack: () => void
  onContinue: () => void
}

// The interview is voice-first but always works as text, so a denied or
// missing microphone never blocks the wizard, it only changes the copy.
export function MicCheckStep({ onBack, onContinue }: MicCheckStepProps) {
  const [state, setState] = useState<MicState>('idle')
  const [level, setLevel] = useState(0)
  const [heardVoice, setHeardVoice] = useState(false)
  const cleanup = useRef<(() => void) | null>(null)

  useEffect(() => () => cleanup.current?.(), [])

  async function startCheck() {
    if (!navigator.mediaDevices?.getUserMedia) {
      setState('unsupported')
      return
    }
    setState('requesting')
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true })
      const audioContext = new AudioContext()
      const analyser = audioContext.createAnalyser()
      analyser.fftSize = 256
      audioContext.createMediaStreamSource(stream).connect(analyser)
      const samples = new Uint8Array(analyser.frequencyBinCount)

      let frame = 0
      const tick = () => {
        analyser.getByteFrequencyData(samples)
        const average = samples.reduce((sum, v) => sum + v, 0) / samples.length
        const normalized = Math.min(1, average / 80)
        setLevel(normalized)
        if (normalized > 0.15) setHeardVoice(true)
        frame = requestAnimationFrame(tick)
      }
      tick()

      cleanup.current = () => {
        cancelAnimationFrame(frame)
        stream.getTracks().forEach((track) => track.stop())
        void audioContext.close()
      }
      setState('listening')
    } catch {
      setState('denied')
    }
  }

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-lg font-semibold text-ink">Check your microphone</h2>
        <p className="mt-1 text-sm text-muted">
          Say a few words and watch the meter. Nothing is recorded during this check.
        </p>
      </div>

      <Card className="space-y-4">
        {state === 'listening' ? (
          <>
            <div
              role="meter"
              aria-label="Microphone level"
              aria-valuemin={0}
              aria-valuemax={100}
              aria-valuenow={Math.round(level * 100)}
              className="h-3 rounded-full bg-[#f4f7fa] overflow-hidden"
            >
              <div
                className="h-full bg-brand transition-[width] duration-75"
                style={{ width: `${Math.round(level * 100)}%` }}
              />
            </div>
            <p className="text-sm text-muted" role="status">
              {heardVoice
                ? 'Your microphone is working.'
                : 'Speak now, the meter should move.'}
            </p>
          </>
        ) : (
          <>
            {state === 'denied' && (
              <p role="alert" className="text-sm text-amber-700">
                Microphone access was blocked. You can still take the interview in
                text, or allow access in your browser settings and try again.
              </p>
            )}
            {state === 'unsupported' && (
              <p role="alert" className="text-sm text-amber-700">
                This browser can't access a microphone. You can take the interview
                in text instead.
              </p>
            )}
            {(state === 'idle' || state === 'requesting' || state === 'denied') && (
              <div className="sm:w-56">
                <Button
                  variant="outline"
                  isLoading={state === 'requesting'}
                  onClick={() => void startCheck()}
                >
                  {state === 'denied' ? 'Try again' : 'Test microphone'}
                </Button>
              </div>
            )}
          </>
        )}
      </Card>

      <div className="flex gap-3 sm:justify-between">
        <div className="sm:w-32">
          <Button variant="secondary" onClick={onBack}>
            Back
          </Button>
        </div>
        <div className="sm:w-56">
          <Button onClick={onContinue}>
            {state === 'listening' ? 'Continue' : 'Skip, use text'}
          </Button>
        </div>
      </div>
    </div>
  )
}
