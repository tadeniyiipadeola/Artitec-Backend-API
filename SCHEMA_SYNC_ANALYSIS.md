# SQLAlchemy Schema Sync Analysis

This document analyzes the differences between your database schema and SQLAlchemy models, and provides recommendations for syncing them.

## Problem Summary

Alembic's autogenerate detects differences because:
1. **Missing SQLAlchemy Models**: Tables exist in the database but have no corresponding SQLAlchemy model
2. **Type Mismatches**: Database columns have different types than SQLAlchemy models define
3. **Schema Evolution**: Database has evolved but models haven't been updated

## Tables in Database (67 tables)

### Tables WITH SQLAlchemy Models (Currently Loaded)
- ✅ `users` (model/user.py)
- ✅ `buyer_profiles` (model/profiles/buyer.py)
- ✅ `builder_profiles` (model/profiles/builder.py)
- ✅ `communities` (model/profiles/community.py)
- ✅ `community_admin_profiles` (model/profiles/community_admin_profile.py)
- ✅ `sales_reps` (model/profiles/sales_rep.py)
- ✅ `properties` (model/property/property.py)
- ✅ `followers` (model/followers.py)
- ✅ `media` (model/media.py)
- ✅ `collection_jobs`, `collection_changes`, `collection_job_logs`, `collection_sources`, `entity_matches` (model/collection.py)
- ✅ `status_history` (src/collection/status_management/history.py)

### Tables WITHOUT SQLAlchemy Models (Missing)

**Authentication & User Management:**
- ❌ `password_reset_tokens` - Has partial model in `model/password_reset.py` (not loaded!)
- ❌ `onboarding_forms`
- ❌ `email_verifications`
- ❌ `sessions`
- ❌ `user_credentials`
- ❌ `roles`

**Builder System:**
- ❌ `builders` - Core builder table (not same as builder_profiles)
- ❌ `builder_team_members`
- ❌ `builder_documents`
- ❌ `builder_awards`
- ❌ `builder_communities` - Junction table
- ❌ `builder_credentials`
- ❌ `builder_home_plans`
- ❌ `builder_portfolio`

**Community System:**
- ❌ `community_documents`
- ❌ `community_admin_links`
- ❌ `community_admins`
- ❌ `community_amenities`
- ❌ `community_awards`
- ❌ `community_builders`
- ❌ `community_events`
- ❌ `community_phases`
- ❌ `community_topics`

**Property System:**
- ❌ `property_documents`
- ❌ `property_features`
- ❌ `property_media`
- ❌ `lots`
- ❌ `lot_status_history`
- ❌ `phase_maps`
- ❌ `phase_map_users`

**Buyer System:**
- ❌ `buyer_documents`
- ❌ `buyer_preferences`
- ❌ `buyer_tours`
- ❌ `buying_timelines`
- ❌ `favorite_properties`
- ❌ `saved_properties`
- ❌ `financing_statuses`
- ❌ `tour_statuses`
- ❌ `preferred_channels`
- ❌ `loan_programs`

**Social Features:**
- ❌ `follows`
- ❌ `likes`
- ❌ `comments`

**Messaging:**
- ❌ `messages`
- ❌ `notifications`

**Enterprise:**
- ❌ `enterprise_invitations` - Has model in `model/enterprise.py` (not loaded!)

## Recommended Solutions

### Option 1: Configure Alembic to Ignore Tables (RECOMMENDED)

This is the **simplest and safest** approach for tables you don't actively modify through migrations.

**Pros:**
- No code changes needed
- Prevents accidental deletions
- Quick to implement
- Tables continue working normally

**Cons:**
- Can't use Alembic migrations for these tables
- Need to manage schema changes manually

**Implementation:** Add `include_object` filter to `alembic/env.py` (already partially implemented with protection system)

### Option 2: Create Missing SQLAlchemy Models

Create models for all missing tables.

**Pros:**
- Full Alembic migration support
- Better code documentation
- Type hints and IDE autocomplete
- Safer database operations

**Cons:**
- Time-consuming (40+ models to create)
- Need to reverse-engineer exact schema
- Risk of type mismatches
- Maintenance burden

**Implementation:** Create model files for each missing table

### Option 3: Hybrid Approach (RECOMMENDED FOR PRODUCTION)

- **Keep models** for tables you actively use in code
- **Ignore tables** that exist but aren't used in application logic (legacy, admin-only, etc.)

## Type Mismatch Issues

Even for tables WITH models, there are type differences:

### Common Type Mismatches:
1. **INTEGER(11) → BIGINT(unsigned=True)**
   - Database: `INTEGER(display_width=11)`
   - Model: `BIGINT(unsigned=True)`
   - **Fix**: Update models to match database OR create migration to update database

2. **DATETIME() → TIMESTAMP()**
   - Database: `DATETIME()`
   - Model: `TIMESTAMP()`
   - **Fix**: Standardize on one type

3. **VARCHAR(X) → String(Y)** where X ≠ Y
   - Database: `VARCHAR(length=200)`
   - Model: `String(length=255)`
   - **Fix**: Update model to match database length

4. **Missing Server Defaults**
   - Database has `DEFAULT CURRENT_TIMESTAMP`
   - Model missing `server_default=func.current_timestamp()`

### Files Needing Type Fixes:
- `model/profiles/builder.py`
- `model/profiles/buyer.py`
- `model/profiles/community.py`
- `model/profiles/community_admin_profile.py`

## Immediate Action Plan

### Step 1: Enhance Alembic Protection (DONE)

Already implemented in `alembic/env.py`:
- ✅ Protected tables list
- ✅ `process_revision_directives` to block dangerous operations
- ✅ Database backup script

### Step 2: Configure Table Exclusion

Update `alembic/env.py` to explicitly exclude tables without models from autogenerate:

```python
# Tables to exclude from autogenerate (no models exist)
EXCLUDED_TABLES = {
    # Auth & User
    'password_reset_tokens', 'onboarding_forms', 'email_verifications',
    'sessions', 'user_credentials', 'roles',

    # Builder
    'builders', 'builder_team_members', 'builder_documents',
    'builder_awards', 'builder_communities', 'builder_credentials',
    'builder_home_plans', 'builder_portfolio',

    # Community
    'community_documents', 'community_admin_links', 'community_admins',
    'community_amenities', 'community_awards', 'community_builders',
    'community_events', 'community_phases', 'community_topics',

    # Property
    'property_documents', 'property_features', 'property_media',
    'lots', 'lot_status_history', 'phase_maps', 'phase_map_users',

    # Buyer
    'buyer_documents', 'buyer_preferences', 'buyer_tours',
    'buying_timelines', 'favorite_properties', 'saved_properties',
    'financing_statuses', 'tour_statuses', 'preferred_channels',
    'loan_programs',

    # Social
    'follows', 'likes', 'comments',

    # Messaging
    'messages', 'notifications',

    # Enterprise
    'enterprise_invitations',
}

def include_object(object, name, type_, reflected, compare_to):
    # Skip excluded tables
    if type_ == "table" and name in EXCLUDED_TABLES:
        return False
    return True
```

### Step 3: Load Existing But Unloaded Models

Add to `model/__init__.py`:
```python
import model.password_reset  # Has PasswordResetToken model
import model.enterprise       # Has EnterpriseInvitation model
import model.social.models    # May have social models
```

### Step 4: Fix Type Mismatches (Optional but Recommended)

Create migration to align database types with models:
- Convert `INTEGER` → `BIGINT` where needed
- Standardize `DATETIME` vs `TIMESTAMP`
- Add missing server defaults

## Testing the Fix

After implementing the solution:

```bash
# Should now generate clean migration (or no migration)
alembic revision --autogenerate -m "test_sync"

# Check the generated file - should be empty or minimal
cat alembic/versions/XXXX_test_sync.py

# Clean up test
rm alembic/versions/XXXX_test_sync.py
```

## Long-term Recommendations

1. **Document Your Schema**: Maintain this analysis document
2. **Use Protection**: Keep the protection system in `alembic/env.py`
3. **Manual Migrations**: For critical changes, always use manual migrations
4. **Backup Before Migrations**: Use `./scripts/backup_db.sh`
5. **Review All Migrations**: Never blindly run `alembic upgrade head`

## Next Steps

Which approach do you want to take?

**A. Quick Fix** (Recommended for now):
- Exclude unmodeled tables from autogenerate
- Load existing models that aren't loaded
- Continue working with current setup

**B. Comprehensive Fix**:
- Create all missing models
- Fix all type mismatches
- Full schema alignment

**C. Hybrid**:
- Exclude legacy/unused tables
- Create models for tables you actively use
- Fix type mismatches in active models
