# alembic/env.py
from logging.config import fileConfig
from alembic import context
from sqlalchemy import engine_from_config, pool

# --- Load .env so we can read DB_URL
import os, sys
from pathlib import Path
from dotenv import load_dotenv

# Ensure project root is on sys.path (so "model" imports work when running alembic from repo root)
PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

# Load .env at project root
load_dotenv(PROJECT_ROOT / ".env")

# Import your SQLAlchemy Base metadata
from model.base import Base  # <- make sure this is correct for your project

# Load all models so they're registered with Base.metadata
from model import load_all_models
load_all_models()

config = context.config

# Prefer DB_URL from env over alembic.ini
db_url = os.getenv("DB_URL")
if db_url:
    config.set_main_option("sqlalchemy.url", db_url)

# Logging config
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata

# ===================================================================
# PROTECTION STRATEGY 4: Safety Checks with process_revision_directives
# ===================================================================

# List of protected tables that should NEVER be dropped
PROTECTED_TABLES = {
    # Core User & Authentication
    'users', 'password_reset_tokens', 'enterprise_invitations', 'onboarding_forms',

    # Builder System
    'builders', 'builder_team_members', 'builder_documents',

    # Community System
    'communities', 'community_documents',

    # Property System
    'properties', 'property_media', 'property_features', 'property_documents',
    'lots', 'lot_status_history', 'phase_maps', 'phase_map_users',

    # Social Features
    'follows', 'likes', 'comments', 'saved_properties',

    # Messaging
    'messages', 'notifications',

    # Collections System (keep safe too)
    'collection_jobs', 'collection_changes', 'collection_job_logs',
    'entity_matches', 'collection_sources'
}

# ===================================================================
# SCHEMA SYNC: Tables to EXCLUDE from autogenerate
# ===================================================================
# These tables exist in the database but don't have SQLAlchemy models.
# Excluding them prevents autogenerate from trying to drop them.

EXCLUDED_FROM_AUTOGENERATE = {
    # Auth & User Management (no models)
    'password_reset_tokens', 'onboarding_forms', 'email_verifications',
    'sessions', 'user_credentials',
    # NOTE: 'roles' is NOT excluded - it has a model and is used in routes

    # Builder System (core table exists, no model)
    'builders', 'builder_team_members', 'builder_documents', 'builder_awards',
    'builder_communities', 'builder_credentials', 'builder_home_plans', 'builder_portfolio',

    # Community System
    'community_documents', 'community_admin_links', 'community_admins',
    'community_amenities', 'community_awards', 'community_builders',
    'community_events', 'community_phases', 'community_topics',

    # Property System
    'property_documents', 'property_features', 'property_media',
    'lots', 'lot_status_history', 'phase_maps', 'phase_map_users',

    # Buyer System
    'buyer_documents', 'buyer_preferences', 'buyer_tours', 'buying_timelines',
    'favorite_properties', 'saved_properties', 'financing_statuses',
    'tour_statuses', 'preferred_channels', 'loan_programs',

    # Social Features
    'follows', 'likes', 'comments',

    # Messaging
    'messages', 'notifications',

    # Enterprise
    'enterprise_invitations',
}

def include_object(object, name, type_, reflected, compare_to):
    """
    Filter for autogenerate: exclude tables without models.

    This prevents Alembic from generating DROP TABLE statements
    for tables that exist in the database but don't have models.
    """
    if type_ == "table" and name in EXCLUDED_FROM_AUTOGENERATE:
        return False
    return True

def process_revision_directives(context, revision, directives):
    """
    Safety check for autogenerate migrations.
    Prevents accidental table drops of protected tables.
    """
    if config.cmd_opts and config.cmd_opts.autogenerate:
        script = directives[0]

        # Check for dangerous operations
        dangerous_ops = []

        for op in script.upgrade_ops.ops:
            # Check for table drops
            if hasattr(op, 'table_name') and op.__class__.__name__ == 'DropTableOp':
                if op.table_name in PROTECTED_TABLES:
                    dangerous_ops.append(f"DROP TABLE {op.table_name}")

            # Check for index drops on protected tables
            elif hasattr(op, 'table_name') and op.__class__.__name__ == 'DropIndexOp':
                if op.table_name in PROTECTED_TABLES:
                    dangerous_ops.append(f"DROP INDEX {op.index_name} on {op.table_name}")

            # Check for column drops on protected tables
            elif hasattr(op, 'table_name') and op.__class__.__name__ == 'DropColumnOp':
                if op.table_name in PROTECTED_TABLES:
                    dangerous_ops.append(f"DROP COLUMN {op.column_name} from {op.table_name}")

        if dangerous_ops:
            print("\n" + "=" * 80)
            print("⚠️  DANGEROUS MIGRATION DETECTED - BLOCKING AUTOGENERATE")
            print("=" * 80)
            print("\nThe following dangerous operations were detected:")
            for op in dangerous_ops:
                print(f"  ❌ {op}")
            print("\n⛔ This migration has been BLOCKED for safety.")
            print("\nIf you need to make these changes:")
            print("  1. Create a manual migration: alembic revision -m 'description'")
            print("  2. Manually edit the migration file")
            print("  3. Review carefully before applying")
            print("  4. Take a database backup first")
            print("=" * 80 + "\n")

            # Clear the directives to prevent migration creation
            directives[:] = []

def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode."""
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        compare_type=True,
        compare_server_default=True,
        process_revision_directives=process_revision_directives,
        include_object=include_object,
    )
    with context.begin_transaction():
        context.run_migrations()

def run_migrations_online() -> None:
    """Run migrations in 'online' mode."""
    connectable = engine_from_config(
        config.get_section(config.config_ini_section),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            compare_type=True,
            compare_server_default=True,
            process_revision_directives=process_revision_directives,
            include_object=include_object,
        )
        with context.begin_transaction():
            context.run_migrations()

if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()