# Preventing Orphaned Builders and Properties

## The Problem

**Orphaned entities** are builders or properties that should be linked to a parent entity (community or builder) but aren't, because the parent didn't exist when they were created.

### Current Situation (FIXED for Builders ✅)

With the auto-approval implementation, **orphaned builders are now prevented** when:
- Builder is approved
- References a community with confidence >= 75%
- Community is automatically approved first
- Builder-community relationship is established

### Remaining Risk: Discovery Phase

However, there's still a potential issue at the **discovery/collection phase**:

## Root Cause Analysis

###  1. Community Discovery Creates Builder Jobs **WITHOUT** Community ID

**Location**: `src/collection/community_collector.py:1102`

```python
builder_job = CollectionJob(
    entity_type="builder",
    entity_id=None,
    job_type="discovery",
    parent_entity_type="community",
    parent_entity_id=None,  # ❌ Community not created yet (pending approval)
    status="pending",
    priority=6,
    search_query=builder_name,
    search_filters={
        "community_name": community_name,
        "location": location
    }
)
```

**Problem**: When a community discovery job finds builders, it creates builder jobs with `parent_entity_id=None` because the community hasn't been created yet (it's still pending approval).

**Impact**: When the builder collector runs (`builder_collector.py:285-287`), it checks:
```python
if self.job.parent_entity_type == "community" and self.job.parent_entity_id:
    entity_data["community_id"] = self.job.parent_entity_id
```

Since `parent_entity_id` is `None`, the `community_id` is **NOT** added to the builder's proposed_entity_data!

### 2. Similar Issue for Properties

Properties likely have the same issue when discovered by builder jobs before the builder is approved.

## Solutions

### Solution 1: Use CollectionChange Entity ID (RECOMMENDED)

Instead of using the database entity ID (which doesn't exist yet), use the **CollectionChange entity_id** which is assigned when the community change is recorded.

**Files to Modify**:
1. `src/collection/community_collector.py` (line 1102)
2. Similar files for property discovery

**Implementation**:

```python
# In community_collector.py, when creating builder jobs:
builder_job = CollectionJob(
    entity_type="builder",
    entity_id=None,
    job_type="discovery",
    parent_entity_type="community",
    parent_entity_id=self.community_change_id,  # ✅ Use CollectionChange ID instead
    status="pending",
    priority=6,
    search_query=builder_name,
    search_filters={
        "community_name": community_name,
        "location": location
    }
)
```

**Requirements**:
- Need to track the CollectionChange ID when recording a new community
- Need to update builder_collector to understand that parent_entity_id might be a CollectionChange ID for pending entities

### Solution 2: Update Builder Jobs After Community Approval (CURRENT WORKAROUND)

When a community is approved, update all related builder jobs with the new community database ID.

**Files to Modify**:
1. `routes/admin/collection.py` - Community approval section

**Implementation**:

```python
# After community is created and approved:
if community.id:
    # Update all builder jobs that reference this community
    from model.collection import CollectionJob

    builder_jobs = db.query(CollectionJob).filter(
        CollectionJob.parent_entity_type == "community",
        CollectionJob.parent_entity_id == None,  # or == change.id
        CollectionJob.search_filters['community_name'].astext == community.name
    ).all()

    for builder_job in builder_jobs:
        builder_job.parent_entity_id = community.id

    db.flush()
```

**Pros**: Simple, doesn't require collector changes
**Cons**: Requires JSON filtering, may miss some jobs if community name doesn't match exactly

### Solution 3: Store Community Reference in Collected Data

Store enough community information in the builder's collected data to look up the community later.

**Files to Modify**:
1. `src/collection/prompts.py` - Add community collection to builder prompts
2. `src/collection/builder_collector.py` - Add community lookup logic

**Implementation**:

```python
# In builder_collector.py:
def _process_new_builder(self, collected_data):
    # ... existing code ...

    # Try to find community by name
    community_name = collected_data.get("community_name")
    if community_name:
        community = db.query(Community).filter(
            Community.name == community_name
        ).first()

        if community:
            entity_data["community_id"] = community.id
        else:
            # Check for pending community change
            community_change = db.query(CollectionChange).filter(
                CollectionChange.entity_type == "community",
                CollectionChange.proposed_entity_data['name'].astext == community_name,
                CollectionChange.status == "pending"
            ).first()

            if community_change and community_change.entity_id:
                entity_data["community_id"] = community_change.entity_id
```

**Pros**: Most robust, uses actual data instead of job metadata
**Cons**: Most complex, requires prompt changes and duplicate detection

## Recommended Implementation Plan

**Phase 1: Immediate Fix (Use Auto-Approval)**
✅ **DONE** - Auto-approval at 75% confidence prevents orphans at approval time

**Phase 2: Fix Discovery Phase (Use Solution 2)**
1. Implement job update logic when community is approved
2. Test with community discovery → builder jobs → approve community → verify jobs updated

**Phase 3: Long-term Fix (Use Solution 1 + 3)**
1. Track CollectionChange IDs in jobs
2. Add community name to builder collected data
3. Update builder_collector to handle both pending and approved communities

## Detection Script

Create a script to detect existing orphaned entities:

```python
# detect_orphans.py
from sqlalchemy import create_engine, text

engine = create_engine(DB_URL)

with engine.connect() as conn:
    # Find builders without community relationships
    orphaned_builders = conn.execute(text("""
        SELECT b.id, b.builder_id, b.name
        FROM builder_profiles b
        LEFT JOIN builder_communities bc ON b.id = bc.builder_id
        WHERE bc.builder_id IS NULL
          AND b.community_id IS NULL
    """))

    print(f"Orphaned Builders: {len(list(orphaned_builders))}")

    # Find properties without community or builder relationships
    orphaned_properties = conn.execute(text("""
        SELECT p.id, p.property_id, p.address
        FROM properties p
        WHERE p.community_id IS NULL
          AND p.builder_id IS NULL
    """))

    print(f"Orphaned Properties: {len(list(orphaned_properties))}")
```

## Testing Plan

1. **Test Discovery Phase**:
   - Create community discovery job
   - Wait for builder jobs to be created
   - Check if builder jobs have parent_entity_id set

2. **Test Approval Flow**:
   - Approve community (confidence >= 75%)
   - Check if related builder jobs get updated with community ID
   - Approve builders
   - Verify builder-community relationships exist

3. **Test Edge Cases**:
   - Community rejected instead of approved
   - Builder approved before community
   - Community name changes during review

## Migration Plan for Existing Orphans

If orphaned entities already exist:

```sql
-- Find and link orphaned builders based on name matching
UPDATE builder_profiles b
SET community_id = (
    SELECT c.community_id
    FROM communities c
    WHERE c.name LIKE CONCAT('%', b.name, '%')
    LIMIT 1
)
WHERE b.community_id IS NULL
  AND NOT EXISTS (
      SELECT 1 FROM builder_communities bc WHERE bc.builder_id = b.id
  );
```

## Summary

**Current State**:
- ✅ Builders are protected from orphaning at approval time (auto-approval)
- ❌ Builders can still get orphaned if job parent_entity_id is not set correctly
- ❌ Properties likely have similar orphan risk

**Next Steps**:
1. Implement Solution 2 (update jobs after community approval)
2. Test end-to-end workflow
3. Create detection script to find any existing orphans
4. Plan migration for existing orphaned entities
