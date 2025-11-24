# Data Collector Quick Start Guide

Get up and running with the Data Collector system in 5 minutes.

---

## Prerequisites

1. Database migrations applied
2. Claude API key configured
3. FastAPI server running

---

## Step 1: Configure Environment

Add to your `.env` file:

```bash
ANTHROPIC_API_KEY=sk-ant-your-api-key-here
```

---

## Step 2: Register Routes

In `src/app.py`, add:

```python
from routes.admin.collection import router as collection_router

app.include_router(collection_router)
```

Restart your FastAPI server.

---

## Step 3: Create Your First Collection Job

### Option A: Via API (Recommended)

```bash
# Create a community collection job
curl -X POST "http://localhost:8000/admin/collection/jobs" \
  -H "Content-Type: application/json" \
  -d '{
    "entity_type": "community",
    "search_query": "Bridgeland",
    "location": "Houston, TX",
    "job_type": "discovery",
    "priority": 7
  }'
```

Response:
```json
{
  "job_id": "JOB-1732473600-ABC123",
  "entity_type": "community",
  "status": "pending",
  "...": "..."
}
```

### Option B: Via Python

```python
from sqlalchemy.orm import Session
from src.collection.job_executor import create_community_collection_job, JobExecutor
from config.database import SessionLocal

# Create database session
db = SessionLocal()

# Create job
job = create_community_collection_job(
    db=db,
    community_name="Bridgeland",
    location="Houston, TX"
)

print(f"Created job: {job.job_id}")

# Execute job
executor = JobExecutor(db)
executor.execute_job(job.job_id)

print(f"Job completed with status: {job.status}")
db.close()
```

---

## Step 4: Execute the Job

```bash
# Execute specific job
curl -X POST "http://localhost:8000/admin/collection/jobs/{job_id}/execute"

# OR execute all pending jobs
curl -X POST "http://localhost:8000/admin/collection/jobs/execute-pending?limit=10"
```

---

## Step 5: Review Changes

```bash
# Get pending changes
curl -X GET "http://localhost:8000/admin/collection/changes?status=pending&limit=50"
```

Response:
```json
[
  {
    "id": 1,
    "entity_type": "community",
    "field_name": "description",
    "old_value": "Old description",
    "new_value": "New description from web",
    "status": "pending",
    "confidence": 0.9,
    "...": "..."
  }
]
```

---

## Step 6: Approve/Reject Changes

### Approve Single Change

```bash
curl -X POST "http://localhost:8000/admin/collection/changes/1/review" \
  -H "Content-Type: application/json" \
  -d '{
    "action": "approve",
    "notes": "Verified and accurate"
  }'
```

### Bulk Approve Multiple Changes

```bash
curl -X POST "http://localhost:8000/admin/collection/changes/review-bulk" \
  -H "Content-Type: application/json" \
  -d '{
    "change_ids": [1, 2, 3, 4, 5],
    "action": "approve",
    "notes": "Batch approval"
  }'
```

---

## Common Workflows

### Workflow 1: Collect Data for Existing Community

```bash
# 1. Create update job for existing community
curl -X POST "http://localhost:8000/admin/collection/jobs" \
  -H "Content-Type: application/json" \
  -d '{
    "entity_type": "community",
    "entity_id": 123,
    "job_type": "update",
    "priority": 5
  }'

# 2. Execute job
curl -X POST "http://localhost:8000/admin/collection/jobs/{job_id}/execute"

# 3. Review changes
curl -X GET "http://localhost:8000/admin/collection/changes?status=pending"

# 4. Approve changes
curl -X POST "http://localhost:8000/admin/collection/changes/review-bulk" \
  -H "Content-Type: application/json" \
  -d '{"change_ids": [1,2,3], "action": "approve"}'
```

### Workflow 2: Discover Properties for Builder in Community

```bash
# Create property inventory job
curl -X POST "http://localhost:8000/admin/collection/jobs" \
  -H "Content-Type: application/json" \
  -d '{
    "entity_type": "property",
    "job_type": "inventory",
    "builder_id": 456,
    "community_id": 123,
    "location": "Houston, TX",
    "priority": 3
  }'

# Execute and review...
```

---

## Monitoring

### Check Job Status

```bash
# List all jobs
curl -X GET "http://localhost:8000/admin/collection/jobs"

# Filter by status
curl -X GET "http://localhost:8000/admin/collection/jobs?status=completed"

# Get specific job
curl -X GET "http://localhost:8000/admin/collection/jobs/{job_id}"
```

### View Statistics

```bash
# Get change statistics
curl -X GET "http://localhost:8000/admin/collection/changes/stats"
```

Response:
```json
{
  "by_status": {
    "pending": 15,
    "approved": 42,
    "rejected": 3
  },
  "by_entity_type": {
    "community": 10,
    "builder": 20,
    "property": 30
  },
  "total_pending": 15
}
```

---

## Troubleshooting

### Job Failed with Error

```bash
# Check job details for error message
curl -X GET "http://localhost:8000/admin/collection/jobs/{job_id}"
```

Look for `error_message` field.

**Common Issues**:
1. **"Claude API call failed"** → Check ANTHROPIC_API_KEY
2. **"Builder context required"** → Ensure builder_id is provided
3. **"No matches found"** → Claude couldn't parse response, check prompt

### No Changes Detected

Possible reasons:
- Data hasn't changed since last collection
- Claude couldn't find reliable information
- Website structure changed

### Changes Have Low Confidence

Review manually - low confidence changes should be verified before approval.

---

## Tips & Best Practices

1. **Start with High Priority Entities**:
   - Use `priority: 7-10` for important communities/builders

2. **Review Changes Daily**:
   - Check pending changes regularly
   - Approve high-confidence changes quickly

3. **Monitor API Costs**:
   - Each community collection costs ~$0.26
   - Limit unnecessary re-collections

4. **Use Cascade Jobs**:
   - Start with community collection
   - Let system automatically create builder/property jobs

5. **Bulk Operations**:
   - Use bulk approve for multiple similar changes
   - More efficient than individual approvals

---

## Next Steps

- Read full documentation: `docs/DATA_COLLECTOR_COMPREHENSIVE_PLAN.md`
- Review implementation: `docs/DATA_COLLECTOR_IMPLEMENTATION_SUMMARY.md`
- Understand property fields: `docs/ENHANCED_PROPERTY_SCHEMA.md`

---

## API Reference Quick Links

### Jobs
- `POST /admin/collection/jobs` - Create job
- `GET /admin/collection/jobs` - List jobs
- `POST /admin/collection/jobs/{id}/execute` - Execute job

### Changes
- `GET /admin/collection/changes` - List changes
- `POST /admin/collection/changes/{id}/review` - Review change
- `POST /admin/collection/changes/review-bulk` - Bulk review
- `GET /admin/collection/changes/stats` - Statistics

---

**Ready to start collecting data!** 🚀

For support, see: `docs/DATA_COLLECTOR_IMPLEMENTATION_SUMMARY.md`
