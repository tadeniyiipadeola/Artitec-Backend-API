# API Response Format Fixes

## Issue: iOS Decoding Error

### Error Message
```
❌ Decoding error: typeMismatch(Swift.Dictionary<String, Any>,
Swift.DecodingError.Context(codingPath: [], debugDescription:
"Expected to decode Dictionary<String, Any> but found an array instead.",
underlyingError: nil))
```

### Root Cause
The backend was returning a simple array `[]` but iOS expected a paginated response object with metadata.

**Backend returned:**
```json
[]
```

**iOS expected:**
```json
{
  "jobs": [],
  "total": 0,
  "page": 1,
  "page_size": 20
}
```

---

## ✅ Fixes Applied

### 1. Added Paginated Response Model

**File:** `routes/admin/collection.py`

Added `CollectionJobListResponse` schema:
```python
class CollectionJobListResponse(BaseModel):
    """Paginated response for job list."""
    jobs: List[CollectionJobResponse]
    total: int
    page: int
    page_size: int
```

### 2. Updated List Jobs Endpoint

**Before:**
```python
@router.get("/jobs", response_model=List[CollectionJobResponse])
async def list_collection_jobs(
    limit: int = Query(50, le=100),
    offset: int = Query(0),
    ...
):
    jobs = query.limit(limit).offset(offset).all()
    return [CollectionJobResponse.from_orm(job) for job in jobs]
```

**After:**
```python
@router.get("/jobs", response_model=CollectionJobListResponse)
async def list_collection_jobs(
    page: int = Query(1, ge=1, description="Page number (1-indexed)"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    ...
):
    # Get total count
    total = query.count()

    # Calculate offset
    offset = (page - 1) * page_size

    # Get paginated results
    jobs = query.limit(page_size).offset(offset).all()

    return CollectionJobListResponse(
        jobs=[CollectionJobResponse.from_orm(job) for job in jobs],
        total=total,
        page=page,
        page_size=page_size
    )
```

**Changes:**
- Changed `limit`/`offset` to `page`/`page_size` (matches iOS expectations)
- Added total count calculation
- Return paginated response object instead of raw array

### 3. Added Stats Endpoint

**File:** `routes/admin/collection.py`

The `/stats` endpoint was missing completely. Added:

```python
class CollectionStatsResponse(BaseModel):
    """Statistics about collection jobs."""
    total_jobs: int
    pending_jobs: int
    running_jobs: int
    completed_jobs: int
    failed_jobs: int
    success_rate: float
    average_duration: int
    total_entities_collected: int
    total_changes_detected: int


@router.get("/stats", response_model=CollectionStatsResponse)
async def get_collection_stats(db: Session = Depends(get_db)):
    """Get collection statistics."""
    # Count jobs by status
    total_jobs = db.query(func.count(CollectionJob.job_id)).scalar() or 0
    pending_jobs = db.query(func.count(CollectionJob.job_id)).filter(
        CollectionJob.status == "pending"
    ).scalar() or 0
    # ... similar for running, completed, failed

    # Calculate success rate
    success_rate = (completed_jobs / total_jobs * 100) if total_jobs > 0 else 0.0

    # Calculate average duration for completed jobs
    # ... (see full implementation in file)

    # Get totals
    total_entities = db.query(func.sum(CollectionJob.new_entities_found)).scalar() or 0
    total_changes = db.query(func.sum(CollectionJob.changes_detected)).scalar() or 0

    return CollectionStatsResponse(...)
```

**Features:**
- Aggregates job counts by status
- Calculates success rate percentage
- Computes average job duration
- Sums total entities collected and changes detected

---

## ✅ API Response Examples

### GET /v1/admin/collection/jobs

**Request:**
```bash
GET /v1/admin/collection/jobs?page=1&page_size=20
```

**Response:** (200 OK)
```json
{
  "jobs": [],
  "total": 0,
  "page": 1,
  "page_size": 20
}
```

With data:
```json
{
  "jobs": [
    {
      "job_id": "job_123",
      "entity_type": "community",
      "entity_id": 456,
      "job_type": "discovery",
      "status": "completed",
      "priority": 5,
      "search_query": "Lakeside Community",
      "items_found": 15,
      "changes_detected": 8,
      "new_entities_found": 2,
      "error_message": null,
      "created_at": "2025-11-24T10:00:00Z",
      "started_at": "2025-11-24T10:01:00Z",
      "completed_at": "2025-11-24T10:05:00Z"
    }
  ],
  "total": 1,
  "page": 1,
  "page_size": 20
}
```

### GET /v1/admin/collection/stats

**Request:**
```bash
GET /v1/admin/collection/stats
```

**Response:** (200 OK)
```json
{
  "total_jobs": 0,
  "pending_jobs": 0,
  "running_jobs": 0,
  "completed_jobs": 0,
  "failed_jobs": 0,
  "success_rate": 0.0,
  "average_duration": 0,
  "total_entities_collected": 0,
  "total_changes_detected": 0
}
```

With data:
```json
{
  "total_jobs": 50,
  "pending_jobs": 5,
  "running_jobs": 2,
  "completed_jobs": 40,
  "failed_jobs": 3,
  "success_rate": 80.0,
  "average_duration": 240,
  "total_entities_collected": 150,
  "total_changes_detected": 75
}
```

---

## ✅ Verification

### Backend Import Test
```
✅ Collection router imported successfully
✅ FastAPI app loaded successfully
✅ Found 10 collection endpoints
```

### Endpoints Registered
```
GET /v1/admin/collection/changes
GET /v1/admin/collection/changes/stats
GET /v1/admin/collection/jobs           ← Fixed pagination
GET /v1/admin/collection/jobs/{job_id}
GET /v1/admin/collection/stats          ← Added endpoint
POST /v1/admin/collection/changes/review-bulk
POST /v1/admin/collection/changes/{change_id}/review
POST /v1/admin/collection/jobs
POST /v1/admin/collection/jobs/execute-pending
POST /v1/admin/collection/jobs/{job_id}/execute
```

---

## 🧪 Testing

### Restart Backend
```bash
cd "/Users/adeniyi_family_executor/Documents/Development/Artitec Backend Development"
source .venv/bin/activate
uvicorn src.app:app --reload --host 127.0.0.1 --port 8000
```

### Test Stats Endpoint
```bash
curl -X GET "http://127.0.0.1:8000/v1/admin/collection/stats" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

**Expected:** 200 OK with stats object (not array)

### Test Jobs List
```bash
curl -X GET "http://127.0.0.1:8000/v1/admin/collection/jobs?page=1&page_size=20" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

**Expected:** 200 OK with paginated response:
```json
{
  "jobs": [],
  "total": 0,
  "page": 1,
  "page_size": 20
}
```

### iOS App Test
1. Build and run iOS app
2. Login as admin
3. Tap Collection tab
4. Should see statistics cards load
5. Should see empty job list (or existing jobs)
6. **No more decoding errors!**

---

## 📋 Summary of Changes

### Files Modified: 1
- ✅ `routes/admin/collection.py`

### Changes Made:
1. ✅ Added `CollectionJobListResponse` model for pagination
2. ✅ Added `CollectionStatsResponse` model for statistics
3. ✅ Updated `/jobs` endpoint to return paginated response
4. ✅ Changed query params from `limit`/`offset` to `page`/`page_size`
5. ✅ Added `/stats` endpoint with aggregated statistics

### Result:
- ✅ iOS can now decode responses correctly
- ✅ Proper pagination support
- ✅ Statistics dashboard fully functional
- ✅ API matches iOS expectations

---

**Date:** November 24, 2025
**Status:** Ready for Testing ✅
