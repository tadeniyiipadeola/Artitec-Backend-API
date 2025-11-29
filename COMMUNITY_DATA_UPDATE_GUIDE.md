# Community Data Update Guide

## Overview

We recently added 13 new fields to the communities table to capture data that was being collected from Claude API but not stored:

### New Fields Added
1. `phone` - Community contact phone
2. `email` - Community contact email
3. `sales_office_address` - Sales office location
4. `elementary_school` - Elementary school assignment
5. `middle_school` - Middle school assignment
6. `high_school` - High school assignment
7. `developer_name` - Developer/builder name
8. `rating` - Average rating
9. `review_count` - Number of reviews

Plus 4 fields that already existed in database:
- `school_district`
- `hoa_management_company`
- `hoa_contact_phone`
- `hoa_contact_email`

## What Was Done

### 1. Database Migration ✅
- **File**: `alembic/versions/92d10784beb7_add_community_contact_schools_hoa_fields.py`
- **Action**: Added 9 new columns to `communities` table
- **Status**: Completed and applied

### 2. SQLAlchemy Model Update ✅
- **File**: `model/profiles/community.py`
- **Action**: Added all 13 fields to Community model
- **Status**: Completed

### 3. Pydantic Schema Updates ✅
- **File**: `schema/community.py`
- **Action**: Updated CommunityBase and CommunityUpdate schemas
- **Status**: Completed

### 4. Collector Logic ✅
- **File**: `src/collection/community_collector.py`
- **Action**: No changes needed - collector automatically uses updated schemas
- **Status**: Verified working

## How to Update Existing Communities

You have 30 existing communities in the database that don't have the new field data. Use the provided script to populate these fields.

### Script: `update_existing_communities.py`

This script creates "update" collection jobs for existing communities to fetch and populate the missing data.

#### Usage Options

**1. Dry Run (Test without making changes)**
```bash
python update_existing_communities.py --dry-run
```

**2. Update first 5 communities (for testing)**
```bash
python update_existing_communities.py --limit 5
```

**3. Update first 5 communities with monitoring**
```bash
python update_existing_communities.py --limit 5 --monitor
```

**4. Update ALL 30 communities**
```bash
python update_existing_communities.py
```

**5. Update ALL communities with monitoring**
```bash
python update_existing_communities.py --monitor --monitor-duration 1800
```

#### Script Parameters

| Parameter | Description | Default |
|-----------|-------------|---------|
| `--limit N` | Only update first N communities | All (30) |
| `--dry-run` | Show what would be done without creating jobs | Off |
| `--monitor` | Monitor job progress after creation | Off |
| `--monitor-duration SEC` | Max monitoring time in seconds | 600 |
| `--batch-delay SEC` | Delay between job creations | 1.0 |

### What the Script Does

1. **Fetches Communities**: Queries database for all active communities
2. **Creates Update Jobs**: For each community, creates a `job_type='update'` collection job
3. **Starts Jobs**: Automatically starts each job
4. **Monitors Progress** (if --monitor): Tracks completion status

### Example Run

```bash
$ python update_existing_communities.py --limit 3 --monitor

================================================================================
Update Existing Communities - Populate Missing Fields
================================================================================

Fetching communities from database...
✅ Found 30 active communities
Limiting to first 3 communities

================================================================================
Creating Update Jobs
================================================================================

[1/3] Light Farms (Celina, TX)
  ✅ Job JOB-1732905123-ABC123 created for: Light Farms
  ▶️  Started
[2/3] Tavola (Porter, TX)
  ✅ Job JOB-1732905124-DEF456 created for: Tavola
  ▶️  Started
[3/3] Woodson's Reserve (Porter, TX)
  ✅ Job JOB-1732905125-GHI789 created for: Woodson's Reserve
  ▶️  Started

================================================================================
Summary: Created 3 jobs
================================================================================

================================================================================
Monitoring 3 jobs (interval: 15s, max: 600s)
================================================================================

✅ JOB-1732905123-ABC123 (Light Farms): 8/8 changes applied
✅ JOB-1732905124-DEF456 (Tavola): 6/6 changes applied
✅ JOB-1732905125-GHI789 (Woodson's Reserve): 7/7 changes applied

================================================================================
Final Summary:
  ✅ Completed: 3
  ❌ Failed: 0
  ⏳ Still Running: 0
================================================================================
```

## Verifying the Updates

After running the script, verify the data was populated:

```sql
-- Check a specific community
SELECT
    name,
    phone,
    email,
    sales_office_address,
    elementary_school,
    middle_school,
    high_school,
    developer_name,
    rating,
    review_count
FROM communities
WHERE name = 'Light Farms';

-- Check how many communities have the new data
SELECT
    COUNT(*) as total_communities,
    COUNT(phone) as have_phone,
    COUNT(email) as have_email,
    COUNT(sales_office_address) as have_sales_office,
    COUNT(elementary_school) as have_elementary,
    COUNT(middle_school) as have_middle,
    COUNT(high_school) as have_high,
    COUNT(developer_name) as have_developer
FROM communities
WHERE is_active = 1;
```

## Future Collections

All **new** community collections (discovery and update jobs) will automatically populate these fields. The collector already knows about them through the updated Pydantic schemas.

## Rollback (if needed)

If you need to roll back the database changes:

```bash
# Downgrade the migration
alembic downgrade -1
```

This will remove the 9 new columns added in the migration.

## API Changes

The fields are now exposed in the API responses:

### GET /v1/communities/{id}
```json
{
  "id": 38,
  "name": "Light Farms",
  "phone": "(555) 123-4567",
  "email": "sales@lightfarms.com",
  "sales_office_address": "123 Main St, Celina, TX 75009",
  "elementary_school": "Light Farms Elementary",
  "middle_school": "Celina Middle School",
  "high_school": "Celina High School",
  "developer_name": "Hillwood Communities",
  "rating": 4.5,
  "review_count": 127,
  ...
}
```

## Monitoring Jobs

You can monitor collection jobs in several ways:

1. **API Docs**: http://127.0.0.1:8000/docs
   - Navigate to `/v1/admin/collection/jobs/{job_id}`

2. **Script with --monitor flag**: See progress in terminal

3. **Database Query**:
```sql
SELECT job_id, entity_type, job_type, status,
       changes_detected, changes_applied, error_message
FROM collection_jobs
WHERE entity_type = 'community'
  AND job_type = 'update'
ORDER BY created_at DESC
LIMIT 10;
```

## Troubleshooting

### Jobs Failing

Check the logs:
```sql
SELECT * FROM collection_job_logs
WHERE job_id = 'JOB-xxx'
ORDER BY logged_at DESC;
```

### Server Not Running

Make sure the backend server is running:
```bash
cd "/Users/adeniyi_family_executor/Documents/Development/Artitec Backend Development"
source .venv/bin/activate
uvicorn src.app:app --reload
```

### Database Connection Issues

Verify database credentials in the script match your environment.

## Summary

- ✅ Database migration applied
- ✅ Models and schemas updated
- ✅ Collector logic verified
- 📝 30 communities ready to update
- 🔧 Script ready: `update_existing_communities.py`

**Next Step**: Run the script to populate the missing data for your 30 existing communities.
