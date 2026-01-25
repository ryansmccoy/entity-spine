import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { 
  feedsApi, 
  recordsApi, 
  healthApi, 
  alertsApi,
  notificationsApi,
  authApi,
  settingsApi,
  Feed, 
  FeedRecord, 
  HealthStatus,
  Alert,
  Notification,
  User,
  AuthTokens,
  Settings,
  LoginCredentials,
  RegisterData,
} from './index'

// Query keys
export const queryKeys = {
  feeds: ['feeds'] as const,
  feed: (id: string) => ['feeds', id] as const,
  records: (params?: Record<string, unknown>) => ['records', params] as const,
  record: (id: string) => ['records', id] as const,
  health: ['health'] as const,
  alerts: ['alerts'] as const,
  alert: (id: string) => ['alerts', id] as const,
  notifications: (params?: Record<string, unknown>) => ['notifications', params] as const,
  notificationCount: ['notifications', 'count'] as const,
  user: ['user'] as const,
  settings: ['settings'] as const,
}

// Feed hooks
export function useFeeds() {
  return useQuery({
    queryKey: queryKeys.feeds,
    queryFn: feedsApi.list,
    refetchInterval: 30000, // Refetch every 30 seconds
  })
}

export function useFeed(id: string) {
  return useQuery({
    queryKey: queryKeys.feed(id),
    queryFn: () => feedsApi.get(id),
    enabled: !!id,
  })
}

export function useCreateFeed() {
  const queryClient = useQueryClient()
  
  return useMutation({
    mutationFn: (feed: Partial<Feed>) => feedsApi.create(feed),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: queryKeys.feeds })
    },
  })
}

export function useUpdateFeed() {
  const queryClient = useQueryClient()
  
  return useMutation({
    mutationFn: ({ id, feed }: { id: string; feed: Partial<Feed> }) => 
      feedsApi.update(id, feed),
    onSuccess: (_, { id }) => {
      queryClient.invalidateQueries({ queryKey: queryKeys.feeds })
      queryClient.invalidateQueries({ queryKey: queryKeys.feed(id) })
    },
  })
}

export function useDeleteFeed() {
  const queryClient = useQueryClient()
  
  return useMutation({
    mutationFn: (id: string) => feedsApi.delete(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: queryKeys.feeds })
    },
  })
}

export function useToggleFeed() {
  const queryClient = useQueryClient()
  
  return useMutation({
    mutationFn: ({ id, enabled }: { id: string; enabled: boolean }) => 
      feedsApi.toggle(id, enabled),
    onSuccess: (_, { id }) => {
      queryClient.invalidateQueries({ queryKey: queryKeys.feeds })
      queryClient.invalidateQueries({ queryKey: queryKeys.feed(id) })
    },
  })
}

export function useRefreshFeed() {
  const queryClient = useQueryClient()
  
  return useMutation({
    mutationFn: (id: string) => feedsApi.refresh(id),
    onSuccess: () => {
      // Invalidate records since they may have changed
      queryClient.invalidateQueries({ queryKey: ['records'] })
    },
  })
}

// Record hooks
export function useRecords(params?: {
  feed_id?: string
  form_type?: string
  is_read?: boolean
  is_starred?: boolean
  search?: string
  limit?: number
  offset?: number
}) {
  return useQuery({
    queryKey: queryKeys.records(params),
    queryFn: () => recordsApi.list(params),
    refetchInterval: 10000, // Refetch every 10 seconds
  })
}

export function useRecord(id: string) {
  return useQuery({
    queryKey: queryKeys.record(id),
    queryFn: () => recordsApi.get(id),
    enabled: !!id,
  })
}

export function useMarkRecordRead() {
  const queryClient = useQueryClient()
  
  return useMutation({
    mutationFn: (id: string) => recordsApi.markRead(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['records'] })
    },
  })
}

export function useToggleRecordStar() {
  const queryClient = useQueryClient()
  
  return useMutation({
    mutationFn: ({ id, isStarred }: { id: string; isStarred: boolean }) => 
      recordsApi.toggleStar(id, isStarred),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['records'] })
    },
  })
}

export function useMarkAllRecordsRead() {
  const queryClient = useQueryClient()
  
  return useMutation({
    mutationFn: (feedId?: string) => recordsApi.markAllRead(feedId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['records'] })
    },
  })
}

// Health hook
export function useHealth() {
  return useQuery({
    queryKey: queryKeys.health,
    queryFn: healthApi.check,
    refetchInterval: 60000, // Refetch every minute
    retry: 1,
  })
}

// Alert hooks
export function useAlerts() {
  return useQuery({
    queryKey: queryKeys.alerts,
    queryFn: alertsApi.list,
  })
}

export function useAlert(id: string) {
  return useQuery({
    queryKey: queryKeys.alert(id),
    queryFn: () => alertsApi.get(id),
    enabled: !!id,
  })
}

export function useCreateAlert() {
  const queryClient = useQueryClient()
  
  return useMutation({
    mutationFn: (alert: Partial<Alert>) => alertsApi.create(alert),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: queryKeys.alerts })
    },
  })
}

export function useUpdateAlert() {
  const queryClient = useQueryClient()
  
  return useMutation({
    mutationFn: ({ id, alert }: { id: string; alert: Partial<Alert> }) => 
      alertsApi.update(id, alert),
    onSuccess: (_, { id }) => {
      queryClient.invalidateQueries({ queryKey: queryKeys.alerts })
      queryClient.invalidateQueries({ queryKey: queryKeys.alert(id) })
    },
  })
}

export function useDeleteAlert() {
  const queryClient = useQueryClient()
  
  return useMutation({
    mutationFn: (id: string) => alertsApi.delete(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: queryKeys.alerts })
    },
  })
}

export function useToggleAlert() {
  const queryClient = useQueryClient()
  
  return useMutation({
    mutationFn: ({ id, enabled }: { id: string; enabled: boolean }) => 
      alertsApi.toggle(id, enabled),
    onSuccess: (_, { id }) => {
      queryClient.invalidateQueries({ queryKey: queryKeys.alerts })
      queryClient.invalidateQueries({ queryKey: queryKeys.alert(id) })
    },
  })
}

// Notification hooks
export function useNotifications(params?: { unread_only?: boolean; limit?: number; offset?: number }) {
  return useQuery({
    queryKey: queryKeys.notifications(params),
    queryFn: () => notificationsApi.list(params),
    refetchInterval: 30000, // Refetch every 30 seconds
  })
}

export function useNotificationCount() {
  return useQuery({
    queryKey: queryKeys.notificationCount,
    queryFn: notificationsApi.getUnreadCount,
    refetchInterval: 30000,
  })
}

export function useMarkNotificationRead() {
  const queryClient = useQueryClient()
  
  return useMutation({
    mutationFn: (id: string) => notificationsApi.markRead(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['notifications'] })
    },
  })
}

export function useMarkAllNotificationsRead() {
  const queryClient = useQueryClient()
  
  return useMutation({
    mutationFn: () => notificationsApi.markAllRead(),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['notifications'] })
    },
  })
}

export function useDeleteNotification() {
  const queryClient = useQueryClient()
  
  return useMutation({
    mutationFn: (id: string) => notificationsApi.delete(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['notifications'] })
    },
  })
}

// Auth hooks
export function useUser() {
  return useQuery({
    queryKey: queryKeys.user,
    queryFn: authApi.me,
    retry: false,
    staleTime: 5 * 60 * 1000, // 5 minutes
  })
}

export function useLogin() {
  const queryClient = useQueryClient()
  
  return useMutation({
    mutationFn: (credentials: LoginCredentials) => authApi.login(credentials),
    onSuccess: (data) => {
      localStorage.setItem('token', data.access_token)
      localStorage.setItem('refresh_token', data.refresh_token)
      queryClient.invalidateQueries({ queryKey: queryKeys.user })
    },
  })
}

export function useRegister() {
  return useMutation({
    mutationFn: (data: RegisterData) => authApi.register(data),
  })
}

export function useLogout() {
  const queryClient = useQueryClient()
  
  return useMutation({
    mutationFn: () => authApi.logout(),
    onSuccess: () => {
      localStorage.removeItem('token')
      localStorage.removeItem('refresh_token')
      queryClient.clear()
    },
  })
}

export function useRequestPasswordReset() {
  return useMutation({
    mutationFn: (email: string) => authApi.requestPasswordReset(email),
  })
}

export function useResetPassword() {
  return useMutation({
    mutationFn: ({ token, newPassword }: { token: string; newPassword: string }) => 
      authApi.resetPassword(token, newPassword),
  })
}

// Settings hooks
export function useSettings() {
  return useQuery({
    queryKey: queryKeys.settings,
    queryFn: settingsApi.get,
  })
}

export function useUpdateSettings() {
  const queryClient = useQueryClient()
  
  return useMutation({
    mutationFn: (settings: Partial<Settings>) => settingsApi.update(settings),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: queryKeys.settings })
    },
  })
}

// Export types for convenience
export type { Feed, FeedRecord, HealthStatus, Alert, Notification, User, AuthTokens, Settings }
