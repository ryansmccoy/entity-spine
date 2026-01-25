import { useState } from 'react';
import { AdminDashboard } from '../components/AdminDashboard';

// Sample data for development - will be replaced with API hooks
const generateSampleData = () => {
  const now = new Date();
  
  const activeUsers = [
    { id: '1', name: 'John Smith', email: 'john@example.com', lastActivity: new Date(now.getTime() - 2 * 60 * 1000), status: 'online' as const, currentPage: 'Newsfeed', ipAddress: '192.168.1.105', device: 'Desktop' },
    { id: '2', name: 'Sarah Johnson', email: 'sarah@example.com', lastActivity: new Date(now.getTime() - 5 * 60 * 1000), status: 'online' as const, currentPage: 'Dashboard', ipAddress: '192.168.1.108', device: 'Mobile' },
    { id: '3', name: 'Mike Brown', email: 'mike@example.com', lastActivity: new Date(now.getTime() - 15 * 60 * 1000), status: 'idle' as const, currentPage: 'Feeds', ipAddress: '192.168.1.112', device: 'Desktop' },
    { id: '4', name: 'Emily Davis', email: 'emily@example.com', lastActivity: new Date(now.getTime() - 30 * 60 * 1000), status: 'idle' as const, currentPage: 'Settings', ipAddress: '10.0.0.55', device: 'Tablet' },
    { id: '5', name: 'Robert Wilson', email: 'robert@example.com', lastActivity: new Date(now.getTime() - 60 * 60 * 1000), status: 'offline' as const, currentPage: undefined, ipAddress: '172.16.0.22', device: 'Desktop' },
  ];

  const recentLogins = [
    { id: '1', email: 'john@example.com', success: true, timestamp: new Date(now.getTime() - 10 * 60 * 1000), ipAddress: '192.168.1.105', userAgent: 'Chrome/120', location: 'New York, US' },
    { id: '2', email: 'unknown@attacker.com', success: false, timestamp: new Date(now.getTime() - 25 * 60 * 1000), ipAddress: '45.227.34.102', userAgent: 'Python/3.9', reason: 'Invalid credentials', location: 'Unknown' },
    { id: '3', email: 'sarah@example.com', success: true, timestamp: new Date(now.getTime() - 35 * 60 * 1000), ipAddress: '192.168.1.108', userAgent: 'Safari/17', location: 'Los Angeles, US' },
    { id: '4', email: 'mike@example.com', success: false, timestamp: new Date(now.getTime() - 50 * 60 * 1000), ipAddress: '192.168.1.112', userAgent: 'Chrome/120', reason: 'Wrong password', location: 'Chicago, US' },
    { id: '5', email: 'mike@example.com', success: true, timestamp: new Date(now.getTime() - 52 * 60 * 1000), ipAddress: '192.168.1.112', userAgent: 'Chrome/120', location: 'Chicago, US' },
    { id: '6', email: 'emily@example.com', success: true, timestamp: new Date(now.getTime() - 90 * 60 * 1000), ipAddress: '10.0.0.55', userAgent: 'Firefox/121', location: 'Seattle, US' },
  ];

  const securityEvents = [
    { id: '1', type: 'login' as const, userId: '1', userName: 'John Smith', description: 'Logged in from new device', timestamp: new Date(now.getTime() - 10 * 60 * 1000), ipAddress: '192.168.1.105', severity: 'info' as const },
    { id: '2', type: 'password_change' as const, userId: '3', userName: 'Mike Brown', description: 'Password changed', timestamp: new Date(now.getTime() - 2 * 60 * 60 * 1000), severity: 'info' as const },
    { id: '3', type: 'mfa_enabled' as const, userId: '2', userName: 'Sarah Johnson', description: 'Enabled two-factor authentication', timestamp: new Date(now.getTime() - 5 * 60 * 60 * 1000), severity: 'info' as const },
    { id: '4', type: 'account_locked' as const, userId: '6', userName: 'Test User', description: 'Account locked after 5 failed attempts', timestamp: new Date(now.getTime() - 8 * 60 * 60 * 1000), severity: 'critical' as const },
    { id: '5', type: 'api_key_created' as const, userId: '1', userName: 'John Smith', description: 'Created new API key', timestamp: new Date(now.getTime() - 12 * 60 * 60 * 1000), severity: 'warning' as const },
    { id: '6', type: 'permission_change' as const, userId: '4', userName: 'Emily Davis', description: 'Role changed from Viewer to Editor', timestamp: new Date(now.getTime() - 24 * 60 * 60 * 1000), severity: 'warning' as const },
  ];

  const stats = {
    totalUsers: 156,
    activeUsers: 23,
    newUsersToday: 5,
    newUsersChange: 25,
    failedLogins24h: 12,
    failedLoginsChange: -15,
    lockedAccounts: 1,
    pendingInvites: 8,
  };

  return { activeUsers, recentLogins, securityEvents, stats };
};

export function AdminPage() {
  const [data, setData] = useState(generateSampleData);
  const [isLoading, setIsLoading] = useState(false);

  const handleRefresh = () => {
    setIsLoading(true);
    // Simulate API call
    setTimeout(() => {
      setData(generateSampleData());
      setIsLoading(false);
    }, 1000);
  };

  const handleViewUser = (userId: string) => {
    console.log('View user:', userId);
    // Navigate to user profile or open modal
  };

  const handleUnlockAccount = (userId: string) => {
    console.log('Unlock account:', userId);
    // Call API to unlock account
  };

  const handleExportLogs = () => {
    console.log('Exporting logs...');
    // Generate and download logs
  };

  return (
    <div className="p-6">
      <AdminDashboard
        stats={data.stats}
        activeUsers={data.activeUsers}
        recentLogins={data.recentLogins}
        securityEvents={data.securityEvents}
        isLoading={isLoading}
        onRefresh={handleRefresh}
        onViewUser={handleViewUser}
        onUnlockAccount={handleUnlockAccount}
        onExportLogs={handleExportLogs}
      />
    </div>
  );
}

export default AdminPage;
