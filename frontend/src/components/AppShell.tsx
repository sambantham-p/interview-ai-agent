import { Link, useLocation } from 'react-router'
import { FolderIcon, GridIcon } from './ui/icons'
import { PrepwiseLogo } from './ui/PrepwiseLogo'
import { UserMenu } from './ui/UserMenu'

interface NavItem {
  label: string
  to: string
  icon: React.ReactNode
}


const NAV_ITEMS: NavItem[] = [
  { label: 'Dashboard', to: '/dashboard', icon: <GridIcon className="w-[18px] h-[18px]" /> },
  { label: 'Documents', to: '/documents', icon: <FolderIcon className="w-4.5 h-4.5" /> },
]

interface AppShellProps {
  children: React.ReactNode
}


export function AppShell({ children }: AppShellProps) {
  const location = useLocation()

  return (
    <div className="min-h-screen flex flex-col md:flex-row bg-[#f4f7fa]">
      <aside className="w-full md:w-60 md:min-h-screen shrink-0 bg-hero flex md:flex-col">
        <div className="px-5 py-5 md:py-6">
          <Link to="/dashboard">
            <PrepwiseLogo size="sm" />
          </Link>
        </div>
        <nav className="flex md:flex-col flex-1 gap-1 px-3 pb-4 md:pb-0 overflow-x-auto">
          {NAV_ITEMS.map((item) => {
            const isActive = location.pathname.startsWith(item.to)
            return (
              <Link
                key={item.to}
                to={item.to}
                className={`flex items-center gap-2.5 px-3 py-2.5 rounded-lg text-[13px] font-medium whitespace-nowrap transition-colors ${
                  isActive
                    ? 'bg-brand/15 text-brand'
                    : 'text-slate-300 hover:bg-white/5 hover:text-white'
                }`}
              >
                {item.icon}
                {item.label}
              </Link>
            )
          })}
        </nav>
      </aside>

      <div className="flex-1 min-w-0 flex flex-col">
        <header className="flex items-center justify-end px-6 sm:px-8 py-4 border-b border-mist bg-white">
          <UserMenu />
        </header>
        <main className="flex-1 px-6 sm:px-8 py-8 max-w-6xl w-full mx-auto">
          {children}
        </main>
      </div>
    </div>
  )
}
