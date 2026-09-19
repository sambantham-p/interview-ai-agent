import { useState } from 'react'

interface AvatarProps {
  name: string
  picture: string | null
  className?: string
}


export function Avatar({ name, picture, className = '' }: AvatarProps) {
  const [imageFailed, setImageFailed] = useState(false)
  const initial = name.charAt(0).toUpperCase()

  if (picture && !imageFailed) {
    return (
      <img
        src={picture}
        alt={name}
        referrerPolicy="no-referrer"
        onError={() => setImageFailed(true)}
        className={`rounded-full object-cover ${className}`}
      />
    )
  }

  return (
    <span
      className={`rounded-full bg-brand text-white font-semibold flex items-center justify-center ${className}`}
    >
      {initial}
    </span>
  )
}
