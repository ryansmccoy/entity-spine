# SettingsPage - API Requirements

## Overview

The SettingsPage allows users to configure application preferences, display settings, and manage their account.

## Current Status: ⚠️ Partial - Using localStorage

Settings are likely stored in localStorage only, not persisted to backend.

---

## Required API Endpoints

### 1. Get Settings

**Endpoint:** `GET /api/settings`

**Used For:** Loading user preferences

**Expected Response:**
```json
{
  "display": {
    "theme": "system",
    "text_size": "sm",
    "article_spacing": "comfortable",
    "default_view_mode": "condensed",
    "show_feed_icons": true,
    "show_tags": true,
    "date_format": "relative"
  },
  "behavior": {
    "keyboard_shortcuts": true,
    "mark_read_on_scroll": false,
    "mark_read_on_open": true,
    "open_links_in_new_tab": true,
    "default_sort": "published_at",
    "default_sort_order": "desc"
  },
  "feeds": {
    "default_poll_interval": 300,
    "max_records_per_feed": 1000,
    "auto_cleanup_days": 30
  },
  "notifications": {
    "enabled": true,
    "sound": false,
    "desktop": true,
    "email_digest": "daily"
  }
}
```

**Frontend Hook:** `useSettings()` - NEEDS TO BE ADDED

---

### 2. Update Settings

**Endpoint:** `PUT /api/settings`

**Used For:** Saving user preferences

**Request Body:** (partial update supported)
```json
{
  "display": {
    "theme": "dark"
  }
}
```

**Response:** Updated settings object

**Frontend Hook:** `useUpdateSettings()` - NEEDS TO BE ADDED

---

### 3. Reset Settings

**Endpoint:** `POST /api/settings/reset`

**Used For:** Reset all settings to defaults

**Response:** Default settings object

---

### 4. Export User Data

**Endpoint:** `GET /api/settings/export`

**Used For:** GDPR-compliant data export

**Response:** JSON file download with all user data

---

### 5. Delete Account (Multi-user)

**Endpoint:** `DELETE /api/users/me`

**Used For:** Account deletion

**Response:** `204 No Content`

---

## Settings Categories

### Display Settings

| Setting | Type | Default | Description |
|---------|------|---------|-------------|
| `theme` | string | "system" | "light", "dark", "system" |
| `text_size` | string | "sm" | "xs", "sm", "md", "lg" |
| `article_spacing` | string | "comfortable" | "compact", "comfortable", "relaxed" |
| `default_view_mode` | string | "condensed" | "condensed", "comfortable", "headlines", "cards", "table" |
| `show_feed_icons` | boolean | true | Show emoji icons in feed list |
| `show_tags` | boolean | true | Show tags on articles |
| `date_format` | string | "relative" | "relative", "absolute", "both" |

### Behavior Settings

| Setting | Type | Default | Description |
|---------|------|---------|-------------|
| `keyboard_shortcuts` | boolean | true | Enable j/k navigation, etc. |
| `mark_read_on_scroll` | boolean | false | Auto-mark as read when scrolled past |
| `mark_read_on_open` | boolean | true | Mark as read when article opened |
| `open_links_in_new_tab` | boolean | true | External links open in new tab |
| `default_sort` | string | "published_at" | "published_at", "captured_at", "title" |
| `default_sort_order` | string | "desc" | "asc", "desc" |

### Feed Settings

| Setting | Type | Default | Description |
|---------|------|---------|-------------|
| `default_poll_interval` | number | 300 | Default poll interval for new feeds (seconds) |
| `max_records_per_feed` | number | 1000 | Max records to keep per feed |
| `auto_cleanup_days` | number | 30 | Delete unread records older than X days |

### Notification Settings

| Setting | Type | Default | Description |
|---------|------|---------|-------------|
| `enabled` | boolean | true | Enable notifications |
| `sound` | boolean | false | Play sound on new items |
| `desktop` | boolean | true | Show desktop notifications |
| `email_digest` | string | "never" | "never", "daily", "weekly" |

---

## Implementation Checklist

### Backend Changes Needed

- [ ] Implement `GET /api/settings` endpoint
- [ ] Implement `PUT /api/settings` endpoint
- [ ] Implement `POST /api/settings/reset` endpoint
- [ ] Implement `GET /api/settings/export` endpoint
- [ ] Add settings table if not using key-value
- [ ] Add user-scoped settings for multi-user

### Frontend Changes Needed

- [ ] Add `useSettings()` hook
- [ ] Add `useUpdateSettings()` hook
- [ ] Create SettingsForm component with sections
- [ ] Add theme toggle that syncs with API
- [ ] Add keyboard shortcuts toggle
- [ ] Add data export button
- [ ] Sync localStorage with API settings

---

## Settings Page Layout

```
┌─────────────────────────────────────────────────────────────────────┐
│                          SETTINGS                                    │
├─────────────────────────────────────────────────────────────────────┤
│                                                                      │
│  Display                                                             │
│  ├─────────────────────────────────────────────────────────────────┤│
│  │ Theme          [Light ▾] [Dark] [System ●]                      ││
│  │ Text Size      [xs] [sm ●] [md] [lg]                            ││
│  │ Spacing        [Compact] [Comfortable ●] [Relaxed]              ││
│  │ Default View   [Condensed ▾]                                    ││
│  │ Show Icons     [✓]                                              ││
│  │ Show Tags      [✓]                                              ││
│  └─────────────────────────────────────────────────────────────────┘│
│                                                                      │
│  Behavior                                                            │
│  ├─────────────────────────────────────────────────────────────────┤│
│  │ Keyboard Shortcuts     [✓]                                      ││
│  │ Mark Read on Scroll    [ ]                                      ││
│  │ Mark Read on Open      [✓]                                      ││
│  │ Open Links in New Tab  [✓]                                      ││
│  └─────────────────────────────────────────────────────────────────┘│
│                                                                      │
│  Feeds                                                               │
│  ├─────────────────────────────────────────────────────────────────┤│
│  │ Default Poll Interval  [5 minutes ▾]                            ││
│  │ Max Records per Feed   [1000]                                   ││
│  │ Auto-cleanup           [30 days ▾]                              ││
│  └─────────────────────────────────────────────────────────────────┘│
│                                                                      │
│  [Reset to Defaults]                         [Save Changes]          │
│                                                                      │
└─────────────────────────────────────────────────────────────────────┘
```
