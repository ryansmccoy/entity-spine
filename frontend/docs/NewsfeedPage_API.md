# NewsfeedPage - API Requirements

## Overview

The NewsfeedPage is the main content view showing articles/records from all feeds. It needs several API endpoints to function properly.

## Current Status: ❌ Using Mock Data

The page currently uses hardcoded `sampleArticles` and `feeds` arrays instead of fetching from the API.

---

## Required API Endpoints

### 1. Feeds List (Sidebar)

**Endpoint:** `GET /api/feeds`

**Used For:** Populating the sidebar feed list with counts

**Expected Response:**
```json
[
  {
    "feed_id": "uuid",
    "name": "SEC Latest Filings",
    "feed_type": "rss",
    "base_url": "https://...",
    "enabled": true,
    "status": "active",
    "record_count": 1250,      // NEEDED: Count of records from this feed
    "unread_count": 45,        // NEEDED: Count of unread records
    "last_polled_at": "2026-01-27T12:00:00Z",
    "icon": "📋"               // OPTIONAL: Custom icon/emoji
  }
]
```

**Frontend Hook:** `useFeeds()` from `src/api/hooks.ts`

**Missing Fields:**
- `record_count` - Total records from this feed
- `unread_count` - Unread records from this feed
- `icon` - Custom feed icon (optional, can default)

---

### 2. Records List (Main Content)

**Endpoint:** `GET /api/records`

**Used For:** Main article list with all view modes

**Query Parameters:**
| Parameter | Type | Description |
|-----------|------|-------------|
| `feed_ids` | string[] | Filter by feed IDs (comma-separated) |
| `record_type` | string | Filter by type (sec_filing, rss_article) |
| `search` | string | Full-text search |
| `is_read` | boolean | Filter by read status |
| `is_starred` | boolean | Filter by starred status |
| `limit` | number | Page size (default: 50) |
| `offset` | number | Pagination offset |
| `sort` | string | Sort field (published_at, captured_at) |
| `order` | string | Sort order (asc, desc) |

**Expected Response:**
```json
{
  "records": [
    {
      "record_id": "uuid",
      "natural_key": "0000320193-24-000081",
      "record_type": "sec_filing",
      "title": "Apple Inc. - 10-K Annual Report",
      "url": "https://www.sec.gov/...",
      "author": null,
      "summary": "Annual report for fiscal year...",
      "published_at": "2026-01-27T12:00:00Z",
      "captured_at": "2026-01-27T12:05:00Z",
      "feed_id": "feed-uuid",
      "feed_name": "SEC Latest Filings",
      "feed_icon": "📋",
      "is_read": false,
      "is_starred": false,
      "is_new": true,          // NEEDED: First seen < 1 hour ago
      "tags": ["SEC", "10-K"],  // NEEDED: Auto-generated tags
      "content": {
        "form_type": "10-K",
        "company_name": "Apple Inc.",
        "ticker": "AAPL",
        "cik": "0000320193"
      }
    }
  ],
  "total": 1250,
  "has_more": true,
  "unread_total": 45
}
```

**Frontend Hook:** `useRecords()` from `src/api/hooks.ts`

**Missing Fields:**
- `is_new` - Boolean indicating if record was captured recently
- `tags` - Auto-generated tags based on content
- `feed_name` - Denormalized feed name for display
- `feed_icon` - Denormalized feed icon

---

### 3. Mark as Read

**Endpoint:** `POST /api/records/{record_id}/read`

**Used For:** Marking articles as read when clicked/viewed

**Request Body:** (optional)
```json
{
  "read": true  // or false to mark unread
}
```

**Response:** `204 No Content` or updated record

**Frontend Hook:** `useMarkAsRead()` - NEEDS TO BE ADDED

---

### 4. Toggle Star

**Endpoint:** `POST /api/records/{record_id}/star`

**Used For:** Starring/unstarring articles

**Request Body:** (optional)
```json
{
  "starred": true  // or false to unstar
}
```

**Response:** `204 No Content` or updated record

**Frontend Hook:** `useToggleStar()` - NEEDS TO BE ADDED

---

### 5. Bulk Actions

**Endpoint:** `POST /api/records/bulk`

**Used For:** Mark multiple as read, star multiple, etc.

**Request Body:**
```json
{
  "record_ids": ["uuid1", "uuid2", "uuid3"],
  "action": "mark_read",  // mark_read, mark_unread, star, unstar, delete
}
```

**Response:** 
```json
{
  "affected": 3
}
```

**Frontend Hook:** `useBulkAction()` - NEEDS TO BE ADDED

---

### 6. Feed Aggregates (for sidebar)

**Endpoint:** `GET /api/feeds/stats`

**Used For:** Efficient sidebar updates without fetching all feeds

**Response:**
```json
{
  "all": { "total": 915260, "unread": 1234 },
  "by_feed": {
    "feed-uuid-1": { "total": 1250, "unread": 45 },
    "feed-uuid-2": { "total": 500, "unread": 12 }
  }
}
```

**Frontend Hook:** `useFeedStats()` - NEEDS TO BE ADDED

---

## Implementation Checklist

### Backend Changes Needed

- [ ] Add `record_count` and `unread_count` to feeds list endpoint
- [ ] Add `is_new` computed field to records (captured_at > now - 1 hour)
- [ ] Add `tags` field with auto-generated tags based on content
- [ ] Implement `POST /api/records/{id}/read` endpoint
- [ ] Implement `POST /api/records/{id}/star` endpoint
- [ ] Implement `POST /api/records/bulk` endpoint
- [ ] Implement `GET /api/feeds/stats` endpoint

### Frontend Changes Needed

- [ ] Wire `useFeeds()` to sidebar in NewsfeedPage
- [ ] Wire `useRecords()` to article list in NewsfeedPage
- [ ] Add `useMarkAsRead()` hook
- [ ] Add `useToggleStar()` hook
- [ ] Add `useBulkAction()` hook
- [ ] Add `useFeedStats()` hook
- [ ] Replace mock data with real API calls
- [ ] Add loading states
- [ ] Add error handling

---

## Data Mapping

| Mock Data Field | API Field | Notes |
|----------------|-----------|-------|
| `article.id` | `record.record_id` | |
| `article.feed` | `record.feed_name` | Short name |
| `article.feedIcon` | `record.feed_icon` | Emoji |
| `article.title` | `record.title` | |
| `article.tags` | `record.tags` | Auto-generated |
| `article.isAI` | N/A | Removed (unused) |
| `article.time` | Computed from `published_at` | "1m ago" format |
| `article.isNew` | `record.is_new` | |
| `article.isRead` | `record.is_read` | |
| `article.isStarred` | `record.is_starred` | |
| `article.captured` | N/A | Removed (use is_captured) |
