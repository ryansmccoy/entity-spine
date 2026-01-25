import { useState } from 'react';
import {
  User,
  Mail,
  Phone,
  Building,
  MapPin,
  Calendar,
  Shield,
  Key,
  Smartphone,
  Monitor,
  Clock,
  Edit2,
  Save,
  X,
  Camera,
  CheckCircle,
  Globe,
  Copy,
  Check,
} from 'lucide-react';
import { clsx } from 'clsx';
import { format, formatDistanceToNow } from 'date-fns';

// Types
interface UserProfile {
  id: string;
  email: string;
  firstName: string;
  lastName: string;
  displayName?: string;
  avatarUrl?: string;
  phone?: string;
  company?: string;
  jobTitle?: string;
  location?: string;
  timezone?: string;
  bio?: string;
  createdAt: Date;
  lastLoginAt?: Date;
  emailVerified: boolean;
  role: 'admin' | 'editor' | 'viewer';
}

interface SecuritySettings {
  mfaEnabled: boolean;
  mfaMethod?: 'totp' | 'sms' | 'email';
  passwordLastChanged: Date;
  recoveryEmail?: string;
  recoveryEmailVerified?: boolean;
  trustedDevicesCount: number;
  activeSessionsCount: number;
}

interface Session {
  id: string;
  device: string;
  browser: string;
  os: string;
  ipAddress: string;
  location?: string;
  lastActivity: Date;
  createdAt: Date;
  isCurrent: boolean;
}

interface UserProfilePageProps {
  profile: UserProfile;
  securitySettings: SecuritySettings;
  sessions: Session[];
  isEditing?: boolean;
  onSaveProfile: (profile: Partial<UserProfile>) => Promise<void>;
  onChangePassword: () => void;
  onEnableMFA: () => void;
  onDisableMFA: () => void;
  onRevokeSession: (sessionId: string) => void;
  onRevokeAllSessions: () => void;
  onUpdateAvatar: (file: File) => Promise<void>;
}

// Profile form component
function ProfileForm({
  profile,
  isEditing,
  onSave,
  onCancel,
}: {
  profile: UserProfile;
  isEditing: boolean;
  onSave: (data: Partial<UserProfile>) => void;
  onCancel: () => void;
}) {
  const [formData, setFormData] = useState({
    firstName: profile.firstName,
    lastName: profile.lastName,
    displayName: profile.displayName || '',
    phone: profile.phone || '',
    company: profile.company || '',
    jobTitle: profile.jobTitle || '',
    location: profile.location || '',
    timezone: profile.timezone || Intl.DateTimeFormat().resolvedOptions().timeZone,
    bio: profile.bio || '',
  });

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    onSave(formData);
  };

  const fields = [
    { key: 'firstName', label: 'First Name', icon: User, required: true },
    { key: 'lastName', label: 'Last Name', icon: User, required: true },
    { key: 'displayName', label: 'Display Name', icon: User },
    { key: 'phone', label: 'Phone', icon: Phone, type: 'tel' },
    { key: 'company', label: 'Company', icon: Building },
    { key: 'jobTitle', label: 'Job Title', icon: Building },
    { key: 'location', label: 'Location', icon: MapPin },
  ];

  if (!isEditing) {
    return (
      <div className="space-y-4">
        {fields.map(({ key, label, icon: Icon }) => {
          const value = formData[key as keyof typeof formData];
          if (!value) return null;
          return (
            <div key={key} className="flex items-center gap-3">
              <Icon className="h-5 w-5 text-gray-400" />
              <div>
                <p className="text-xs text-gray-500 dark:text-gray-400">{label}</p>
                <p className="text-sm text-gray-900 dark:text-white">{value}</p>
              </div>
            </div>
          );
        })}
        {formData.bio && (
          <div className="pt-4 border-t border-gray-100 dark:border-gray-700">
            <p className="text-xs text-gray-500 dark:text-gray-400 mb-1">Bio</p>
            <p className="text-sm text-gray-700 dark:text-gray-300">{formData.bio}</p>
          </div>
        )}
      </div>
    );
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-4">
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {fields.map(({ key, label, icon: Icon, required, type }) => (
          <div key={key}>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
              {label} {required && <span className="text-red-500">*</span>}
            </label>
            <div className="relative">
              <Icon className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-gray-400" />
              <input
                type={type || 'text'}
                value={formData[key as keyof typeof formData]}
                onChange={(e) => setFormData({ ...formData, [key]: e.target.value })}
                required={required}
                className="w-full pl-10 pr-3 py-2 text-sm bg-white dark:bg-gray-900 border border-gray-200 dark:border-gray-700 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary-500"
              />
            </div>
          </div>
        ))}
      </div>

      <div>
        <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
          Timezone
        </label>
        <div className="relative">
          <Globe className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-gray-400" />
          <select
            value={formData.timezone}
            onChange={(e) => setFormData({ ...formData, timezone: e.target.value })}
            className="w-full pl-10 pr-3 py-2 text-sm bg-white dark:bg-gray-900 border border-gray-200 dark:border-gray-700 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary-500"
          >
            <option value="America/New_York">Eastern Time (ET)</option>
            <option value="America/Chicago">Central Time (CT)</option>
            <option value="America/Denver">Mountain Time (MT)</option>
            <option value="America/Los_Angeles">Pacific Time (PT)</option>
            <option value="America/Anchorage">Alaska Time (AKT)</option>
            <option value="Pacific/Honolulu">Hawaii Time (HST)</option>
            <option value="UTC">UTC</option>
            <option value="Europe/London">London (GMT/BST)</option>
            <option value="Europe/Paris">Central European (CET)</option>
            <option value="Asia/Tokyo">Japan (JST)</option>
          </select>
        </div>
      </div>

      <div>
        <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
          Bio
        </label>
        <textarea
          value={formData.bio}
          onChange={(e) => setFormData({ ...formData, bio: e.target.value })}
          rows={3}
          maxLength={500}
          className="w-full px-3 py-2 text-sm bg-white dark:bg-gray-900 border border-gray-200 dark:border-gray-700 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary-500 resize-none"
          placeholder="Tell us about yourself..."
        />
        <p className="text-xs text-gray-400 mt-1">{formData.bio.length}/500</p>
      </div>

      <div className="flex items-center justify-end gap-2 pt-4 border-t border-gray-100 dark:border-gray-700">
        <button
          type="button"
          onClick={onCancel}
          className="px-4 py-2 text-sm font-medium text-gray-600 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-800 rounded-lg"
        >
          Cancel
        </button>
        <button
          type="submit"
          className="flex items-center gap-2 px-4 py-2 text-sm font-medium text-white bg-primary-600 hover:bg-primary-700 rounded-lg"
        >
          <Save className="h-4 w-4" />
          Save Changes
        </button>
      </div>
    </form>
  );
}

// Session row component
function SessionRow({
  session,
  onRevoke,
}: {
  session: Session;
  onRevoke: () => void;
}) {
  const deviceIcon = session.device.toLowerCase().includes('mobile') ? Smartphone : Monitor;
  const DeviceIcon = deviceIcon;

  return (
    <div className="flex items-center gap-4 p-4 bg-gray-50 dark:bg-gray-800/50 rounded-lg">
      <div className="p-2 bg-white dark:bg-gray-800 rounded-lg shadow-sm">
        <DeviceIcon className="h-5 w-5 text-gray-600 dark:text-gray-400" />
      </div>
      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-2">
          <p className="text-sm font-medium text-gray-900 dark:text-white">
            {session.browser} on {session.os}
          </p>
          {session.isCurrent && (
            <span className="text-xs bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400 px-2 py-0.5 rounded-full">
              Current
            </span>
          )}
        </div>
        <p className="text-xs text-gray-500 dark:text-gray-400 mt-0.5">
          {session.ipAddress} {session.location && `• ${session.location}`}
        </p>
        <p className="text-xs text-gray-400 mt-0.5">
          Last active {formatDistanceToNow(session.lastActivity, { addSuffix: true })}
        </p>
      </div>
      {!session.isCurrent && (
        <button
          onClick={onRevoke}
          className="text-sm text-red-600 hover:text-red-700 dark:text-red-400 font-medium"
        >
          Revoke
        </button>
      )}
    </div>
  );
}

// Main component
export function UserProfilePage({
  profile,
  securitySettings,
  sessions,
  isEditing: initialEditing = false,
  onSaveProfile,
  onChangePassword,
  onEnableMFA,
  onDisableMFA,
  onRevokeSession,
  onRevokeAllSessions,
  onUpdateAvatar,
}: UserProfilePageProps) {
  const [isEditing, setIsEditing] = useState(initialEditing);
  const [_isSaving, setIsSaving] = useState(false);
  const [copiedId, setCopiedId] = useState(false);
  // Note: isSaving is used for button loading states in future enhancements
  void _isSaving;

  const handleSave = async (data: Partial<UserProfile>) => {
    setIsSaving(true);
    try {
      await onSaveProfile(data);
      setIsEditing(false);
    } finally {
      setIsSaving(false);
    }
  };

  const handleAvatarChange = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) {
      await onUpdateAvatar(file);
    }
  };

  const copyUserId = () => {
    navigator.clipboard.writeText(profile.id);
    setCopiedId(true);
    setTimeout(() => setCopiedId(false), 2000);
  };

  return (
    <div className="max-w-4xl mx-auto space-y-6">
      {/* Profile Header */}
      <div className="bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 p-6">
        <div className="flex items-start gap-6">
          {/* Avatar */}
          <div className="relative group">
            {profile.avatarUrl ? (
              <img
                src={profile.avatarUrl}
                alt={profile.displayName || profile.firstName}
                className="w-24 h-24 rounded-full object-cover"
              />
            ) : (
              <div className="w-24 h-24 rounded-full bg-gradient-to-br from-primary-400 to-primary-600 flex items-center justify-center text-3xl font-bold text-white">
                {profile.firstName.charAt(0)}{profile.lastName.charAt(0)}
              </div>
            )}
            <label className="absolute inset-0 flex items-center justify-center bg-black/50 rounded-full opacity-0 group-hover:opacity-100 transition-opacity cursor-pointer">
              <Camera className="h-6 w-6 text-white" />
              <input
                type="file"
                accept="image/*"
                className="hidden"
                onChange={handleAvatarChange}
              />
            </label>
          </div>

          {/* Info */}
          <div className="flex-1">
            <div className="flex items-center justify-between">
              <div>
                <h1 className="text-2xl font-bold text-gray-900 dark:text-white">
                  {profile.displayName || `${profile.firstName} ${profile.lastName}`}
                </h1>
                <div className="flex items-center gap-2 mt-1">
                  <Mail className="h-4 w-4 text-gray-400" />
                  <span className="text-sm text-gray-600 dark:text-gray-400">{profile.email}</span>
                  {profile.emailVerified && (
                    <span title="Verified">
                      <CheckCircle className="h-4 w-4 text-green-500" />
                    </span>
                  )}
                </div>
              </div>
              <button
                onClick={() => setIsEditing(!isEditing)}
                className="flex items-center gap-2 px-4 py-2 text-sm font-medium text-gray-700 dark:text-gray-200 bg-gray-100 dark:bg-gray-700 hover:bg-gray-200 dark:hover:bg-gray-600 rounded-lg"
              >
                {isEditing ? <X className="h-4 w-4" /> : <Edit2 className="h-4 w-4" />}
                {isEditing ? 'Cancel' : 'Edit Profile'}
              </button>
            </div>

            <div className="flex items-center gap-4 mt-4 text-sm text-gray-500 dark:text-gray-400">
              <span className={clsx(
                'px-2 py-0.5 rounded text-xs font-semibold uppercase',
                profile.role === 'admin' && 'bg-purple-100 text-purple-700 dark:bg-purple-900/30 dark:text-purple-400',
                profile.role === 'editor' && 'bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-400',
                profile.role === 'viewer' && 'bg-gray-100 text-gray-700 dark:bg-gray-700 dark:text-gray-300'
              )}>
                {profile.role}
              </span>
              <span className="flex items-center gap-1">
                <Calendar className="h-4 w-4" />
                Joined {format(profile.createdAt, 'MMM yyyy')}
              </span>
              {profile.lastLoginAt && (
                <span className="flex items-center gap-1">
                  <Clock className="h-4 w-4" />
                  Last login {formatDistanceToNow(profile.lastLoginAt, { addSuffix: true })}
                </span>
              )}
            </div>

            <div className="flex items-center gap-2 mt-3">
              <span className="text-xs text-gray-400 font-mono">ID: {profile.id}</span>
              <button
                onClick={copyUserId}
                className="text-gray-400 hover:text-gray-600"
                title="Copy user ID"
              >
                {copiedId ? <Check className="h-3 w-3 text-green-500" /> : <Copy className="h-3 w-3" />}
              </button>
            </div>
          </div>
        </div>

        {/* Profile Form */}
        <div className="mt-6 pt-6 border-t border-gray-100 dark:border-gray-700">
          <ProfileForm
            profile={profile}
            isEditing={isEditing}
            onSave={handleSave}
            onCancel={() => setIsEditing(false)}
          />
        </div>
      </div>

      {/* Security Settings */}
      <div className="bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 p-6">
        <div className="flex items-center gap-2 mb-6">
          <Shield className="h-5 w-5 text-gray-400" />
          <h2 className="text-lg font-semibold text-gray-900 dark:text-white">Security</h2>
        </div>

        <div className="space-y-4">
          {/* Password */}
          <div className="flex items-center justify-between p-4 bg-gray-50 dark:bg-gray-800/50 rounded-lg">
            <div className="flex items-center gap-3">
              <div className="p-2 bg-white dark:bg-gray-800 rounded-lg">
                <Key className="h-5 w-5 text-gray-600 dark:text-gray-400" />
              </div>
              <div>
                <p className="text-sm font-medium text-gray-900 dark:text-white">Password</p>
                <p className="text-xs text-gray-500 dark:text-gray-400">
                  Last changed {formatDistanceToNow(securitySettings.passwordLastChanged, { addSuffix: true })}
                </p>
              </div>
            </div>
            <button
              onClick={onChangePassword}
              className="text-sm text-primary-600 hover:text-primary-700 dark:text-primary-400 font-medium"
            >
              Change password
            </button>
          </div>

          {/* MFA */}
          <div className="flex items-center justify-between p-4 bg-gray-50 dark:bg-gray-800/50 rounded-lg">
            <div className="flex items-center gap-3">
              <div className="p-2 bg-white dark:bg-gray-800 rounded-lg">
                <Smartphone className="h-5 w-5 text-gray-600 dark:text-gray-400" />
              </div>
              <div>
                <p className="text-sm font-medium text-gray-900 dark:text-white">
                  Two-Factor Authentication
                </p>
                <p className="text-xs text-gray-500 dark:text-gray-400">
                  {securitySettings.mfaEnabled
                    ? `Enabled via ${securitySettings.mfaMethod === 'totp' ? 'Authenticator App' : securitySettings.mfaMethod}`
                    : 'Add an extra layer of security'}
                </p>
              </div>
            </div>
            {securitySettings.mfaEnabled ? (
              <div className="flex items-center gap-2">
                <span className="flex items-center gap-1 text-xs text-green-600 dark:text-green-400">
                  <CheckCircle className="h-4 w-4" /> Enabled
                </span>
                <button
                  onClick={onDisableMFA}
                  className="text-sm text-red-600 hover:text-red-700 dark:text-red-400 font-medium"
                >
                  Disable
                </button>
              </div>
            ) : (
              <button
                onClick={onEnableMFA}
                className="text-sm text-primary-600 hover:text-primary-700 dark:text-primary-400 font-medium"
              >
                Enable
              </button>
            )}
          </div>

          {/* Recovery Email */}
          <div className="flex items-center justify-between p-4 bg-gray-50 dark:bg-gray-800/50 rounded-lg">
            <div className="flex items-center gap-3">
              <div className="p-2 bg-white dark:bg-gray-800 rounded-lg">
                <Mail className="h-5 w-5 text-gray-600 dark:text-gray-400" />
              </div>
              <div>
                <p className="text-sm font-medium text-gray-900 dark:text-white">Recovery Email</p>
                <p className="text-xs text-gray-500 dark:text-gray-400">
                  {securitySettings.recoveryEmail || 'Not set - recommended for account recovery'}
                </p>
              </div>
            </div>
            <button className="text-sm text-primary-600 hover:text-primary-700 dark:text-primary-400 font-medium">
              {securitySettings.recoveryEmail ? 'Change' : 'Add'}
            </button>
          </div>
        </div>
      </div>

      {/* Active Sessions */}
      <div className="bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 p-6">
        <div className="flex items-center justify-between mb-6">
          <div className="flex items-center gap-2">
            <Monitor className="h-5 w-5 text-gray-400" />
            <h2 className="text-lg font-semibold text-gray-900 dark:text-white">
              Active Sessions
            </h2>
            <span className="text-xs bg-gray-100 text-gray-600 dark:bg-gray-700 dark:text-gray-400 px-2 py-0.5 rounded-full">
              {sessions.length}
            </span>
          </div>
          {sessions.length > 1 && (
            <button
              onClick={onRevokeAllSessions}
              className="text-sm text-red-600 hover:text-red-700 dark:text-red-400 font-medium"
            >
              Sign out all other sessions
            </button>
          )}
        </div>

        <div className="space-y-3">
          {sessions.map((session) => (
            <SessionRow
              key={session.id}
              session={session}
              onRevoke={() => onRevokeSession(session.id)}
            />
          ))}
        </div>
      </div>
    </div>
  );
}

export default UserProfilePage;
