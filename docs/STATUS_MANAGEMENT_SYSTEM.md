# Entity Status Management System

**Feature**: Automated status tracking and lifecycle management for Builders, Communities, and Properties

---

## Overview

The Status Management System automatically tracks entity lifecycle states and transitions based on activity, data collection, and business rules. This ensures data accuracy and provides visibility into entity states across the platform.

---

## Entity Status Types

### 1. **Builder Status Management**

#### Status Fields

| Field | Type | Values | Description |
|-------|------|--------|-------------|
| `is_active` | Boolean | true/false | Is builder currently active? |
| `business_status` | String | active, inactive, out_of_business, merged | Business operation status |
| `last_activity_at` | Timestamp | - | Last activity detected |
| `inactivated_at` | Timestamp | - | When marked inactive |
| `inactivation_reason` | String | - | Why builder was inactivated |

#### Business Status Values

- **active**: Builder is actively building and has recent activity
- **inactive**: Temporarily not active (no activity for 90 days)
- **out_of_business**: Permanently closed/defunct
- **merged**: Merged with another builder

#### Auto-Inactivation Rules

**Grace Period**: 90 days (3 months)

**Activity Triggers** (resets grace period):
- New properties listed
- Builder data collected/verified
- Builder appears in web searches
- Property sales/updates

**Auto-Inactivation**:
- Triggered when: `last_activity_at` > 90 days ago
- Status set to: `inactive`
- Reason: "No activity for 90 days"

#### Manual Status Changes

```python
from src.collection.status_managers import BuilderStatusManager

status_mgr = BuilderStatusManager(db)

# Mark builder as out of business
status_mgr.mark_builder_out_of_business(
    builder_id=123,
    reason="Confirmed closure via news article"
)
```

---

### 2. **Community Status Management**

#### Status Fields

| Field | Type | Values | Description |
|-------|------|--------|-------------|
| `is_active` | Boolean | true/false | Is community currently active? |
| `development_status` | String | planned, under_development, active, sold_out, inactive | Development phase |
| `availability_status` | String | available, limited_availability, sold_out, closed | Sales availability |
| `last_activity_at` | Timestamp | - | Last activity detected |
| `status_changed_at` | Timestamp | - | When status last changed |
| `status_change_reason` | String | - | Reason for status change |

#### Development Status Values

- **planned**: Community is planned but construction hasn't started
- **under_development**: Actively being built
- **active**: Actively selling homes
- **sold_out**: All lots sold
- **inactive**: No longer active (no activity for 180 days)

#### Availability Status Values

- **available**: Properties available (10+)
- **limited_availability**: Few properties remaining (<10)
- **sold_out**: No available properties
- **closed**: Community closed to new sales

#### Auto-Status Rules

**Grace Period**: 180 days (6 months)

**Availability Auto-Update**:
- Triggered after property collection
- Based on available property count:
  - 0 properties → `sold_out`
  - 1-9 properties → `limited_availability`
  - 10+ properties → `available`

**Auto-Inactivation**:
- Triggered when: `last_activity_at` > 180 days ago
- Status set to: `inactive`
- Development status set to: `inactive`

---

### 3. **Property Status Management**

#### Status Fields

| Field | Type | Values | Description |
|-------|------|--------|-------------|
| `listing_status` | String | available, pending, reserved, under_contract, sold, off_market | Sales status |
| `visibility_status` | String | public, private, hidden, archived | Visibility state |
| `last_verified_at` | Timestamp | - | Last verification date |
| `status_changed_at` | Timestamp | - | When status last changed |
| `status_change_reason` | String | - | Reason for change |
| `auto_archive_at` | Timestamp | - | Scheduled archival date |

#### Listing Status Values

- **available**: Property is available for purchase
- **pending**: Offer submitted, pending acceptance
- **reserved**: Reserved by buyer (holding fee paid)
- **under_contract**: Contract signed, in closing process
- **sold**: Property sold and closed
- **off_market**: Temporarily removed from market

#### Visibility Status Values

- **public**: Visible to all users
- **private**: Visible only to specific users/groups
- **hidden**: Hidden from public view (admin only)
- **archived**: Old/stale listing, not actively shown

#### Auto-Archival Rules

**Grace Period**: 60 days (2 months)

**Auto-Archive Triggers**:
1. **Stale Listings**: Not verified in 60 days
   - Status: `listing_status IN ('available', 'pending', 'reserved')`
   - Action: Set `visibility_status = 'archived'`
   - Reason: "Not verified in 60 days"

2. **Scheduled Archive**: Reaches `auto_archive_at` date
   - Action: Set `visibility_status = 'archived'`
   - Reason: "Reached auto-archive date"

3. **Sold Properties**: Automatically archived
   - When: `listing_status = 'sold'`
   - Action: Set `visibility_status = 'archived'`

**Verification Resets**:
- Property collection/update clears `auto_archive_at`
- Updates `last_verified_at` to current timestamp

---

## API Usage Examples

### Builder Status Management

```python
from src.collection.status_managers import BuilderStatusManager

status_mgr = BuilderStatusManager(db)

# Update activity (prevents auto-inactivation)
status_mgr.update_builder_activity(builder_id=123)

# Check for inactive builders (run periodically)
inactive_builders = status_mgr.check_inactive_builders()
print(f"Found {len(inactive_builders)} inactive builders")

# Get builders needing review (60 days no activity)
review_needed = status_mgr.get_builders_needing_review()

# Manual status change
status_mgr.mark_builder_out_of_business(
    builder_id=123,
    reason="Company dissolved"
)
```

### Community Status Management

```python
from src.collection.status_managers import CommunityStatusManager

status_mgr = CommunityStatusManager(db)

# Update activity
status_mgr.update_community_activity(community_id=456)

# Update availability based on inventory
status_mgr.update_availability_from_inventory(community_id=456)
# This checks property count and sets:
# - sold_out (0 properties)
# - limited_availability (1-9)
# - available (10+)

# Check for inactive communities
inactive_communities = status_mgr.check_inactive_communities()
```

### Property Status Management

```python
from src.collection.status_managers import PropertyStatusManager

status_mgr = PropertyStatusManager(db)

# Update property status
status_mgr.update_property_status(
    property_id=789,
    new_status='under_contract',
    reason='Offer accepted'
)

# Verify property (prevents auto-archive)
status_mgr.verify_property_listing(property_id=789)

# Schedule auto-archive
status_mgr.schedule_auto_archive(
    property_id=789,
    days_until_archive=30  # Custom grace period
)

# Run archival jobs (scheduled task)
stale_props = status_mgr.archive_stale_listings()
scheduled_props = status_mgr.auto_archive_scheduled()

# Bulk status update
count = status_mgr.bulk_update_status(
    property_ids=[1, 2, 3, 4, 5],
    new_status='sold',
    reason='Bulk sale to investor'
)
```

---

## Integration with Data Collectors

Status managers are automatically integrated with data collectors:

### CommunityCollector

```python
# Automatically called after successful collection
self.status_manager.update_community_activity(self.community.id)
self.status_manager.update_availability_from_inventory(self.community.id)
```

### BuilderCollector

```python
# Automatically called after successful collection
self.status_manager.update_builder_activity(self.builder.id)
```

### PropertyCollector

```python
# Automatically called for each property update
self.status_manager.verify_property_listing(existing_property.id)
```

---

## Scheduled Tasks

For optimal performance, run these periodic maintenance tasks:

### Daily Tasks

```python
# Check and archive stale property listings
property_mgr = PropertyStatusManager(db)
stale_props = property_mgr.archive_stale_listings()
scheduled_props = property_mgr.auto_archive_scheduled()

logger.info(f"Archived {len(stale_props)} stale listings")
logger.info(f"Archived {len(scheduled_props)} scheduled properties")
```

### Weekly Tasks

```python
# Check for inactive builders
builder_mgr = BuilderStatusManager(db)
inactive_builders = builder_mgr.check_inactive_builders()

# Review builders approaching inactivation
review_needed = builder_mgr.get_builders_needing_review()

logger.info(f"Marked {len(inactive_builders)} builders as inactive")
logger.info(f"{len(review_needed)} builders need manual review")
```

### Monthly Tasks

```python
# Check for inactive communities
community_mgr = CommunityStatusManager(db)
inactive_communities = community_mgr.check_inactive_communities()

logger.info(f"Marked {len(inactive_communities)} communities as inactive")
```

---

## Database Queries

### Find Active Builders with Recent Activity

```sql
SELECT * FROM builder_profiles
WHERE is_active = TRUE
  AND business_status = 'active'
  AND last_activity_at > DATE_SUB(NOW(), INTERVAL 30 DAY)
ORDER BY last_activity_at DESC;
```

### Find Communities Sold Out

```sql
SELECT * FROM communities
WHERE availability_status = 'sold_out'
  AND development_status = 'active'
ORDER BY status_changed_at DESC;
```

### Find Available Properties by Status

```sql
SELECT * FROM properties
WHERE listing_status = 'available'
  AND visibility_status = 'public'
  AND construction_stage = 'completed'
ORDER BY price ASC;
```

### Find Properties Needing Review

```sql
SELECT * FROM properties
WHERE listing_status IN ('available', 'pending')
  AND visibility_status = 'public'
  AND last_verified_at < DATE_SUB(NOW(), INTERVAL 45 DAY)
ORDER BY last_verified_at ASC
LIMIT 100;
```

---

## Status Transition Workflows

### Builder Lifecycle

```
NEW BUILDER
    ↓
[active] → Data collected, properties listed
    ↓ (90 days no activity)
[inactive] → Auto-marked inactive
    ↓ (activity detected)
[active] → Reactivated
    ↓ (manual action)
[out_of_business] → Permanently closed
```

### Community Lifecycle

```
NEW COMMUNITY
    ↓
[planned] → Future development
    ↓
[under_development] → Construction started
    ↓
[active, available] → Lots available (10+)
    ↓
[active, limited_availability] → Few lots (1-9)
    ↓
[sold_out, sold_out] → All lots sold
    ↓ (180 days no activity)
[inactive] → Auto-marked inactive
```

### Property Lifecycle

```
NEW PROPERTY
    ↓
[available, public] → Listed for sale
    ↓
[pending, public] → Offer submitted
    ↓
[reserved, public] → Reserved by buyer
    ↓
[under_contract, public] → Contract signed
    ↓
[sold, archived] → Sold and closed
    ↓ (or 60 days no verification)
[*, archived] → Auto-archived
```

---

## Admin Dashboard Queries

### Status Summary

```python
# Builders by status
from sqlalchemy import func

builder_stats = db.query(
    BuilderProfile.business_status,
    func.count(BuilderProfile.id).label('count')
).group_by(BuilderProfile.business_status).all()

# Communities by availability
community_stats = db.query(
    Community.availability_status,
    func.count(Community.id).label('count')
).group_by(Community.availability_status).all()

# Properties by listing status
property_stats = db.query(
    Property.listing_status,
    func.count(Property.id).label('count')
).group_by(Property.listing_status).all()
```

---

## Migration Applied

**File**: `40631958258f_add_entity_status_management.py`

**Columns Added**:
- Builder: 5 columns (is_active, business_status, last_activity_at, inactivated_at, inactivation_reason)
- Community: 6 columns (is_active, development_status, availability_status, last_activity_at, status_changed_at, status_change_reason)
- Property: 6 columns (listing_status, visibility_status, last_verified_at, status_changed_at, status_change_reason, auto_archive_at)

**Indexes Added**:
- 7 new indexes for efficient status queries

---

## Best Practices

1. **Always Update Activity**: Call `update_*_activity()` after any significant action
2. **Verify Properties Regularly**: Run property collection jobs to keep listings current
3. **Review Before Auto-Actions**: Check entities approaching auto-inactivation
4. **Use Bulk Operations**: For mass status updates, use bulk methods
5. **Set Meaningful Reasons**: Always provide status_change_reason for audit trail
6. **Monitor Grace Periods**: Adjust grace periods based on market conditions

---

## Summary

✅ **Builder Status**: 90-day grace period, auto-inactivation
✅ **Community Status**: Development + availability tracking, 180-day grace period
✅ **Property Status**: Listing + visibility management, 60-day auto-archive
✅ **Automated Workflows**: Integrated with data collectors
✅ **Scheduled Maintenance**: Daily/weekly/monthly cleanup tasks

**Status management is now fully operational!** 🎉
