import { useState } from 'react'
import {
  Bell,
  FileText,
  AlertCircle,
  CheckCircle2,
  Info,
  Clock,
  Trash2,
  Check,
  X,
  Filter,
} from 'lucide-react'
import { clsx } from 'clsx'

// Sample notifications
const sampleNotifications = [
  {
    id: '1',
    title: 'New 10-K Filing Detected',
    message: 'Apple Inc. (AAPL) has filed a new 10-K annual report with the SEC.',
    time: '2025-01-27T10:30:00Z',
    type: 'filing',
    read: false,
  },
  {
    id: '2',
    title: 'Feed Sync Complete',
    message: 'SEC Latest Filings feed has been successfully synchronized. 47 new items found.',
    time: '2025-01-27T10:15:00Z',
    type: 'success',
    read: false,
  },
  {
    id: '3',
    title: 'New 8-K Filing Detected',
    message: 'Microsoft Corporation (MSFT) has filed a new 8-K current report.',
    time: '2025-01-27T09:45:00Z',
    type: 'filing',
    read: false,
  },
  {
    id: '4',
    title: 'Feed Error',
    message: 'SEC Form 4 feed encountered an error: Connection timeout. Retrying in 5 minutes.',
    time: '2025-01-27T08:30:00Z',
    type: 'error',
    read: true,
  },
  {
    id: '5',
    title: 'System Update Available',
    message: 'Capture Spine Basic v0.1.1 is now available. View the changelog for details.',
    time: '2025-01-26T14:00:00Z',
    type: 'info',
    read: true,
  },
  {
    id: '6',
    title: 'Feed Sync Complete',
    message: 'SEC Form 10-K feed has been successfully synchronized. 12 new items found.',
    time: '2025-01-26T10:00:00Z',
    type: 'success',
    read: true,
  },
  {
    id: '7',
    title: 'New 10-Q Filing Detected',
    message: 'Tesla, Inc. (TSLA) has filed a new 10-Q quarterly report.',
    time: '2025-01-25T16:30:00Z',
    type: 'filing',
    read: true,
  },
]

type FilterType = 'all' | 'unread' | 'filing' | 'error'

const typeIcons = {
  filing: FileText,
  success: CheckCircle2,
  error: AlertCircle,
  info: Info,
}

const typeColors = {
  filing: 'bg-primary-100 text-primary-600 dark:bg-primary-900/30 dark:text-primary-400',
  success: 'bg-success-light text-success dark:bg-success/20',
  error: 'bg-danger-light text-danger dark:bg-danger/20',
  info: 'bg-info-light text-info dark:bg-info/20',
}

export function NotificationsPage() {
  const [notifications, setNotifications] = useState(sampleNotifications)
  const [filter, setFilter] = useState<FilterType>('all')

  const unreadCount = notifications.filter((n) => !n.read).length

  const filteredNotifications = notifications.filter((n) => {
    if (filter === 'all') return true
    if (filter === 'unread') return !n.read
    return n.type === filter
  })

  const markAsRead = (id: string) => {
    setNotifications((prev) =>
      prev.map((n) => (n.id === id ? { ...n, read: true } : n))
    )
  }

  const markAllAsRead = () => {
    setNotifications((prev) => prev.map((n) => ({ ...n, read: true })))
  }

  const deleteNotification = (id: string) => {
    setNotifications((prev) => prev.filter((n) => n.id !== id))
  }

  const clearAll = () => {
    setNotifications([])
  }

  const formatTime = (dateStr: string) => {
    const date = new Date(dateStr)
    const now = new Date()
    const diff = now.getTime() - date.getTime()
    const mins = Math.floor(diff / (1000 * 60))
    
    if (mins < 1) return 'Just now'
    if (mins < 60) return `${mins} min ago`
    const hours = Math.floor(mins / 60)
    if (hours < 24) return `${hours}h ago`
    const days = Math.floor(hours / 24)
    if (days < 7) return `${days}d ago`
    return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' })
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h2 className="text-xl font-bold text-gray-900 dark:text-white">Notifications</h2>
          <p className="text-sm text-gray-500 dark:text-[#565674]">
            {unreadCount > 0 ? `You have ${unreadCount} unread notifications` : 'All caught up!'}
          </p>
        </div>
        <div className="flex items-center gap-2">
          {unreadCount > 0 && (
            <button
              onClick={markAllAsRead}
              className="btn btn-secondary flex items-center gap-2 text-sm"
            >
              <Check className="h-4 w-4" />
              Mark all read
            </button>
          )}
          {notifications.length > 0 && (
            <button
              onClick={clearAll}
              className="btn bg-danger-light text-danger hover:bg-danger hover:text-white flex items-center gap-2 text-sm"
            >
              <Trash2 className="h-4 w-4" />
              Clear all
            </button>
          )}
        </div>
      </div>

      {/* Filters */}
      <div className="card rounded-xl">
        <div className="flex items-center gap-2 p-4 border-b border-gray-100 dark:border-[#2D2D43] overflow-x-auto">
          <Filter className="h-4 w-4 text-gray-400 flex-shrink-0" />
          {[
            { id: 'all', label: 'All' },
            { id: 'unread', label: 'Unread' },
            { id: 'filing', label: 'Filings' },
            { id: 'error', label: 'Errors' },
          ].map((f) => (
            <button
              key={f.id}
              onClick={() => setFilter(f.id as FilterType)}
              className={clsx(
                'rounded-full px-3 py-1.5 text-xs font-medium transition-colors whitespace-nowrap',
                filter === f.id
                  ? 'bg-primary-600 text-white'
                  : 'bg-gray-100 text-gray-600 hover:bg-gray-200 dark:bg-[#2D2D43] dark:text-gray-400 dark:hover:bg-[#3D3D53]'
              )}
            >
              {f.label}
              {f.id === 'unread' && unreadCount > 0 && (
                <span className="ml-1.5 rounded-full bg-white/20 px-1.5 text-[10px]">{unreadCount}</span>
              )}
            </button>
          ))}
        </div>

        {/* Notifications List */}
        {filteredNotifications.length === 0 ? (
          <div className="flex flex-col items-center justify-center py-16">
            <div className="flex h-16 w-16 items-center justify-center rounded-full bg-gray-100 dark:bg-[#2D2D43] mb-4">
              <Bell className="h-8 w-8 text-gray-400" />
            </div>
            <h3 className="text-base font-semibold text-gray-900 dark:text-white mb-1">No notifications</h3>
            <p className="text-sm text-gray-500 dark:text-[#565674]">
              {filter === 'all' ? "You're all caught up!" : `No ${filter} notifications`}
            </p>
          </div>
        ) : (
          <div className="divide-y divide-gray-100 dark:divide-[#2D2D43]">
            {filteredNotifications.map((notification) => {
              const Icon = typeIcons[notification.type as keyof typeof typeIcons] || Bell
              const colorClass = typeColors[notification.type as keyof typeof typeColors]

              return (
                <div
                  key={notification.id}
                  className={clsx(
                    'flex items-start gap-4 px-6 py-4 transition-colors cursor-pointer',
                    !notification.read
                      ? 'bg-primary-50/50 hover:bg-primary-50 dark:bg-primary-900/10 dark:hover:bg-primary-900/20'
                      : 'hover:bg-gray-50 dark:hover:bg-[#1B1B29]'
                  )}
                  onClick={() => markAsRead(notification.id)}
                >
                  <div className={clsx('flex h-10 w-10 items-center justify-center rounded-lg flex-shrink-0', colorClass)}>
                    <Icon className="h-5 w-5" />
                  </div>
                  <div className="flex-1 min-w-0">
                    <div className="flex items-start justify-between gap-3">
                      <div>
                        <div className="flex items-center gap-2">
                          <h4 className="text-sm font-medium text-gray-900 dark:text-white">{notification.title}</h4>
                          {!notification.read && (
                            <span className="h-2 w-2 rounded-full bg-primary-500 flex-shrink-0" />
                          )}
                        </div>
                        <p className="mt-1 text-sm text-gray-600 dark:text-gray-400">{notification.message}</p>
                        <div className="mt-2 flex items-center gap-1 text-xs text-gray-400">
                          <Clock className="h-3 w-3" />
                          {formatTime(notification.time)}
                        </div>
                      </div>
                      <button
                        onClick={(e) => {
                          e.stopPropagation()
                          deleteNotification(notification.id)
                        }}
                        className="flex h-8 w-8 items-center justify-center rounded-lg text-gray-400 hover:bg-gray-100 hover:text-gray-600 dark:hover:bg-[#2D2D43] flex-shrink-0 opacity-0 group-hover:opacity-100 transition-opacity"
                        title="Delete"
                      >
                        <X className="h-4 w-4" />
                      </button>
                    </div>
                  </div>
                </div>
              )
            })}
          </div>
        )}
      </div>
    </div>
  )
}
