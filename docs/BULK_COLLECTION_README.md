# Bulk Collection for Active Communities

This guide explains how to run bulk collection jobs for builders and properties across all active (non-completed) communities.

## Overview

The system provides scripts to:
1. **Create jobs** for all active communities (builder + property collection)
2. **Execute jobs** in controlled batches
3. **Monitor progress** in real-time

## Quick Start

### Step 1: Check What Will Be Collected

First, see how many communities will be processed:

```bash
python -c "
from sqlalchemy import text
from config.db import SessionLocal

db = SessionLocal()
query = text('''
    SELECT COUNT(*) as count,
           SUM(CASE WHEN development_stage = \"Completed\" THEN 1 ELSE 0 END) as completed,
           SUM(CASE WHEN development_stage != \"Completed\" OR development_stage IS NULL THEN 1 ELSE 0 END) as active
    FROM communities
''')
result = db.execute(query).fetchone()
db.close()

print(f'Total communities: {result.count}')
print(f'Completed: {result.completed}')
print(f'Active (not completed): {result.active}')
print(f'Jobs that will be created: {result.active * 2} (builder + property)')
"
```

### Step 2: Run Bulk Collection Script

Make the script executable:
```bash
chmod +x bulk_collect_active_communities.py
```

Run the script:
```bash
python bulk_collect_active_communities.py
```

The script will:
1. ✅ Find all active communities (not completed)
2. ✅ Create builder collection jobs for each
3. ✅ Create property inventory jobs for each
4. ❓ Ask if you want to execute jobs now

**Example Output:**
```
================================================================================
BULK COLLECTION FOR ACTIVE COMMUNITIES
================================================================================

📋 Fetching active communities (not completed)...

✅ Found 30 active communities

--------------------------------------------------------------------------------

[1/30] Harper's Preserve
   Location: Conroe, TX
   Stage: Phase 2
   Status: active
   🏗️  Creating builder collection job...
   ✅ Builder job created: JOB-1764105000-ABC123
   🏘️  Creating property collection job...
   ✅ Property job created: JOB-1764105001-DEF456

[2/30] Woodson's Reserve
   ...
```

### Step 3: Monitor Progress

**One-time check:**
```bash
python monitor_bulk_collection.py
```

**Continuous monitoring** (updates every 10 seconds):
```bash
python monitor_bulk_collection.py --watch
```

**Custom refresh interval** (e.g., every 5 seconds):
```bash
python monitor_bulk_collection.py --watch 5
```

**Example Output:**
```
================================================================================
BULK COLLECTION PROGRESS MONITOR
================================================================================

📊 OVERALL JOB STATISTICS
--------------------------------------------------------------------------------
   Total Jobs: 60
   ✅ Completed: 15
   🔄 Running: 5
   ⏳ Pending: 38
   ❌ Failed: 2

🏗️  BUILDER COLLECTION JOBS
--------------------------------------------------------------------------------
   ✅ Completed: 8
   🔄 Running: 2
   ⏳ Pending: 19
   ❌ Failed: 1

🏘️  PROPERTY COLLECTION JOBS
--------------------------------------------------------------------------------
   ✅ Completed: 7
   🔄 Running: 3
   ⏳ Pending: 19
   ❌ Failed: 1
```

## Detailed Usage

### Creating Jobs Only (No Execution)

If you want to create jobs but execute them later:

1. Run the bulk collection script
2. When prompted "Do you want to execute jobs now?", answer **no**
3. Jobs will be created in "pending" status
4. Execute them later via API or script

### Executing Jobs in Batches

**Option 1: During creation**
- The script will ask if you want to execute jobs
- Specify batch size (default: 5)
- Jobs will execute automatically

**Option 2: Via API**
```bash
curl -X POST "http://127.0.0.1:8000/v1/admin/collection/jobs/execute?limit=5"
```

**Option 3: Via Python**
```python
import requests

response = requests.post(
    "http://127.0.0.1:8000/v1/admin/collection/jobs/execute",
    params={"limit": 5}
)
print(response.json())
```

### Recommended Batch Sizes

- **Small scale (< 10 communities)**: 5-10 jobs at once
- **Medium scale (10-50 communities)**: 3-5 jobs at once
- **Large scale (> 50 communities)**: 2-3 jobs at once

Lower batch sizes prevent:
- API rate limiting
- System overload
- Database connection exhaustion

## What Gets Collected

### For Each Active Community:

#### Builder Collection Job
- Discovers home builders operating in the community
- Collects builder details (name, website, contact info)
- Creates builder profiles if they don't exist
- Updates existing builder information
- May create cascade jobs for sales reps

#### Property Inventory Job
- Finds homes for sale in the community
- Collects property details (price, beds, baths, sqft)
- Creates property listings
- Updates availability counts for the community
- Links properties to builders and communities

## Job Priorities

All bulk-created jobs have **priority 5** (medium priority).

You can manually adjust priority via API if needed:
- Priority 1-3: Low priority
- Priority 4-6: Medium priority
- Priority 7-10: High priority

## Filtering Communities

### Current Filter
The script collects for communities where:
- `development_stage != 'Completed'`
- OR `development_stage IS NULL`

### Custom Filters

Edit `bulk_collect_active_communities.py` and modify the SQL query:

**Example 1: Only specific states**
```python
query = text("""
    SELECT ...
    FROM communities
    WHERE (development_stage != 'Completed' OR development_stage IS NULL)
      AND state IN ('TX', 'CA', 'FL')
    ORDER BY created_at DESC
""")
```

**Example 2: Only specific development stages**
```python
query = text("""
    SELECT ...
    FROM communities
    WHERE development_stage IN ('Phase 1', 'Phase 2', 'Phase 3')
    ORDER BY created_at DESC
""")
```

**Example 3: Recently created communities only**
```python
query = text("""
    SELECT ...
    FROM communities
    WHERE (development_stage != 'Completed' OR development_stage IS NULL)
      AND created_at >= DATE_SUB(NOW(), INTERVAL 30 DAY)
    ORDER BY created_at DESC
""")
```

## Troubleshooting

### Problem: Jobs stuck in "pending"
**Solution:** Execute them manually
```bash
curl -X POST "http://127.0.0.1:8000/v1/admin/collection/jobs/execute?limit=10"
```

### Problem: Many failed jobs
**Solution:**
1. Check the error messages in job logs
2. Common causes: API rate limits, invalid data, network issues
3. Retry failed jobs via API

### Problem: Script can't connect to API
**Solution:**
1. Ensure backend is running: `cd /path/to/backend && uvicorn main:app --reload`
2. Check API URL in script (default: `http://127.0.0.1:8000`)

### Problem: Database connection errors
**Solution:**
1. Check database credentials in `.env`
2. Ensure database is running
3. Check connection limits

## Performance Tips

1. **Don't run all jobs at once** - Use batch execution
2. **Monitor system resources** - Watch CPU, memory, API calls
3. **Run during off-peak hours** - Less strain on external APIs
4. **Check rate limits** - Some data sources have rate limits
5. **Use monitoring script** - Track progress to catch issues early

## API Endpoints Used

- `POST /v1/admin/collection/jobs` - Create new job
- `POST /v1/admin/collection/jobs/execute` - Execute pending jobs
- `GET /v1/admin/collection/jobs` - List jobs (with filters)
- `GET /v1/admin/collection/stats` - Get job statistics
- `GET /v1/admin/collection/jobs/{job_id}` - Get specific job details

## Files

- `bulk_collect_active_communities.py` - Main bulk collection script
- `monitor_bulk_collection.py` - Job monitoring script
- `BULK_COLLECTION_README.md` - This file

## Examples

### Full Workflow Example

```bash
# 1. Check what will be collected
python -c "from sqlalchemy import text; from config.db import SessionLocal; ..."

# 2. Run bulk collection (creates jobs, asks about execution)
python bulk_collect_active_communities.py

# 3. Start monitoring in another terminal
python monitor_bulk_collection.py --watch 10

# 4. Wait for jobs to complete
# (Monitor will show progress)

# 5. Check final results
python monitor_bulk_collection.py
```

### Creating Jobs for Testing (1 community)

Modify the script temporarily:
```python
# In get_active_communities(), add LIMIT
query = text("""
    ...
    ORDER BY created_at DESC
    LIMIT 1  # <-- Add this line
""")
```

This creates only 2 jobs (1 builder + 1 property) for testing.

## Next Steps

After collection completes:
1. ✅ Review collected data in database
2. ✅ Check for any failed jobs and retry
3. ✅ Verify builder and property data quality
4. ✅ Run additional inventory updates as needed
5. ✅ Set up periodic collection schedules if desired
