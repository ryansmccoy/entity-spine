# DashboardPage - API Requirements

## Overview

The DashboardPage shows an overview of the system with key statistics, recent activity, and quick actions.

## Current Status: ❌ No API Integration

The page likely shows placeholder data or hardcoded values.

---

## Required API Endpoints

### 1. Dashboard Statistics

**Endpoint:** `GET /api/stats`

**Used For:** Main statistics cards

**Expected Response:**
```json
{
  "feeds": {
    "total": 12,
    "active": 10,
    "error": 1,
    "disabled": 1
  },
  "records": {
    "total": 915260,
    "today": 234,
    "this_week": 1523,
    "unread": 1234
  },
  "storage": {
    "database_size_mb": 256,
    "blob_storage_mb": 1024
  },
  "polling": {
    "last_poll_at": "2026-01-27T12:00:00Z",
    "polls_today": 288,
    "avg_poll_duration_ms": 450
  }
}
```

**Frontend Hook:** `useStats()` - NEEDS TO BE ADDED

---

### 2. Recent Activity

**Endpoint:** `GET /api/activity`

**Used For:** Activity feed on dashboard

**Query Parameters:**
- `limit`: number (default: 20)

**Expected Response:**
```json
{
  "activities": [
    {
      "id": "uuid",
      "type": "feed_polled",
      "message": "SEC Latest Filings polled - 5 new records",
      "timestamp": "2026-01-27T12:00:00Z",
      "metadata": {
        "feed_id": "uuid",
        "feed_name": "SEC Latest Filings",
        "new_records": 5
      }
    },
    {
      "id": "uuid",
      "type": "feed_error",
      "message": "Failed to poll HN Feed: Connection timeout",
      "timestamp": "2026-01-27T11:55:00Z",
      "metadata": {
        "feed_id": "uuid",
        "feed_name": "HN Feed",
        "error": "Connection timeout"
      }
    },
    {
      "id": "uuid",
      "type": "record_starred",
      "message": "Starred: Apple Inc. - 10-K Annual Report",
      "timestamp": "2026-01-27T11:30:00Z",
      "metadata": {
        "record_id": "uuid",
        "record_title": "Apple Inc. - 10-K Annual Report"
      }
    }
  ]
}
```

**Activity Types:**
- `feed_polled` - Feed was polled
- `feed_error` - Feed poll failed
- `feed_created` - New feed added
- `feed_deleted` - Feed removed
- `record_starred` - Record starred
- `alert_triggered` - Alert condition met

**Frontend Hook:** `useActivity()` - NEEDS TO BE ADDED

---

### 3. Feed Status Overview

**Endpoint:** `GET /api/feeds/status`

**Used For:** Quick view of all feed statuses

**Expected Response:**
```json
{
  "feeds": [
    {
      "feed_id": "uuid",
      "name": "SEC Latest Filings",
      "status": "active",
      "last_polled_at": "2026-01-27T12:00:00Z",
      "next_poll_at": "2026-01-27T12:05:00Z",
      "error_count": 0
    },
    {
      "feed_id": "uuid",
      "name": "HN Feed",
      "status": "error",
      "last_polled_at": "2026-01-27T11:55:00Z",
      "next_poll_at": "2026-01-27T12:05:00Z",
      "error_count": 3,
      "last_error": "Connection timeout"
    }
  ]
}
```

**Frontend Hook:** `useFeedStatus()` - NEEDS TO BE ADDED

---

### 4. Records Timeline

**Endpoint:** `GET /api/stats/timeline`

**Used For:** Chart showing records over time

**Query Parameters:**
- `period`: string - "day", "week", "month"
- `feed_id`: string - Optional, filter by feed

**Expected Response:**
```json
{
  "period": "week",
  "data": [
    { "date": "2026-01-21", "count": 145 },
    { "date": "2026-01-22", "count": 189 },
    { "date": "2026-01-23", "count": 134 },
    { "date": "2026-01-24", "count": 256 },
    { "date": "2026-01-25", "count": 198 },
    { "date": "2026-01-26", "count": 223 },
    { "date": "2026-01-27", "count": 178 }
  ]
}
```

**Frontend Hook:** `useRecordsTimeline()` - NEEDS TO BE ADDED

---

### 5. Top Feeds

**Endpoint:** `GET /api/stats/top-feeds`

**Used For:** Showing most active feeds

**Query Parameters:**
- `period`: string - "day", "week", "month"
- `limit`: number (default: 5)

**Expected Response:**
```json
{
  "period": "week",
  "feeds": [
    { "feed_id": "uuid", "name": "SEC Latest", "count": 523 },
    { "feed_id": "uuid", "name": "HN Feed", "count": 412 },
    { "feed_id": "uuid", "name": "Tech News", "count": 289 }
  ]
}
```

**Frontend Hook:** `useTopFeeds()` - NEEDS TO BE ADDED

---

## Implementation Checklist

### Backend Changes Needed

- [ ] Implement `GET /api/stats` endpoint
- [ ] Implement `GET /api/activity` endpoint
- [ ] Implement `GET /api/feeds/status` endpoint
- [ ] Implement `GET /api/stats/timeline` endpoint
- [ ] Implement `GET /api/stats/top-feeds` endpoint
- [ ] Add activity logging for feed events
- [ ] Add activity logging for user actions

### Frontend Changes Needed

- [ ] Add `useStats()` hook
- [ ] Add `useActivity()` hook
- [ ] Add `useFeedStatus()` hook
- [ ] Add `useRecordsTimeline()` hook
- [ ] Add `useTopFeeds()` hook
- [ ] Create StatCard component
- [ ] Create ActivityFeed component
- [ ] Create FeedStatusList component
- [ ] Create RecordsChart component
- [ ] Wire up DashboardPage with hooks

---

## Dashboard Layout Suggestion

```
┌─────────────────────────────────────────────────────────────────────┐
│                           DASHBOARD                                  │
├─────────────────────────────────────────────────────────────────────┤
│                                                                      │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐            │
│  │  12      │  │  915,260 │  │  1,234   │  │  10/12   │            │
│  │  Feeds   │  │  Records │  │  Unread  │  │  Active  │            │
│  └──────────┘  └──────────┘  └──────────┘  └──────────┘            │
│                                                                      │
│  ┌────────────────────────────┐  ┌───────────────────────────────┐  │
│  │    Records This Week       │  │     Recent Activity           │  │
│  │    ▂▄▃▆▅▇▄                │  │  • SEC polled - 5 new         │  │
│  │    M T W T F S S          │  │  • HN Feed error               │  │
│  │                            │  │  • Starred: Apple 10-K         │  │
│  └────────────────────────────┘  └───────────────────────────────┘  │
│                                                                      │
│  ┌────────────────────────────────────────────────────────────────┐ │
│  │                    Feed Status                                  │ │
│  │  ● SEC Latest Filings    ✓ Active    5m ago    Next: 0m       │ │
│  │  ● HN Feed               ✗ Error     10m ago   Retry: 5m      │ │
│  │  ● Tech News             ✓ Active    2m ago    Next: 8m       │ │
│  └────────────────────────────────────────────────────────────────┘ │
│                                                                      │
└─────────────────────────────────────────────────────────────────────┘
```
