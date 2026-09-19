import { useState } from 'react'
import { useMutation } from '@tanstack/react-query'
import { useNavigate } from 'react-router'
import { AppShell } from '../../components/AppShell'
import { Button } from '../../components/ui/Button'
import { Card } from '../../components/ui/Card'
import { ErrorAlert } from '../../components/ui/ErrorAlert'
import { Input } from '../../components/ui/Input'
import { PageIntro } from '../../components/ui/PageIntro'
import { useAuth } from '../../lib/authContext'
import { toErrorMessage } from '../../lib/errorMessage'
import { useToast } from '../../lib/toastContext'

const PREFERRED_NAME_MAX_LENGTH = 50

function SectionHeading({ title, description }: { title: string; description: string }) {
  return (
    <div className="mb-5">
      <h3 className="text-[16px] font-semibold text-ink">{title}</h3>
      <p className="mt-1 text-sm text-muted">{description}</p>
    </div>
  )
}

function ProfileSection() {
  const { user, updatePreferredName } = useAuth()
  const { showToast } = useToast()
  const savedName = user?.preferred_name ?? ''
  const [preferredName, setPreferredName] = useState(savedName)

  const save = useMutation<unknown, Error, string>({
    mutationFn: (name) =>
      updatePreferredName(name).catch((err: unknown) => {
        throw new Error(toErrorMessage(err, "Couldn't save your name. Please try again."))
      }),
    onSuccess: () => showToast('Profile name updated'),
    onError: (error) => showToast(error.message, 'error'),
  })

  if (!user) return null

  const isUnchanged = preferredName.trim() === savedName
  const handleSubmit = (event: React.FormEvent) => {
    event.preventDefault()
    save.mutate(preferredName)
  }

  return (
    <Card>
      <SectionHeading title="Profile" description="How Prepwise knows and addresses you." />
      <form onSubmit={handleSubmit} className="flex max-w-md flex-col gap-5">
        <div className="flex flex-col gap-1.5">
          <Input
            label="Email"
            type="email"
            value={user.email}
            disabled
            className="cursor-not-allowed bg-slate-50 text-muted"
          />
          <p className="text-xs text-muted">Your email is tied to your account and can't be changed.</p>
        </div>

        <div className="flex flex-col gap-1.5">
          <Input
            label="Profile name"
            value={preferredName}
            maxLength={PREFERRED_NAME_MAX_LENGTH}
            placeholder="What should we call you?"
            onChange={(event) => {
              setPreferredName(event.target.value)
              save.reset()
            }}
          />
          <p className="text-xs text-muted">
            Used when we greet you, like "Welcome back, Sam". Leave it empty to use your first name.
          </p>
        </div>


        <div className="w-full sm:w-40">
          <Button type="submit" isLoading={save.isPending} disabled={isUnchanged}>
            Save changes
          </Button>
        </div>
      </form>
    </Card>
  )
}

function PasswordSection() {
  const { user, forgotPassword } = useAuth()
  const { showToast } = useToast()
  const navigate = useNavigate()

  const sendReset = useMutation<unknown, Error, string>({
    mutationFn: (email) =>
      forgotPassword(email).catch((err: unknown) => {
        throw new Error(toErrorMessage(err, "Couldn't send the email. Please try again."))
      }),
    onSuccess: (_result, email) => {
      navigate(`/reset-password/verify?email=${encodeURIComponent(email)}`)
      showToast('Thanks! Check your email for the reset code.')
    },
    onError: (error) => showToast(error.message, 'error'),
  })

  if (!user) return null

  return (
    <Card>
      <SectionHeading
        title="Password"
        description="To add or change your password, we'll email you a 6-digit code. Once the new password is saved, you'll be signed out and can sign in again."
      />
      <div className="w-full sm:w-48">
        <Button
          type="button"
          variant="outline"
          isLoading={sendReset.isPending}
          onClick={() => sendReset.mutate(user.email)}
        >
          Send reset email
        </Button>
      </div>
    </Card>
  )
}

function DeleteAccountSection() {
  const { deleteAccount } = useAuth()
  const { showToast } = useToast()
  const navigate = useNavigate()
  const [isConfirming, setIsConfirming] = useState(false)

  const remove = useMutation<void, Error>({
    mutationFn: () =>
      deleteAccount().catch((err: unknown) => {
        throw new Error(toErrorMessage(err, "Couldn't delete your account. Please try again."))
      }),
    onSuccess: () => {
      navigate('/', { replace: true })
      showToast('Your account has been deleted.')
    },
  })

  return (
    <Card className="border-red-200">
      <SectionHeading
        title="Delete account"
        description="Permanently deletes your account along with your resumes, job descriptions, interviews and reports. This can't be undone."
      />
      <ErrorAlert message={remove.error?.message ?? null} />
      {isConfirming ? (
        <div className="flex flex-col gap-3 sm:flex-row">
          <div className="w-full sm:w-48">
            <Button type="button" variant="danger" isLoading={remove.isPending} onClick={() => remove.mutate()}>
              Yes, delete everything
            </Button>
          </div>
          <div className="w-full sm:w-32">
            <Button
              type="button"
              variant="secondary"
              disabled={remove.isPending}
              onClick={() => setIsConfirming(false)}
            >
              Cancel
            </Button>
          </div>
        </div>
      ) : (
        <div className="w-full sm:w-48">
          <Button type="button" variant="danger" onClick={() => setIsConfirming(true)}>
            Delete account
          </Button>
        </div>
      )}
    </Card>
  )
}

export function SettingsPage() {
  return (
    <AppShell title="Settings">
      <PageIntro
        title="Account settings"
        description="Manage how Prepwise addresses you, how you sign in, and your data."
      />
      <div className="mt-8 flex max-w-3xl flex-col gap-6">
        <ProfileSection />
        <PasswordSection />
        <DeleteAccountSection />
      </div>
    </AppShell>
  )
}
