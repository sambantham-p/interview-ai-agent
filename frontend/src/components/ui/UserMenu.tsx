import { useEffect, useRef, useState } from 'react'
import { Link, useNavigate } from 'react-router'
import { useAuth } from '../../lib/authContext'
import { Avatar } from './Avatar'


export function UserMenu() {
  const { user, logout } = useAuth()
  const navigate = useNavigate()
  const [isOpen, setIsOpen] = useState(false)
  const menuRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    function handleClickOutside(event: MouseEvent) {
      if (menuRef.current && !menuRef.current.contains(event.target as Node)) {
        setIsOpen(false)
      }
    }
    document.addEventListener('mousedown', handleClickOutside)
    return () => document.removeEventListener('mousedown', handleClickOutside)
  }, [])

  if (!user) return null

  const handleSignOut = () => {
    logout()
    navigate('/')
  }

  return (
    <div className="relative" ref={menuRef}>
      <button
        type="button"
        onClick={() => setIsOpen((open) => !open)}
        aria-expanded={isOpen}
        aria-label="Account menu"
        className="cursor-pointer hover:opacity-90 transition-opacity"
      >
        <Avatar name={user.name} picture={user.picture} className="w-9 h-9 text-sm" />
      </button>

      {isOpen && (
        <div className="absolute right-0 mt-2 w-64 rounded-xl bg-white border border-mist shadow-lg py-2 z-50">
          <div className="px-4 py-2.5 border-b border-mist">
            <p className="text-[13px] font-semibold text-ink truncate">{user.name}</p>
            <p className="text-xs text-muted truncate">{user.email}</p>
          </div>
          <Link
            to="/settings"
            onClick={() => setIsOpen(false)}
            className="block px-4 py-2.5 text-sm text-ink hover:bg-[#f4f7fa] transition-colors"
          >
            Settings
          </Link>
          <button
            type="button"
            onClick={handleSignOut}
            className="w-full text-left px-4 py-2.5 text-sm text-red-600 hover:bg-red-50 transition-colors cursor-pointer"
          >
            Sign out
          </button>
        </div>
      )}
    </div>
  )
}
