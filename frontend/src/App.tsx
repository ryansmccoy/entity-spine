import { Routes, Route, Navigate } from 'react-router-dom'
import { AdminLayout } from './layouts/AdminLayout'
import { NewsfeedPage } from './pages/NewsfeedPage'
import { DashboardPage } from './pages/DashboardPage'
import { SettingsPage } from './pages/SettingsPage'
import { FeedsPage } from './pages/FeedsPage'
import { NotificationsPage } from './pages/NotificationsPage'
import AlertsPage from './pages/AlertsPage'
import LoginPage from './pages/LoginPage'
import RegisterPage from './pages/RegisterPage'
import ForgotPasswordPage from './pages/ForgotPasswordPage'
import EntityGraphPage from './pages/EntityGraphPage'
import IndustryExplorerPage from './pages/IndustryExplorerPage'
import UserProfilePage from './pages/UserProfilePage'
import MessagingPage from './pages/MessagingPage'
import TodayPage from './pages/TodayPage'
import AdminPage from './pages/AdminPage'
import ResearchPage from './pages/ResearchPage'

// Placeholder for TradingPage until implemented
const TradingPage = () => <div className="p-8"><h1 className="text-2xl font-bold">Trading Center</h1><p className="text-gray-500 mt-2">Coming soon - see docs/marketspine/TRADING_CENTER.md</p></div>

function App() {
  return (
    <Routes>
      {/* Auth routes (public) */}
      <Route path="/login" element={<LoginPage />} />
      <Route path="/register" element={<RegisterPage />} />
      <Route path="/forgot-password" element={<ForgotPasswordPage />} />
      
      {/* Main app routes */}
      <Route path="/" element={<AdminLayout />}>
        <Route index element={<Navigate to="/dashboard" replace />} />
        <Route path="dashboard" element={<DashboardPage />} />
        <Route path="newsfeed" element={<NewsfeedPage />} />
        <Route path="today" element={<TodayPage />} />
        <Route path="trading" element={<TradingPage />} />
        <Route path="research" element={<ResearchPage />} />
        <Route path="feeds" element={<FeedsPage />} />
        <Route path="notifications" element={<NotificationsPage />} />
        <Route path="alerts" element={<AlertsPage />} />
        <Route path="messages" element={<MessagingPage />} />
        <Route path="profile" element={<UserProfilePage />} />
        <Route path="admin" element={<AdminPage />} />
        <Route path="settings" element={<SettingsPage />} />
      </Route>
      
      {/* Full-screen entity graph (no layout) */}
      <Route path="/graph" element={<EntityGraphPage />} />
      
      {/* Industry Explorer - Bloomberg-style dashboard */}
      <Route path="/explore" element={<IndustryExplorerPage />} />
    </Routes>
  )
}

export default App
