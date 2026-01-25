import {
  Newspaper,
  Rss,
  FileText,
  Clock,
  ArrowUpRight,
  ArrowDownRight,
  Activity,
  Eye,
  Download,
  RefreshCw,
  CheckCircle2,
  ExternalLink,
  Network,
} from 'lucide-react'
import { clsx } from 'clsx'
import { EntityMiniGraph } from '../components/graph'

// Stat card component
interface StatCardProps {
  title: string
  value: string
  change?: string
  changeType?: 'increase' | 'decrease'
  icon: React.ElementType
  iconColor: string
  iconBg: string
}

function StatCard({ title, value, change, changeType, icon: Icon, iconColor, iconBg }: StatCardProps) {
  return (
    <div className="card rounded-xl p-6">
      <div className="flex items-start justify-between">
        <div>
          <p className="text-[13px] font-medium text-gray-500 dark:text-[#565674]">{title}</p>
          <h3 className="mt-2 text-2xl font-bold text-gray-900 dark:text-white">{value}</h3>
          {change && (
            <div className="mt-2 flex items-center gap-1">
              {changeType === 'increase' ? (
                <ArrowUpRight className="h-4 w-4 text-success" />
              ) : (
                <ArrowDownRight className="h-4 w-4 text-danger" />
              )}
              <span className={clsx('text-xs font-medium', changeType === 'increase' ? 'text-success' : 'text-danger')}>
                {change}
              </span>
              <span className="text-xs text-gray-400">vs last week</span>
            </div>
          )}
        </div>
        <div className={clsx('flex h-12 w-12 items-center justify-center rounded-lg', iconBg)}>
          <Icon className={clsx('h-6 w-6', iconColor)} />
        </div>
      </div>
    </div>
  )
}

// Recent filings
const recentFilings = [
  { company: 'Apple Inc.', form: '10-K', time: '5 min ago', status: 'new' },
  { company: 'Microsoft Corp.', form: '8-K', time: '15 min ago', status: 'new' },
  { company: 'Tesla Inc.', form: '10-Q', time: '1 hour ago', status: 'viewed' },
  { company: 'Amazon.com Inc.', form: '10-K', time: '2 hours ago', status: 'viewed' },
  { company: 'NVIDIA Corp.', form: 'DEF 14A', time: '3 hours ago', status: 'captured' },
]

// Feed status
const feedStatus = [
  { name: 'SEC Latest Filings', status: 'active', lastSync: '2 min ago', items: 1250 },
  { name: 'SEC Form 10-K', status: 'active', lastSync: '5 min ago', items: 423 },
  { name: 'SEC Form 8-K', status: 'active', lastSync: '3 min ago', items: 892 },
  { name: 'SEC Form 4', status: 'paused', lastSync: '1 hour ago', items: 2341 },
]

export function DashboardPage() {
  return (
    <div className="space-y-6">
      {/* Stats Grid */}
      <div className="grid gap-6 sm:grid-cols-2 lg:grid-cols-4">
        <StatCard
          title="Total Filings"
          value="4,721"
          change="12.5%"
          changeType="increase"
          icon={FileText}
          iconColor="text-primary-600"
          iconBg="bg-primary-100 dark:bg-primary-900/30"
        />
        <StatCard
          title="Active Feeds"
          value="6"
          icon={Rss}
          iconColor="text-success"
          iconBg="bg-success-light dark:bg-success/20"
        />
        <StatCard
          title="Captured Today"
          value="47"
          change="8.2%"
          changeType="increase"
          icon={Download}
          iconColor="text-info"
          iconBg="bg-info-light dark:bg-info/20"
        />
        <StatCard
          title="New This Week"
          value="312"
          change="3.1%"
          changeType="decrease"
          icon={Newspaper}
          iconColor="text-warning"
          iconBg="bg-warning-light dark:bg-warning/20"
        />
      </div>

      {/* Main Content Grid */}
      <div className="grid gap-6 lg:grid-cols-3">
        {/* Recent Filings */}
        <div className="card rounded-xl lg:col-span-2">
          <div className="flex items-center justify-between border-b border-gray-100 dark:border-[#2D2D43] px-6 py-4">
            <div>
              <h3 className="text-base font-semibold text-gray-900 dark:text-white">Recent Filings</h3>
              <p className="text-xs text-gray-500 dark:text-[#565674]">Latest SEC filings from your feeds</p>
            </div>
            <a
              href="/newsfeed"
              className="flex items-center gap-1 text-xs font-medium text-primary-600 hover:text-primary-700"
            >
              View all
              <ExternalLink className="h-3 w-3" />
            </a>
          </div>
          <div className="divide-y divide-gray-100 dark:divide-[#2D2D43]">
            {recentFilings.map((filing, index) => (
              <div
                key={index}
                className="flex items-center justify-between px-6 py-4 hover:bg-gray-50 dark:hover:bg-[#1B1B29] transition-colors cursor-pointer"
              >
                <div className="flex items-center gap-4">
                  <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-gray-100 dark:bg-[#2D2D43]">
                    <FileText className="h-5 w-5 text-gray-500 dark:text-gray-400" />
                  </div>
                  <div>
                    <p className="text-sm font-medium text-gray-900 dark:text-white">{filing.company}</p>
                    <div className="flex items-center gap-2 mt-0.5">
                      <span className="rounded bg-gray-100 px-1.5 py-0.5 text-[10px] font-semibold text-gray-600 dark:bg-[#2D2D43] dark:text-gray-400">
                        {filing.form}
                      </span>
                      <span className="flex items-center gap-1 text-[11px] text-gray-400">
                        <Clock className="h-3 w-3" />
                        {filing.time}
                      </span>
                    </div>
                  </div>
                </div>
                <div className="flex items-center gap-3">
                  {filing.status === 'new' && (
                    <span className="badge badge-primary">New</span>
                  )}
                  {filing.status === 'viewed' && (
                    <Eye className="h-4 w-4 text-gray-400" />
                  )}
                  {filing.status === 'captured' && (
                    <CheckCircle2 className="h-4 w-4 text-success" />
                  )}
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Feed Status */}
        <div className="card rounded-xl">
          <div className="flex items-center justify-between border-b border-gray-100 dark:border-[#2D2D43] px-6 py-4">
            <div>
              <h3 className="text-base font-semibold text-gray-900 dark:text-white">Feed Status</h3>
              <p className="text-xs text-gray-500 dark:text-[#565674]">Monitor your feed sources</p>
            </div>
            <button className="flex h-8 w-8 items-center justify-center rounded-lg text-gray-400 hover:bg-gray-100 hover:text-gray-600 dark:hover:bg-[#2D2D43]">
              <RefreshCw className="h-4 w-4" />
            </button>
          </div>
          <div className="divide-y divide-gray-100 dark:divide-[#2D2D43]">
            {feedStatus.map((feed, index) => (
              <div key={index} className="px-6 py-4">
                <div className="flex items-center justify-between">
                  <p className="text-sm font-medium text-gray-900 dark:text-white">{feed.name}</p>
                  <div className="flex items-center gap-1.5">
                    <div
                      className={clsx(
                        'h-2 w-2 rounded-full',
                        feed.status === 'active' ? 'bg-success' : 'bg-warning'
                      )}
                    />
                    <span
                      className={clsx(
                        'text-[11px] font-medium capitalize',
                        feed.status === 'active' ? 'text-success' : 'text-warning'
                      )}
                    >
                      {feed.status}
                    </span>
                  </div>
                </div>
                <div className="mt-2 flex items-center justify-between text-[11px] text-gray-400">
                  <span>Last sync: {feed.lastSync}</span>
                  <span>{feed.items.toLocaleString()} items</span>
                </div>
              </div>
            ))}
          </div>
          <div className="border-t border-gray-100 dark:border-[#2D2D43] px-6 py-4">
            <a
              href="/feeds"
              className="flex items-center justify-center gap-1 text-xs font-medium text-primary-600 hover:text-primary-700"
            >
              Manage feeds
              <ExternalLink className="h-3 w-3" />
            </a>
          </div>
        </div>
      </div>

      {/* Quick Actions */}
      <div className="card rounded-xl p-6">
        <h3 className="text-base font-semibold text-gray-900 dark:text-white mb-4">Quick Actions</h3>
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
          <a
            href="/newsfeed"
            className="group flex items-center gap-4 rounded-lg border border-gray-200 dark:border-[#2D2D43] p-4 hover:border-primary-500 hover:bg-primary-50/50 dark:hover:bg-primary-900/10 transition-all"
          >
            <div className="flex h-12 w-12 items-center justify-center rounded-lg bg-primary-100 dark:bg-primary-900/30 text-primary-600 group-hover:bg-primary-600 group-hover:text-white transition-colors">
              <Newspaper className="h-6 w-6" />
            </div>
            <div>
              <p className="text-sm font-medium text-gray-900 dark:text-white">Browse Newsfeed</p>
              <p className="text-xs text-gray-500 dark:text-[#565674]">View latest filings</p>
            </div>
          </a>
          <a
            href="/feeds"
            className="group flex items-center gap-4 rounded-lg border border-gray-200 dark:border-[#2D2D43] p-4 hover:border-success hover:bg-success-light/50 dark:hover:bg-success/10 transition-all"
          >
            <div className="flex h-12 w-12 items-center justify-center rounded-lg bg-success-light dark:bg-success/20 text-success group-hover:bg-success group-hover:text-white transition-colors">
              <Rss className="h-6 w-6" />
            </div>
            <div>
              <p className="text-sm font-medium text-gray-900 dark:text-white">Add Feed</p>
              <p className="text-xs text-gray-500 dark:text-[#565674]">Configure new source</p>
            </div>
          </a>
          <a
            href="/settings"
            className="group flex items-center gap-4 rounded-lg border border-gray-200 dark:border-[#2D2D43] p-4 hover:border-info hover:bg-info-light/50 dark:hover:bg-info/10 transition-all"
          >
            <div className="flex h-12 w-12 items-center justify-center rounded-lg bg-info-light dark:bg-info/20 text-info group-hover:bg-info group-hover:text-white transition-colors">
              <Activity className="h-6 w-6" />
            </div>
            <div>
              <p className="text-sm font-medium text-gray-900 dark:text-white">System Status</p>
              <p className="text-xs text-gray-500 dark:text-[#565674]">Check health</p>
            </div>
          </a>
          <a
            href="/graph"
            className="group flex items-center gap-4 rounded-lg border border-gray-200 dark:border-[#2D2D43] p-4 hover:border-purple-500 hover:bg-purple-50/50 dark:hover:bg-purple-900/10 transition-all"
          >
            <div className="flex h-12 w-12 items-center justify-center rounded-lg bg-purple-100 dark:bg-purple-900/30 text-purple-600 group-hover:bg-purple-600 group-hover:text-white transition-colors">
              <Network className="h-6 w-6" />
            </div>
            <div>
              <p className="text-sm font-medium text-gray-900 dark:text-white">Entity Graph</p>
              <p className="text-xs text-gray-500 dark:text-[#565674]">Explore relationships</p>
            </div>
          </a>
        </div>
      </div>

      {/* Entity Relationship Graph */}
      <div className="card rounded-xl overflow-hidden">
        <div className="flex items-center justify-between border-b border-gray-100 dark:border-[#2D2D43] px-6 py-4">
          <div>
            <h3 className="text-base font-semibold text-gray-900 dark:text-white">Entity Relationships</h3>
            <p className="text-xs text-gray-500 dark:text-[#565674]">Interactive graph of company relationships</p>
          </div>
          <a
            href="/graph"
            className="flex items-center gap-1 text-xs font-medium text-primary-600 hover:text-primary-700"
          >
            Full view
            <ExternalLink className="h-3 w-3" />
          </a>
        </div>
        <EntityMiniGraph height={400} showDetailPanel={true} />
      </div>
    </div>
  )
}
