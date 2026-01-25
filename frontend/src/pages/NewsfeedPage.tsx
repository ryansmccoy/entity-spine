import { useState, useMemo } from 'react'
import {
  Search,
  Filter,
  RefreshCw,
  ChevronLeft,
  ChevronRight,
  ExternalLink,
  Clock,
  FileText,
  Star,
  Download,
  X,
  Rss,
  List,
  LayoutGrid,
  Eye,
  Check,
  CheckCheck,
  Bookmark,
  MoreVertical,
  Table,
  Rows3,
  LayoutList,
  PanelRightClose,
  PanelRightOpen,
  Loader2,
  AlertCircle,
} from 'lucide-react'
import { clsx } from 'clsx'
import { useLocalStorage, useResizable } from '../hooks'
import { useFeeds, useRecords, useMarkRecordRead, useToggleRecordStar, useRefreshFeed } from '../api/hooks'
import type { Feed, FeedRecord } from '../api'
import { formatDistanceToNow } from 'date-fns'

// Transform API Feed to display format
function transformFeed(feed: Feed): DisplayFeed {
  return {
    id: feed.id,
    name: feed.name,
    count: 0, // TODO: Get from API
    icon: feed.name.toLowerCase().includes('sec') ? '📋' : 
          feed.name.toLowerCase().includes('news') ? '📰' :
          feed.name.toLowerCase().includes('hack') ? '🟠' : '📡',
  }
}

// Transform API Record to display format
function transformRecord(record: FeedRecord): Article {
  const publishedDate = record.published ? new Date(record.published) : new Date(record.first_seen_at)
  return {
    id: record.id,
    feed: record.ticker || 'Feed',
    feedIcon: record.form_type ? '📋' : '📰',
    title: record.title,
    tags: [
      ...(record.form_type ? [record.form_type] : []),
      ...(record.ticker ? [record.ticker] : []),
    ].filter(Boolean),
    isAI: false,
    time: formatDistanceToNow(publishedDate, { addSuffix: false }).replace('about ', '').replace(' ago', ''),
    isNew: (Date.now() - publishedDate.getTime()) < 3600000, // < 1 hour
    isRead: record.is_read,
    isStarred: record.is_starred,
    captured: false, // TODO: Add captured state to API
    url: record.link,
  }
}

// Display types
interface DisplayFeed {
  id: string
  name: string
  count: number
  icon: string
  isGroup?: boolean
  indent?: boolean
}

interface Article {
  id: string
  feed: string
  feedIcon: string
  title: string
  tags: string[]
  isAI: boolean
  time: string
  isNew: boolean
  isRead: boolean
  isStarred: boolean
  captured: boolean
  url?: string
}

// Fallback mock data for when API is unavailable
const mockFeeds: DisplayFeed[] = [
  { id: 'all', name: 'All Articles', count: 915260, icon: '📰' },
  { id: 'top-news', name: 'top_news', count: 1045, icon: '🔝' },
  { id: 'sec-latest', name: 'SEC Latest Filings', count: 1250, icon: '📋' },
]

const mockArticles: Article[] = [
  { id: '1', feed: 'HN', feedIcon: '🟠', title: 'Sample Article - API not connected', tags: ['Demo'], isAI: false, time: '1m', isNew: true, isRead: false, isStarred: false, captured: false },
]

// Tag colors
const tagColors: Record<string, string> = {
  'Tech': 'bg-sky-100 text-sky-700 dark:bg-sky-900/30 dark:text-sky-400',
  'AI/ML': 'bg-purple-100 text-purple-700 dark:bg-purple-900/30 dark:text-purple-400',
  'SEC': 'bg-amber-100 text-amber-700 dark:bg-amber-900/30 dark:text-amber-400',
  '10-K': 'bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-400',
  '10-Q': 'bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400',
  '8-K': 'bg-orange-100 text-orange-700 dark:bg-orange-900/30 dark:text-orange-400',
  'Earnings': 'bg-emerald-100 text-emerald-700 dark:bg-emerald-900/30 dark:text-emerald-400',
}

// View modes with descriptions
const viewModes = [
  { id: 'condensed', label: 'Condensed', icon: Rows3, description: 'Tight rows, maximum density' },
  { id: 'comfortable', label: 'Comfortable', icon: LayoutList, description: 'More spacing, easier reading' },
  { id: 'headlines', label: 'Headlines Only', icon: List, description: 'Title and time only' },
  { id: 'cards', label: 'Card Grid', icon: LayoutGrid, description: 'Cards in a grid layout' },
  { id: 'table', label: 'Table', icon: Table, description: 'Full table with all columns' },
] as const

type ViewMode = typeof viewModes[number]['id']

// Resize handle component
function ResizeHandle({ 
  onMouseDown, 
  direction = 'horizontal',
  isResizing = false 
}: { 
  onMouseDown: (e: React.MouseEvent) => void
  direction?: 'horizontal' | 'vertical'
  isResizing?: boolean
}) {
  return (
    <div
      onMouseDown={onMouseDown}
      className={clsx(
        'group flex items-center justify-center',
        direction === 'horizontal'
          ? 'w-1 cursor-col-resize hover:bg-primary-500/20'
          : 'h-1 cursor-row-resize hover:bg-primary-500/20',
        isResizing && 'bg-primary-500/30'
      )}
    >
      <div
        className={clsx(
          'rounded-full bg-gray-300 dark:bg-gray-600 transition-colors',
          direction === 'horizontal' ? 'w-0.5 h-8' : 'h-0.5 w-8',
          'group-hover:bg-primary-500',
          isResizing && 'bg-primary-500'
        )}
      />
    </div>
  )
}

// View mode selector dropdown
function ViewModeSelector({ 
  viewMode, 
  setViewMode 
}: { 
  viewMode: ViewMode
  setViewMode: (mode: ViewMode) => void 
}) {
  const [isOpen, setIsOpen] = useState(false)
  const current = viewModes.find(v => v.id === viewMode)!

  return (
    <div className="relative">
      <button
        onClick={() => setIsOpen(!isOpen)}
        className="flex items-center gap-1.5 h-7 px-2 rounded border border-gray-200 dark:border-[#2D2D43] text-xs font-medium text-gray-600 dark:text-gray-400 hover:bg-gray-50 dark:hover:bg-[#2D2D43]"
      >
        <current.icon className="h-3.5 w-3.5" />
        <span className="hidden sm:inline">{current.label}</span>
        <ChevronRight className={clsx('h-3 w-3 transition-transform', isOpen && 'rotate-90')} />
      </button>
      
      {isOpen && (
        <>
          <div className="fixed inset-0 z-10" onClick={() => setIsOpen(false)} />
          <div className="absolute right-0 top-full mt-1 z-20 w-48 rounded-lg border border-gray-200 dark:border-[#2D2D43] bg-white dark:bg-[#1E1E2D] shadow-lg py-1">
            {viewModes.map((mode) => {
              const Icon = mode.icon
              return (
                <button
                  key={mode.id}
                  onClick={() => {
                    setViewMode(mode.id)
                    setIsOpen(false)
                  }}
                  className={clsx(
                    'w-full flex items-center gap-2 px-3 py-2 text-left text-xs transition-colors',
                    viewMode === mode.id
                      ? 'bg-primary-50 text-primary-700 dark:bg-primary-900/20 dark:text-primary-400'
                      : 'text-gray-700 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-[#2D2D43]'
                  )}
                >
                  <Icon className="h-4 w-4" />
                  <div className="flex-1">
                    <div className="font-medium">{mode.label}</div>
                    <div className="text-[10px] text-gray-500 dark:text-gray-400">{mode.description}</div>
                  </div>
                  {viewMode === mode.id && <Check className="h-3.5 w-3.5" />}
                </button>
              )
            })}
          </div>
        </>
      )}
    </div>
  )
}

// Article row for condensed/comfortable views
function ArticleRow({ 
  article, 
  viewMode, 
  isSelected, 
  onClick, 
  onToggleStar 
}: { 
  article: Article
  viewMode: ViewMode
  isSelected: boolean
  onClick: () => void
  onToggleStar: () => void
}) {
  const isCondensed = viewMode === 'condensed'
  const isHeadlines = viewMode === 'headlines'

  if (isHeadlines) {
    return (
      <div
        onClick={onClick}
        className={clsx(
          'flex items-center px-3 py-1 border-b border-gray-50 dark:border-[#252536] cursor-pointer transition-colors group',
          isSelected
            ? 'bg-primary-50 dark:bg-primary-900/20'
            : 'hover:bg-gray-50 dark:hover:bg-[#1B1B29]',
          !article.isRead && 'bg-blue-50/30 dark:bg-blue-900/5'
        )}
      >
        {!article.isRead && (
          <div className="w-1.5 h-1.5 rounded-full bg-primary-500 flex-shrink-0 mr-2" />
        )}
        <span className={clsx(
          'flex-1 text-[13px] truncate',
          article.isRead ? 'text-gray-500 dark:text-gray-400' : 'text-gray-900 dark:text-white font-medium'
        )}>
          {article.title}
        </span>
        <span className="text-[11px] text-gray-400 tabular-nums ml-2">{article.time}</span>
      </div>
    )
  }

  return (
    <div
      onClick={onClick}
      className={clsx(
        'flex items-center px-3 border-b border-gray-50 dark:border-[#252536] cursor-pointer transition-colors group',
        isCondensed ? 'py-1' : 'py-2',
        isSelected
          ? 'bg-primary-50 dark:bg-primary-900/20'
          : 'hover:bg-gray-50 dark:hover:bg-[#1B1B29]',
        !article.isRead && 'bg-blue-50/30 dark:bg-blue-900/5'
      )}
    >
      {/* Star */}
      <div className="w-8 flex-shrink-0">
        <button
          onClick={(e) => {
            e.stopPropagation()
            onToggleStar()
          }}
          className={clsx(
            'flex h-5 w-5 items-center justify-center rounded',
            article.isStarred ? 'text-yellow-500' : 'text-gray-300 opacity-0 group-hover:opacity-100 hover:text-yellow-500'
          )}
        >
          <Star className={clsx('h-3.5 w-3.5', article.isStarred && 'fill-current')} />
        </button>
      </div>

      {/* Feed */}
      <div className="w-12 flex-shrink-0">
        <span className="text-sm" title={article.feed}>{article.feedIcon}</span>
      </div>

      {/* Headline */}
      <div className="flex-1 min-w-0 flex items-center gap-2">
        {!article.isRead && (
          <div className="w-1.5 h-1.5 rounded-full bg-primary-500 flex-shrink-0" />
        )}
        <span className={clsx(
          'text-[13px] truncate',
          article.isRead ? 'text-gray-500 dark:text-gray-400' : 'text-gray-900 dark:text-white font-medium'
        )}>
          {article.title}
        </span>
        {article.tags.slice(0, 2).map((tag) => (
          <span
            key={tag}
            className={clsx(
              'flex-shrink-0 rounded px-1.5 py-0.5 text-[9px] font-semibold uppercase',
              tagColors[tag] || 'bg-gray-100 text-gray-600 dark:bg-gray-800 dark:text-gray-400'
            )}
          >
            {tag}
          </span>
        ))}
        {article.isAI && (
          <span className="flex-shrink-0 rounded bg-violet-100 text-violet-700 dark:bg-violet-900/30 dark:text-violet-400 px-1.5 py-0.5 text-[9px] font-semibold">
            AI/ML
          </span>
        )}
      </div>

      {/* Captured Status */}
      <div className="w-20 flex-shrink-0 text-right">
        {article.captured ? (
          <span className="inline-flex items-center gap-1 text-[10px] text-green-600 dark:text-green-400 font-medium">
            <Check className="h-3 w-3" />
            Captured
          </span>
        ) : (
          <button
            onClick={(e) => e.stopPropagation()}
            className="opacity-0 group-hover:opacity-100 text-[10px] text-gray-400 hover:text-primary-600"
          >
            Capture
          </button>
        )}
      </div>

      {/* Time */}
      <div className="w-16 flex-shrink-0 text-right pr-2">
        <span className="text-[11px] text-gray-400 tabular-nums">{article.time}</span>
      </div>
    </div>
  )
}

// Card view for a single article
function ArticleCard({ 
  article, 
  isSelected, 
  onClick, 
  onToggleStar 
}: { 
  article: Article
  isSelected: boolean
  onClick: () => void
  onToggleStar: () => void
}) {
  return (
    <div
      onClick={onClick}
      className={clsx(
        'group rounded-lg border p-3 cursor-pointer transition-all',
        isSelected
          ? 'border-primary-500 bg-primary-50 dark:bg-primary-900/20'
          : 'border-gray-200 dark:border-[#2D2D43] hover:border-primary-300 dark:hover:border-primary-700 hover:shadow-sm',
        !article.isRead && 'border-l-2 border-l-primary-500'
      )}
    >
      <div className="flex items-start justify-between gap-2 mb-2">
        <div className="flex items-center gap-2">
          <span className="text-lg">{article.feedIcon}</span>
          <span className="text-xs text-gray-500">{article.feed}</span>
        </div>
        <button
          onClick={(e) => {
            e.stopPropagation()
            onToggleStar()
          }}
          className={clsx(
            'flex h-6 w-6 items-center justify-center rounded',
            article.isStarred ? 'text-yellow-500' : 'text-gray-300 opacity-0 group-hover:opacity-100 hover:text-yellow-500'
          )}
        >
          <Star className={clsx('h-4 w-4', article.isStarred && 'fill-current')} />
        </button>
      </div>
      
      <h4 className={clsx(
        'text-sm leading-snug mb-2 line-clamp-2',
        article.isRead ? 'text-gray-500 dark:text-gray-400' : 'text-gray-900 dark:text-white font-medium'
      )}>
        {article.title}
      </h4>
      
      <div className="flex items-center justify-between">
        <div className="flex flex-wrap gap-1">
          {article.tags.slice(0, 2).map((tag) => (
            <span
              key={tag}
              className={clsx(
                'rounded px-1.5 py-0.5 text-[9px] font-semibold uppercase',
                tagColors[tag] || 'bg-gray-100 text-gray-600 dark:bg-gray-800 dark:text-gray-400'
              )}
            >
              {tag}
            </span>
          ))}
        </div>
        <span className="text-[10px] text-gray-400">{article.time}</span>
      </div>

      {article.captured && (
        <div className="mt-2 flex items-center gap-1 text-[10px] text-green-600 dark:text-green-400">
          <Check className="h-3 w-3" />
          Captured
        </div>
      )}
    </div>
  )
}

// Table view for articles
function ArticleTable({ 
  articles, 
  selectedId, 
  onSelect, 
  onToggleStar 
}: { 
  articles: Article[]
  selectedId: string | null
  onSelect: (article: Article) => void
  onToggleStar: (id: string) => void
}) {
  return (
    <div className="overflow-x-auto">
      <table className="w-full text-sm">
        <thead className="bg-gray-50 dark:bg-[#1B1B29] sticky top-0">
          <tr className="text-left text-[10px] font-semibold uppercase tracking-wider text-gray-500">
            <th className="px-3 py-2 w-10"></th>
            <th className="px-3 py-2 w-12">Feed</th>
            <th className="px-3 py-2">Headline</th>
            <th className="px-3 py-2 w-32">Tags</th>
            <th className="px-3 py-2 w-20 text-center">Status</th>
            <th className="px-3 py-2 w-20">Time</th>
          </tr>
        </thead>
        <tbody>
          {articles.map((article) => (
            <tr
              key={article.id}
              onClick={() => onSelect(article)}
              className={clsx(
                'border-b border-gray-50 dark:border-[#252536] cursor-pointer transition-colors group',
                selectedId === article.id
                  ? 'bg-primary-50 dark:bg-primary-900/20'
                  : 'hover:bg-gray-50 dark:hover:bg-[#1B1B29]',
                !article.isRead && 'bg-blue-50/30 dark:bg-blue-900/5'
              )}
            >
              <td className="px-3 py-2">
                <button
                  onClick={(e) => {
                    e.stopPropagation()
                    onToggleStar(article.id)
                  }}
                  className={clsx(
                    'flex h-5 w-5 items-center justify-center rounded',
                    article.isStarred ? 'text-yellow-500' : 'text-gray-300 opacity-0 group-hover:opacity-100 hover:text-yellow-500'
                  )}
                >
                  <Star className={clsx('h-3.5 w-3.5', article.isStarred && 'fill-current')} />
                </button>
              </td>
              <td className="px-3 py-2">
                <span className="text-base" title={article.feed}>{article.feedIcon}</span>
              </td>
              <td className="px-3 py-2">
                <div className="flex items-center gap-2">
                  {!article.isRead && (
                    <div className="w-1.5 h-1.5 rounded-full bg-primary-500 flex-shrink-0" />
                  )}
                  <span className={clsx(
                    'text-[13px]',
                    article.isRead ? 'text-gray-500 dark:text-gray-400' : 'text-gray-900 dark:text-white font-medium'
                  )}>
                    {article.title}
                  </span>
                </div>
              </td>
              <td className="px-3 py-2">
                <div className="flex flex-wrap gap-1">
                  {article.tags.slice(0, 2).map((tag) => (
                    <span
                      key={tag}
                      className={clsx(
                        'rounded px-1.5 py-0.5 text-[9px] font-semibold uppercase',
                        tagColors[tag] || 'bg-gray-100 text-gray-600 dark:bg-gray-800 dark:text-gray-400'
                      )}
                    >
                      {tag}
                    </span>
                  ))}
                </div>
              </td>
              <td className="px-3 py-2 text-center">
                {article.captured ? (
                  <span className="inline-flex items-center gap-1 text-[10px] text-green-600 dark:text-green-400 font-medium">
                    <Check className="h-3 w-3" />
                    Captured
                  </span>
                ) : (
                  <span className="text-[10px] text-gray-400">—</span>
                )}
              </td>
              <td className="px-3 py-2">
                <span className="text-[11px] text-gray-400 tabular-nums">{article.time}</span>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}

// Preview panel component
function PreviewPanel({ 
  article, 
  onClose, 
  onToggleStar 
}: { 
  article: Article | null
  onClose: () => void
  onToggleStar: () => void
}) {
  if (!article) {
    return (
      <div className="flex flex-col items-center justify-center h-full text-center p-8">
        <div className="w-16 h-16 rounded-full bg-gray-100 dark:bg-[#2D2D43] flex items-center justify-center mb-4">
          <Rss className="h-8 w-8 text-gray-400" />
        </div>
        <h4 className="text-sm font-semibold text-gray-900 dark:text-white mb-1">Select an article</h4>
        <p className="text-xs text-gray-500 dark:text-gray-400">
          Click on any headline to preview and capture content
        </p>
      </div>
    )
  }

  return (
    <div className="h-full flex flex-col">
      {/* Header */}
      <div className="flex items-center justify-between px-4 py-3 border-b border-gray-100 dark:border-[#2D2D43]">
        <div className="flex items-center gap-2">
          <span className="text-lg">{article.feedIcon}</span>
          <span className="text-xs font-medium text-gray-500">{article.feed}</span>
        </div>
        <div className="flex items-center gap-1">
          <button
            onClick={onToggleStar}
            className={clsx(
              'flex h-7 w-7 items-center justify-center rounded',
              article.isStarred ? 'text-yellow-500' : 'text-gray-400 hover:text-yellow-500'
            )}
          >
            <Star className={clsx('h-4 w-4', article.isStarred && 'fill-current')} />
          </button>
          <button className="flex h-7 w-7 items-center justify-center rounded text-gray-400 hover:text-gray-600 dark:hover:bg-[#2D2D43]">
            <Bookmark className="h-4 w-4" />
          </button>
          <button className="flex h-7 w-7 items-center justify-center rounded text-gray-400 hover:text-gray-600 dark:hover:bg-[#2D2D43]">
            <MoreVertical className="h-4 w-4" />
          </button>
          <button
            onClick={onClose}
            className="flex h-7 w-7 items-center justify-center rounded text-gray-400 hover:bg-gray-100 hover:text-gray-600 dark:hover:bg-[#2D2D43]"
          >
            <X className="h-4 w-4" />
          </button>
        </div>
      </div>

      {/* Content */}
      <div className="flex-1 overflow-y-auto p-4">
        {article.captured ? (
          <>
            {/* Tags */}
            <div className="flex flex-wrap gap-1.5 mb-3">
              {article.tags.map((tag) => (
                <span
                  key={tag}
                  className={clsx(
                    'rounded px-2 py-0.5 text-[10px] font-semibold uppercase',
                    tagColors[tag] || 'bg-gray-100 text-gray-600'
                  )}
                >
                  {tag}
                </span>
              ))}
            </div>

            {/* Title */}
            <h3 className="text-base font-semibold text-gray-900 dark:text-white leading-snug mb-3">
              {article.title}
            </h3>

            {/* Meta */}
            <div className="flex items-center gap-3 text-xs text-gray-500 mb-4">
              <span className="flex items-center gap-1">
                <Clock className="h-3 w-3" />
                {article.time}
              </span>
            </div>

            {/* Content preview placeholder */}
            <div className="prose prose-sm dark:prose-invert">
              <p className="text-sm text-gray-600 dark:text-gray-400 leading-relaxed">
                Content has been captured and is available for viewing. Click "Read Full Article" to see the complete content in a clean reader view.
              </p>
            </div>
          </>
        ) : (
          <div className="flex flex-col items-center justify-center h-full text-center py-12">
            <div className="w-16 h-16 rounded-full bg-gray-100 dark:bg-[#2D2D43] flex items-center justify-center mb-4">
              <FileText className="h-8 w-8 text-gray-400" />
            </div>
            <h4 className="text-sm font-semibold text-gray-900 dark:text-white mb-1">Content not yet captured</h4>
            <p className="text-xs text-gray-500 dark:text-gray-400 max-w-[240px]">
              Capture the article content to read it here with a clean reader view
            </p>
          </div>
        )}
      </div>

      {/* Actions */}
      <div className="border-t border-gray-100 dark:border-[#2D2D43] p-4">
        {article.captured ? (
          <div className="space-y-2">
            <button className="w-full btn btn-primary flex items-center justify-center gap-2 h-9 text-sm">
              <Eye className="h-4 w-4" />
              Read Full Article
            </button>
            <button className="w-full btn btn-secondary flex items-center justify-center gap-2 h-9 text-sm">
              <ExternalLink className="h-4 w-4" />
              Open in New Tab
            </button>
          </div>
        ) : (
          <div className="space-y-2">
            <button className="w-full btn btn-primary flex items-center justify-center gap-2 h-9 text-sm">
              <Download className="h-4 w-4" />
              Capture Content
            </button>
            <div className="flex gap-2">
              <button className="flex-1 btn btn-secondary flex items-center justify-center gap-2 h-9 text-sm">
                <Eye className="h-4 w-4" />
                Preview Site
              </button>
              <button className="flex-1 btn btn-secondary flex items-center justify-center gap-2 h-9 text-sm">
                <ExternalLink className="h-4 w-4" />
                Open in New Tab
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}

export function NewsfeedPage() {
  const [selectedFeed, setSelectedFeed] = useState('all')
  const [selectedArticle, setSelectedArticle] = useState<Article | null>(null)
  const [searchQuery, setSearchQuery] = useState('')
  const [showUnreadOnly, setShowUnreadOnly] = useState(false)

  // API Hooks
  const { 
    data: apiFeeds, 
    isLoading: feedsLoading, 
    error: feedsError 
  } = useFeeds()
  
  const { 
    data: apiRecords, 
    isLoading: recordsLoading, 
    error: recordsError,
    refetch: refetchRecords 
  } = useRecords({
    feed_id: selectedFeed === 'all' ? undefined : selectedFeed,
    is_read: showUnreadOnly ? false : undefined,
    search: searchQuery || undefined,
    limit: 100,
  })

  const markReadMutation = useMarkRecordRead()
  const toggleStarMutation = useToggleRecordStar()
  const refreshFeedMutation = useRefreshFeed()

  // Transform API data to display format, with fallbacks
  const feeds: DisplayFeed[] = useMemo(() => {
    if (feedsError || !apiFeeds || apiFeeds.length === 0) {
      return mockFeeds
    }
    return [
      { id: 'all', name: 'All Articles', count: apiRecords?.length || 0, icon: '📰' },
      ...apiFeeds.map(transformFeed)
    ]
  }, [apiFeeds, apiRecords, feedsError])

  const articles: Article[] = useMemo(() => {
    if (recordsError || !apiRecords || apiRecords.length === 0) {
      return mockArticles
    }
    return apiRecords.map(transformRecord)
  }, [apiRecords, recordsError])

  // Persisted UI preferences
  const [viewMode, setViewMode] = useLocalStorage<ViewMode>('newsfeed-view-mode', 'condensed')
  const [sidebarOpen, setSidebarOpen] = useLocalStorage('newsfeed-sidebar-open', true)
  const [previewOpen, setPreviewOpen] = useLocalStorage('newsfeed-preview-open', true)

  // Resizable panels
  const sidebar = useResizable({
    direction: 'horizontal',
    initialSize: 220,
    minSize: 160,
    maxSize: 350,
    storageKey: 'newsfeed-sidebar-width',
    handlePosition: 'right',
  })

  const preview = useResizable({
    direction: 'horizontal',
    initialSize: 380,
    minSize: 280,
    maxSize: 600,
    storageKey: 'newsfeed-preview-width',
    handlePosition: 'left',
  })

  const filteredArticles = useMemo(() => {
    let result = articles
    if (searchQuery) {
      const query = searchQuery.toLowerCase()
      result = result.filter((a) => a.title.toLowerCase().includes(query))
    }
    if (showUnreadOnly) {
      result = result.filter((a) => !a.isRead)
    }
    return result
  }, [articles, searchQuery, showUnreadOnly])

  const toggleStar = (id: string) => {
    const article = articles.find(a => a.id === id)
    if (article) {
      toggleStarMutation.mutate({ id, isStarred: !article.isStarred })
    }
  }

  const markAsRead = (id: string) => {
    markReadMutation.mutate(id)
  }

  const handleSelectArticle = (article: Article) => {
    setSelectedArticle(article)
    if (!article.isRead) {
      markAsRead(article.id)
    }
  }

  const handleRefresh = () => {
    if (selectedFeed !== 'all') {
      refreshFeedMutation.mutate(selectedFeed)
    }
    refetchRecords()
  }

  const unreadCount = articles.filter((a) => !a.isRead).length
  const isLoading = feedsLoading || recordsLoading
  const hasError = feedsError || recordsError

  return (
    <div className="flex h-[calc(100vh-130px)]">
      {/* Feed Sidebar */}
      {sidebarOpen && (
        <>
          <div
            className="flex-shrink-0 border-r border-gray-200 dark:border-[#2D2D43] bg-white dark:bg-[#1E1E2D]"
            style={{ width: sidebar.size }}
          >
            <div className="h-full flex flex-col">
              <div className="flex items-center justify-between px-3 py-2 border-b border-gray-100 dark:border-[#2D2D43]">
                <span className="text-xs font-semibold text-gray-500 dark:text-gray-400 uppercase tracking-wider">Feeds</span>
                <button className="flex h-6 w-6 items-center justify-center rounded text-gray-400 hover:bg-gray-100 hover:text-gray-600 dark:hover:bg-[#2D2D43]">
                  <RefreshCw className="h-3 w-3" />
                </button>
              </div>
              <div className="flex-1 overflow-y-auto py-1">
                {feeds.map((feed) => (
                  <button
                    key={feed.id}
                    onClick={() => setSelectedFeed(feed.id)}
                    className={clsx(
                      'flex w-full items-center gap-2 px-3 py-1.5 text-left transition-colors text-[13px]',
                      feed.indent && 'pl-6',
                      selectedFeed === feed.id
                        ? 'bg-primary-50 text-primary-700 dark:bg-primary-900/20 dark:text-primary-400'
                        : 'text-gray-700 hover:bg-gray-50 dark:text-gray-300 dark:hover:bg-[#2D2D43]'
                    )}
                  >
                    <span className="text-sm">{feed.icon}</span>
                    <span className="flex-1 truncate font-medium">{feed.name}</span>
                    <span className="text-[11px] text-gray-400 tabular-nums">{feed.count.toLocaleString()}</span>
                  </button>
                ))}
              </div>
            </div>
          </div>
          <ResizeHandle
            onMouseDown={sidebar.startResize}
            isResizing={sidebar.isResizing}
          />
        </>
      )}

      {/* Article List */}
      <div className="flex-1 flex flex-col min-w-0 bg-white dark:bg-[#1E1E2D]">
        {/* Toolbar */}
        <div className="flex items-center justify-between px-3 py-2 border-b border-gray-200 dark:border-[#2D2D43]">
          <div className="flex items-center gap-2">
            <button
              onClick={() => setSidebarOpen(!sidebarOpen)}
              className="flex h-7 w-7 items-center justify-center rounded text-gray-500 hover:bg-gray-100 dark:hover:bg-[#2D2D43]"
              title={sidebarOpen ? 'Hide sidebar' : 'Show sidebar'}
            >
              {sidebarOpen ? <ChevronLeft className="h-4 w-4" /> : <ChevronRight className="h-4 w-4" />}
            </button>
            <span className="text-sm font-semibold text-gray-900 dark:text-white">Newsfeed</span>
            <span className="text-xs text-gray-400">Unread ({unreadCount})</span>
          </div>
          <div className="flex items-center gap-1">
            {/* View mode selector */}
            <ViewModeSelector viewMode={viewMode} setViewMode={setViewMode} />
            
            <div className="w-px h-5 bg-gray-200 dark:bg-[#2D2D43] mx-1" />
            
            <div className="relative">
              <Search className="absolute left-2.5 top-1/2 h-3.5 w-3.5 -translate-y-1/2 text-gray-400" />
              <input
                type="text"
                placeholder="Filter articles..."
                className="h-7 w-[160px] rounded border border-gray-200 bg-gray-50 pl-8 pr-2 text-xs focus:border-primary-500 focus:bg-white focus:outline-none dark:border-[#2D2D43] dark:bg-[#1B1B29] dark:text-white"
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
              />
            </div>
            <button
              onClick={() => setShowUnreadOnly(!showUnreadOnly)}
              className={clsx(
                'flex h-7 items-center gap-1.5 rounded border px-2 text-xs font-medium',
                showUnreadOnly
                  ? 'border-primary-500 bg-primary-50 text-primary-700 dark:bg-primary-900/20'
                  : 'border-gray-200 text-gray-600 hover:bg-gray-50 dark:border-[#2D2D43] dark:text-gray-400'
              )}
            >
              <Eye className="h-3 w-3" />
              Unread
            </button>
            <button className="flex h-7 w-7 items-center justify-center rounded text-gray-500 hover:bg-gray-100 dark:hover:bg-[#2D2D43]">
              <Filter className="h-3.5 w-3.5" />
            </button>
            <button 
              onClick={handleRefresh}
              disabled={isLoading}
              className="flex h-7 w-7 items-center justify-center rounded text-gray-500 hover:bg-gray-100 dark:hover:bg-[#2D2D43] disabled:opacity-50"
            >
              <RefreshCw className={clsx('h-3.5 w-3.5', isLoading && 'animate-spin')} />
            </button>
            <button className="flex h-7 w-7 items-center justify-center rounded text-gray-500 hover:bg-gray-100 dark:hover:bg-[#2D2D43]">
              <CheckCheck className="h-3.5 w-3.5" />
            </button>
            
            <div className="w-px h-5 bg-gray-200 dark:bg-[#2D2D43] mx-1" />
            
            {/* Preview toggle */}
            <button
              onClick={() => setPreviewOpen(!previewOpen)}
              className={clsx(
                'flex h-7 w-7 items-center justify-center rounded',
                previewOpen
                  ? 'text-primary-600 bg-primary-50 dark:bg-primary-900/20'
                  : 'text-gray-500 hover:bg-gray-100 dark:hover:bg-[#2D2D43]'
              )}
              title={previewOpen ? 'Hide preview' : 'Show preview'}
            >
              {previewOpen ? <PanelRightClose className="h-4 w-4" /> : <PanelRightOpen className="h-4 w-4" />}
            </button>
          </div>
        </div>

        {/* Column Headers (only for row-based views) */}
        {(viewMode === 'condensed' || viewMode === 'comfortable') && (
          <div className="flex items-center px-3 py-1.5 border-b border-gray-100 dark:border-[#2D2D43] bg-gray-50 dark:bg-[#1B1B29] text-[10px] font-semibold uppercase tracking-wider text-gray-500">
            <div className="w-8"></div>
            <div className="w-12">Feed</div>
            <div className="flex-1">Headline</div>
            <div className="w-20 text-right">Captured</div>
            <div className="w-16 text-right pr-2">Time</div>
          </div>
        )}

        {/* Article List - Different views */}
        <div className="flex-1 overflow-y-auto">
          {/* Loading State */}
          {isLoading && filteredArticles.length === 0 && (
            <div className="flex flex-col items-center justify-center h-64 text-center p-8">
              <Loader2 className="h-8 w-8 text-primary-500 animate-spin mb-4" />
              <p className="text-sm text-gray-500 dark:text-gray-400">Loading articles...</p>
            </div>
          )}

          {/* Error State */}
          {hasError && (
            <div className="flex flex-col items-center justify-center h-64 text-center p-8">
              <div className="w-12 h-12 rounded-full bg-amber-100 dark:bg-amber-900/30 flex items-center justify-center mb-4">
                <AlertCircle className="h-6 w-6 text-amber-500" />
              </div>
              <p className="text-sm font-medium text-gray-900 dark:text-white mb-1">Using demo data</p>
              <p className="text-xs text-gray-500 dark:text-gray-400 max-w-[280px]">
                API not available. Showing sample data. Start the backend to see real feeds.
              </p>
            </div>
          )}

          {/* Empty State */}
          {!isLoading && !hasError && filteredArticles.length === 0 && (
            <div className="flex flex-col items-center justify-center h-64 text-center p-8">
              <div className="w-12 h-12 rounded-full bg-gray-100 dark:bg-[#2D2D43] flex items-center justify-center mb-4">
                <Rss className="h-6 w-6 text-gray-400" />
              </div>
              <p className="text-sm font-medium text-gray-900 dark:text-white mb-1">No articles found</p>
              <p className="text-xs text-gray-500 dark:text-gray-400">
                {searchQuery ? 'Try a different search term' : 'Add feeds to start capturing content'}
              </p>
            </div>
          )}

          {/* Content */}
          {viewMode === 'cards' ? (
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3 p-3">
              {filteredArticles.map((article) => (
                <ArticleCard
                  key={article.id}
                  article={article}
                  isSelected={selectedArticle?.id === article.id}
                  onClick={() => handleSelectArticle(article)}
                  onToggleStar={() => toggleStar(article.id)}
                />
              ))}
            </div>
          ) : viewMode === 'table' ? (
            <ArticleTable
              articles={filteredArticles}
              selectedId={selectedArticle?.id || null}
              onSelect={handleSelectArticle}
              onToggleStar={toggleStar}
            />
          ) : (
            filteredArticles.map((article) => (
              <ArticleRow
                key={article.id}
                article={article}
                viewMode={viewMode}
                isSelected={selectedArticle?.id === article.id}
                onClick={() => handleSelectArticle(article)}
                onToggleStar={() => toggleStar(article.id)}
              />
            ))
          )}
        </div>
      </div>

      {/* Preview Panel */}
      {previewOpen && (
        <>
          <ResizeHandle
            onMouseDown={preview.startResize}
            isResizing={preview.isResizing}
          />
          <div
            className={clsx(
              'flex-shrink-0 border-l border-gray-200 dark:border-[#2D2D43]',
              selectedArticle
                ? 'bg-white dark:bg-[#1E1E2D]'
                : 'bg-gray-50 dark:bg-[#1B1B29]'
            )}
            style={{ width: preview.size }}
          >
            <PreviewPanel
              article={selectedArticle}
              onClose={() => setSelectedArticle(null)}
              onToggleStar={() => selectedArticle && toggleStar(selectedArticle.id)}
            />
          </div>
        </>
      )}
    </div>
  )
}
