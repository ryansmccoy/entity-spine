import { useState } from 'react'
import {
  User,
  Bell,
  Moon,
  Sun,
  Globe,
  Shield,
  Database,
  Palette,
  Save,
  RefreshCw,
  CheckCircle2,
  AlertCircle,
  Info,
  ChevronRight,
  ExternalLink,
} from 'lucide-react'
import { clsx } from 'clsx'
import { useLayout } from '../layouts/AdminLayout'

// Settings sections
const settingsSections = [
  { id: 'profile', name: 'Profile', icon: User, description: 'Manage your account information' },
  { id: 'appearance', name: 'Appearance', icon: Palette, description: 'Customize the look and feel' },
  { id: 'notifications', name: 'Notifications', icon: Bell, description: 'Configure alert preferences' },
  { id: 'system', name: 'System', icon: Database, description: 'System configuration and status' },
  { id: 'about', name: 'About', icon: Info, description: 'Version info and resources' },
]

// System status
const systemStatus = [
  { name: 'API Server', status: 'online', version: 'v0.1.0', port: '8000' },
  { name: 'PostgreSQL', status: 'online', version: '15.4', port: '5432' },
  { name: 'Feed Poller', status: 'running', lastRun: '2 min ago' },
  { name: 'Redis Cache', status: 'offline', error: 'Not configured' },
]

export function SettingsPage() {
  const { darkMode, setDarkMode } = useLayout()
  const [activeSection, setActiveSection] = useState('profile')
  const [notifications, setNotifications] = useState({
    newFilings: true,
    feedErrors: true,
    systemUpdates: false,
    emailDigest: false,
  })

  return (
    <div className="flex gap-6">
      {/* Settings Navigation */}
      <div className="w-[260px] flex-shrink-0">
        <div className="card rounded-xl">
          <div className="p-4 border-b border-gray-100 dark:border-[#2D2D43]">
            <h3 className="text-sm font-semibold text-gray-900 dark:text-white">Settings</h3>
          </div>
          <nav className="p-2">
            {settingsSections.map((section) => (
              <button
                key={section.id}
                onClick={() => setActiveSection(section.id)}
                className={clsx(
                  'flex w-full items-center gap-3 rounded-lg px-3 py-2.5 text-left transition-colors',
                  activeSection === section.id
                    ? 'bg-primary-50 text-primary-700 dark:bg-primary-900/20 dark:text-primary-400'
                    : 'text-gray-600 hover:bg-gray-50 dark:text-gray-400 dark:hover:bg-[#2D2D43]'
                )}
              >
                <section.icon className="h-5 w-5" />
                <div className="flex-1">
                  <p className="text-sm font-medium">{section.name}</p>
                  <p className="text-[11px] text-gray-400">{section.description}</p>
                </div>
                <ChevronRight className={clsx('h-4 w-4', activeSection === section.id && 'text-primary-500')} />
              </button>
            ))}
          </nav>
        </div>
      </div>

      {/* Settings Content */}
      <div className="flex-1 min-w-0">
        {/* Profile Settings */}
        {activeSection === 'profile' && (
          <div className="card rounded-xl">
            <div className="border-b border-gray-100 dark:border-[#2D2D43] px-6 py-4">
              <h3 className="text-base font-semibold text-gray-900 dark:text-white">Profile Settings</h3>
              <p className="text-sm text-gray-500 dark:text-[#565674]">Manage your account information</p>
            </div>
            <div className="p-6 space-y-6">
              <div className="flex items-center gap-6">
                <div className="flex h-20 w-20 items-center justify-center rounded-xl bg-gradient-to-br from-primary-500 to-primary-600 text-2xl font-bold text-white">
                  U
                </div>
                <div>
                  <button className="btn btn-secondary text-sm">Change Avatar</button>
                  <p className="mt-2 text-xs text-gray-400">JPG, PNG or GIF. Max 2MB.</p>
                </div>
              </div>
              <div className="grid gap-4 sm:grid-cols-2">
                <div>
                  <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                    Display Name
                  </label>
                  <input
                    type="text"
                    defaultValue="User"
                    className="w-full rounded-lg border border-gray-200 px-4 py-2.5 text-sm focus:border-primary-500 focus:outline-none dark:border-[#2D2D43] dark:bg-[#1B1B29] dark:text-white"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                    Email
                  </label>
                  <input
                    type="email"
                    defaultValue="user@example.com"
                    className="w-full rounded-lg border border-gray-200 px-4 py-2.5 text-sm focus:border-primary-500 focus:outline-none dark:border-[#2D2D43] dark:bg-[#1B1B29] dark:text-white"
                  />
                </div>
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                  Time Zone
                </label>
                <select className="w-full rounded-lg border border-gray-200 px-4 py-2.5 text-sm focus:border-primary-500 focus:outline-none dark:border-[#2D2D43] dark:bg-[#1B1B29] dark:text-white">
                  <option>America/New_York (EST)</option>
                  <option>America/Chicago (CST)</option>
                  <option>America/Denver (MST)</option>
                  <option>America/Los_Angeles (PST)</option>
                  <option>UTC</option>
                </select>
              </div>
              <div className="flex justify-end">
                <button className="btn btn-primary flex items-center gap-2">
                  <Save className="h-4 w-4" />
                  Save Changes
                </button>
              </div>
            </div>
          </div>
        )}

        {/* Appearance Settings */}
        {activeSection === 'appearance' && (
          <div className="space-y-6">
            <div className="card rounded-xl">
              <div className="border-b border-gray-100 dark:border-[#2D2D43] px-6 py-4">
                <h3 className="text-base font-semibold text-gray-900 dark:text-white">Theme</h3>
                <p className="text-sm text-gray-500 dark:text-[#565674]">Choose your preferred color scheme</p>
              </div>
              <div className="p-6">
                <div className="grid gap-4 sm:grid-cols-3">
                  <button
                    onClick={() => setDarkMode(false)}
                    className={clsx(
                      'flex flex-col items-center gap-3 rounded-xl border-2 p-4 transition-colors',
                      !darkMode
                        ? 'border-primary-500 bg-primary-50 dark:bg-primary-900/20'
                        : 'border-gray-200 hover:border-gray-300 dark:border-[#2D2D43] dark:hover:border-[#3D3D53]'
                    )}
                  >
                    <div className="flex h-14 w-14 items-center justify-center rounded-xl bg-white shadow-md">
                      <Sun className="h-7 w-7 text-yellow-500" />
                    </div>
                    <span className="text-sm font-medium text-gray-900 dark:text-white">Light</span>
                  </button>
                  <button
                    onClick={() => setDarkMode(true)}
                    className={clsx(
                      'flex flex-col items-center gap-3 rounded-xl border-2 p-4 transition-colors',
                      darkMode
                        ? 'border-primary-500 bg-primary-50 dark:bg-primary-900/20'
                        : 'border-gray-200 hover:border-gray-300 dark:border-[#2D2D43] dark:hover:border-[#3D3D53]'
                    )}
                  >
                    <div className="flex h-14 w-14 items-center justify-center rounded-xl bg-[#1E1E2D] shadow-md">
                      <Moon className="h-7 w-7 text-blue-400" />
                    </div>
                    <span className="text-sm font-medium text-gray-900 dark:text-white">Dark</span>
                  </button>
                  <button
                    className="flex flex-col items-center gap-3 rounded-xl border-2 border-gray-200 p-4 transition-colors hover:border-gray-300 dark:border-[#2D2D43] dark:hover:border-[#3D3D53]"
                  >
                    <div className="flex h-14 w-14 items-center justify-center rounded-xl bg-gradient-to-br from-white to-[#1E1E2D] shadow-md">
                      <Globe className="h-7 w-7 text-gray-400" />
                    </div>
                    <span className="text-sm font-medium text-gray-900 dark:text-white">System</span>
                  </button>
                </div>
              </div>
            </div>

            <div className="card rounded-xl">
              <div className="border-b border-gray-100 dark:border-[#2D2D43] px-6 py-4">
                <h3 className="text-base font-semibold text-gray-900 dark:text-white">Sidebar</h3>
                <p className="text-sm text-gray-500 dark:text-[#565674]">Customize sidebar behavior</p>
              </div>
              <div className="p-6 space-y-4">
                <label className="flex items-center justify-between cursor-pointer">
                  <div>
                    <p className="text-sm font-medium text-gray-900 dark:text-white">Collapsed by default</p>
                    <p className="text-xs text-gray-500 dark:text-[#565674]">Start with a minimized sidebar</p>
                  </div>
                  <input type="checkbox" className="toggle" />
                </label>
                <label className="flex items-center justify-between cursor-pointer">
                  <div>
                    <p className="text-sm font-medium text-gray-900 dark:text-white">Show status card</p>
                    <p className="text-xs text-gray-500 dark:text-[#565674]">Display system status in sidebar</p>
                  </div>
                  <input type="checkbox" defaultChecked className="toggle" />
                </label>
              </div>
            </div>
          </div>
        )}

        {/* Notification Settings */}
        {activeSection === 'notifications' && (
          <div className="card rounded-xl">
            <div className="border-b border-gray-100 dark:border-[#2D2D43] px-6 py-4">
              <h3 className="text-base font-semibold text-gray-900 dark:text-white">Notification Preferences</h3>
              <p className="text-sm text-gray-500 dark:text-[#565674]">Configure how you want to be notified</p>
            </div>
            <div className="p-6 space-y-4">
              <label className="flex items-center justify-between cursor-pointer py-2">
                <div>
                  <p className="text-sm font-medium text-gray-900 dark:text-white">New Filings</p>
                  <p className="text-xs text-gray-500 dark:text-[#565674]">Get notified when new filings are detected</p>
                </div>
                <input
                  type="checkbox"
                  checked={notifications.newFilings}
                  onChange={(e) => setNotifications({ ...notifications, newFilings: e.target.checked })}
                  className="toggle"
                />
              </label>
              <label className="flex items-center justify-between cursor-pointer py-2">
                <div>
                  <p className="text-sm font-medium text-gray-900 dark:text-white">Feed Errors</p>
                  <p className="text-xs text-gray-500 dark:text-[#565674]">Alert when a feed encounters an error</p>
                </div>
                <input
                  type="checkbox"
                  checked={notifications.feedErrors}
                  onChange={(e) => setNotifications({ ...notifications, feedErrors: e.target.checked })}
                  className="toggle"
                />
              </label>
              <label className="flex items-center justify-between cursor-pointer py-2">
                <div>
                  <p className="text-sm font-medium text-gray-900 dark:text-white">System Updates</p>
                  <p className="text-xs text-gray-500 dark:text-[#565674]">Notifications about system updates</p>
                </div>
                <input
                  type="checkbox"
                  checked={notifications.systemUpdates}
                  onChange={(e) => setNotifications({ ...notifications, systemUpdates: e.target.checked })}
                  className="toggle"
                />
              </label>
              <label className="flex items-center justify-between cursor-pointer py-2">
                <div>
                  <p className="text-sm font-medium text-gray-900 dark:text-white">Email Digest</p>
                  <p className="text-xs text-gray-500 dark:text-[#565674]">Receive daily summary via email</p>
                </div>
                <input
                  type="checkbox"
                  checked={notifications.emailDigest}
                  onChange={(e) => setNotifications({ ...notifications, emailDigest: e.target.checked })}
                  className="toggle"
                />
              </label>
            </div>
          </div>
        )}

        {/* System Settings */}
        {activeSection === 'system' && (
          <div className="space-y-6">
            <div className="card rounded-xl">
              <div className="border-b border-gray-100 dark:border-[#2D2D43] px-6 py-4">
                <div className="flex items-center justify-between">
                  <div>
                    <h3 className="text-base font-semibold text-gray-900 dark:text-white">System Status</h3>
                    <p className="text-sm text-gray-500 dark:text-[#565674]">Monitor system components</p>
                  </div>
                  <button className="flex items-center gap-2 text-sm font-medium text-primary-600 hover:text-primary-700">
                    <RefreshCw className="h-4 w-4" />
                    Refresh
                  </button>
                </div>
              </div>
              <div className="p-6">
                <div className="space-y-3">
                  {systemStatus.map((service, index) => (
                    <div
                      key={index}
                      className="flex items-center justify-between rounded-lg border border-gray-100 dark:border-[#2D2D43] p-4"
                    >
                      <div className="flex items-center gap-3">
                        <div
                          className={clsx(
                            'flex h-10 w-10 items-center justify-center rounded-lg',
                            service.status === 'online' || service.status === 'running'
                              ? 'bg-success-light dark:bg-success/20'
                              : 'bg-danger-light dark:bg-danger/20'
                          )}
                        >
                          {service.status === 'online' || service.status === 'running' ? (
                            <CheckCircle2
                              className={clsx(
                                'h-5 w-5',
                                service.status === 'online' || service.status === 'running' ? 'text-success' : 'text-danger'
                              )}
                            />
                          ) : (
                            <AlertCircle className="h-5 w-5 text-danger" />
                          )}
                        </div>
                        <div>
                          <p className="text-sm font-medium text-gray-900 dark:text-white">{service.name}</p>
                          <p className="text-xs text-gray-500 dark:text-[#565674]">
                            {service.version && `Version ${service.version}`}
                            {service.port && ` • Port ${service.port}`}
                            {service.lastRun && `Last run: ${service.lastRun}`}
                            {service.error && service.error}
                          </p>
                        </div>
                      </div>
                      <span
                        className={clsx(
                          'rounded-full px-2.5 py-1 text-xs font-medium capitalize',
                          service.status === 'online' && 'bg-success-light text-success-dark dark:bg-success/20 dark:text-success',
                          service.status === 'running' && 'bg-success-light text-success-dark dark:bg-success/20 dark:text-success',
                          service.status === 'offline' && 'bg-danger-light text-danger-dark dark:bg-danger/20 dark:text-danger'
                        )}
                      >
                        {service.status}
                      </span>
                    </div>
                  ))}
                </div>
              </div>
            </div>

            <div className="card rounded-xl">
              <div className="border-b border-gray-100 dark:border-[#2D2D43] px-6 py-4">
                <h3 className="text-base font-semibold text-gray-900 dark:text-white">Database</h3>
                <p className="text-sm text-gray-500 dark:text-[#565674]">Manage database operations</p>
              </div>
              <div className="p-6 space-y-4">
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-sm font-medium text-gray-900 dark:text-white">Clear All Data</p>
                    <p className="text-xs text-gray-500 dark:text-[#565674]">Remove all captured filings and reset feeds</p>
                  </div>
                  <button className="btn bg-danger-light text-danger hover:bg-danger hover:text-white">
                    Clear Data
                  </button>
                </div>
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-sm font-medium text-gray-900 dark:text-white">Export Data</p>
                    <p className="text-xs text-gray-500 dark:text-[#565674]">Download all data as JSON</p>
                  </div>
                  <button className="btn btn-secondary">Export</button>
                </div>
              </div>
            </div>
          </div>
        )}

        {/* About */}
        {activeSection === 'about' && (
          <div className="space-y-6">
            <div className="card rounded-xl">
              <div className="p-6 text-center">
                <div className="mx-auto flex h-20 w-20 items-center justify-center rounded-2xl bg-gradient-to-br from-primary-500 to-primary-600 mb-4">
                  <Shield className="h-10 w-10 text-white" />
                </div>
                <h3 className="text-xl font-bold text-gray-900 dark:text-white">Capture Spine Basic</h3>
                <p className="text-sm text-gray-500 dark:text-[#565674]">SEC Filing Feed Reader</p>
                <p className="mt-2 text-2xl font-bold text-primary-600">v0.1.0</p>
              </div>
            </div>

            <div className="card rounded-xl">
              <div className="border-b border-gray-100 dark:border-[#2D2D43] px-6 py-4">
                <h3 className="text-base font-semibold text-gray-900 dark:text-white">Resources</h3>
              </div>
              <div className="p-2">
                <a
                  href="#"
                  className="flex items-center justify-between rounded-lg px-4 py-3 hover:bg-gray-50 dark:hover:bg-[#1B1B29]"
                >
                  <span className="text-sm text-gray-700 dark:text-gray-300">Documentation</span>
                  <ExternalLink className="h-4 w-4 text-gray-400" />
                </a>
                <a
                  href="#"
                  className="flex items-center justify-between rounded-lg px-4 py-3 hover:bg-gray-50 dark:hover:bg-[#1B1B29]"
                >
                  <span className="text-sm text-gray-700 dark:text-gray-300">GitHub Repository</span>
                  <ExternalLink className="h-4 w-4 text-gray-400" />
                </a>
                <a
                  href="#"
                  className="flex items-center justify-between rounded-lg px-4 py-3 hover:bg-gray-50 dark:hover:bg-[#1B1B29]"
                >
                  <span className="text-sm text-gray-700 dark:text-gray-300">Report an Issue</span>
                  <ExternalLink className="h-4 w-4 text-gray-400" />
                </a>
                <a
                  href="#"
                  className="flex items-center justify-between rounded-lg px-4 py-3 hover:bg-gray-50 dark:hover:bg-[#1B1B29]"
                >
                  <span className="text-sm text-gray-700 dark:text-gray-300">Changelog</span>
                  <ExternalLink className="h-4 w-4 text-gray-400" />
                </a>
              </div>
            </div>

            <div className="card rounded-xl p-6">
              <p className="text-center text-xs text-gray-400">
                Part of the py-sec-edgar ecosystem<br />
                © 2025 Capture Spine. All rights reserved.
              </p>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
