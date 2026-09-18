import { Link, useNavigate } from 'react-router'
import { PrepwiseLogo } from './ui/PrepwiseLogo'
import { useAuth } from '../lib/authContext'

interface NavigationProps {
  /** Renders over a dark hero instead of the default white app bar - see
   * App.tsx's HomePage, the only place with a dark background behind it. */
  transparent?: boolean
}

export function Navigation({ transparent = false }: NavigationProps) {
  const { user, isAuthenticated, logout } = useAuth()
  const navigate = useNavigate()

  const handleLogout = () => {
    logout()
    navigate('/login')
  }

  const headerClass = transparent
    ? 'bg-transparent'
    : 'bg-white border-b border-[#e2e8f0] sticky top-0'

  return (
    <header
      className={`w-full px-6 py-3.5 flex items-center justify-between z-40 ${headerClass}`}
    >
      <Link to="/" className="flex items-center">
        <PrepwiseLogo variant={transparent ? 'dark' : 'light'} size="sm" />
      </Link>

      <div className="flex items-center gap-4">
        {isAuthenticated && user ? (
          <div className="flex items-center gap-3">
            {user.picture ? (
              <img
                src={user.picture}
                alt={user.name}
                className="w-8 h-8 rounded-full border border-mist object-cover"
              />
            ) : (
              <div className="w-8 h-8 rounded-full bg-brand text-white font-semibold text-sm flex items-center justify-center">
                {user.name.charAt(0).toUpperCase()}
              </div>
            )}
            <div
              className={`hidden sm:flex flex-col text-left ${transparent ? 'text-white' : ''}`}
            >
              <span
                className={`text-[13px] font-semibold leading-tight ${transparent ? 'text-white' : 'text-ink'}`}
              >
                {user.name}
              </span>
              <span
                className={`text-[11px] leading-tight ${transparent ? 'text-slate-300' : 'text-muted'}`}
              >
                {user.email}
              </span>
            </div>
            <button
              type="button"
              onClick={handleLogout}
              className={`ml-2 text-[13px] font-medium transition-colors cursor-pointer ${
                transparent
                  ? 'text-slate-300 hover:text-white'
                  : 'text-muted hover:text-red-600'
              }`}
            >
              Sign out
            </button>
          </div>
        ) : (
          <div className="flex items-center gap-3">
            <Link
              to="/login"
              className={`text-[14px] font-semibold hover:underline ${
                transparent ? 'text-white' : 'text-navy'
              }`}
            >
              Sign in
            </Link>
            <Link
              to="/signup"
              className={
                transparent
                  ? 'text-[13px] font-semibold px-4 py-2 rounded-lg bg-brand text-[#06251f] hover:bg-[#14c3a8] transition-all'
                  : 'text-[13px] font-semibold px-4 py-2 rounded-lg bg-navy text-white hover:bg-[#112d4e] transition-all'
              }
            >
              Sign up
            </Link>
          </div>
        )}
      </div>
    </header>
  )
}
