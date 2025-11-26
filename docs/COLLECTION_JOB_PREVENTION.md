# Collection Job Stuck Prevention

This document describes the safeguards implemented to prevent collection jobs from getting stuck in "running" status.

## Problem

Jobs were getting stuck at 10% progress for hours because:

1. **Immediate Status Update**: Jobs are marked as "running" immediately when execution starts
2. **Background Thread Failures**: The actual execution happens in a background thread which can fail silently
3. **No Timeout Mechanism**: Jobs could remain in "running" state indefinitely
4. **Silent Errors**: Background thread crashes weren't properly caught or logged

## Solutions Implemented

### 1. Improved Background Execution Error Handling

**File**: `routes/admin/collection.py` (lines 1020-1066)

**Changes**:
- ✅ Better exception handling around each job execution
- ✅ Automatic job failure marking when exceptions occur
- ✅ Detailed error logging with emoji indicators (🔵 🟢✅ ❌ 🔧 🏁)
- ✅ Thread-level exception catching to prevent silent crashes
- ✅ Proper database rollback on errors

**Benefits**:
- Jobs that fail during execution are immediately marked as "failed"
- Error messages are stored in the database for debugging
- Thread crashes are logged for investigation

### 2. Automatic Stuck Job Monitor

**File**: `src/app.py` (lines 148-190)

**Changes**:
- ✅ Background daemon thread that runs continuously
- ✅ Checks every 5 minutes for stuck jobs
- ✅ Automatically marks jobs as "failed" if running > 30 minutes
- ✅ Logs all cleanup operations

**Configuration**:
```python
CHECK_INTERVAL = 300  # seconds (5 minutes)
TIMEOUT_THRESHOLD = 30  # minutes
```

**Benefits**:
- Automatic cleanup without manual intervention
- Jobs never stay stuck indefinitely
- Runs in daemon thread (doesn't prevent server shutdown)

### 3. Manual Reset Endpoint

**File**: `routes/admin/collection.py` (lines 715-769)

**Endpoint**: `POST /v1/admin/collection/jobs/reset-stuck`

**Parameters**:
- `timeout_minutes` (optional, default: 30) - Consider jobs stuck after this duration

**Usage**:
```bash
# Reset jobs stuck for more than 30 minutes (default)
POST /v1/admin/collection/jobs/reset-stuck

# Reset jobs stuck for more than 10 minutes
POST /v1/admin/collection/jobs/reset-stuck?timeout_minutes=10
```

**Response**:
```json
{
  "success": true,
  "reset_count": 5,
  "job_ids": ["JOB-123...", "JOB-456..."],
  "message": "Reset 5 stuck job(s)"
}
```

**Benefits**:
- Manual intervention when needed
- Customizable timeout threshold
- Immediate cleanup without waiting for monitor

### 4. Enhanced Bulk Delete

**File**: `routes/admin/collection.py` (lines 623-666)

**Changes**:
- ✅ Allows deleting jobs in any status (except "running")
- ✅ Prevents deletion of actively running jobs
- ✅ Cascading delete of associated changes
- ✅ Clear error messages

**Benefits**:
- Easy cleanup of failed/stuck jobs
- Safety check prevents data corruption
- Clean removal of all related data

## Architecture

```
┌─────────────────────────────────────────┐
│     Job Execution Flow (Sequential)     │
└─────────────────────────────────────────┘

1. API Request: POST /jobs/execute-pending
   ↓
2. Check: Any jobs already running?
   ├─→ YES: Return error (only 1 job at a time)
   └─→ NO: Continue
   ↓
3. Get next pending job (priority order)
   ↓
4. Mark job as "running" (immediate)
   ↓
5. Start background thread
   ↓
6. Return response to client
   │
   └─→ Background Thread:
       ├─→ Try: Execute job
       │   ├─→ Success: Job completes normally
       │   └─→ Error: Mark as "failed" + log
       └─→ Catch: Thread crash logged

NOTE: Only ONE job runs at a time to prevent
      resource conflicts and rate limiting issues

┌─────────────────────────────────────────┐
│     Job Monitor (Background)            │
└─────────────────────────────────────────┘

Every 5 minutes:
1. Query: Find jobs running > 30 min
2. If found: Mark as "failed"
3. Log cleanup operation
4. Sleep 5 minutes
5. Repeat
```

## Monitoring

### Log Messages

**Job Execution**:
- `🔵 Executing job {job_id} in background` - Job started
- `✅ Job {job_id} completed successfully` - Job finished
- `❌ Background job {job_id} failed: {error}` - Job execution failed
- `🔧 Marked job {job_id} as failed in database` - Auto-marked as failed
- `🏁 Background thread finished processing X job(s)` - Thread complete

**Stuck Job Monitor**:
- `🔍 Started background job monitor (checks every 5 minutes)` - Monitor started
- `🔧 Found X stuck job(s), marking as failed` - Cleanup in progress
- `✅ Reset X stuck job(s)` - Cleanup complete
- `❌ Job monitor error: {error}` - Monitor error (continues running)
- `❌ Job monitor thread crashed: {error}` - Monitor crash (logged)

### Database Queries

Check stuck jobs manually:
```python
from model.collection import CollectionJob
from datetime import datetime, timedelta

# Find jobs stuck for more than 30 minutes
cutoff = datetime.utcnow() - timedelta(minutes=30)
stuck = db.query(CollectionJob).filter(
    CollectionJob.status == "running",
    CollectionJob.started_at < cutoff
).all()
```

## Configuration

Environment variables (optional):
```bash
# Disable automatic job monitor (not recommended)
ARTITEC_JOB_MONITOR_ENABLED=0

# Customize monitor interval (seconds)
ARTITEC_JOB_MONITOR_INTERVAL=300

# Customize timeout threshold (minutes)
ARTITEC_JOB_TIMEOUT_MINUTES=30
```

## Testing

### Test Stuck Job Detection
```bash
# 1. Create a job that will fail
POST /v1/admin/collection/jobs

# 2. Manually mark it as running in database
UPDATE collection_jobs SET status='running', started_at=NOW() - INTERVAL 1 HOUR WHERE job_id='JOB-XXX';

# 3. Wait 5 minutes or trigger manual cleanup
POST /v1/admin/collection/jobs/reset-stuck?timeout_minutes=30

# 4. Verify job is marked as failed
GET /v1/admin/collection/jobs/JOB-XXX
```

### Test Background Error Handling
```bash
# 1. Create a job with invalid data
POST /v1/admin/collection/jobs
{
  "entity_type": "invalid",
  "job_type": "test"
}

# 2. Execute the job
POST /v1/admin/collection/jobs/execute-pending

# 3. Check logs for error handling
# Should see: ❌ Background job XXX failed: ...
# Should see: 🔧 Marked job XXX as failed in database

# 4. Verify job status
GET /v1/admin/collection/jobs/JOB-XXX
# Should show status: "failed" with error_message
```

## Troubleshooting

### Jobs Still Getting Stuck

1. **Check if monitor is running**:
   - Look for log: `🔍 Started background job monitor`
   - If missing, check server startup logs

2. **Check monitor interval**:
   - Default is 5 minutes
   - Jobs may appear stuck until next check

3. **Manual cleanup**:
   ```bash
   POST /v1/admin/collection/jobs/reset-stuck?timeout_minutes=10
   ```

4. **Check for database connection issues**:
   - Monitor creates new DB sessions
   - Check for connection pool exhaustion

### High Number of Failed Jobs

1. **Check error messages**:
   ```bash
   GET /v1/admin/collection/jobs?status=failed
   ```

2. **Common causes**:
   - API rate limiting (Claude, web scraping)
   - Network timeouts
   - Invalid search queries
   - Missing API keys

3. **Review logs** for patterns:
   ```bash
   grep "Background job.*failed" logs/app.log
   ```

## Sequential Execution Mode

**Location**: `routes/admin/collection.py:974-1104`

**Why Sequential?**
- Prevents API rate limiting (Claude, web scraping APIs)
- Reduces resource contention (database, memory)
- Easier to debug and monitor
- Prevents multiple jobs from interfering with each other

**How It Works**:
1. Before starting a job, check if any job is running
2. If a job is running, reject the request with informative message
3. If no job running, start the next highest-priority job
4. The frontend must call execute-pending again after each job completes

**API Response When Job Already Running**:
```json
{
  "total_pending": 5,
  "started": 0,
  "job_ids": [],
  "message": "Cannot start new job: 1 job(s) already running. Only one job can run at a time."
}
```

**API Response When Job Started**:
```json
{
  "total_pending": 4,
  "started": 1,
  "job_ids": ["JOB-123..."],
  "message": "Started job JOB-123... in background (sequential mode: 1 job at a time). 4 job(s) remaining in queue."
}
```

## Best Practices

1. **Monitor regularly**: Check job statuses in dashboard
2. **Set realistic timeouts**: 30 minutes is usually sufficient
3. **Review failed jobs**: Check error messages for patterns
4. **Use bulk operations**: Clean up failed jobs periodically
5. **Check logs**: Monitor background thread health
6. **Poll for completion**: After starting a job, poll `/jobs/{job_id}` to know when to start the next one
7. **Respect sequential mode**: Don't try to start multiple jobs simultaneously

## Future Improvements

Potential enhancements:

1. **Configurable timeouts** per job type
2. **Retry mechanism** for transient failures
3. **Job priority queue** with better resource management
4. **Metrics/monitoring** dashboard for job health
5. **Alert notifications** for stuck jobs
6. **Job cancellation** support (graceful shutdown)
