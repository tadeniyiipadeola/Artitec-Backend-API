# Audit Logs API Documentation

The Audit Logs API provides comprehensive tracking of all property approval and denial activities in the Artitec system. This documentation covers how to use the audit log endpoints in your admin settings page.

## Overview

The audit log system automatically tracks:
- **Auto-Approved Properties**: Properties approved by the auto-approval service (high confidence)
- **Auto-Denied Properties**: Properties rejected by the auto-approval service (low confidence/quality)
- **Manually Approved**: Properties approved by admin reviewers
- **Manually Rejected**: Properties rejected by admin reviewers

All audit data is stored in the `collection_changes` table and includes detailed information about the decision, reviewer, confidence scores, and timestamps.

## API Endpoints

### 1. Get Audit Log Statistics

**Endpoint**: `GET /v1/admin/collection/audit-logs/stats`

**Description**: Returns statistical overview of approval/denial activities.

**Query Parameters**:
- `days` (optional): Number of days to look back (default: 30, max: 365)

**Response**:
```json
{
  "total_actions": 150,
  "auto_approved": 85,
  "auto_denied": 25,
  "manually_approved": 30,
  "manually_rejected": 10,
  "pending_review": 45,
  "properties_added": 115,
  "properties_updated": 20,
  "last_7_days": 45,
  "last_30_days": 150
}
```

**Example Usage**:
```bash
curl "http://localhost:8000/v1/admin/collection/audit-logs/stats?days=7"
```

---

### 2. Get Audit Log Entries

**Endpoint**: `GET /v1/admin/collection/audit-logs`

**Description**: Returns paginated list of audit log entries with detailed information.

**Query Parameters**:
- `action` (optional): Filter by action type
  - `auto_approved`: Auto-approved properties
  - `auto_denied`: Auto-denied properties
  - `approved`: Manually approved
  - `rejected`: Manually rejected
- `entity_type` (optional): Filter by entity type (`property`, `builder`, `community`)
- `reviewer_id` (optional): Filter by reviewer user ID
- `days` (optional): Number of days to look back (default: 30, max: 365)
- `limit` (optional): Number of entries to return (default: 50, max: 200)
- `offset` (optional): Offset for pagination (default: 0)

**Response**:
```json
[
  {
    "id": 1523,
    "timestamp": "2025-11-27T10:30:45Z",
    "action": "auto_approved",
    "entity_type": "property",
    "entity_name": "Beautiful 4BR Home in Oak Meadows",
    "property_address": "123 Oak Street",
    "property_bedrooms": 4,
    "property_bathrooms": 2.5,
    "property_price": 450000.00,
    "reviewer_name": null,
    "reviewer_id": null,
    "review_notes": "AUTO-APPROVED: High confidence (95%), valid beds/baths",
    "confidence": 0.95,
    "change_type": "added",
    "is_auto_action": true,
    "source_url": "https://perryhomes.com/property/123"
  },
  {
    "id": 1522,
    "timestamp": "2025-11-27T09:15:30Z",
    "action": "rejected",
    "entity_type": "property",
    "entity_name": "Incomplete Property Listing",
    "property_address": "456 Elm Ave",
    "property_bedrooms": 0,
    "property_bathrooms": 0,
    "property_price": null,
    "reviewer_name": "John Smith",
    "reviewer_id": "USR-123456",
    "review_notes": "Missing critical information - bedrooms/bathrooms not specified",
    "confidence": 0.45,
    "change_type": "added",
    "is_auto_action": false,
    "source_url": "https://builder.com/property/456"
  }
]
```

**Example Usage**:

Get all auto-approved properties:
```bash
curl "http://localhost:8000/v1/admin/collection/audit-logs?action=auto_approved&limit=20"
```

Get properties reviewed in last 7 days:
```bash
curl "http://localhost:8000/v1/admin/collection/audit-logs?entity_type=property&days=7"
```

Get actions by specific reviewer:
```bash
curl "http://localhost:8000/v1/admin/collection/audit-logs?reviewer_id=USR-123456&days=30"
```

---

## Integration with Settings Page

### Display Audit Log Dashboard

Create a dashboard in your admin settings page that shows:

1. **Statistics Cards**:
```javascript
const statsResponse = await fetch('/v1/admin/collection/audit-logs/stats?days=30');
const stats = await statsResponse.json();

// Display cards:
// - Total Actions (stats.total_actions)
// - Auto-Approved (stats.auto_approved)
// - Pending Review (stats.pending_review)
// - Recent Activity (stats.last_7_days)
```

2. **Activity Timeline**:
```javascript
const logsResponse = await fetch('/v1/admin/collection/audit-logs?limit=50&days=30');
const logs = await logsResponse.json();

// Display timeline with:
// - Action icon (✅ approved, ❌ denied, 👍 manual approve, 👎 manual reject)
// - Property name/address
// - Timestamp
// - Reviewer name (if manual action)
// - Confidence score
```

3. **Filter Controls**:
```javascript
// Add dropdowns/filters for:
// - Action type (all, auto_approved, auto_denied, approved, rejected)
// - Time range (7 days, 30 days, 90 days)
// - Entity type (property, builder, community)
```

### Sample React Component

```tsx
import React, { useEffect, useState } from 'react';

const AuditLogDashboard = () => {
  const [stats, setStats] = useState(null);
  const [logs, setLogs] = useState([]);
  const [filter, setFilter] = useState('all');

  useEffect(() => {
    // Load stats
    fetch('/v1/admin/collection/audit-logs/stats?days=30')
      .then(res => res.json())
      .then(data => setStats(data));

    // Load logs
    const url = filter === 'all'
      ? '/v1/admin/collection/audit-logs?limit=50&days=30'
      : `/v1/admin/collection/audit-logs?action=${filter}&limit=50&days=30`;

    fetch(url)
      .then(res => res.json())
      .then(data => setLogs(data));
  }, [filter]);

  return (
    <div className="audit-log-dashboard">
      {/* Stats Cards */}
      <div className="stats-grid">
        <StatCard title="Total Actions" value={stats?.total_actions} />
        <StatCard title="Auto-Approved" value={stats?.auto_approved} color="green" />
        <StatCard title="Pending Review" value={stats?.pending_review} color="yellow" />
        <StatCard title="Last 7 Days" value={stats?.last_7_days} />
      </div>

      {/* Filter Controls */}
      <select onChange={(e) => setFilter(e.target.value)}>
        <option value="all">All Actions</option>
        <option value="auto_approved">Auto-Approved</option>
        <option value="auto_denied">Auto-Denied</option>
        <option value="approved">Manually Approved</option>
        <option value="rejected">Manually Rejected</option>
      </select>

      {/* Activity Timeline */}
      <div className="activity-timeline">
        {logs.map(log => (
          <AuditLogEntry key={log.id} log={log} />
        ))}
      </div>
    </div>
  );
};
```

---

## Data Fields Explained

### Action Types

| Action | Description | Auto Action |
|--------|-------------|-------------|
| `auto_approved` | Property passed auto-approval criteria (confidence > 90%, valid beds/baths) | Yes |
| `auto_denied` | Property failed auto-approval criteria (confidence < 75% or invalid data) | Yes |
| `approved` | Property manually approved by admin reviewer | No |
| `rejected` | Property manually rejected by admin reviewer | No |

### Entity Types

- `property`: Real estate property listings
- `builder`: Builder profile data
- `community`: Community/neighborhood data

### Confidence Scores

Confidence scores range from 0.0 to 1.0 (0% to 100%):
- **0.90 - 1.0**: High confidence - Auto-approved
- **0.75 - 0.90**: Medium confidence - Requires manual review
- **0.0 - 0.75**: Low confidence - Auto-denied

### Review Notes

Contains the reason for the decision:
- Auto-approved: "AUTO-APPROVED: High confidence (95%), valid beds/baths"
- Auto-denied: "AUTO-DENIED: low confidence (65%), invalid bedrooms (0)"
- Manual actions: Admin's custom notes

---

## Testing

Use the provided test script to verify the audit log API:

```bash
cd /Users/adeniyi_family_executor/Documents/Development/Artitec\ Backend\ Development
source .venv/bin/activate
python test_audit_logs.py
```

This will test all endpoints and display sample data.

---

## Performance Considerations

1. **Pagination**: Always use `limit` and `offset` for large datasets
2. **Date Filtering**: Use `days` parameter to limit query scope
3. **Caching**: Consider caching stats for 5-10 minutes
4. **Indexing**: Database indexes on `reviewed_at`, `status`, and `entity_type` ensure fast queries

---

## Security Notes

- Audit logs are read-only via this API (no modification endpoints)
- Currently no authentication (TODO: Add admin authentication)
- All actions are permanently stored for compliance
- Reviewer user IDs are tracked for accountability

---

## Environment Variables

Configure email notifications for audit events in `.env`:

```bash
# Admin notification emails (comma-separated)
ADMIN_NOTIFICATION_EMAILS=admin@artitec.com,manager@artitec.com

# Webhook for external audit systems
PROPERTY_APPROVAL_WEBHOOK_URL=https://audit-system.example.com/webhook

# Frontend URL for email links
FRONTEND_URL=https://app.artitec.com
```

---

## Related Endpoints

- `GET /v1/admin/collection/changes` - Get pending changes for review
- `POST /v1/admin/collection/changes/{change_id}/review` - Review a change
- `GET /v1/admin/collection/stats` - Get collection job statistics

---

## Support

For questions or issues with the audit log system, contact the development team or refer to:
- Source code: `routes/admin/collection.py` (lines 2047-2336)
- Database model: `model/collection.py` (CollectionChange model)
- Auto-approval logic: `src/collection/auto_approval.py`
