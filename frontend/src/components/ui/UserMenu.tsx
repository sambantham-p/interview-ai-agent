import { useEffect, useRef, useState } from 'react'
import { Link, useNavigate } from 'react-router'
import { useAuth } from '../../lib/authContext'
import { Avatar } from './Avatar'
import { ChevronUpDownIcon, LogOutIcon, SettingsIcon } from './icons'

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
        className="flex w-full cursor-pointer items-center gap-3 rounded-xl p-2 text-left transition-colors hover:bg-white/5"
      >
        <Avatar name={user.name} picture={user.picture} className="w-9 h-9 shrink-0 text-sm ring-1 ring-white/20" />
        <span className="hidden min-w-0 flex-1 md:block">
          <span className="block truncate text-[13px] font-semibold text-white">{user.name}</span>
          <span className="block truncate text-xs text-slate-400">{user.email}</span>
        </span>
        <ChevronUpDownIcon className="hidden h-4 w-4 shrink-0 text-slate-400 md:block" />
      </button>

      {isOpen && (
        // Opens upward on desktop because the trigger sits at the bottom of
        // the sidebar; on mobile the sidebar is a top strip, so it opens down.
        <div className="absolute right-0 top-full z-50 mt-2 w-64 rounded-xl border border-mist bg-white py-2 shadow-[0_12px_32px_-8px_rgba(0,0,0,0.45)] ring-1 ring-white/15 md:bottom-full md:left-0 md:right-0 md:top-auto md:mb-2 md:mt-0 md:w-auto">
          <div className="border-b border-mist px-4 pb-3 pt-2">
            <p className="truncate text-[13px] font-semibold text-ink">{user.name}</p>
            <p className="truncate text-xs text-muted">{user.email}</p>
          </div>
          <div className="py-1">
            <Link
              to="/settings"
              onClick={() => setIsOpen(false)}
              className="flex items-center gap-3 px-4 py-2.5 text-sm text-ink transition-colors hover:bg-[#e9f0f7]"
            >
              <SettingsIcon className="h-4.5 w-4.5 text-muted" />
              Settings
            </Link>
          </div>
          <div className="border-t border-mist pt-1">
            <button
              type="button"
              onClick={handleSignOut}
              className="flex w-full cursor-pointer items-center gap-3 px-4 py-2.5 text-left text-sm text-ink transition-colors hover:bg-[#e9f0f7]"
            >
              <LogOutIcon className="h-4.5 w-4.5 text-muted" />
              Log out
            </button>
          </div>
        </div>
      )}
    </div>
  )
}
