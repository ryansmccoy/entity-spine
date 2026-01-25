import axios from 'axios'

// Create axios instance with base URL from environment
export const api = axios.create({
  baseURL: import.meta.env.VITE_API_URL || '/api',
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json',
  },
})

// Request interceptor
api.interceptors.request.use(
  (config) => {
    // Add auth token if available
    const token = localStorage.getItem('token')
    if (token) {
      config.headers.Authorization = `Bearer ${token}`
    }
    return config
  },
  (error) => {
    return Promise.reject(error)
  }
)

// Response interceptor
api.interceptors.response.use(
  (response) => response,
  (error) => {
    // Handle common errors
    if (error.response?.status === 401) {
      // Handle unauthorized
      localStorage.removeItem('token')
    }
    return Promise.reject(error)
  }
)

// Types
export interface Feed {
  id: string
  name: string
  url: string
  enabled: boolean
  poll_interval: number
  last_poll?: string
  error_count: number
  created_at: string
  updated_at: string
}

export interface FeedRecord {
  id: string
  feed_id: string
  guid: string
  title: string
  link: string
  description?: string
  published?: string
  author?: string
  form_type?: string
  company_name?: string
  ticker?: string
  accession_number?: string
  first_seen_at: string
  is_read: boolean
  is_starred: boolean
}

export interface FeedCheckpoint {
  id: string
  feed_id: string
  etag?: string
  last_modified?: string
  last_success?: string
  last_error?: string
  error_message?: string
}

export interface HealthStatus {
  status: string
  database: string
  version: string
  timestamp: string
}

// API functions
export const feedsApi = {
  // List all feeds
  list: async (): Promise<Feed[]> => {
    const response = await api.get('/feeds')
    return response.data
  },

  // Get a single feed
  get: async (id: string): Promise<Feed> => {
    const response = await api.get(`/feeds/${id}`)
    return response.data
  },

  // Create a new feed
  create: async (feed: Partial<Feed>): Promise<Feed> => {
    const response = await api.post('/feeds', feed)
    return response.data
  },

  // Update a feed
  update: async (id: string, feed: Partial<Feed>): Promise<Feed> => {
    const response = await api.put(`/feeds/${id}`, feed)
    return response.data
  },

  // Delete a feed
  delete: async (id: string): Promise<void> => {
    await api.delete(`/feeds/${id}`)
  },

  // Toggle feed enabled status
  toggle: async (id: string, enabled: boolean): Promise<Feed> => {
    const response = await api.patch(`/feeds/${id}`, { enabled })
    return response.data
  },

  // Force refresh a feed
  refresh: async (id: string): Promise<void> => {
    await api.post(`/feeds/${id}/refresh`)
  },
}

export const recordsApi = {
  // List records with optional filters
  list: async (params?: {
    feed_id?: string
    form_type?: string
    is_read?: boolean
    is_starred?: boolean
    search?: string
    limit?: number
    offset?: number
  }): Promise<FeedRecord[]> => {
    const response = await api.get('/records', { params })
    return response.data
  },

  // Get a single record
  get: async (id: string): Promise<FeedRecord> => {
    const response = await api.get(`/records/${id}`)
    return response.data
  },

  // Mark record as read
  markRead: async (id: string): Promise<FeedRecord> => {
    const response = await api.patch(`/records/${id}`, { is_read: true })
    return response.data
  },

  // Toggle star status
  toggleStar: async (id: string, isStarred: boolean): Promise<FeedRecord> => {
    const response = await api.patch(`/records/${id}`, { is_starred: isStarred })
    return response.data
  },

  // Mark all as read
  markAllRead: async (feedId?: string): Promise<void> => {
    await api.post('/records/mark-all-read', { feed_id: feedId })
  },
}

export const healthApi = {
  // Get health status
  check: async (): Promise<HealthStatus> => {
    const response = await api.get('/health')
    return response.data
  },
}

export const integrationsApi = {
  // List available integrations
  list: async (): Promise<{ name: string; available: boolean }[]> => {
    const response = await api.get('/integrations')
    return response.data
  },
}

// Alert types
export interface AlertCondition {
  type: 'keywords' | 'form_types' | 'filers' | 'cik' | 'industry'
  operator: 'contains' | 'equals' | 'not_contains' | 'regex'
  value: string | string[]
}

export interface AlertAction {
  type: 'notification' | 'email' | 'webhook'
  enabled: boolean
  config?: {
    email?: string
    webhook_url?: string
    include_content?: boolean
  }
}

export interface Alert {
  alert_id: string
  name: string
  description?: string
  enabled: boolean
  conditions: AlertCondition[]
  actions: AlertAction[]
  feed_ids?: string[]
  triggered_count: number
  last_triggered_at?: string
  created_at: string
  updated_at: string
}

export const alertsApi = {
  // List all alerts
  list: async (): Promise<Alert[]> => {
    const response = await api.get('/alerts')
    return response.data
  },

  // Get a single alert
  get: async (id: string): Promise<Alert> => {
    const response = await api.get(`/alerts/${id}`)
    return response.data
  },

  // Create a new alert
  create: async (alert: Partial<Alert>): Promise<Alert> => {
    const response = await api.post('/alerts', alert)
    return response.data
  },

  // Update an alert
  update: async (id: string, alert: Partial<Alert>): Promise<Alert> => {
    const response = await api.put(`/alerts/${id}`, alert)
    return response.data
  },

  // Delete an alert
  delete: async (id: string): Promise<void> => {
    await api.delete(`/alerts/${id}`)
  },

  // Toggle alert enabled status
  toggle: async (id: string, enabled: boolean): Promise<Alert> => {
    const response = await api.patch(`/alerts/${id}`, { enabled })
    return response.data
  },
}

// Notification types
export interface Notification {
  notification_id: string
  type: 'alert_triggered' | 'feed_error' | 'system' | 'digest'
  title: string
  message?: string
  read: boolean
  metadata?: Record<string, unknown>
  created_at: string
}

export const notificationsApi = {
  // List all notifications
  list: async (params?: { unread_only?: boolean; limit?: number; offset?: number }): Promise<Notification[]> => {
    const response = await api.get('/notifications', { params })
    return response.data
  },

  // Get unread count
  getUnreadCount: async (): Promise<{ count: number }> => {
    const response = await api.get('/notifications/unread-count')
    return response.data
  },

  // Mark notification as read
  markRead: async (id: string): Promise<Notification> => {
    const response = await api.patch(`/notifications/${id}`, { read: true })
    return response.data
  },

  // Mark all as read
  markAllRead: async (): Promise<void> => {
    await api.post('/notifications/mark-all-read')
  },

  // Delete a notification
  delete: async (id: string): Promise<void> => {
    await api.delete(`/notifications/${id}`)
  },
}

// Auth types
export interface User {
  user_id: string
  email: string
  name?: string
  role: 'user' | 'admin'
  status: 'active' | 'disabled' | 'pending'
  avatar_url?: string
  created_at: string
  last_login_at?: string
}

export interface AuthTokens {
  access_token: string
  refresh_token: string
  token_type: string
  expires_in: number
}

export interface LoginCredentials {
  email: string
  password: string
}

export interface RegisterData {
  email: string
  password: string
  name?: string
}

export const authApi = {
  // Login
  login: async (credentials: LoginCredentials): Promise<AuthTokens> => {
    const response = await api.post('/auth/login', credentials)
    return response.data
  },

  // Register
  register: async (data: RegisterData): Promise<User> => {
    const response = await api.post('/auth/register', data)
    return response.data
  },

  // Logout
  logout: async (): Promise<void> => {
    await api.post('/auth/logout')
    localStorage.removeItem('token')
  },

  // Refresh token
  refresh: async (refreshToken: string): Promise<AuthTokens> => {
    const response = await api.post('/auth/refresh', { refresh_token: refreshToken })
    return response.data
  },

  // Get current user
  me: async (): Promise<User> => {
    const response = await api.get('/auth/me')
    return response.data
  },

  // Request password reset
  requestPasswordReset: async (email: string): Promise<void> => {
    await api.post('/auth/forgot-password', { email })
  },

  // Reset password
  resetPassword: async (token: string, newPassword: string): Promise<void> => {
    await api.post('/auth/reset-password', { token, new_password: newPassword })
  },
}

// Settings types
export interface Settings {
  theme?: 'light' | 'dark' | 'system'
  notifications_enabled?: boolean
  email_notifications?: boolean
  digest_frequency?: 'daily' | 'weekly' | 'never'
  default_view_mode?: 'condensed' | 'comfortable' | 'headlines' | 'cards' | 'table'
  timezone?: string
}

export const settingsApi = {
  // Get settings
  get: async (): Promise<Settings> => {
    const response = await api.get('/settings')
    return response.data
  },

  // Update settings
  update: async (settings: Partial<Settings>): Promise<Settings> => {
    const response = await api.put('/settings', settings)
    return response.data
  },
}

export default api
