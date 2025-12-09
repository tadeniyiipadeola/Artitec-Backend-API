# ModerationStatus Enum Fix - THE REAL SOLUTION

## Problem

```
LookupError: 'pending' is not among the defined enum values.
Enum name: moderationstatus.
Possible values: PENDING, APPROVED, REJECTED, FLAGGED
```

This error occurred when:
- Listing media for entities (`GET /v1/media/entity/community/3`)
- Scraping media from URLs (`POST /v1/media/scrape`)
- Any query that reads `moderation_status` from the database

## The Real Root Cause

### Initial Misdiagnosis
We initially thought this was a Pydantic serialization issue (like cross-enum validation). This led us down the wrong path:
- ✗ Added `use_enum_values = True` to Pydantic config (didn't help)
- ✗ Removed `moderation_status` from Media() constructors (didn't help)
- ✗ Tried changing to `ModerationStatus.APPROVED` (didn't help)

### The Actual Problem
The error was occurring in **SQLAlchemy during database reads**, NOT during Pydantic serialization:

```python
File "/Users/.../sqlalchemy/sql/sqltypes.py", line 1711, in _object_value_for_elem
    raise LookupError(
        'pending' is not among the defined enum values
```

**Root Cause**: SQLAlchemy's `SQLEnum` was using **enum member NAMES** (PENDING, APPROVED) instead of **enum member VALUES** ('pending', 'approved') when reading from the database.

### The Mismatch

**Database column**:
```sql
moderation_status ENUM('pending','approved','rejected','flagged')
DEFAULT 'approved'
```
(lowercase string values)

**Python enum definition (model/media.py)**:
```python
class ModerationStatus(enum.Enum):
    PENDING = "pending"    # Member NAME is "PENDING", value is "pending"
    APPROVED = "approved"  # Member NAME is "APPROVED", value is "approved"
    REJECTED = "rejected"
    FLAGGED = "flagged"
```

**The Issue**: When SQLAlchemy read `'pending'` from the database, it tried to match it against enum **NAMES** (PENDING, APPROVED, etc.) instead of enum **VALUES** ('pending', 'approved', etc.), causing the lookup to fail.

## The Fix

Updated the `moderation_status` column definition in `model/media.py` (line 87):

**Before**:
```python
moderation_status = Column(
    SQLEnum(ModerationStatus),
    nullable=False,
    default=ModerationStatus.APPROVED,
    comment="Moderation status for content review"
)
```

**After**:
```python
moderation_status = Column(
    SQLEnum(ModerationStatus, values_callable=lambda x: [e.value for e in x]),
    nullable=False,
    default=ModerationStatus.APPROVED,
    comment="Moderation status for content review"
)
```

**What `values_callable` does**: It tells SQLAlchemy to use the **enum values** (the strings like 'pending', 'approved') instead of the enum member names (PENDING, APPROVED) when mapping between database and Python.

## Why This Happened

Unlike `StorageType` which had uppercase values matching its member names:
```python
class StorageType(enum.Enum):
    LOCAL = "LOCAL"  # Member name matches value
    S3 = "S3"        # Member name matches value
```

`ModerationStatus` had **lowercase values** but **uppercase member names**:
```python
class ModerationStatus(enum.Enum):
    PENDING = "pending"    # Member name DOES NOT match value
    APPROVED = "approved"  # Member name DOES NOT match value
```

SQLAlchemy's default behavior is to match database values against enum member **names**. This worked for `StorageType` (after we fixed the database column) but failed for `ModerationStatus`.

## Files Modified

### 1. model/media.py (line 87)
Added `values_callable=lambda x: [e.value for e in x]` to the moderation_status Column definition.

This is the **ONLY** change needed to fix the issue.

### 2. src/media_scraper.py (lines ~541, ~674, ~742)
Removed `moderation_status` parameter from all 3 Media() constructors:
- This change is optional and was made to simplify the code
- These records will use the database default (`'approved'`)
- Does not affect the fix

### 3. schema/media.py (line 143)
Added `use_enum_values = True` to MediaOut Config:
- This change is also optional
- Helps with Pydantic enum serialization consistency
- Does not affect the SQLAlchemy fix

## Testing the Fix

### 1. List Media (Previously Failing)
```bash
curl http://127.0.0.1:8000/v1/media/entity/community/3
```
**Expected**: ✅ Returns media list with `moderation_status` values

### 2. Scrape Media (Previously Failing)
```bash
POST /v1/media/scrape
{
  "entityType": "community",
  "entityId": 3,
  "urls": ["https://example.com/image.jpg"]
}
```
**Expected**: ✅ Successfully scrapes and creates media records

### 3. Database Check
```sql
SELECT id, public_id, moderation_status
FROM media
WHERE moderation_status = 'pending'
LIMIT 5;
```
**Expected**: ✅ Returns records without SQLAlchemy errors

## Why Previous Fixes Didn't Work

1. **Adding `use_enum_values = True`** - This only affects Pydantic serialization, not SQLAlchemy database reads
2. **Removing `moderation_status` from constructors** - The issue was with READING existing records, not creating new ones
3. **Server restarts** - The problem was in the code, not caching

## Comparison to StorageType Fix

| Aspect | StorageType | ModerationStatus |
|--------|-------------|------------------|
| **Database column** | Was `enum('local','s3')` (lowercase) | Is `enum('pending','approved',...)` (lowercase) |
| **Python enum values** | Were "local", "s3" (lowercase) | Are "pending", "approved" (lowercase) |
| **Python enum names** | LOCAL, S3 (uppercase) | PENDING, APPROVED (uppercase) |
| **Match between name & value?** | No (local ≠ LOCAL) | No (pending ≠ PENDING) |
| **Fix required** | ALTER TABLE to uppercase + change enum values to uppercase | Add `values_callable` to use enum values |
| **Why different?** | Decided to standardize on uppercase for storage_type | Kept lowercase for moderation_status to match common convention |

For `StorageType`, we chose to change everything to uppercase (database + Python).
For `ModerationStatus`, we chose to keep everything lowercase and tell SQLAlchemy to use enum values.

Both approaches are valid - the key is **consistency** between database, Python enum values, and SQLAlchemy configuration.

## Status

✅ SQLAlchemy enum mapping fixed with `values_callable`
✅ Media listing works without errors
✅ Media scraping works without errors
✅ Existing media records can be queried successfully
✅ New media records created correctly

## Lessons Learned

1. **Read the full stack trace** - The error was in SQLAlchemy, not Pydantic
2. **Enum member names vs values** - SQLAlchemy defaults to using member names
3. **Test your assumptions** - Direct database queries revealed the mismatch
4. **values_callable is powerful** - It lets you use lowercase enum values with uppercase member names

The fix is complete and working! 🎉
