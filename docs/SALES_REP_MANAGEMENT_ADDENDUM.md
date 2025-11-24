# Sales Rep Management - Data Collector Addendum

**Date**: November 24, 2025
**Purpose**: Define how the Data Collector handles SalesRep discovery, updates, and status management
**Related**: DATA_COLLECTOR_COMPREHENSIVE_PLAN.md

---

## Overview

The SalesRep entity has **dual foreign key relationships**:
- `builder_id` → Links to BuilderProfile (required)
- `community_id` → Links to Community (optional, specific assignment)

When collecting data, the system must:
1. Discover new sales reps from builder/community websites
2. Update existing sales rep information
3. **Mark reps as inactive** when they're no longer listed
4. Maintain correct relationships between Community → Builder → SalesRep

---

## Current SalesRep Schema

```python
class SalesRep(Base):
    __tablename__ = "sales_reps"

    # IDs
    id                  # BIGINT (internal PK)
    sales_rep_id        # String (public: "SLS-1699564234-P7Q8R9")
    user_id             # String FK to users.user_id (optional)

    # Relationships
    builder_id          # BIGINT FK to builder_profiles.id (REQUIRED)
    community_id        # BIGINT FK to communities.id (OPTIONAL)

    # Personal Info
    first_name          # String(128)
    last_name           # String(128)
    title               # String(128) - e.g., "New Home Consultant"
    email               # String(255)
    phone               # String(64)
    avatar_url          # String(1024)
    region              # String(128) - e.g., "North Houston"
    office_address      # String(255)
    verified            # Boolean

    # Timestamps
    created_at          # TIMESTAMP
    updated_at          # TIMESTAMP

    # Relationships
    builder             # → BuilderProfile
    community           # → Community
```

---

## Required Schema Updates

### Add Status Tracking to `sales_reps` Table

```sql
ALTER TABLE sales_reps
ADD COLUMN is_active BOOLEAN DEFAULT TRUE AFTER verified,
ADD COLUMN last_seen_at TIMESTAMP NULL AFTER updated_at,
ADD COLUMN inactivated_at TIMESTAMP NULL AFTER last_seen_at,
ADD COLUMN inactivation_reason VARCHAR(255) AFTER inactivated_at,
ADD COLUMN data_source VARCHAR(50) DEFAULT 'manual' AFTER inactivation_reason,
ADD COLUMN last_data_sync TIMESTAMP NULL AFTER data_source;

-- Add index for active status queries
CREATE INDEX idx_sales_reps_active ON sales_reps(is_active);
CREATE INDEX idx_sales_reps_builder_active ON sales_reps(builder_id, is_active);
CREATE INDEX idx_sales_reps_community_active ON sales_reps(community_id, is_active);
```

### Field Definitions

| Field | Type | Purpose |
|-------|------|---------|
| `is_active` | BOOLEAN | TRUE = currently listed, FALSE = no longer found on website |
| `last_seen_at` | TIMESTAMP | Last time this rep was found during collection |
| `inactivated_at` | TIMESTAMP | When the rep was marked inactive |
| `inactivation_reason` | VARCHAR(255) | Why marked inactive: "not_found_on_website", "replaced", "manual" |
| `data_source` | VARCHAR(50) | "manual", "collected", "imported" |
| `last_data_sync` | TIMESTAMP | Last collection job that checked this rep |

---

## Relationship Flows

### Flow 1: Community → Builder → SalesRep Discovery

```
Community Collection Job
         ↓
   Collect Community Data (Cinco Ranch)
         ↓
   Discover Active Builders in Community:
   - Perry Homes (builder_id=123)
   - Toll Brothers (builder_id=456)
   - David Weekley (builder_id=789)
         ↓
   For each Builder, discover SalesReps:
         ↓
   Perry Homes Team:
   ├─ Jane Smith (New Home Consultant)
   │  ├─ community_id = 999 (Cinco Ranch)
   │  └─ builder_id = 123 (Perry Homes)
   │
   └─ John Doe (Sales Manager)
      ├─ community_id = 999 (Cinco Ranch)
      └─ builder_id = 123 (Perry Homes)
```

### Flow 2: Builder → SalesRep → Community Assignment

```
Builder Collection Job (Perry Homes)
         ↓
   Discover Sales Team on perryhomes.com
         ↓
   Corporate Team (No community_id):
   ├─ Sarah Johnson (Regional VP)
   │  ├─ community_id = NULL (covers all)
   │  └─ builder_id = 123
   │
   Community-Specific Reps:
   ├─ Jane Smith → Cinco Ranch (community_id=999)
   ├─ Mike Chen → Bridgeland (community_id=888)
   └─ Lisa Wang → Aliana (community_id=777)
```

---

## Sales Rep Management Logic

### 1. Discovery & Matching

When discovering sales reps, the system must:

```python
def discover_sales_rep(collected_data, builder_id, community_id=None):
    """
    Discover and match a sales rep.

    Matching criteria (in order):
    1. Email match (highest confidence)
    2. First name + Last name + Builder ID
    3. Phone number match
    4. Fuzzy name match + Builder ID
    """

    # Step 1: Try exact email match
    existing = find_by_email(collected_data['email'], builder_id)
    if existing:
        return {
            'action': 'update',
            'sales_rep_id': existing.id,
            'changes': detect_changes(existing, collected_data)
        }

    # Step 2: Try name match
    existing = find_by_name(
        collected_data['first_name'],
        collected_data['last_name'],
        builder_id
    )
    if existing:
        return {
            'action': 'update',
            'sales_rep_id': existing.id,
            'changes': detect_changes(existing, collected_data),
            'warning': 'Matched by name only - verify identity'
        }

    # Step 3: No match - create new
    return {
        'action': 'create',
        'data': collected_data,
        'builder_id': builder_id,
        'community_id': community_id
    }
```

### 2. Active Status Management

**Rule**: A sales rep is marked `is_active=FALSE` when:
1. Multiple collection runs (2+) don't find them on the website
2. Another rep explicitly replaces them
3. Builder confirms they no longer work there

```python
def manage_sales_rep_status(job_id, builder_id, found_reps, community_id=None):
    """
    Update sales rep active status based on collection results.

    Args:
        job_id: Current collection job
        builder_id: Builder being collected
        found_reps: List of rep emails/names found during collection
        community_id: Optional community filter
    """

    # Get all currently active reps for this builder/community
    if community_id:
        existing_reps = get_active_sales_reps(
            builder_id=builder_id,
            community_id=community_id
        )
    else:
        existing_reps = get_active_sales_reps(builder_id=builder_id)

    found_emails = [rep['email'] for rep in found_reps if rep.get('email')]
    found_names = [(rep['first_name'], rep['last_name']) for rep in found_reps]

    for existing_rep in existing_reps:
        # Check if rep was found
        rep_found = (
            existing_rep.email in found_emails or
            (existing_rep.first_name, existing_rep.last_name) in found_names
        )

        if rep_found:
            # Rep still listed - update last_seen_at
            update_sales_rep_status(
                rep_id=existing_rep.id,
                last_seen_at=datetime.now(),
                last_data_sync=datetime.now()
            )
        else:
            # Rep NOT found - handle inactivation
            handle_missing_rep(existing_rep, job_id)


def handle_missing_rep(sales_rep, job_id):
    """
    Handle a sales rep that wasn't found during collection.

    Strategy: Grace period approach
    - 1st miss: Do nothing (might be temporary)
    - 2nd miss: Create pending change to mark inactive
    - Manual confirmation: Admin approves inactivation
    """

    days_since_last_seen = (datetime.now() - sales_rep.last_seen_at).days

    if days_since_last_seen > 60:  # Not seen in 2 months
        # Create pending change to mark inactive
        create_collection_change(
            job_id=job_id,
            entity_type='sales_rep',
            entity_id=sales_rep.id,
            field_name='is_active',
            old_value='true',
            new_value='false',
            change_type='modified',
            confidence=0.85,
            review_notes=f"Rep not found on website for {days_since_last_seen} days"
        )
    elif days_since_last_seen > 30:  # Not seen in 1 month
        # Log warning but don't create change yet
        log_warning(
            f"SalesRep {sales_rep.id} not found for {days_since_last_seen} days"
        )
```

### 3. Updating Existing Reps

```python
def update_sales_rep_info(sales_rep_id, new_data, job_id):
    """
    Detect changes and create pending updates for sales rep.
    """

    existing = get_sales_rep(sales_rep_id)
    changes = []

    # Compare each field
    fields_to_check = [
        'first_name', 'last_name', 'title', 'email',
        'phone', 'region', 'office_address'
    ]

    for field in fields_to_check:
        old_value = getattr(existing, field)
        new_value = new_data.get(field)

        if new_value and old_value != new_value:
            changes.append({
                'field': field,
                'old': old_value,
                'new': new_value,
                'confidence': calculate_confidence(field, old_value, new_value)
            })

    # Create collection_changes records
    for change in changes:
        create_collection_change(
            job_id=job_id,
            entity_type='sales_rep',
            entity_id=sales_rep_id,
            field_name=change['field'],
            old_value=change['old'],
            new_value=change['new'],
            change_type='modified',
            confidence=change['confidence']
        )

    # Update last_seen_at
    update_last_seen(sales_rep_id, datetime.now())

    return changes
```

---

## Collection Scenarios

### Scenario 1: Builder Collection (No Community Context)

```
Job: Collect Perry Homes builder data
URL: https://perryhomes.com/sales-team

Claude finds:
  Corporate Team:
  - Sarah Johnson (Regional VP) - sarah@perryhomes.com
  - Mike Davis (Sales Director) - mike@perryhomes.com

System Actions:
1. Search for existing reps by email
   - Sarah exists: id=501, community_id=NULL ✓
   - Mike is NEW

2. Compare Sarah's data:
   - Title changed: "VP of Sales" → "Regional VP"
   - Create pending change

3. Create Mike as new rep:
   - builder_id = 123 (Perry Homes)
   - community_id = NULL (corporate level)
   - is_active = TRUE
   - data_source = 'collected'

4. Check for missing reps:
   - Linda Brown (id=502) not found
   - Last seen: 45 days ago
   - Log warning (no action yet)
```

### Scenario 2: Community Collection (With Builder Context)

```
Job: Collect Cinco Ranch community data
URL: https://cincoranch.com/new-homes

Claude finds:
  Active Builders:
  - Perry Homes
    └─ Jane Smith (New Home Consultant)
       Email: jane@perryhomes.com
       Phone: (713) 555-0100
       Office: Cinco Ranch Sales Center

  - Toll Brothers
    └─ Tom Wilson (Sales Manager)
       Email: tom@tollbrothers.com

System Actions:
1. Link builders to community:
   - Perry Homes (builder_id=123) ↔ Cinco Ranch (community_id=999)
   - Toll Brothers (builder_id=456) ↔ Cinco Ranch (community_id=999)
   - Use builder_communities association table

2. For Jane Smith:
   - Search: email=jane@perryhomes.com, builder_id=123
   - Found: id=601, currently community_id=888 (Bridgeland)
   - Detect: Community reassignment!
   - Create change: community_id: 888 → 999

3. For Tom Wilson:
   - Search: email=tom@tollbrothers.com, builder_id=456
   - Not found: Create new
   - builder_id = 456
   - community_id = 999
   - is_active = TRUE

4. Check for missing reps at Cinco Ranch:
   - John Doe (id=603): builder_id=123, community_id=999
   - Not found in Perry Homes section
   - Last seen: 65 days ago
   - Create pending change: is_active: TRUE → FALSE
```

### Scenario 3: Rep Replacement Detection

```
Job: Collect Perry Homes at Cinco Ranch
Previous rep: John Doe (id=603, is_active=TRUE)

Claude finds:
  Perry Homes - Cinco Ranch:
  - Jane Smith (replacing John Doe as of March 2025)

System Actions:
1. Create Jane Smith as new rep:
   - builder_id = 123
   - community_id = 999
   - is_active = TRUE

2. Mark John Doe inactive:
   - Create change: is_active: TRUE → FALSE
   - inactivation_reason = "replaced"
   - replacement_note = "Replaced by Jane Smith (id=604)"

3. Notify admin:
   - "John Doe no longer listed, replaced by Jane Smith"
   - Admin reviews and approves
```

---

## API Endpoint Updates

### Get Sales Reps with Status Filter

```http
GET /api/v1/builders/{builder_id}/sales-reps?is_active=true&community_id=999
Authorization: Bearer {token}

Response 200:
{
  "builder_id": 123,
  "builder_name": "Perry Homes",
  "community_id": 999,
  "community_name": "Cinco Ranch",
  "sales_reps": [
    {
      "id": 601,
      "sales_rep_id": "SLS-001",
      "first_name": "Jane",
      "last_name": "Smith",
      "title": "New Home Consultant",
      "email": "jane@perryhomes.com",
      "phone": "(713) 555-0100",
      "is_active": true,
      "last_seen_at": "2025-11-24T14:30:00Z",
      "data_source": "collected"
    }
  ],
  "inactive_reps": [
    {
      "id": 603,
      "first_name": "John",
      "last_name": "Doe",
      "is_active": false,
      "inactivated_at": "2025-03-15T10:00:00Z",
      "inactivation_reason": "not_found_on_website"
    }
  ]
}
```

### Sales Rep Change Review

```http
GET /api/v1/admin/sales-reps/pending-changes?builder_id=123

Response 200:
{
  "pending_changes": [
    {
      "change_id": 3001,
      "entity_type": "sales_rep",
      "entity_id": 603,
      "rep_name": "John Doe",
      "field": "is_active",
      "current_value": true,
      "proposed_value": false,
      "reason": "Not found on website for 65 days",
      "confidence": 0.85,
      "last_seen_at": "2025-09-20T08:00:00Z"
    },
    {
      "change_id": 3002,
      "entity_type": "sales_rep",
      "entity_id": 601,
      "rep_name": "Jane Smith",
      "field": "community_id",
      "current_value": 888,
      "proposed_value": 999,
      "reason": "Found listed at new community",
      "confidence": 0.92
    }
  ]
}
```

---

## Change Detection Examples

### Example 1: Title Update
```json
{
  "change_id": 4001,
  "entity_type": "sales_rep",
  "entity_id": 601,
  "field": "title",
  "old_value": "Sales Consultant",
  "new_value": "Senior New Home Consultant",
  "change_type": "modified",
  "confidence": 0.95,
  "source_url": "https://perryhomes.com/cincor anch/team"
}
```

### Example 2: Community Reassignment
```json
{
  "change_id": 4002,
  "entity_type": "sales_rep",
  "entity_id": 601,
  "field": "community_id",
  "old_value": "888",
  "new_value": "999",
  "change_type": "modified",
  "confidence": 0.90,
  "source_url": "https://cincoranch.com/new-homes",
  "review_notes": "Jane Smith now listed at Cinco Ranch instead of Bridgeland"
}
```

### Example 3: Inactivation
```json
{
  "change_id": 4003,
  "entity_type": "sales_rep",
  "entity_id": 603,
  "field": "is_active",
  "old_value": "true",
  "new_value": "false",
  "change_type": "modified",
  "confidence": 0.85,
  "review_notes": "Not found on website since 2025-09-20 (65 days ago)"
}
```

### Example 4: New Rep Discovery
```json
{
  "change_id": 4004,
  "entity_type": "sales_rep",
  "entity_id": null,
  "is_new_entity": true,
  "proposed_entity_data": {
    "first_name": "Tom",
    "last_name": "Wilson",
    "title": "Sales Manager",
    "email": "tom@tollbrothers.com",
    "phone": "(713) 555-0200",
    "builder_id": 456,
    "community_id": 999,
    "is_active": true,
    "data_source": "collected"
  },
  "confidence": 0.92,
  "source_url": "https://cincoranch.com/toll-brothers"
}
```

---

## Data Collection Prompt Updates

### Builder Collection - Include Sales Team

```python
prompt = f"""
Search the web for information about {builder_name}, a home builder in {location}.

Extract the following information:

1. Company Information:
   - Company name, website, phone, email
   - Founded year, employee count
   - Specialties and service areas

2. **Sales Team** (IMPORTANT):
   - List ALL sales representatives
   - For each rep, extract:
     * First name and last name
     * Job title (e.g., "New Home Consultant", "Sales Manager")
     * Email address
     * Phone number
     * Office location or region
     * Community assignment (if mentioned)

3. Credentials, Awards, Communities served

Format the sales team as a JSON array:
{{
  "sales_team": [
    {{
      "first_name": "Jane",
      "last_name": "Smith",
      "title": "New Home Consultant",
      "email": "jane@perryhomes.com",
      "phone": "(713) 555-0100",
      "region": "Northwest Houston",
      "community": "Cinco Ranch"  // if mentioned
    }}
  ]
}}

Include source URLs and confidence scores.
"""
```

### Community Collection - Include Builder Sales Contacts

```python
prompt = f"""
Search the web for information about {community_name}, an HOA/community in {location}.

Extract the following information:

1. Community Details:
   - Name, location, HOA fees
   - Amenities, total homes

2. **Active Builders** (IMPORTANT):
   - List ALL builders currently building in this community
   - For each builder, extract:
     * Builder/company name
     * **Sales representative(s) for this community**:
       - First name, last name
       - Title
       - Contact info (email, phone)
       - Sales office location

3. Awards, Events, Development phases

Format as JSON:
{{
  "builders": [
    {{
      "name": "Perry Homes",
      "sales_reps": [
        {{
          "first_name": "Jane",
          "last_name": "Smith",
          "title": "New Home Consultant",
          "email": "jane@perryhomes.com",
          "phone": "(713) 555-0100",
          "office": "Cinco Ranch Sales Center"
        }}
      ]
    }}
  ]
}}
"""
```

---

## Database Migration

```sql
-- Migration: Add sales rep status tracking
-- Version: 20251124_add_sales_rep_status

-- Add new columns
ALTER TABLE sales_reps
ADD COLUMN is_active BOOLEAN DEFAULT TRUE NOT NULL AFTER verified,
ADD COLUMN last_seen_at TIMESTAMP NULL AFTER updated_at,
ADD COLUMN inactivated_at TIMESTAMP NULL AFTER last_seen_at,
ADD COLUMN inactivation_reason VARCHAR(255) AFTER inactivated_at,
ADD COLUMN data_source VARCHAR(50) DEFAULT 'manual' NOT NULL AFTER inactivation_reason,
ADD COLUMN last_data_sync TIMESTAMP NULL AFTER data_source;

-- Add indexes
CREATE INDEX idx_sales_reps_active ON sales_reps(is_active);
CREATE INDEX idx_sales_reps_builder_active ON sales_reps(builder_id, is_active);
CREATE INDEX idx_sales_reps_community_active ON sales_reps(community_id, is_active);
CREATE INDEX idx_sales_reps_last_seen ON sales_reps(last_seen_at);

-- Set initial values for existing reps
UPDATE sales_reps
SET
    is_active = TRUE,
    last_seen_at = updated_at,
    data_source = 'manual'
WHERE is_active IS NULL;

-- Add comment
ALTER TABLE sales_reps
COMMENT = 'Sales representatives linked to builders and optionally to specific communities';
```

---

## Testing Scenarios

### Test 1: New Rep Discovery
```
GIVEN: Perry Homes has no reps in DB
WHEN: Collection finds Jane Smith
THEN: Create new SalesRep with is_active=TRUE
```

### Test 2: Rep Update
```
GIVEN: Jane Smith exists (id=601)
WHEN: Collection finds updated title
THEN: Create pending change, update last_seen_at
```

### Test 3: Rep Goes Missing
```
GIVEN: John Doe (id=603, last_seen_at=60 days ago)
WHEN: Collection doesn't find John
THEN: Create pending change to mark is_active=FALSE
```

### Test 4: Rep Reassignment
```
GIVEN: Jane at Bridgeland (community_id=888)
WHEN: Collection finds Jane at Cinco Ranch
THEN: Create change: community_id 888→999
```

### Test 5: Relationship Integrity
```
GIVEN: Community collection finds builder + rep
WHEN: Applying changes
THEN: Verify builder_id and community_id match
      AND builder is linked to community via builder_communities
```

---

## Summary

### Key Points

1. **Three-way relationship**: Community ↔ Builder ↔ SalesRep
2. **Status tracking**: `is_active` field with grace period (60 days)
3. **Change detection**: Compare all fields, create pending updates
4. **Dual context**: Reps can be corporate (no community) or community-specific
5. **Admin review**: All status changes require approval

### Next Steps

1. Add `is_active` and related fields to `sales_reps` table
2. Update collection prompts to explicitly request sales team info
3. Implement rep matching logic (email → name → phone)
4. Build status management functions
5. Create admin UI for reviewing rep changes
6. Test all relationship flows

---

**Document Version**: v1.0
**Status**: Draft - Ready for Implementation
**Dependencies**: DATA_COLLECTOR_COMPREHENSIVE_PLAN.md
