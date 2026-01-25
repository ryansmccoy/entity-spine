import { useState } from 'react';
import {
  Users,
  Shield,
  AlertTriangle,
  Activity,
  LogIn,
  LogOut,
  Lock,
  Unlock,
  UserCheck,
  Key,
  RefreshCw,
  ChevronRight,
  CheckCircle2,
  XCircle,
  Search,
  Download,
  TrendingUp,
  TrendingDown,
  Minus,
} from 'lucide-react';
import { clsx } from 'clsx';
import { formatDistanceToNow } from 'date-fns';

// Types
interface ActiveUser {
  id: string;
  name: string;
  email: string;
  avatarUrl?: string;
  lastActivity: Date;
  status: 'online' | 'idle' | 'offline';
  currentPage?: string;
  ipAddress?: string;
  device?: string;
}

interface LoginAttempt {
  id: string;
  email: string;
  success: boolean;
  timestamp: Date;
  ipAddress: string;
  userAgent: string;
  location?: string;
  reason?: string;
}

interface SecurityEvent {
  id: string;
  type: 'login' | 'logout' | 'password_change' | 'mfa_enabled' | 'mfa_disabled' | 'account_locked' | 'api_key_created' | 'permission_change';
  userId: string;
  userName: string;
  description: string;
  timestamp: Date;
  ipAddress?: string;
  severity: 'info' | 'warning' | 'critical';
}

interface DashboardStats {
  totalUsers: number;
  activeUsers: number;
  newUsersToday: number;
  newUsersChange: number;
  failedLogins24h: number;
  failedLoginsChange: number;
  lockedAccounts: number;
  pendingInvites: number;
}

interface AdminDashboardProps {
  stats: DashboardStats;
  activeUsers: ActiveUser[];
  recentLogins: LoginAttempt[];
  securityEvents: SecurityEvent[];
  isLoading?: boolean;
  onRefresh: () => void;
  onViewUser: (userId: string) => void;
  onUnlockAccount: (userId: string) => void;
  onExportLogs: () => void;
}

// Stat card component
function StatCard({
  title,
  value,
  change,
  changeLabel,
  icon: Icon,
  iconBg,
  onClick,
}: {
  title: string;
  value: number | string;
  change?: number;
  changeLabel?: string;
  icon: React.ElementType;
  iconBg: string;
  onClick?: () => void;
}) {
  return (
    <div
      onClick={onClick}
      className={clsx(
        'bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 p-5',
        onClick && 'cursor-pointer hover:border-primary-300 dark:hover:border-primary-700 transition-colors'
      )}
    >
      <div className="flex items-start justify-between">
        <div>
          <p className="text-sm text-gray-500 dark:text-gray-400">{title}</p>
          <p className="text-2xl font-bold text-gray-900 dark:text-white mt-1">{value}</p>
          {change !== undefined && (
            <div className="flex items-center gap-1 mt-2">
              {change > 0 ? (
                <TrendingUp className="h-4 w-4 text-green-500" />
              ) : change < 0 ? (
                <TrendingDown className="h-4 w-4 text-red-500" />
              ) : (
                <Minus className="h-4 w-4 text-gray-400" />
              )}
              <span
                className={clsx(
                  'text-sm font-medium',
                  change > 0 ? 'text-green-600' : change < 0 ? 'text-red-600' : 'text-gray-500'
                )}
              >
                {change > 0 ? '+' : ''}{change}%
              </span>
              {changeLabel && (
                <span className="text-xs text-gray-400 ml-1">{changeLabel}</span>
              )}
            </div>
          )}
        </div>
        <div className={clsx('p-3 rounded-xl', iconBg)}>
          <Icon className="h-6 w-6 text-white" />
        </div>
      </div>
    </div>
  );
}

// Active user row
function ActiveUserRow({ user, onView }: { user: ActiveUser; onView: () => void }) {
  return (
    <div
      onClick={onView}
      className="flex items-center gap-3 p-3 hover:bg-gray-50 dark:hover:bg-gray-800/50 rounded-lg cursor-pointer"
    >
      <div className="relative">
        {user.avatarUrl ? (
          <img src={user.avatarUrl} alt={user.name} className="w-9 h-9 rounded-full" />
        ) : (
          <div className="w-9 h-9 rounded-full bg-gray-200 dark:bg-gray-700 flex items-center justify-center text-sm font-medium text-gray-600 dark:text-gray-300">
            {user.name.charAt(0).toUpperCase()}
          </div>
        )}
        <div
          className={clsx(
            'absolute bottom-0 right-0 w-3 h-3 rounded-full border-2 border-white dark:border-gray-800',
            user.status === 'online' && 'bg-green-500',
            user.status === 'idle' && 'bg-yellow-500',
            user.status === 'offline' && 'bg-gray-400'
          )}
        />
      </div>
      <div className="flex-1 min-w-0">
        <p className="text-sm font-medium text-gray-900 dark:text-white truncate">{user.name}</p>
        <p className="text-xs text-gray-500 dark:text-gray-400">
          {user.currentPage || 'Unknown page'} • {formatDistanceToNow(user.lastActivity, { addSuffix: true })}
        </p>
      </div>
      <div className="text-right text-xs text-gray-400">
        <p>{user.device || 'Unknown'}</p>
        <p className="font-mono">{user.ipAddress}</p>
      </div>
    </div>
  );
}

// Login attempt row
function LoginAttemptRow({ attempt }: { attempt: LoginAttempt }) {
  return (
    <div className="flex items-center gap-3 p-3 hover:bg-gray-50 dark:hover:bg-gray-800/50 rounded-lg">
      <div
        className={clsx(
          'p-2 rounded-lg',
          attempt.success ? 'bg-green-100 dark:bg-green-900/30' : 'bg-red-100 dark:bg-red-900/30'
        )}
      >
        {attempt.success ? (
          <CheckCircle2 className="h-4 w-4 text-green-600 dark:text-green-400" />
        ) : (
          <XCircle className="h-4 w-4 text-red-600 dark:text-red-400" />
        )}
      </div>
      <div className="flex-1 min-w-0">
        <p className="text-sm text-gray-900 dark:text-white truncate">{attempt.email}</p>
        <p className="text-xs text-gray-500 dark:text-gray-400">
          {attempt.success ? 'Successful login' : attempt.reason || 'Failed login'}
        </p>
      </div>
      <div className="text-right text-xs text-gray-400">
        <p>{formatDistanceToNow(attempt.timestamp, { addSuffix: true })}</p>
        <p className="font-mono">{attempt.ipAddress}</p>
      </div>
    </div>
  );
}

// Security event row
function SecurityEventRow({ event }: { event: SecurityEvent }) {
  const icons = {
    login: LogIn,
    logout: LogOut,
    password_change: Key,
    mfa_enabled: Shield,
    mfa_disabled: Unlock,
    account_locked: Lock,
    api_key_created: Key,
    permission_change: UserCheck,
  };
  
  const Icon = icons[event.type] || Activity;

  return (
    <div className="flex items-start gap-3 p-3 hover:bg-gray-50 dark:hover:bg-gray-800/50 rounded-lg">
      <div
        className={clsx(
          'p-2 rounded-lg',
          event.severity === 'critical' && 'bg-red-100 dark:bg-red-900/30',
          event.severity === 'warning' && 'bg-yellow-100 dark:bg-yellow-900/30',
          event.severity === 'info' && 'bg-blue-100 dark:bg-blue-900/30'
        )}
      >
        <Icon
          className={clsx(
            'h-4 w-4',
            event.severity === 'critical' && 'text-red-600 dark:text-red-400',
            event.severity === 'warning' && 'text-yellow-600 dark:text-yellow-400',
            event.severity === 'info' && 'text-blue-600 dark:text-blue-400'
          )}
        />
      </div>
      <div className="flex-1 min-w-0">
        <p className="text-sm text-gray-900 dark:text-white">{event.description}</p>
        <p className="text-xs text-gray-500 dark:text-gray-400">
          {event.userName} • {formatDistanceToNow(event.timestamp, { addSuffix: true })}
        </p>
      </div>
      {event.severity !== 'info' && (
        <div
          className={clsx(
            'px-2 py-0.5 rounded text-[10px] font-semibold uppercase',
            event.severity === 'critical' && 'bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-400',
            event.severity === 'warning' && 'bg-yellow-100 text-yellow-700 dark:bg-yellow-900/30 dark:text-yellow-400'
          )}
        >
          {event.severity}
        </div>
      )}
    </div>
  );
}

// Main component
export function AdminDashboard({
  stats,
  activeUsers,
  recentLogins,
  securityEvents,
  isLoading = false,
  onRefresh,
  onViewUser,
  onUnlockAccount: _onUnlockAccount,
  onExportLogs,
}: AdminDashboardProps) {
  // Note: _onUnlockAccount will be used in future locked accounts feature
  void _onUnlockAccount;
  
  const [activeUsersSearch, setActiveUsersSearch] = useState('');

  const filteredActiveUsers = activeUsers.filter(
    (user) =>
      user.name.toLowerCase().includes(activeUsersSearch.toLowerCase()) ||
      user.email.toLowerCase().includes(activeUsersSearch.toLowerCase())
  );

  const onlineCount = activeUsers.filter((u) => u.status === 'online').length;

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900 dark:text-white flex items-center gap-2">
            <Shield className="h-7 w-7 text-primary-500" />
            Admin Dashboard
          </h1>
          <p className="text-sm text-gray-500 dark:text-gray-400 mt-1">
            Monitor users, security events, and system health
          </p>
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={onExportLogs}
            className="flex items-center gap-2 px-4 py-2 text-sm font-medium text-gray-700 dark:text-gray-200 bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-lg hover:bg-gray-50 dark:hover:bg-gray-700"
          >
            <Download className="h-4 w-4" />
            Export Logs
          </button>
          <button
            onClick={onRefresh}
            disabled={isLoading}
            className="flex items-center gap-2 px-4 py-2 text-sm font-medium text-white bg-primary-600 hover:bg-primary-700 rounded-lg disabled:opacity-50"
          >
            <RefreshCw className={clsx('h-4 w-4', isLoading && 'animate-spin')} />
            Refresh
          </button>
        </div>
      </div>

      {/* Stats Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        <StatCard
          title="Total Users"
          value={stats.totalUsers}
          icon={Users}
          iconBg="bg-blue-500"
        />
        <StatCard
          title="Online Now"
          value={onlineCount}
          change={((onlineCount / stats.totalUsers) * 100) | 0}
          changeLabel="of total"
          icon={Activity}
          iconBg="bg-green-500"
        />
        <StatCard
          title="Failed Logins (24h)"
          value={stats.failedLogins24h}
          change={stats.failedLoginsChange}
          changeLabel="vs yesterday"
          icon={AlertTriangle}
          iconBg={stats.failedLogins24h > 10 ? 'bg-red-500' : 'bg-yellow-500'}
        />
        <StatCard
          title="Locked Accounts"
          value={stats.lockedAccounts}
          icon={Lock}
          iconBg={stats.lockedAccounts > 0 ? 'bg-red-500' : 'bg-gray-400'}
        />
      </div>

      {/* Main Content Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Active Users */}
        <div className="lg:col-span-1 bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700">
          <div className="flex items-center justify-between px-4 py-3 border-b border-gray-100 dark:border-gray-700">
            <div className="flex items-center gap-2">
              <Users className="h-5 w-5 text-gray-400" />
              <h3 className="font-semibold text-gray-900 dark:text-white">Active Users</h3>
              <span className="text-xs bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400 px-2 py-0.5 rounded-full">
                {onlineCount} online
              </span>
            </div>
            <button className="text-xs text-primary-600 hover:text-primary-700 dark:text-primary-400 font-medium flex items-center gap-1">
              View all <ChevronRight className="h-3 w-3" />
            </button>
          </div>
          
          <div className="p-3">
            <div className="relative">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-gray-400" />
              <input
                type="text"
                placeholder="Search users..."
                value={activeUsersSearch}
                onChange={(e) => setActiveUsersSearch(e.target.value)}
                className="w-full pl-9 pr-3 py-2 text-sm bg-gray-50 dark:bg-gray-900 border border-gray-200 dark:border-gray-700 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary-500"
              />
            </div>
          </div>

          <div className="px-3 pb-3 max-h-[400px] overflow-y-auto">
            {filteredActiveUsers.length > 0 ? (
              filteredActiveUsers.map((user) => (
                <ActiveUserRow
                  key={user.id}
                  user={user}
                  onView={() => onViewUser(user.id)}
                />
              ))
            ) : (
              <div className="text-center py-8 text-gray-500 dark:text-gray-400">
                <Users className="h-8 w-8 mx-auto mb-2 opacity-50" />
                <p className="text-sm">No active users</p>
              </div>
            )}
          </div>
        </div>

        {/* Recent Login Attempts */}
        <div className="lg:col-span-1 bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700">
          <div className="flex items-center justify-between px-4 py-3 border-b border-gray-100 dark:border-gray-700">
            <div className="flex items-center gap-2">
              <LogIn className="h-5 w-5 text-gray-400" />
              <h3 className="font-semibold text-gray-900 dark:text-white">Login Attempts</h3>
            </div>
            <button className="text-xs text-primary-600 hover:text-primary-700 dark:text-primary-400 font-medium flex items-center gap-1">
              View all <ChevronRight className="h-3 w-3" />
            </button>
          </div>

          <div className="px-3 py-3 max-h-[460px] overflow-y-auto divide-y divide-gray-100 dark:divide-gray-700">
            {recentLogins.length > 0 ? (
              recentLogins.map((attempt) => (
                <LoginAttemptRow key={attempt.id} attempt={attempt} />
              ))
            ) : (
              <div className="text-center py-8 text-gray-500 dark:text-gray-400">
                <LogIn className="h-8 w-8 mx-auto mb-2 opacity-50" />
                <p className="text-sm">No recent login attempts</p>
              </div>
            )}
          </div>
        </div>

        {/* Security Events */}
        <div className="lg:col-span-1 bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700">
          <div className="flex items-center justify-between px-4 py-3 border-b border-gray-100 dark:border-gray-700">
            <div className="flex items-center gap-2">
              <Shield className="h-5 w-5 text-gray-400" />
              <h3 className="font-semibold text-gray-900 dark:text-white">Security Events</h3>
            </div>
            <button className="text-xs text-primary-600 hover:text-primary-700 dark:text-primary-400 font-medium flex items-center gap-1">
              View all <ChevronRight className="h-3 w-3" />
            </button>
          </div>

          <div className="px-3 py-3 max-h-[460px] overflow-y-auto">
            {securityEvents.length > 0 ? (
              securityEvents.map((event) => (
                <SecurityEventRow key={event.id} event={event} />
              ))
            ) : (
              <div className="text-center py-8 text-gray-500 dark:text-gray-400">
                <Shield className="h-8 w-8 mx-auto mb-2 opacity-50" />
                <p className="text-sm">No security events</p>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}

export default AdminDashboard;
