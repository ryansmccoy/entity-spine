import { useState, useRef, useEffect } from 'react'
import { useLocation } from 'react-router-dom'
import { useLayout } from '../../layouts/AdminLayout'
import {
  Menu,
  Search,
  Bell,
  Sun,
  Moon,
  User,
  Settings,
  LogOut,
  ChevronDown,
  X,
  Clock,
  FileText,
  RefreshCw,
  HelpCircle,
  MessageSquare,
} from 'lucide-react'
import { clsx } from 'clsx'

// Sample notifications
const sampleNotifications = [
  {
    id: '1',
    title: 'New 10-K Filing',
    message: 'Apple Inc. has filed a new 10-K report',
    time: '5 min ago',
    read: false,
    type: 'filing',
  },
  {
    id: '2',
    title: 'Feed Updated',
    message: 'SEC Latest Filings feed has been refreshed',
    time: '1 hour ago',
    read: false,
    type: 'feed',
  },
  {
    id: '3',
    title: 'System Update',
    message: 'Capture Spine Basic has been updated to v0.1.1',
    time: '2 hours ago',
    read: true,
    type: 'system',
  },
]

// Page titles
const pageTitles: Record<string, { title: string; description: string }> = {
  '/dashboard': { title: 'Dashboard', description: 'Welcome back! Here\'s what\'s happening with your feeds.' },
  '/newsfeed': { title: 'Newsfeed', description: 'Browse and capture SEC filings in real-time.' },
  '/feeds': { title: 'Feed Management', description: 'Configure and manage your feed sources.' },
  '/notifications': { title: 'Notifications', description: 'Stay updated with the latest alerts.' },
  '/settings': { title: 'Settings', description: 'Customize your preferences and account.' },
}

export function Header() {
  const location = useLocation()
  const { setSidebarOpen, darkMode, setDarkMode } = useLayout()
  const [searchOpen, setSearchOpen] = useState(false)
  const [searchQuery, setSearchQuery] = useState('')
  const [notificationsOpen, setNotificationsOpen] = useState(false)
  const [userMenuOpen, setUserMenuOpen] = useState(false)
  const [notifications, setNotifications] = useState(sampleNotifications)

  const searchRef = useRef<HTMLInputElement>(null)
  const notificationsRef = useRef<HTMLDivElement>(null)
  const userMenuRef = useRef<HTMLDivElement>(null)

  const unreadCount = notifications.filter((n) => !n.read).length
  const pageInfo = pageTitles[location.pathname] || { title: 'Page', description: '' }

  // Close dropdowns on outside click
  useEffect(() => {
    function handleClickOutside(event: MouseEvent) {
      if (notificationsRef.current && !notificationsRef.current.contains(event.target as Node)) {
        setNotificationsOpen(false)
      }
      if (userMenuRef.current && !userMenuRef.current.contains(event.target as Node)) {
        setUserMenuOpen(false)
      }
    }
    document.addEventListener('mousedown', handleClickOutside)
    return () => document.removeEventListener('mousedown', handleClickOutside)
  }, [])

  // Focus search on open
  useEffect(() => {
    if (searchOpen && searchRef.current) {
      searchRef.current.focus()
    }
  }, [searchOpen])

  const markAllRead = () => {
    setNotifications(notifications.map((n) => ({ ...n, read: true })))
  }

  return (
    <header className="sticky top-0 z-30 bg-white dark:bg-[#1E1E2D] border-b border-gray-200 dark:border-[#2D2D43]">
      <div className="flex h-[70px] items-center justify-between px-4 lg:px-8">
        {/* Left side */}
        <div className="flex items-center gap-4">
          {/* Mobile menu button */}
          <button
            onClick={() => setSidebarOpen(true)}
            className="flex h-10 w-10 items-center justify-center rounded-lg text-gray-500 hover:bg-gray-100 dark:text-gray-400 dark:hover:bg-[#2D2D43] lg:hidden"
          >
            <Menu className="h-5 w-5" />
          </button>

          {/* Page Title */}
          <div className="hidden sm:block">
            <h1 className="text-lg font-semibold text-gray-900 dark:text-white">{pageInfo.title}</h1>
            <p className="text-xs text-gray-500 dark:text-[#565674]">{pageInfo.description}</p>
          </div>
        </div>

        {/* Right side */}
        <div className="flex items-center gap-1 sm:gap-2">
          {/* Search */}
          <div className="relative hidden md:block">
            <div className="relative">
              <Search className="absolute left-3.5 top-1/2 h-4 w-4 -translate-y-1/2 text-gray-400" />
              <input
                type="text"
                placeholder="Search..."
                className="h-10 w-[200px] lg:w-[280px] rounded-lg border border-gray-200 bg-gray-50 pl-10 pr-4 text-sm text-gray-900 placeholder-gray-400 focus:border-primary-500 focus:bg-white focus:outline-none focus:ring-1 focus:ring-primary-500 dark:border-[#2D2D43] dark:bg-[#1B1B29] dark:text-white dark:placeholder-[#565674] dark:focus:border-primary-500"
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
              />
              {searchQuery && (
                <button
                  onClick={() => setSearchQuery('')}
                  className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-400 hover:text-gray-600"
                >
                  <X className="h-3.5 w-3.5" />
                </button>
              )}
            </div>
          </div>

          {/* Mobile Search Toggle */}
          <button
            onClick={() => setSearchOpen(!searchOpen)}
            className="flex h-10 w-10 items-center justify-center rounded-lg text-gray-500 hover:bg-gray-100 dark:text-gray-400 dark:hover:bg-[#2D2D43] md:hidden"
          >
            <Search className="h-5 w-5" />
          </button>

          {/* Help */}
          <button
            className="hidden sm:flex h-10 w-10 items-center justify-center rounded-lg text-gray-500 hover:bg-gray-100 dark:text-gray-400 dark:hover:bg-[#2D2D43]"
            title="Help & Documentation"
          >
            <HelpCircle className="h-5 w-5" />
          </button>

          {/* Dark mode toggle */}
          <button
            onClick={() => setDarkMode(!darkMode)}
            className="flex h-10 w-10 items-center justify-center rounded-lg text-gray-500 hover:bg-gray-100 dark:text-gray-400 dark:hover:bg-[#2D2D43]"
            title={darkMode ? 'Switch to light mode' : 'Switch to dark mode'}
          >
            {darkMode ? <Sun className="h-5 w-5" /> : <Moon className="h-5 w-5" />}
          </button>

          {/* Notifications */}
          <div className="relative" ref={notificationsRef}>
            <button
              onClick={() => setNotificationsOpen(!notificationsOpen)}
              className="relative flex h-10 w-10 items-center justify-center rounded-lg text-gray-500 hover:bg-gray-100 dark:text-gray-400 dark:hover:bg-[#2D2D43]"
            >
              <Bell className="h-5 w-5" />
              {unreadCount > 0 && (
                <span className="absolute right-1 top-1 flex h-5 w-5 items-center justify-center rounded-full bg-danger text-[10px] font-bold text-white">
                  {unreadCount}
                </span>
              )}
            </button>

            {/* Notifications Dropdown */}
            {notificationsOpen && (
              <div className="absolute right-0 mt-2 w-[340px] rounded-xl bg-white shadow-xl ring-1 ring-black/5 dark:bg-[#1E1E2D] dark:ring-white/10 animate-in">
                <div className="flex items-center justify-between border-b border-gray-100 dark:border-[#2D2D43] px-5 py-4">
                  <div>
                    <h3 className="text-sm font-semibold text-gray-900 dark:text-white">Notifications</h3>
                    <p className="text-xs text-gray-500 dark:text-[#565674]">{unreadCount} unread</p>
                  </div>
                  {unreadCount > 0 && (
                    <button
                      onClick={markAllRead}
                      className="text-xs font-medium text-primary-600 hover:text-primary-700"
                    >
                      Mark all read
                    </button>
                  )}
                </div>
                <div className="max-h-[360px] overflow-y-auto">
                  {notifications.length === 0 ? (
                    <div className="px-5 py-8 text-center">
                      <Bell className="mx-auto h-10 w-10 text-gray-300 dark:text-[#565674]" />
                      <p className="mt-2 text-sm text-gray-500 dark:text-[#565674]">No notifications</p>
                    </div>
                  ) : (
                    notifications.map((notification) => (
                      <div
                        key={notification.id}
                        className={clsx(
                          'flex gap-3 border-b border-gray-100 dark:border-[#2D2D43] px-5 py-4 hover:bg-gray-50 dark:hover:bg-[#1B1B29] cursor-pointer transition-colors',
                          !notification.read && 'bg-primary-50/50 dark:bg-primary-900/10'
                        )}
                      >
                        <div
                          className={clsx(
                            'flex h-10 w-10 items-center justify-center rounded-lg flex-shrink-0',
                            notification.type === 'filing' && 'bg-primary-100 text-primary-600 dark:bg-primary-900/30 dark:text-primary-400',
                            notification.type === 'feed' && 'bg-success-light text-success dark:bg-success/20',
                            notification.type === 'system' && 'bg-gray-100 text-gray-600 dark:bg-[#2D2D43] dark:text-gray-400'
                          )}
                        >
                          {notification.type === 'filing' && <FileText className="h-5 w-5" />}
                          {notification.type === 'feed' && <RefreshCw className="h-5 w-5" />}
                          {notification.type === 'system' && <Bell className="h-5 w-5" />}
                        </div>
                        <div className="flex-1 min-w-0">
                          <div className="flex items-start justify-between gap-2">
                            <p className="text-sm font-medium text-gray-900 dark:text-white">{notification.title}</p>
                            {!notification.read && (
                              <div className="h-2 w-2 rounded-full bg-primary-500 flex-shrink-0 mt-1.5" />
                            )}
                          </div>
                          <p className="text-xs text-gray-500 dark:text-[#565674] truncate mt-0.5">
                            {notification.message}
                          </p>
                          <div className="mt-1.5 flex items-center gap-1 text-[11px] text-gray-400 dark:text-[#565674]">
                            <Clock className="h-3 w-3" />
                            {notification.time}
                          </div>
                        </div>
                      </div>
                    ))
                  )}
                </div>
                <div className="border-t border-gray-100 dark:border-[#2D2D43] p-3">
                  <a
                    href="/notifications"
                    className="block rounded-lg py-2 text-center text-xs font-medium text-primary-600 hover:bg-gray-50 dark:hover:bg-[#1B1B29]"
                  >
                    View all notifications
                  </a>
                </div>
              </div>
            )}
          </div>

          {/* Divider */}
          <div className="hidden h-8 w-px bg-gray-200 dark:bg-[#2D2D43] sm:block mx-2" />

          {/* User Menu */}
          <div className="relative" ref={userMenuRef}>
            <button
              onClick={() => setUserMenuOpen(!userMenuOpen)}
              className="flex items-center gap-2 rounded-lg py-1.5 px-2 hover:bg-gray-100 dark:hover:bg-[#2D2D43] transition-colors"
            >
              <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-gradient-to-br from-primary-500 to-primary-600 text-sm font-semibold text-white">
                U
              </div>
              <div className="hidden md:block text-left">
                <p className="text-sm font-medium text-gray-900 dark:text-white">User</p>
                <p className="text-[11px] text-gray-500 dark:text-[#565674]">Administrator</p>
              </div>
              <ChevronDown className="hidden md:block h-4 w-4 text-gray-400" />
            </button>

            {/* User Menu Dropdown */}
            {userMenuOpen && (
              <div className="absolute right-0 mt-2 w-[220px] rounded-xl bg-white shadow-xl ring-1 ring-black/5 dark:bg-[#1E1E2D] dark:ring-white/10 animate-in">
                <div className="border-b border-gray-100 dark:border-[#2D2D43] px-5 py-4">
                  <p className="text-sm font-medium text-gray-900 dark:text-white">User</p>
                  <p className="text-xs text-gray-500 dark:text-[#565674]">user@example.com</p>
                </div>
                <div className="p-2">
                  <a
                    href="/settings"
                    className="flex items-center gap-3 rounded-lg px-3 py-2.5 text-sm text-gray-700 hover:bg-gray-50 dark:text-gray-300 dark:hover:bg-[#1B1B29]"
                  >
                    <User className="h-4 w-4 text-gray-400" />
                    Profile
                  </a>
                  <a
                    href="/settings"
                    className="flex items-center gap-3 rounded-lg px-3 py-2.5 text-sm text-gray-700 hover:bg-gray-50 dark:text-gray-300 dark:hover:bg-[#1B1B29]"
                  >
                    <Settings className="h-4 w-4 text-gray-400" />
                    Settings
                  </a>
                  <a
                    href="#"
                    className="flex items-center gap-3 rounded-lg px-3 py-2.5 text-sm text-gray-700 hover:bg-gray-50 dark:text-gray-300 dark:hover:bg-[#1B1B29]"
                  >
                    <MessageSquare className="h-4 w-4 text-gray-400" />
                    Feedback
                  </a>
                </div>
                <div className="border-t border-gray-100 dark:border-[#2D2D43] p-2">
                  <button className="flex w-full items-center gap-3 rounded-lg px-3 py-2.5 text-sm text-danger hover:bg-danger-light dark:hover:bg-danger/10">
                    <LogOut className="h-4 w-4" />
                    Sign out
                  </button>
                </div>
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Mobile Search Bar */}
      {searchOpen && (
        <div className="border-t border-gray-200 dark:border-[#2D2D43] bg-white dark:bg-[#1E1E2D] px-4 py-3 md:hidden animate-in">
          <div className="relative">
            <Search className="absolute left-3.5 top-1/2 h-4 w-4 -translate-y-1/2 text-gray-400" />
            <input
              ref={searchRef}
              type="text"
              placeholder="Search filings, feeds..."
              className="h-10 w-full rounded-lg border border-gray-200 bg-gray-50 pl-10 pr-10 text-sm text-gray-900 placeholder-gray-400 focus:border-primary-500 focus:bg-white focus:outline-none focus:ring-1 focus:ring-primary-500 dark:border-[#2D2D43] dark:bg-[#1B1B29] dark:text-white dark:placeholder-[#565674] dark:focus:border-primary-500"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
            />
            <button
              onClick={() => {
                setSearchOpen(false)
                setSearchQuery('')
              }}
              className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-400 hover:text-gray-600"
            >
              <X className="h-4 w-4" />
            </button>
          </div>
        </div>
      )}
    </header>
  )
}
