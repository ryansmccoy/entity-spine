# Admin Dashboard Features Roadmap

## Overview
Features organized by category for a complete admin dashboard experience, inspired by Django Admin, WordPress, and enterprise feed readers.

---

## 1. User Management & Security 🔐

### User Profiles
- [ ] Profile page with avatar upload
- [ ] Display name, email, timezone
- [ ] Account creation date
- [ ] Last login info
- [ ] Activity summary

### Multi-Factor Authentication (MFA)
- [ ] TOTP (Google Authenticator, Authy)
- [ ] Backup codes generation
- [ ] SMS fallback (optional)
- [ ] Remember trusted devices (30 days)
- [ ] Force MFA for admin accounts

### Password & Recovery
- [ ] Password strength meter
- [ ] Password history (prevent reuse)
- [ ] Secure password reset via email
- [ ] Account lockout after failed attempts
- [ ] Security questions (optional)

### Session Management
- [ ] View all active sessions
- [ ] Device/browser info per session
- [ ] IP address & location
- [ ] "Sign out all devices" button
- [ ] Session timeout settings

### Security Audit Log
- [ ] Login attempts (success/failed)
- [ ] Password changes
- [ ] Permission changes
- [ ] API key usage
- [ ] Export audit logs

---

## 2. Admin Dashboard Widgets 📊

### Active Users Widget
- [ ] Currently online users count
- [ ] Online users list with avatars
- [ ] Last activity timestamp
- [ ] "Online now" indicator in header

### Security Overview
- [ ] Failed login attempts (24h/7d/30d)
- [ ] Suspicious activity alerts
- [ ] New user registrations
- [ ] Password reset requests
- [ ] Locked accounts count

### System Health
- [ ] Database connection status
- [ ] Feed polling status
- [ ] Queue lengths
- [ ] Error rates
- [ ] API response times

### Activity Feed
- [ ] Recent user actions
- [ ] Feed updates
- [ ] Alert triggers
- [ ] System events
- [ ] Filterable by type/user

### Quick Stats Cards
- [ ] Total users
- [ ] Active feeds
- [ ] Records captured today
- [ ] Alerts triggered today
- [ ] Storage usage

---

## 3. Content Preview Improvements 📄

### Preview Panel Header
- [ ] Move "View Site" button to top
- [ ] "Open in New Tab" at top
- [ ] Copy link button
- [ ] Share button
- [ ] Print/PDF export

### Rich Preview Content
- [ ] Filing metadata (CIK, form type, filing date)
- [ ] Company info (name, ticker, industry)
- [ ] Document links (HTML, PDF, exhibits)
- [ ] Related filings
- [ ] Historical filings by same company

### Preview Actions
- [ ] Mark as read/unread
- [ ] Star/bookmark
- [ ] Add to collection/folder
- [ ] Add notes/annotations
- [ ] Send to email

### "Not Yet Captured" State
- [ ] Show filing summary from RSS
- [ ] Estimated capture time
- [ ] "Capture Now" button
- [ ] Queue position indicator
- [ ] Link to original source

---

## 4. Today View / Discovery 🌟

### Today's Highlights
- [ ] Latest 10 articles across all feeds
- [ ] Configurable "latest" count
- [ ] Auto-refresh toggle
- [ ] Time-based grouping (Last hour, today, yesterday)

### Popular/Trending
- [ ] Most viewed articles (by all users)
- [ ] Most starred articles
- [ ] Most shared articles
- [ ] Trending form types
- [ ] Trending companies

### Smart Views
- [ ] Unread count by feed
- [ ] Starred items
- [ ] Recently viewed
- [ ] "Read Later" queue
- [ ] Custom saved searches

---

## 5. Feed Group Management 📁

### Group Operations
- [ ] Create new group
- [ ] Rename group (inline edit)
- [ ] Delete group (with confirmation)
- [ ] Group color/icon customization
- [ ] Group description

### Drag & Drop
- [ ] Reorder groups
- [ ] Reorder feeds within groups
- [ ] Move feeds between groups
- [ ] Collapse/expand individual groups
- [ ] Collapse/expand all groups

### Group Settings
- [ ] Default view mode per group
- [ ] Notification settings per group
- [ ] Retention settings per group
- [ ] Auto-archive rules

### Bulk Operations
- [ ] Select multiple feeds
- [ ] Bulk move to group
- [ ] Bulk enable/disable
- [ ] Bulk delete
- [ ] Bulk refresh

---

## 6. User Messaging & Collaboration 💬

### Internal Messaging
- [ ] Direct messages between users
- [ ] Message inbox/sent
- [ ] Unread message indicator
- [ ] Message notifications

### Article Sharing
- [ ] Share article with team member
- [ ] Add note when sharing
- [ ] Shared with me view
- [ ] Share via email

### Comments & Annotations
- [ ] Comment on articles
- [ ] Team-visible annotations
- [ ] @mentions in comments
- [ ] Comment notifications

---

## 7. API & Integrations 🔌

### API Keys Management
- [ ] Generate API keys
- [ ] Key permissions/scopes
- [ ] Usage statistics
- [ ] Revoke keys
- [ ] Rate limit settings

### Webhooks
- [ ] Outgoing webhook configuration
- [ ] Webhook delivery logs
- [ ] Retry failed webhooks
- [ ] Webhook templates (Slack, Discord, Teams)

### Import/Export
- [ ] OPML import/export
- [ ] CSV export of records
- [ ] Backup/restore settings
- [ ] Data export (GDPR)

---

## 8. Appearance & Personalization 🎨

### Theme Settings
- [ ] Light/Dark/System mode
- [ ] Accent color picker
- [ ] Font size adjustment
- [ ] Compact/comfortable density

### Layout Preferences
- [ ] Default view mode
- [ ] Sidebar position
- [ ] Panel sizes (remembered)
- [ ] Column visibility (table view)

### Keyboard Shortcuts
- [ ] Keyboard shortcut reference
- [ ] Customizable shortcuts
- [ ] Vim-style navigation (optional)

---

## Implementation Priority

### Phase 1 (Core) 🎯
1. Preview panel improvements
2. Feed group management (reorder, collapse)
3. Today view / Latest articles
4. User profile page
5. Session management

### Phase 2 (Security) 🔒
1. MFA/2FA setup
2. Security audit log
3. Failed login tracking
4. Account lockout
5. Password policies

### Phase 3 (Dashboard) 📈
1. Admin dashboard widgets
2. Active users tracking
3. System health monitoring
4. Activity feed

### Phase 4 (Collaboration) 👥
1. Internal messaging
2. Article sharing
3. Comments/annotations
4. API keys management

---

## Database Schema Additions

```sql
-- User profiles
ALTER TABLE users ADD COLUMN avatar_url TEXT;
ALTER TABLE users ADD COLUMN timezone TEXT DEFAULT 'UTC';
ALTER TABLE users ADD COLUMN preferences JSONB DEFAULT '{}';

-- MFA
CREATE TABLE user_mfa (
    user_id UUID PRIMARY KEY REFERENCES users(user_id),
    totp_secret TEXT,
    backup_codes TEXT[],
    enabled_at TIMESTAMPTZ,
    last_used_at TIMESTAMPTZ
);

-- Trusted devices
CREATE TABLE trusted_devices (
    device_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(user_id),
    device_fingerprint TEXT NOT NULL,
    device_name TEXT,
    trusted_until TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Security audit log
CREATE TABLE security_audit (
    audit_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(user_id),
    event_type TEXT NOT NULL,
    ip_address INET,
    user_agent TEXT,
    details JSONB,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Feed groups
CREATE TABLE feed_groups (
    group_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(user_id),
    name TEXT NOT NULL,
    color TEXT,
    icon TEXT,
    sort_order INTEGER DEFAULT 0,
    is_collapsed BOOLEAN DEFAULT false,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Feed to group mapping
ALTER TABLE feeds ADD COLUMN group_id UUID REFERENCES feed_groups(group_id);
ALTER TABLE feeds ADD COLUMN sort_order INTEGER DEFAULT 0;

-- Messages
CREATE TABLE messages (
    message_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    from_user_id UUID REFERENCES users(user_id),
    to_user_id UUID REFERENCES users(user_id),
    subject TEXT,
    body TEXT NOT NULL,
    read_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Shared articles
CREATE TABLE shared_articles (
    share_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    record_id UUID REFERENCES records(record_id),
    from_user_id UUID REFERENCES users(user_id),
    to_user_id UUID REFERENCES users(user_id),
    note TEXT,
    read_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Article comments
CREATE TABLE article_comments (
    comment_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    record_id UUID REFERENCES records(record_id),
    user_id UUID REFERENCES users(user_id),
    parent_id UUID REFERENCES article_comments(comment_id),
    body TEXT NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);
```
