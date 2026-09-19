import { Link, useLocation } from 'react-router'
import { SETUP_ROUTE } from '../lib/routes'
import {
  ChartBarIcon,
  ChevronRightIcon,
  FolderIcon,
  GridIcon,
  SparkleIcon,
} from './ui/icons'
import { PrepwiseLogo } from './ui/PrepwiseLogo'
import { UserMenu } from './ui/UserMenu'

interface NavItem {
  label: string
  to: string
  icon: React.ReactNode
  isActive: (pathname: string) => boolean
}

const startsWith = (prefix: string) => (pathname: string) =>
  pathname.startsWith(prefix)
// A single report lives under its interview, but belongs to Reports.
const isReportsPath = (pathname: string) =>
  pathname.startsWith('/reports') ||
  /^\/interview\/[^/]+\/report/.test(pathname)

const NAV_ITEMS: NavItem[] = [
  {
    label: 'Dashboard',
    to: '/dashboard',
    icon: <GridIcon className="w-4.5 h-4.5" />,
    isActive: startsWith('/dashboard'),
  },
  {
    label: 'Prepare',
    to: SETUP_ROUTE,
    icon: <SparkleIcon className="w-4.5 h-4.5" />,
    isActive: startsWith(SETUP_ROUTE),
  },
  {
    label: 'Documents',
    to: '/documents',
    icon: <FolderIcon className="w-4.5 h-4.5" />,
    isActive: startsWith('/documents'),
  },
  {
    label: 'Reports',
    to: '/reports',
    icon: <ChartBarIcon className="w-4.5 h-4.5" />,
    isActive: isReportsPath,
  },
]

interface AppShellProps {
  title: string
  parent?: { label: string; to: string }
  children: React.ReactNode
}

export function AppShell({ title, parent, children }: AppShellProps) {
  const location = useLocation()

  return (
    <div className="h-dvh overflow-hidden flex flex-col md:flex-row bg-[#f4f7fa]">
      <aside className="w-full md:w-60 md:h-full shrink-0 bg-hero flex md:flex-col">
        <div className="flex h-16 shrink-0 items-center px-5 md:border-b md:border-white/10">
          <Link to="/dashboard">
            <PrepwiseLogo size="md" />
          </Link>
        </div>
        <nav className="scrollbar-soft [--scroll-thumb:rgba(255,255,255,0.2)] flex md:flex-col flex-1 items-center md:items-stretch gap-1.5 px-4 md:pt-7 md:pb-6 overflow-x-auto md:overflow-y-auto">
          {NAV_ITEMS.map((item) => {
            const isActive = item.isActive(location.pathname)
            return (
              <Link
                key={item.to}
                to={item.to}
                aria-current={isActive ? 'page' : undefined}
                className={`flex items-center gap-3 px-3.5 py-3 rounded-xl text-[14px] font-medium whitespace-nowrap transition-colors ${
                  isActive
                    ? 'bg-brand/15 text-brand md:shadow-[inset_3px_0_0_var(--color-brand)]'
                    : 'text-slate-300 hover:bg-white/5 hover:text-white'
                }`}
              >
                {item.icon}
                {item.label}
              </Link>
            )
          })}
        </nav>
        <div className="flex items-center gap-2 px-4 md:flex-col md:items-stretch md:gap-3 md:border-t md:border-white/10 md:py-4">
          <UserMenu />
        </div>
      </aside>

      <div className="flex-1 min-w-0 min-h-0 flex flex-col">
        <main
          tabIndex={0}
          className="scrollbar-soft scroll-smooth motion-reduce:scroll-auto flex-1 min-h-0 overflow-y-auto focus-visible:outline-2 focus-visible:-outline-offset-2 focus-visible:outline-brand"
        >
          <div className="px-6 sm:px-8 pt-8 pb-8 max-w-6xl w-full mx-auto">
            {parent && (
              <nav aria-label="Breadcrumb" className="mb-6">
                <ol className="flex min-w-0 items-center gap-2 text-[14px]">
                  {parent && (
                    <>
                      <li className="shrink-0">
                        <Link
                          to={parent.to}
                          className="font-medium text-muted hover:text-ink transition-colors"
                        >
                          {parent.label}
                        </Link>
                      </li>
                      <li aria-hidden="true" className="shrink-0 text-faint">
                        <ChevronRightIcon className="w-4 h-4" />
                      </li>
                    </>
                  )}
                  <li
                    aria-current="page"
                    className="truncate font-semibold text-ink"
                  >
                    {title}
                  </li>
                </ol>
              </nav>
            )}
            {children}
          </div>
        </main>
      </div>
    </div>
  )
}
