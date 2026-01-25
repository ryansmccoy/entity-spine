# NotificationsPage - API Requirements

## Overview

The NotificationsPage displays system notifications, alerts triggered by rules, and activity history.

## Current Status: ❌ Not Implemented

The notifications system needs to be built from scratch.

---

## Required API Endpoints

### 1. List Notifications

**Endpoint:** `GET /api/notifications`

**Used For:** Displaying notification list

**Query Parameters:**
| Parameter | Type | Description |
|-----------|------|-------------|
| `unread_only` | boolean | Show only unread |
| `type` | string | Filter by type |
| `limit` | number | Page size (default: 50) |
| `offset` | number | Pagination offset |

**Expected Response:**
```json
{
  "notifications": [
    {
      "id": "uuid",
      "type": "alert_triggered",
      "title": "New Apple 10-K Filing",
      "message": "Apple Inc. filed their annual report (10-K)",
      "read": false,
      "created_at": "2026-01-27T12:00:00Z",
      "metadata": {
        "alert_id": "uuid",
        "record_id": "uuid",
        "record_title": "Apple Inc. - 10-K"
      },
      "actions": [
        { "label": "View", "action": "open_record", "params": { "id": "uuid" } },
        { "label": "Dismiss", "action": "dismiss" }
      ]
    },
    {
      "id": "uuid",
      "type": "feed_error",
      "title": "Feed Error: HN Feed",
      "message": "Failed to poll feed: Connection timeout",
      "read": true,
      "created_at": "2026-01-27T11:55:00Z",
      "metadata": {
        "feed_id": "uuid",
        "error": "Connection timeout"
      }
    },
    {
      "id": "uuid",
      "type": "system",
      "title": "Welcome to Capture Spine!",
      "message": "Get started by adding your first feed.",
      "read": true,
      "created_at": "2026-01-01T00:00:00Z"
    }
  ],
  "total": 156,
  "unread_count": 12,
  "has_more": true
}
```

**Notification Types:**
- `alert_triggered` - Alert rule matched a record
- `feed_error` - Feed polling error
- `feed_recovered` - Feed recovered from error
- `system` - System messages
- `digest` - Daily/weekly digest

**Frontend Hook:** `useNotifications()` - NEEDS TO BE ADDED

---

### 2. Mark Notification as Read

**Endpoint:** `POST /api/notifications/{id}/read`

**Used For:** Mark single notification as read

**Response:** `204 No Content`

**Frontend Hook:** `useMarkNotificationRead()` - NEEDS TO BE ADDED

---

### 3. Mark All Notifications as Read

**Endpoint:** `POST /api/notifications/read-all`

**Used For:** Mark all notifications as read

**Response:** 
```json
{
  "marked": 12
}
```

---

### 4. Dismiss Notification

**Endpoint:** `DELETE /api/notifications/{id}`

**Used For:** Remove notification from list

**Response:** `204 No Content`

---

### 5. Clear All Notifications

**Endpoint:** `DELETE /api/notifications`

**Used For:** Clear all notifications

**Query Parameters:**
- `read_only`: boolean - Only clear read notifications

**Response:**
```json
{
  "deleted": 144
}
```

---

### 6. Get Unread Count

**Endpoint:** `GET /api/notifications/count`

**Used For:** Badge in navigation

**Response:**
```json
{
  "unread": 12
}
```

**Frontend Hook:** `useNotificationCount()` - NEEDS TO BE ADDED

---

## Alerts System

Alerts are rules that generate notifications when conditions are met.

### 7. List Alerts

**Endpoint:** `GET /api/alerts`

**Used For:** Managing alert rules

**Expected Response:**
```json
{
  "alerts": [
    {
      "id": "uuid",
      "name": "Apple Filings",
      "enabled": true,
      "conditions": {
        "feed_ids": ["uuid"],
        "keywords": ["Apple", "AAPL"],
        "form_types": ["10-K", "10-Q", "8-K"]
      },
      "actions": {
        "notify": true,
        "email": false,
        "webhook": null
      },
      "triggered_count": 45,
      "last_triggered_at": "2026-01-27T12:00:00Z",
      "created_at": "2026-01-15T00:00:00Z"
    }
  ]
}
```

**Frontend Hook:** `useAlerts()` - NEEDS TO BE ADDED

---

### 8. Create Alert

**Endpoint:** `POST /api/alerts`

**Used For:** Creating new alert rules

**Request Body:**
```json
{
  "name": "Tech News Keywords",
  "enabled": true,
  "conditions": {
    "feed_ids": [],
    "keywords": ["AI", "machine learning", "GPT"],
    "form_types": [],
    "company_names": [],
    "tickers": []
  },
  "actions": {
    "notify": true,
    "email": false,
    "webhook": null
  }
}
```

**Condition Types:**
- `feed_ids` - Match specific feeds (empty = all)
- `keywords` - Text search in title/summary
- `form_types` - SEC form types (10-K, 8-K, etc.)
- `company_names` - Match company names
- `tickers` - Match stock tickers

**Response:** Created alert object

**Frontend Hook:** `useCreateAlert()` - NEEDS TO BE ADDED

---

### 9. Update Alert

**Endpoint:** `PUT /api/alerts/{id}`

**Response:** Updated alert object

**Frontend Hook:** `useUpdateAlert()` - NEEDS TO BE ADDED

---

### 10. Delete Alert

**Endpoint:** `DELETE /api/alerts/{id}`

**Response:** `204 No Content`

**Frontend Hook:** `useDeleteAlert()` - NEEDS TO BE ADDED

---

### 11. Test Alert

**Endpoint:** `POST /api/alerts/{id}/test`

**Used For:** Test alert against recent records

**Response:**
```json
{
  "would_match": 5,
  "sample_matches": [
    { "record_id": "uuid", "title": "..." }
  ]
}
```

---

## Implementation Checklist

### Database Changes Needed

```sql
-- Notifications table
CREATE TABLE notifications (
    notification_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(user_id),  -- for multi-user
    type TEXT NOT NULL,
    title TEXT NOT NULL,
    message TEXT,
    read BOOLEAN DEFAULT false,
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Alerts table
CREATE TABLE alerts (
    alert_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(user_id),  -- for multi-user
    name TEXT NOT NULL,
    enabled BOOLEAN DEFAULT true,
    conditions JSONB NOT NULL,
    actions JSONB NOT NULL DEFAULT '{"notify": true}',
    triggered_count INTEGER DEFAULT 0,
    last_triggered_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Index for unread notifications
CREATE INDEX idx_notifications_unread ON notifications(user_id, read) WHERE NOT read;
```

### Backend Changes Needed

- [ ] Add notifications table to schema
- [ ] Add alerts table to schema
- [ ] Implement all notification endpoints
- [ ] Implement all alert endpoints
- [ ] Add alert matching logic in poller
- [ ] Add notification cleanup job
- [ ] Add WebSocket for real-time notifications (optional)

### Frontend Changes Needed

- [ ] Add `useNotifications()` hook
- [ ] Add `useNotificationCount()` hook
- [ ] Add `useAlerts()` hook
- [ ] Add `useCreateAlert()` hook
- [ ] Create NotificationList component
- [ ] Create NotificationItem component
- [ ] Create AlertsList component
- [ ] Create AlertForm component
- [ ] Add notification badge in header
- [ ] Add real-time updates (polling or WebSocket)

---

## Notifications Page Layout

```
┌─────────────────────────────────────────────────────────────────────┐
│                       NOTIFICATIONS                                  │
├─────────────────────────────────────────────────────────────────────┤
│  [All] [Unread (12)] [Alerts] [System]     [Mark All Read] [Clear] │
├─────────────────────────────────────────────────────────────────────┤
│                                                                      │
│  ┌─────────────────────────────────────────────────────────────────┐│
│  │ 🔔 New Apple 10-K Filing                              2m ago    ││
│  │    Apple Inc. filed their annual report (10-K)                  ││
│  │    [View] [Dismiss]                                             ││
│  └─────────────────────────────────────────────────────────────────┘│
│                                                                      │
│  ┌─────────────────────────────────────────────────────────────────┐│
│  │ ⚠️ Feed Error: HN Feed                                 10m ago  ││
│  │    Failed to poll feed: Connection timeout                      ││
│  │    [View Feed] [Dismiss]                                        ││
│  └─────────────────────────────────────────────────────────────────┘│
│                                                                      │
│  ┌─────────────────────────────────────────────────────────────────┐│
│  │ ℹ️ Welcome to Capture Spine!                           Jan 1    ││
│  │    Get started by adding your first feed.                       ││
│  │    [Add Feed] [Dismiss]                                         ││
│  └─────────────────────────────────────────────────────────────────┘│
│                                                                      │
│                        [Load More]                                   │
│                                                                      │
└─────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────┐
│                         ALERTS                                       │
├─────────────────────────────────────────────────────────────────────┤
│                                               [+ Create Alert]       │
│                                                                      │
│  ┌─────────────────────────────────────────────────────────────────┐│
│  │ ● Apple Filings                                        Enabled  ││
│  │   Feeds: SEC Latest • Keywords: Apple, AAPL                     ││
│  │   Forms: 10-K, 10-Q, 8-K                                        ││
│  │   Triggered 45 times • Last: 2 hours ago                        ││
│  │   [Edit] [Test] [Disable] [Delete]                              ││
│  └─────────────────────────────────────────────────────────────────┘│
│                                                                      │
│  ┌─────────────────────────────────────────────────────────────────┐│
│  │ ○ Tech News Keywords                                   Disabled ││
│  │   All Feeds • Keywords: AI, machine learning, GPT               ││
│  │   Never triggered                                               ││
│  │   [Edit] [Test] [Enable] [Delete]                               ││
│  └─────────────────────────────────────────────────────────────────┘│
│                                                                      │
└─────────────────────────────────────────────────────────────────────┘
```
