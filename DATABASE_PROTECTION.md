# Database Protection Guide

This document explains the database protection mechanisms implemented to prevent accidental data loss during migrations.

## Protection Mechanisms

### 1. Protected Tables List

The following tables are protected from accidental deletion:

**Core User & Authentication:**
- `users`
- `password_reset_tokens`
- `enterprise_invitations`
- `onboarding_forms`

**Builder System:**
- `builders`
- `builder_team_members`
- `builder_documents`

**Community System:**
- `communities`
- `community_documents`

**Property System:**
- `properties`
- `property_media`
- `property_features`
- `property_documents`
- `lots`
- `lot_status_history`
- `phase_maps`
- `phase_map_users`

**Social Features:**
- `follows`
- `likes`
- `comments`
- `saved_properties`

**Messaging:**
- `messages`
- `notifications`

**Collections System:**
- `collection_jobs`
- `collection_changes`
- `collection_job_logs`
- `entity_matches`
- `collection_sources`

### 2. Autogenerate Protection (alembic/env.py)

The `process_revision_directives` function automatically blocks dangerous autogenerate migrations that try to:

- Drop protected tables
- Drop indexes on protected tables
- Drop columns on protected tables

When a dangerous migration is detected, you'll see:

```
================================================================================
⚠️  DANGEROUS MIGRATION DETECTED - BLOCKING AUTOGENERATE
================================================================================

The following dangerous operations were detected:
  ❌ DROP TABLE communities
  ❌ DROP TABLE builders

⛔ This migration has been BLOCKED for safety.

If you need to make these changes:
  1. Create a manual migration: alembic revision -m 'description'
  2. Manually edit the migration file
  3. Review carefully before applying
  4. Take a database backup first
================================================================================
```

### 3. Database Backup Script

Location: `scripts/backup_db.sh`

This script creates timestamped backups of your database before migrations.

**Features:**
- Automatic timestamped backups
- Compression (gzip)
- Keeps last 10 backups (auto-cleanup)
- Provides restore instructions

**Usage:**

```bash
# Before running migrations, create a backup:
./scripts/backup_db.sh

# Then run your migration:
alembic upgrade head
```

**To restore a backup:**

```bash
# Decompress the backup
gunzip backups/artitec_backup_YYYYMMDD_HHMMSS.sql.gz

# Restore to database
mysql -h HOST -P PORT -u USER -p DATABASE < backups/artitec_backup_YYYYMMDD_HHMMSS.sql
```

## Best Practices

### 1. Always Use Manual Migrations for Schema Changes

Instead of using `alembic revision --autogenerate`, use:

```bash
# Create empty migration
alembic revision -m "Add field to communities table"

# Then manually edit the migration file
```

### 2. Review All Migrations Before Applying

```bash
# Check current database version
alembic current

# Show pending migrations
alembic history

# Review the migration file before applying
cat alembic/versions/REVISION_ID.py

# Apply migration
alembic upgrade head
```

### 3. Backup Before Major Changes

```bash
# Create backup
./scripts/backup_db.sh

# Apply migration
alembic upgrade head

# Verify success
alembic current
```

### 4. Test Migrations in Development First

Never run untested migrations directly on production:

1. Test migration on local database
2. Test migration on staging database
3. Create production backup
4. Apply to production during maintenance window

## Updating Protected Tables List

If you add new important tables to the system, add them to the `PROTECTED_TABLES` set in `alembic/env.py`:

```python
PROTECTED_TABLES = {
    # ... existing tables ...
    'your_new_table',
}
```

## Emergency Recovery

If you accidentally run a dangerous migration:

1. **Stop immediately** - Don't run any more migrations
2. **Restore from backup**:
   ```bash
   gunzip backups/artitec_backup_LATEST.sql.gz
   mysql -h HOST -P PORT -u USER -p DATABASE < backups/artitec_backup_LATEST.sql
   ```
3. **Downgrade the migration**:
   ```bash
   alembic downgrade -1
   ```
4. **Review and fix** the migration file

## Testing Protection

To test that the protection works:

```bash
# Try to autogenerate a migration
# The protection should block any dangerous operations
alembic revision --autogenerate -m "test"

# Check if dangerous operations were blocked
# You should see the protection warning if any were detected
```

## Questions?

If you're unsure about a migration:
1. Create a backup first
2. Test on development database
3. Review the migration file carefully
4. Ask for a code review
5. Document the changes

Remember: **It's better to be safe than sorry when dealing with production data!**
