import { Link } from 'react-router'
import { Navigation } from '../../components/Navigation'
import { MeshGradientBackground } from '../../components/ui/MeshGradientBackground'
import { CompassIcon } from '../../components/ui/CompassIcon'
import { useAuth } from '../../lib/authContext'
import { STARTUP_ROUTE } from '../../lib/routes'

// A signed-in candidate bouncing off a broken link has no use for the
// public marketing homepage they already converted from - send them
// back to their actual next step instead of re-pitching the product.
const AUTHENTICATED_HOME_ROUTE = '/setup'

export function NotFoundPage() {
  const { isAuthenticated } = useAuth()
  const homeRoute = isAuthenticated ? AUTHENTICATED_HOME_ROUTE : STARTUP_ROUTE

  return (
    <div className="min-h-screen flex flex-col bg-hero">
      <div className="relative isolate overflow-hidden flex-1 flex flex-col">
        <MeshGradientBackground muted />

        <Navigation transparent />

        <main className="mx-auto max-w-3xl w-full px-6 sm:px-10 flex-1 flex items-center justify-center py-20 sm:py-28">
          <section aria-labelledby="not-found-title" className="text-center">
            <CompassIcon className="w-9 h-9 mx-auto" />
            <p className="mt-5 text-8xl sm:text-9xl font-bold tracking-tight bg-linear-to-r from-brand to-[#5eead4] bg-clip-text text-transparent leading-none">
              404
            </p>
            <h1
              id="not-found-title"
              className="mt-7 text-3xl sm:text-5xl font-bold tracking-tight text-white text-balance"
            >
              The page you’re looking for doesn’t exist or has been moved.
            </h1>
            <p className="mt-5 text-lg text-slate-300 text-balance">
              {isAuthenticated
                ? 'Head back and start a new interview.'
                : 'Head back to Prepwise and continue from the start.'}
            </p>
            <div className="mt-9 flex justify-center">
              <Link
                to={homeRoute}
                className="px-7 py-3.5 rounded-[10px] bg-brand text-[#06251f] text-[15px] font-semibold shadow-lg shadow-teal-900/30 hover:bg-[#14c3a8] active:scale-[0.99] transition-all focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-4 focus-visible:outline-brand"
              >
                {isAuthenticated ? 'Start an interview' : 'Go home'}
              </Link>
            </div>
          </section>
        </main>
      </div>
    </div>
  )
}

export default NotFoundPage
