import { NavLink } from 'react-router-dom'
import { useLayout } from '../../layouts/AdminLayout'
import {
  LayoutDashboard,
  Newspaper,
  Rss,
  Bell,
  Settings,
  ChevronLeft,
  X,
  Activity,
  Shield,
  AlertTriangle,
  Network,
  MessageSquare,
  User,
  Calendar,
  ShieldCheck,
  TrendingUp,
  FileText,
} from 'lucide-react'
import { clsx } from 'clsx'

const navigation = [
  { name: 'Dashboard', href: '/dashboard', icon: LayoutDashboard },
  { name: 'Today', href: '/today', icon: Calendar, badge: 'New' },
  { name: 'Trading', href: '/trading', icon: TrendingUp, badge: 'Live' },
  { name: 'Research', href: '/research', icon: FileText },
  { name: 'Newsfeed', href: '/newsfeed', icon: Newspaper },
  { name: 'Feeds', href: '/feeds', icon: Rss },
  { name: 'Entity Graph', href: '/graph', icon: Network, badge: '3D', external: true },
  { name: 'Notifications', href: '/notifications', icon: Bell },
  { name: 'Alerts', href: '/alerts', icon: AlertTriangle },
  { name: 'Messages', href: '/messages', icon: MessageSquare },
]

const systemNav = [
  { name: 'Admin', href: '/admin', icon: ShieldCheck },
  { name: 'Profile', href: '/profile', icon: User },
  { name: 'Settings', href: '/settings', icon: Settings },
]

export function Sidebar() {
  const { sidebarOpen, setSidebarOpen, sidebarCollapsed, setSidebarCollapsed } = useLayout()

  const SidebarContent = ({ isMobile = false }: { isMobile?: boolean }) => (
    <div className="flex h-full flex-col">
      {/* Logo */}
      <div className="flex h-[70px] items-center justify-between px-5 border-b border-[#2D2D43]">
        {(!sidebarCollapsed || isMobile) && (
          <div className="flex items-center gap-3">
            <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-gradient-to-br from-primary-500 to-primary-600">
              <Shield className="h-5 w-5 text-white" />
            </div>
            <div>
              <h1 className="text-[15px] font-semibold text-white">Capture Spine</h1>
              <span className="text-[11px] font-medium text-[#565674]">Basic Edition</span>
            </div>
          </div>
        )}
        {sidebarCollapsed && !isMobile && (
          <div className="mx-auto flex h-9 w-9 items-center justify-center rounded-lg bg-gradient-to-br from-primary-500 to-primary-600">
            <Shield className="h-5 w-5 text-white" />
          </div>
        )}
        {isMobile ? (
          <button
            onClick={() => setSidebarOpen(false)}
            className="rounded-lg p-1.5 text-[#565674] hover:bg-[#2D2D43] hover:text-white transition-colors"
          >
            <X className="h-5 w-5" />
          </button>
        ) : (
          <button
            onClick={() => setSidebarCollapsed(!sidebarCollapsed)}
            className={clsx(
              'hidden lg:flex rounded-lg p-1.5 text-[#565674] hover:bg-[#2D2D43] hover:text-white transition-colors',
              sidebarCollapsed && 'mx-auto mt-2'
            )}
          >
            <ChevronLeft
              className={clsx(
                'h-4 w-4 transition-transform',
                sidebarCollapsed && 'rotate-180'
              )}
            />
          </button>
        )}
      </div>

      {/* Navigation */}
      <nav className="flex-1 space-y-1 px-4 py-5 overflow-y-auto">
        {(!sidebarCollapsed || isMobile) && (
          <div className="mb-4 px-3">
            <span className="text-[11px] font-semibold uppercase tracking-wider text-[#565674]">
              Main Menu
            </span>
          </div>
        )}
        {navigation.map((item) => (
          <NavLink
            key={item.name}
            to={item.href}
            onClick={() => isMobile && setSidebarOpen(false)}
            className={({ isActive }) =>
              clsx(
                'group flex items-center rounded-lg px-3 py-2.5 text-[13px] font-medium transition-all duration-200',
                isActive
                  ? 'bg-[#1B1B29] text-white'
                  : 'text-[#9D9DA6] hover:bg-[#1B1B29] hover:text-white',
                sidebarCollapsed && !isMobile && 'justify-center px-2'
              )
            }
          >
            {({ isActive }) => (
              <>
                <item.icon 
                  className={clsx(
                    'h-[18px] w-[18px] flex-shrink-0 transition-colors',
                    !sidebarCollapsed && !isMobile && 'mr-3',
                    isActive ? 'text-primary-500' : 'text-[#565674] group-hover:text-primary-400'
                  )} 
                />
                {(!sidebarCollapsed || isMobile) && (
                  <>
                    <span className="flex-1">{item.name}</span>
                    {item.badge && (
                      <span className="ml-2 rounded bg-primary-500/20 px-1.5 py-0.5 text-[10px] font-semibold text-primary-400">
                        {item.badge}
                      </span>
                    )}
                  </>
                )}
              </>
            )}
          </NavLink>
        ))}

        <div className="my-5 border-t border-[#2D2D43]" />

        {(!sidebarCollapsed || isMobile) && (
          <div className="mb-4 px-3">
            <span className="text-[11px] font-semibold uppercase tracking-wider text-[#565674]">
              System
            </span>
          </div>
        )}
        {systemNav.map((item) => (
          <NavLink
            key={item.name}
            to={item.href}
            onClick={() => isMobile && setSidebarOpen(false)}
            className={({ isActive }) =>
              clsx(
                'group flex items-center rounded-lg px-3 py-2.5 text-[13px] font-medium transition-all duration-200',
                isActive
                  ? 'bg-[#1B1B29] text-white'
                  : 'text-[#9D9DA6] hover:bg-[#1B1B29] hover:text-white',
                sidebarCollapsed && !isMobile && 'justify-center px-2'
              )
            }
          >
            {({ isActive }) => (
              <>
                <item.icon 
                  className={clsx(
                    'h-[18px] w-[18px] flex-shrink-0 transition-colors',
                    !sidebarCollapsed && !isMobile && 'mr-3',
                    isActive ? 'text-primary-500' : 'text-[#565674] group-hover:text-primary-400'
                  )} 
                />
                {(!sidebarCollapsed || isMobile) && item.name}
              </>
            )}
          </NavLink>
        ))}
      </nav>

      {/* Status Card */}
      {(!sidebarCollapsed || isMobile) && (
        <div className="border-t border-[#2D2D43] p-4">
          <div className="rounded-lg bg-gradient-to-br from-[#1B1B29] to-[#2D2D43] p-4">
            <div className="flex items-center gap-3 mb-3">
              <div className="flex h-8 w-8 items-center justify-center rounded-full bg-success/20">
                <Activity className="h-4 w-4 text-success" />
              </div>
              <div>
                <p className="text-xs font-medium text-white">System Status</p>
                <p className="text-[10px] text-[#565674]">All services running</p>
              </div>
            </div>
            <div className="space-y-2">
              <div className="flex items-center justify-between text-[11px]">
                <span className="text-[#565674]">API</span>
                <span className="text-success">● Online</span>
              </div>
              <div className="flex items-center justify-between text-[11px]">
                <span className="text-[#565674]">Database</span>
                <span className="text-success">● Online</span>
              </div>
              <div className="flex items-center justify-between text-[11px]">
                <span className="text-[#565674]">Poller</span>
                <span className="text-success">● Running</span>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  )

  return (
    <>
      {/* Desktop Sidebar */}
      <aside
        className={clsx(
          'hidden lg:flex flex-col bg-[#1E1E2D] transition-all duration-300',
          sidebarCollapsed ? 'w-[70px]' : 'w-[265px]'
        )}
      >
        <SidebarContent />
      </aside>

      {/* Mobile Sidebar */}
      <aside
        className={clsx(
          'fixed inset-y-0 left-0 z-50 flex w-[265px] flex-col bg-[#1E1E2D] transition-transform duration-300 lg:hidden',
          sidebarOpen ? 'translate-x-0' : '-translate-x-full'
        )}
      >
        <SidebarContent isMobile />
      </aside>
    </>
  )
}
