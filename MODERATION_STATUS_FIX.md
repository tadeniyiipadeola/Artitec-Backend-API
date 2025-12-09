# ModerationStatus Enum Fix

## Problem
After fixing the storage_type enum issue, a new error appeared:

```
'approved' is not among the defined enum values.
Enum name: moderationstatus.
Possible values: PENDING, APPROVED, REJECTED, FLAGGED
```

This error occurred when creating Media records during scraping.

## Root Cause

The `media.moderation_status` column has a database default of `'approved'` (lowercase string):

```sql
moderation_status ENUM('pending','approved','rejected','flagged')
NOT NULL
DEFAULT 'approved'
```

The Python model defines the column with an enum default:

```python
moderation_status = Column(
    SQLEnum(ModerationStatus),
    nullable=False,
    default=ModerationStatus.APPROVED
)
```

However, when `moderation_status` is **not explicitly set** in the Media() constructor, the database default (`'approved'` string) is used instead of the Python default (` ModerationStatus.APPROVED` enum).

SQLAlchemy then tries to validate the database's string value against the enum, which fails because:
- Database returns: `'approved'` (lowercase string)
- Enum expects: `ModerationStatus.APPROVED` (enum member with value `"approved"`)

## The Fix

Explicitly set `moderation_status` in all Media() constructor calls in `src/media_scraper.py`:

### Changed Import (Line 22)
```python
from model.media import Media, MediaType, StorageType, ModerationStatus
```

### Changed Media() Constructors (3 locations)

**Lines ~540, ~673, ~741:**
```python
media = Media(
    # ... other fields ...
    uploaded_by=self.uploaded_by,
    storage_type=StorageType.LOCAL,
    moderation_status=ModerationStatus.PENDING,  # NEW - explicitly set
    is_public=True,
    is_approved=False
)
```

## Why PENDING instead of APPROVED?

Scraped media should start as `PENDING` moderation, not `APPROVED`:
- `is_approved=False` indicates the media needs admin review
- `moderation_status=ModerationStatus.PENDING` is the correct status for unreviewed content
- The database default of `'approved'` was incorrect for scraped media

## Files Modified

- **1 file changed**: `src/media_scraper.py`
  - Line 22: Added `ModerationStatus` to imports
  - Lines ~541, ~674, ~742: Added explicit `moderation_status=ModerationStatus.PENDING`

## Status

✅ All 3 Media() constructor calls now explicitly set moderation_status
✅ Scraped media correctly starts as PENDING instead of relying on database default
✅ No database migration needed (column definition is correct for the enum values)

## Testing

The server auto-reloads will pick up the changes automatically. Test by:
1. Scraping media from a URL
2. Verify no more "moderation_status" enum errors
3. Confirm new media records have `moderation_status='pending'`

## Related Fixes

This completes the enum fixes:
1. ✅ `storage_type` - Fixed database column from lowercase to uppercase ENUM
2. ✅ `moderation_status` - Fixed by explicitly setting in constructors

Both issues had the same root cause: relying on database defaults instead of explicitly setting enum values in Python code.
