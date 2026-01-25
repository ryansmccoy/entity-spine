# FeedsPage - API Requirements

## Overview

The FeedsPage allows users to manage their feed subscriptions - add, edit, delete, enable/disable feeds.

## Current Status: ⚠️ Partial Implementation

The API hooks exist but the page may not be fully wired up.

---

## Required API Endpoints

### 1. List All Feeds

**Endpoint:** `GET /api/feeds`

**Used For:** Displaying the feeds management table

**Expected Response:**
```json
[
  {
    "feed_id": "uuid",
    "name": "SEC Latest Filings",
    "feed_type": "rss",
    "base_url": "https://www.sec.gov/cgi-bin/browse-edgar?action=getcurrent&output=atom",
    "config": {
      "poll_interval": 300,
      "max_items": 100
    },
    "enabled": true,
    "status": "active",
    "last_polled_at": "2026-01-27T12:00:00Z",
    "last_error": null,
    "error_count": 0,
    "record_count": 1250,
    "created_at": "2026-01-01T00:00:00Z",
    "updated_at": "2026-01-27T12:00:00Z"
  }
]
```

**Frontend Hook:** `useFeeds()` ✅ Exists

---

### 2. Get Single Feed

**Endpoint:** `GET /api/feeds/{feed_id}`

**Used For:** Feed detail view / edit form

**Response:** Same as single feed object above

**Frontend Hook:** `useFeed(id)` ✅ Exists

---

### 3. Create Feed

**Endpoint:** `POST /api/feeds`

**Used For:** Adding new feed subscriptions

**Request Body:**
```json
{
  "name": "Hacker News",
  "feed_type": "rss",
  "base_url": "https://news.ycombinator.com/rss",
  "config": {
    "poll_interval": 600
  },
  "enabled": true
}
```

**Validation:**
- `name`: Required, unique, max 255 chars
- `feed_type`: Required, one of: rss, atom, api, index
- `base_url`: Required, valid URL
- `config.poll_interval`: Optional, min 60 seconds

**Response:** `201 Created` with created feed object

**Frontend Hook:** `useCreateFeed()` ✅ Exists

---

### 4. Update Feed

**Endpoint:** `PUT /api/feeds/{feed_id}`

**Used For:** Editing feed settings

**Request Body:** (partial update supported)
```json
{
  "name": "HN Feed (Updated)",
  "enabled": false,
  "config": {
    "poll_interval": 1800
  }
}
```

**Response:** Updated feed object

**Frontend Hook:** `useUpdateFeed()` ✅ Exists

---

### 5. Delete Feed

**Endpoint:** `DELETE /api/feeds/{feed_id}`

**Used For:** Removing feed subscription

**Query Parameters:**
- `delete_records`: boolean - Also delete all records from this feed (default: false)

**Response:** `204 No Content`

**Frontend Hook:** `useDeleteFeed()` ✅ Exists

---

### 6. Toggle Feed Enabled

**Endpoint:** `PATCH /api/feeds/{feed_id}/toggle`

**Used For:** Quick enable/disable without full update

**Request Body:**
```json
{
  "enabled": false
}
```

**Response:** Updated feed object

**Frontend Hook:** `useToggleFeed()` ✅ Exists

---

### 7. Refresh Feed

**Endpoint:** `POST /api/feeds/{feed_id}/refresh`

**Used For:** Force immediate poll of a feed

**Response:** `202 Accepted`
```json
{
  "message": "Feed refresh queued",
  "feed_id": "uuid"
}
```

**Frontend Hook:** `useRefreshFeed()` ✅ Exists

---

### 8. Feed Health/Status

**Endpoint:** `GET /api/feeds/{feed_id}/health`

**Used For:** Showing feed polling history and errors

**Response:**
```json
{
  "feed_id": "uuid",
  "status": "active",
  "last_success_at": "2026-01-27T12:00:00Z",
  "last_error_at": "2026-01-26T10:30:00Z",
  "last_error": "Connection timeout",
  "error_count": 2,
  "success_rate": 0.98,
  "avg_poll_duration_ms": 450,
  "recent_polls": [
    { "at": "2026-01-27T12:00:00Z", "status": "success", "records": 5 },
    { "at": "2026-01-27T11:55:00Z", "status": "success", "records": 3 }
  ]
}
```

**Frontend Hook:** `useFeedHealth(id)` - NEEDS TO BE ADDED

---

### 9. Discover Feed

**Endpoint:** `POST /api/feeds/discover`

**Used For:** Auto-detect RSS/Atom feed from a URL

**Request Body:**
```json
{
  "url": "https://example.com"
}
```

**Response:**
```json
{
  "feeds_found": [
    {
      "url": "https://example.com/rss",
      "title": "Example Blog RSS",
      "type": "rss"
    },
    {
      "url": "https://example.com/atom.xml",
      "title": "Example Blog Atom",
      "type": "atom"
    }
  ]
}
```

**Frontend Hook:** `useDiscoverFeed()` - NEEDS TO BE ADDED

---

### 10. Import OPML

**Endpoint:** `POST /api/feeds/import`

**Used For:** Bulk import feeds from OPML file

**Request:** `multipart/form-data` with file upload

**Response:**
```json
{
  "imported": 15,
  "skipped": 3,
  "errors": [
    { "name": "Bad Feed", "error": "Invalid URL" }
  ]
}
```

**Frontend Hook:** `useImportOPML()` - NEEDS TO BE ADDED

---

### 11. Export OPML

**Endpoint:** `GET /api/feeds/export`

**Used For:** Export all feeds as OPML

**Response:** `application/xml` OPML file

**Frontend:** Direct download link, no hook needed

---

## Implementation Checklist

### Backend Changes Needed

- [ ] Add `record_count` to feeds list response
- [ ] Implement `GET /api/feeds/{id}/health` endpoint
- [ ] Implement `POST /api/feeds/discover` endpoint
- [ ] Implement `POST /api/feeds/import` endpoint
- [ ] Implement `GET /api/feeds/export` endpoint
- [ ] Add validation for feed URLs
- [ ] Add feed URL duplicate detection

### Frontend Changes Needed

- [ ] Verify FeedsPage uses `useFeeds()` hook
- [ ] Add feed health display component
- [ ] Add "Discover Feed" feature in add modal
- [ ] Add OPML import button and modal
- [ ] Add OPML export button
- [ ] Add confirmation dialog for delete
- [ ] Add feed status indicators (active/error/disabled)

---

## Feed Types

| Type | Description | Example |
|------|-------------|---------|
| `rss` | RSS 2.0 feed | Most blogs, news sites |
| `atom` | Atom 1.0 feed | GitHub releases, some blogs |
| `api` | Custom API endpoint | SEC EDGAR API |
| `index` | Index page scraping | SEC full-text search |
