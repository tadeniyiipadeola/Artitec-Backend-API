# Auto-Cleanup System for Scraped Media

## Overview

Scraped media is automatically deleted after 7 days unless approved/selected by the user. This prevents storage from filling up with unused images.

## How It Works

### 1. **Media Lifecycle**

```
Scrape Website
     ↓
Media Saved (is_approved = False)
     ↓
User Reviews in MediaScraperView
     ↓
┌─────────────┬─────────────┐
│   Selected  │ Not Selected│
│   (Approve) │             │
└──────┬──────┴──────┬──────┘
       ↓             ↓
is_approved = True   Stays False
Kept Permanently     ↓
                Auto-Deleted
                After 7 Days
```

### 2. **Database Schema**

```sql
ALTER TABLE media ADD COLUMN is_approved BOOLEAN DEFAULT TRUE;
CREATE INDEX idx_media_is_approved_created_at ON media(is_approved, created_at);
```

- **is_approved = True**: Permanent media (manually uploaded or approved)
- **is_approved = False**: Temporary scraped media (auto-deleted after 7 days)

### 3. **Approval Methods**

#### Option A: Automatic (Not Yet Implemented in iOS)
When user adds scraped media to their gallery/profile, it's automatically approved.

#### Option B: Manual Approval API
```bash
POST /v1/media/batch/approve
Body: [1, 2, 3, 4, 5]  # Media IDs to keep

Response:
{
  "approved": [1, 2, 3],
  "approved_count": 3,
  "failed": [],
  "message": "Successfully approved 3 items"
}
```

## Running Cleanup

### Manual Cleanup

**Dry Run** (see what would be deleted):
```bash
cd /path/to/project
source .venv/bin/activate
python cleanup_old_media.py --dry-run
```

**Actual Cleanup**:
```bash
python cleanup_old_media.py
```

### Automated Cleanup (Recommended)

Set up a daily cron job to run cleanup automatically:

```bash
# Edit crontab
crontab -e

# Add this line (runs daily at 2 AM)
0 2 * * * cd /Users/adeniyi_family_executor/Documents/Development/Artitec\ Backend\ Development && .venv/bin/python cleanup_old_media.py >> /tmp/media_cleanup.log 2>&1
```

## Monitoring

### Check Unapproved Media Count

```sql
-- Count unapproved media
SELECT COUNT(*) FROM media WHERE is_approved = FALSE;

-- See old unapproved media (will be deleted soon)
SELECT
    public_id,
    original_filename,
    entity_type,
    entity_id,
    created_at,
    DATEDIFF(NOW(), created_at) as age_days
FROM media
WHERE is_approved = FALSE
  AND created_at < DATE_SUB(NOW(), INTERVAL 7 DAY);
```

### Cleanup Logs

Check cleanup output:
```bash
tail -f /tmp/media_cleanup.log
```

## Testing

### 1. Scrape Some Media

Use MediaScraperView in iOS app or API:
```bash
POST /v1/media/scraper/scrape-page
{
  "url": "https://example.com",
  "entity_type": "community",
  "entity_id": 3,
  "entity_field": "gallery",
  "max_images": 10
}
```

### 2. Check Database

```sql
-- Should show is_approved = FALSE for new scraped media
SELECT public_id, original_filename, is_approved, created_at
FROM media
ORDER BY created_at DESC
LIMIT 10;
```

### 3. Test Approval

```bash
# Approve some media
curl -X POST http://localhost:8000/v1/media/batch/approve \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '[1, 2, 3]'
```

### 4. Test Cleanup (Dry Run)

```bash
python cleanup_old_media.py --dry-run
```

## Storage Savings

The cleanup script reports:
- Number of items deleted
- Total storage space freed (in MB)

Example output:
```
✅ Cleanup complete!
   Deleted: 47 items
   Failed: 0 items
   Space freed: 23.56 MB
```

## Benefits

✅ **Automatic Storage Management** - No manual intervention needed
✅ **7-Day Grace Period** - Users have time to review scraped media
✅ **Safe** - Only deletes unapproved media (never touches manually uploaded files)
✅ **Efficient** - Indexed queries, runs quickly even with millions of records
✅ **Reversible** - Dry-run mode lets you preview before deleting

## Safety Features

1. **Default to Keep** - Existing media set to `is_approved = TRUE` during migration
2. **Manual Uploads Always Kept** - Only scraped media starts as unapproved
3. **Permission Checks** - Users can only approve their own media
4. **Dry Run Mode** - Test cleanup without actually deleting
5. **Detailed Logging** - Full audit trail of what was deleted

## Future Enhancements

- [ ] Add "Approve Selected" button in MediaScraperView (iOS)
- [ ] Auto-approve when media is used in gallery/profile
- [ ] Email notifications before deletion
- [ ] Recycle bin (soft delete with 30-day recovery period)
- [ ] Admin dashboard showing cleanup statistics

## Troubleshooting

### Cleanup script fails

```bash
# Check database connection
python -c "from config.db import SessionLocal; db = SessionLocal(); print('✅ Database connected')"

# Check storage connection
python -c "from src.storage import get_storage_backend; s = get_storage_backend(); print('✅ Storage connected')"
```

### Media not being deleted

```sql
-- Check if media is old enough (> 7 days)
SELECT
    public_id,
    is_approved,
    created_at,
    DATEDIFF(NOW(), created_at) as age_days
FROM media
WHERE is_approved = FALSE;
```

### Want to change retention period

Edit `cleanup_old_media.py`:
```python
# Change from 7 days to 14 days
cutoff_date = datetime.now() - timedelta(days=14)
```

## Summary

- ✅ Scraped media saved with `is_approved = FALSE`
- ✅ User can approve media via API endpoint
- ✅ Cleanup script deletes unapproved media > 7 days old
- ✅ Run cleanup manually or via cron job
- ✅ All existing media protected (set to approved)
- ✅ Storage automatically managed
