# Alerts Page API Requirements

## Overview
The Alerts page allows users to create, manage, and monitor alert rules that trigger notifications when new SEC filings match specified criteria.

## API Endpoints

### 1. List Alerts
```
GET /api/alerts
```

**Query Parameters:**
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `enabled` | boolean | No | Filter by enabled status |
| `limit` | integer | No | Max results (default: 50) |
| `offset` | integer | No | Pagination offset |

**Response:**
```json
[
  {
    "alert_id": "uuid",
    "name": "10-K Annual Reports",
    "description": "Get notified when companies file annual reports",
    "enabled": true,
    "conditions": [
      {
        "type": "form_types",
        "operator": "contains",
        "value": ["10-K", "10-K/A"]
      }
    ],
    "actions": [
      {
        "type": "notification",
        "enabled": true
      },
      {
        "type": "email",
        "enabled": true,
        "config": {
          "email": "user@example.com"
        }
      }
    ],
    "feed_ids": ["uuid1", "uuid2"],
    "triggered_count": 45,
    "last_triggered_at": "2025-01-15T10:30:00Z",
    "created_at": "2024-12-01T00:00:00Z",
    "updated_at": "2025-01-15T10:30:00Z"
  }
]
```

---

### 2. Get Single Alert
```
GET /api/alerts/{alert_id}
```

**Response:** Same as single item in list response

---

### 3. Create Alert
```
POST /api/alerts
```

**Request Body:**
```json
{
  "name": "Tech Company 10-K Filings",
  "description": "Optional description",
  "enabled": true,
  "conditions": [
    {
      "type": "form_types",
      "operator": "equals",
      "value": ["10-K"]
    },
    {
      "type": "keywords",
      "operator": "contains",
      "value": "technology"
    }
  ],
  "actions": [
    {
      "type": "notification",
      "enabled": true
    },
    {
      "type": "email",
      "enabled": true,
      "config": {
        "email": "alerts@example.com",
        "include_content": true
      }
    }
  ],
  "feed_ids": ["uuid1"]
}
```

**Response:** Created alert object with `alert_id`

---

### 4. Update Alert
```
PUT /api/alerts/{alert_id}
```

**Request Body:** Same as create

**Response:** Updated alert object

---

### 5. Toggle Alert Status
```
PATCH /api/alerts/{alert_id}
```

**Request Body:**
```json
{
  "enabled": false
}
```

**Response:** Updated alert object

---

### 6. Delete Alert
```
DELETE /api/alerts/{alert_id}
```

**Response:** 204 No Content

---

### 7. Test Alert
```
POST /api/alerts/{alert_id}/test
```

Manually trigger an alert to test its conditions and actions.

**Response:**
```json
{
  "matches": [
    {
      "record_id": "uuid",
      "title": "APPLE INC 10-K",
      "match_reason": "Form type matches: 10-K"
    }
  ],
  "actions_executed": [
    {
      "type": "notification",
      "status": "success"
    }
  ]
}
```

---

## Alert Condition Types

### Keywords
```json
{
  "type": "keywords",
  "operator": "contains|equals|not_contains|regex",
  "value": "merger acquisition"
}
```
Matches against title, description, and content of records.

### Form Types
```json
{
  "type": "form_types",
  "operator": "contains|equals",
  "value": ["10-K", "10-Q", "8-K"]
}
```
Matches SEC form types.

### Filer Names
```json
{
  "type": "filers",
  "operator": "contains|equals",
  "value": "Apple Inc"
}
```
Matches company/filer names.

### CIK
```json
{
  "type": "cik",
  "operator": "equals",
  "value": ["0000320193", "0000789019"]
}
```
Matches SEC Central Index Key numbers.

### Industry
```json
{
  "type": "industry",
  "operator": "contains|equals",
  "value": "Technology"
}
```
Matches SIC industry codes or descriptions.

---

## Alert Action Types

### In-App Notification
```json
{
  "type": "notification",
  "enabled": true
}
```
Creates an entry in the notifications table.

### Email Notification
```json
{
  "type": "email",
  "enabled": true,
  "config": {
    "email": "user@example.com",
    "include_content": false
  }
}
```

### Webhook
```json
{
  "type": "webhook",
  "enabled": true,
  "config": {
    "webhook_url": "https://hooks.slack.com/services/...",
    "include_content": true,
    "headers": {
      "Authorization": "Bearer token"
    }
  }
}
```

---

## Database Schema

```sql
-- alerts table
CREATE TABLE alerts (
    alert_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(user_id) ON DELETE CASCADE,
    name TEXT NOT NULL,
    description TEXT,
    enabled BOOLEAN DEFAULT true,
    conditions JSONB NOT NULL,
    actions JSONB NOT NULL DEFAULT '{"notify": true}',
    feed_ids UUID[],
    triggered_count INTEGER DEFAULT 0,
    last_triggered_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_alerts_user ON alerts(user_id);
CREATE INDEX idx_alerts_enabled ON alerts(enabled) WHERE enabled;

-- alert_history table (optional, for tracking triggered alerts)
CREATE TABLE alert_history (
    history_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    alert_id UUID REFERENCES alerts(alert_id) ON DELETE CASCADE,
    record_id UUID REFERENCES records(record_id) ON DELETE SET NULL,
    triggered_at TIMESTAMPTZ DEFAULT NOW(),
    match_details JSONB
);

CREATE INDEX idx_alert_history_alert ON alert_history(alert_id);
CREATE INDEX idx_alert_history_record ON alert_history(record_id);
```

---

## Alert Processing Flow

1. **New Record Ingested**: Feed poller captures new SEC filing
2. **Alert Evaluation**: Background job checks record against all enabled alerts
3. **Condition Matching**: Each condition is evaluated with AND logic
4. **Action Execution**: For matching alerts, execute configured actions:
   - Create notification entry
   - Send email via configured SMTP
   - POST to webhook URL
5. **Update Statistics**: Increment `triggered_count`, update `last_triggered_at`

---

## Frontend Components

### AlertsPage
- List of alerts with enable/disable toggles
- Expandable rows showing conditions and actions
- Create/Edit alert modal
- Search and filter by enabled status

### AlertEditor (Modal)
- Alert name and description fields
- Dynamic condition builder
- Action checkboxes with configuration
- Save/Cancel buttons

### Hook Usage
```tsx
import { 
  useAlerts, 
  useCreateAlert, 
  useUpdateAlert, 
  useDeleteAlert, 
  useToggleAlert 
} from '../api/hooks';

// In component:
const { data: alerts, isLoading } = useAlerts();
const createMutation = useCreateAlert();
const toggleMutation = useToggleAlert();
```

---

## Error Handling

| Status | Description |
|--------|-------------|
| 400 | Invalid conditions or actions format |
| 401 | Unauthorized (not logged in) |
| 403 | Forbidden (alert belongs to another user) |
| 404 | Alert not found |
| 422 | Validation error (missing name, invalid condition type) |
