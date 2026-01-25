import { useState } from 'react'
import {
  Rss,
  Plus,
  Search,
  MoreVertical,
  Play,
  Pause,
  RefreshCw,
  Trash2,
  Edit3,
  ExternalLink,
  Clock,
  CheckCircle2,
  AlertCircle,
  X,
  Save,
} from 'lucide-react'
import { clsx } from 'clsx'

// Sample feeds data
const sampleFeeds = [
  {
    id: 'sec-latest',
    name: 'SEC Latest Filings',
    url: 'https://www.sec.gov/cgi-bin/browse-edgar?action=getcurrent&type=&company=&dateb=&owner=include&count=100&output=atom',
    status: 'active',
    lastSync: '2025-01-27T10:30:00Z',
    itemCount: 1250,
    errorCount: 0,
    syncInterval: 300,
  },
  {
    id: 'sec-10k',
    name: 'SEC Form 10-K',
    url: 'https://www.sec.gov/cgi-bin/browse-edgar?action=getcurrent&type=10-K&company=&dateb=&owner=include&count=100&output=atom',
    status: 'active',
    lastSync: '2025-01-27T10:25:00Z',
    itemCount: 423,
    errorCount: 0,
    syncInterval: 600,
  },
  {
    id: 'sec-8k',
    name: 'SEC Form 8-K',
    url: 'https://www.sec.gov/cgi-bin/browse-edgar?action=getcurrent&type=8-K&company=&dateb=&owner=include&count=100&output=atom',
    status: 'active',
    lastSync: '2025-01-27T10:28:00Z',
    itemCount: 892,
    errorCount: 0,
    syncInterval: 300,
  },
  {
    id: 'sec-10q',
    name: 'SEC Form 10-Q',
    url: 'https://www.sec.gov/cgi-bin/browse-edgar?action=getcurrent&type=10-Q&company=&dateb=&owner=include&count=100&output=atom',
    status: 'active',
    lastSync: '2025-01-27T10:20:00Z',
    itemCount: 567,
    errorCount: 0,
    syncInterval: 600,
  },
  {
    id: 'sec-def14a',
    name: 'SEC Proxy Statements',
    url: 'https://www.sec.gov/cgi-bin/browse-edgar?action=getcurrent&type=DEF+14A&company=&dateb=&owner=include&count=100&output=atom',
    status: 'paused',
    lastSync: '2025-01-27T08:00:00Z',
    itemCount: 234,
    errorCount: 0,
    syncInterval: 900,
  },
  {
    id: 'sec-form4',
    name: 'SEC Form 4 (Insider)',
    url: 'https://www.sec.gov/cgi-bin/browse-edgar?action=getcurrent&type=4&company=&dateb=&owner=include&count=100&output=atom',
    status: 'error',
    lastSync: '2025-01-27T06:00:00Z',
    itemCount: 2341,
    errorCount: 3,
    syncInterval: 300,
  },
]

type Feed = typeof sampleFeeds[0]

export function FeedsPage() {
  const [feeds, setFeeds] = useState(sampleFeeds)
  const [searchQuery, setSearchQuery] = useState('')
  const [selectedFeed, setSelectedFeed] = useState<Feed | null>(null)
  const [showAddModal, setShowAddModal] = useState(false)
  const [menuOpenId, setMenuOpenId] = useState<string | null>(null)

  const filteredFeeds = feeds.filter((feed) =>
    feed.name.toLowerCase().includes(searchQuery.toLowerCase())
  )

  const toggleFeedStatus = (id: string) => {
    setFeeds((prev) =>
      prev.map((feed) =>
        feed.id === id
          ? { ...feed, status: feed.status === 'active' ? 'paused' : 'active' }
          : feed
      )
    )
  }

  const formatSyncTime = (dateStr: string) => {
    const date = new Date(dateStr)
    const now = new Date()
    const diff = now.getTime() - date.getTime()
    const mins = Math.floor(diff / (1000 * 60))
    if (mins < 1) return 'Just now'
    if (mins < 60) return `${mins} min ago`
    const hours = Math.floor(mins / 60)
    if (hours < 24) return `${hours} hour${hours > 1 ? 's' : ''} ago`
    return date.toLocaleDateString()
  }

  const formatInterval = (seconds: number) => {
    if (seconds < 60) return `${seconds}s`
    const mins = Math.floor(seconds / 60)
    return `${mins} min`
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h2 className="text-xl font-bold text-gray-900 dark:text-white">Feed Management</h2>
          <p className="text-sm text-gray-500 dark:text-[#565674]">
            Configure and manage your SEC filing feed sources
          </p>
        </div>
        <button
          onClick={() => setShowAddModal(true)}
          className="btn btn-primary flex items-center gap-2"
        >
          <Plus className="h-4 w-4" />
          Add Feed
        </button>
      </div>

      {/* Stats Cards */}
      <div className="grid gap-4 sm:grid-cols-3">
        <div className="card rounded-xl p-5">
          <div className="flex items-center gap-4">
            <div className="flex h-12 w-12 items-center justify-center rounded-lg bg-success-light dark:bg-success/20">
              <CheckCircle2 className="h-6 w-6 text-success" />
            </div>
            <div>
              <p className="text-2xl font-bold text-gray-900 dark:text-white">
                {feeds.filter((f) => f.status === 'active').length}
              </p>
              <p className="text-sm text-gray-500 dark:text-[#565674]">Active Feeds</p>
            </div>
          </div>
        </div>
        <div className="card rounded-xl p-5">
          <div className="flex items-center gap-4">
            <div className="flex h-12 w-12 items-center justify-center rounded-lg bg-warning-light dark:bg-warning/20">
              <Pause className="h-6 w-6 text-warning" />
            </div>
            <div>
              <p className="text-2xl font-bold text-gray-900 dark:text-white">
                {feeds.filter((f) => f.status === 'paused').length}
              </p>
              <p className="text-sm text-gray-500 dark:text-[#565674]">Paused Feeds</p>
            </div>
          </div>
        </div>
        <div className="card rounded-xl p-5">
          <div className="flex items-center gap-4">
            <div className="flex h-12 w-12 items-center justify-center rounded-lg bg-danger-light dark:bg-danger/20">
              <AlertCircle className="h-6 w-6 text-danger" />
            </div>
            <div>
              <p className="text-2xl font-bold text-gray-900 dark:text-white">
                {feeds.filter((f) => f.status === 'error').length}
              </p>
              <p className="text-sm text-gray-500 dark:text-[#565674]">Error Feeds</p>
            </div>
          </div>
        </div>
      </div>

      {/* Feeds Table */}
      <div className="card rounded-xl">
        {/* Table Header */}
        <div className="flex items-center justify-between border-b border-gray-100 dark:border-[#2D2D43] px-6 py-4">
          <div className="relative">
            <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-gray-400" />
            <input
              type="text"
              placeholder="Search feeds..."
              className="h-9 w-[250px] rounded-lg border border-gray-200 bg-gray-50 pl-9 pr-3 text-sm focus:border-primary-500 focus:bg-white focus:outline-none dark:border-[#2D2D43] dark:bg-[#1B1B29] dark:text-white"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
            />
          </div>
          <button className="flex items-center gap-2 text-sm font-medium text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-300">
            <RefreshCw className="h-4 w-4" />
            Refresh All
          </button>
        </div>

        {/* Table */}
        <div className="overflow-x-auto">
          <table className="w-full">
            <thead>
              <tr className="border-b border-gray-100 dark:border-[#2D2D43]">
                <th className="px-6 py-3 text-left text-xs font-semibold uppercase tracking-wider text-gray-500 dark:text-[#565674]">
                  Feed Name
                </th>
                <th className="px-6 py-3 text-left text-xs font-semibold uppercase tracking-wider text-gray-500 dark:text-[#565674]">
                  Status
                </th>
                <th className="px-6 py-3 text-left text-xs font-semibold uppercase tracking-wider text-gray-500 dark:text-[#565674]">
                  Items
                </th>
                <th className="px-6 py-3 text-left text-xs font-semibold uppercase tracking-wider text-gray-500 dark:text-[#565674]">
                  Last Sync
                </th>
                <th className="px-6 py-3 text-left text-xs font-semibold uppercase tracking-wider text-gray-500 dark:text-[#565674]">
                  Interval
                </th>
                <th className="px-6 py-3 text-right text-xs font-semibold uppercase tracking-wider text-gray-500 dark:text-[#565674]">
                  Actions
                </th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100 dark:divide-[#2D2D43]">
              {filteredFeeds.map((feed) => (
                <tr
                  key={feed.id}
                  className="hover:bg-gray-50 dark:hover:bg-[#1B1B29] transition-colors"
                >
                  <td className="px-6 py-4">
                    <div className="flex items-center gap-3">
                      <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-primary-100 dark:bg-primary-900/30">
                        <Rss className="h-5 w-5 text-primary-600" />
                      </div>
                      <div>
                        <p className="text-sm font-medium text-gray-900 dark:text-white">{feed.name}</p>
                        <p className="text-xs text-gray-400 truncate max-w-[300px]">{feed.url}</p>
                      </div>
                    </div>
                  </td>
                  <td className="px-6 py-4">
                    <span
                      className={clsx(
                        'inline-flex items-center gap-1.5 rounded-full px-2.5 py-1 text-xs font-medium',
                        feed.status === 'active' && 'bg-success-light text-success-dark dark:bg-success/20 dark:text-success',
                        feed.status === 'paused' && 'bg-warning-light text-warning-dark dark:bg-warning/20 dark:text-warning',
                        feed.status === 'error' && 'bg-danger-light text-danger-dark dark:bg-danger/20 dark:text-danger'
                      )}
                    >
                      <span
                        className={clsx(
                          'h-1.5 w-1.5 rounded-full',
                          feed.status === 'active' && 'bg-success',
                          feed.status === 'paused' && 'bg-warning',
                          feed.status === 'error' && 'bg-danger'
                        )}
                      />
                      {feed.status.charAt(0).toUpperCase() + feed.status.slice(1)}
                    </span>
                  </td>
                  <td className="px-6 py-4">
                    <span className="text-sm text-gray-900 dark:text-white">{feed.itemCount.toLocaleString()}</span>
                  </td>
                  <td className="px-6 py-4">
                    <div className="flex items-center gap-1.5 text-sm text-gray-500 dark:text-gray-400">
                      <Clock className="h-3.5 w-3.5" />
                      {formatSyncTime(feed.lastSync)}
                    </div>
                  </td>
                  <td className="px-6 py-4">
                    <span className="text-sm text-gray-500 dark:text-gray-400">
                      {formatInterval(feed.syncInterval)}
                    </span>
                  </td>
                  <td className="px-6 py-4">
                    <div className="flex items-center justify-end gap-1">
                      <button
                        onClick={() => toggleFeedStatus(feed.id)}
                        className={clsx(
                          'flex h-8 w-8 items-center justify-center rounded-lg transition-colors',
                          feed.status === 'active'
                            ? 'text-warning hover:bg-warning-light dark:hover:bg-warning/20'
                            : 'text-success hover:bg-success-light dark:hover:bg-success/20'
                        )}
                        title={feed.status === 'active' ? 'Pause' : 'Resume'}
                      >
                        {feed.status === 'active' ? <Pause className="h-4 w-4" /> : <Play className="h-4 w-4" />}
                      </button>
                      <button
                        className="flex h-8 w-8 items-center justify-center rounded-lg text-gray-400 hover:bg-gray-100 hover:text-gray-600 dark:hover:bg-[#2D2D43]"
                        title="Sync Now"
                      >
                        <RefreshCw className="h-4 w-4" />
                      </button>
                      <button
                        onClick={() => setSelectedFeed(feed)}
                        className="flex h-8 w-8 items-center justify-center rounded-lg text-gray-400 hover:bg-gray-100 hover:text-gray-600 dark:hover:bg-[#2D2D43]"
                        title="Edit"
                      >
                        <Edit3 className="h-4 w-4" />
                      </button>
                      <div className="relative">
                        <button
                          onClick={() => setMenuOpenId(menuOpenId === feed.id ? null : feed.id)}
                          className="flex h-8 w-8 items-center justify-center rounded-lg text-gray-400 hover:bg-gray-100 hover:text-gray-600 dark:hover:bg-[#2D2D43]"
                        >
                          <MoreVertical className="h-4 w-4" />
                        </button>
                        {menuOpenId === feed.id && (
                          <div className="absolute right-0 top-full z-10 mt-1 w-40 rounded-lg bg-white shadow-lg ring-1 ring-black/5 dark:bg-[#1E1E2D] dark:ring-white/10">
                            <div className="p-1">
                              <button className="flex w-full items-center gap-2 rounded px-3 py-2 text-sm text-gray-700 hover:bg-gray-50 dark:text-gray-300 dark:hover:bg-[#1B1B29]">
                                <ExternalLink className="h-4 w-4" />
                                Open URL
                              </button>
                              <button className="flex w-full items-center gap-2 rounded px-3 py-2 text-sm text-danger hover:bg-danger-light dark:hover:bg-danger/10">
                                <Trash2 className="h-4 w-4" />
                                Delete
                              </button>
                            </div>
                          </div>
                        )}
                      </div>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* Edit Feed Modal */}
      {selectedFeed && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm">
          <div className="w-full max-w-lg rounded-xl bg-white p-6 shadow-xl dark:bg-[#1E1E2D]">
            <div className="flex items-center justify-between mb-6">
              <h3 className="text-lg font-semibold text-gray-900 dark:text-white">Edit Feed</h3>
              <button
                onClick={() => setSelectedFeed(null)}
                className="flex h-8 w-8 items-center justify-center rounded-lg text-gray-400 hover:bg-gray-100 dark:hover:bg-[#2D2D43]"
              >
                <X className="h-5 w-5" />
              </button>
            </div>
            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                  Feed Name
                </label>
                <input
                  type="text"
                  defaultValue={selectedFeed.name}
                  className="w-full rounded-lg border border-gray-200 px-4 py-2.5 text-sm focus:border-primary-500 focus:outline-none dark:border-[#2D2D43] dark:bg-[#1B1B29] dark:text-white"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                  Feed URL
                </label>
                <input
                  type="url"
                  defaultValue={selectedFeed.url}
                  className="w-full rounded-lg border border-gray-200 px-4 py-2.5 text-sm font-mono focus:border-primary-500 focus:outline-none dark:border-[#2D2D43] dark:bg-[#1B1B29] dark:text-white"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                  Sync Interval (seconds)
                </label>
                <input
                  type="number"
                  defaultValue={selectedFeed.syncInterval}
                  className="w-full rounded-lg border border-gray-200 px-4 py-2.5 text-sm focus:border-primary-500 focus:outline-none dark:border-[#2D2D43] dark:bg-[#1B1B29] dark:text-white"
                />
              </div>
            </div>
            <div className="mt-6 flex justify-end gap-3">
              <button onClick={() => setSelectedFeed(null)} className="btn btn-secondary">
                Cancel
              </button>
              <button onClick={() => setSelectedFeed(null)} className="btn btn-primary flex items-center gap-2">
                <Save className="h-4 w-4" />
                Save Changes
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Add Feed Modal */}
      {showAddModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm">
          <div className="w-full max-w-lg rounded-xl bg-white p-6 shadow-xl dark:bg-[#1E1E2D]">
            <div className="flex items-center justify-between mb-6">
              <h3 className="text-lg font-semibold text-gray-900 dark:text-white">Add New Feed</h3>
              <button
                onClick={() => setShowAddModal(false)}
                className="flex h-8 w-8 items-center justify-center rounded-lg text-gray-400 hover:bg-gray-100 dark:hover:bg-[#2D2D43]"
              >
                <X className="h-5 w-5" />
              </button>
            </div>
            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                  Feed Name
                </label>
                <input
                  type="text"
                  placeholder="e.g., SEC Form 13F"
                  className="w-full rounded-lg border border-gray-200 px-4 py-2.5 text-sm focus:border-primary-500 focus:outline-none dark:border-[#2D2D43] dark:bg-[#1B1B29] dark:text-white"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                  Feed URL
                </label>
                <input
                  type="url"
                  placeholder="https://www.sec.gov/..."
                  className="w-full rounded-lg border border-gray-200 px-4 py-2.5 text-sm font-mono focus:border-primary-500 focus:outline-none dark:border-[#2D2D43] dark:bg-[#1B1B29] dark:text-white"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                  Sync Interval
                </label>
                <select className="w-full rounded-lg border border-gray-200 px-4 py-2.5 text-sm focus:border-primary-500 focus:outline-none dark:border-[#2D2D43] dark:bg-[#1B1B29] dark:text-white">
                  <option value="60">1 minute</option>
                  <option value="300">5 minutes</option>
                  <option value="600">10 minutes</option>
                  <option value="900">15 minutes</option>
                  <option value="1800">30 minutes</option>
                  <option value="3600">1 hour</option>
                </select>
              </div>
            </div>
            <div className="mt-6 flex justify-end gap-3">
              <button onClick={() => setShowAddModal(false)} className="btn btn-secondary">
                Cancel
              </button>
              <button onClick={() => setShowAddModal(false)} className="btn btn-primary flex items-center gap-2">
                <Plus className="h-4 w-4" />
                Add Feed
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
