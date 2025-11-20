# routes/admin_helpers.py
"""
Admin helper endpoints for database management tasks
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import text
import os
from datetime import datetime
from typing import Optional

from config.db import get_db, engine
from src.id_generator import generate_community_admin_id
from src.schemas import DatabaseStatsOut, TableStatOut, DatabaseHealthOut
from src.storage import get_storage_backend

router = APIRouter()


@router.post("/connect-user-to-community")
def connect_user_to_community(
    user_email: str = None,
    user_public_id: str = None,
    community_name: str = None,
    community_id: int = None,
    db: Session = Depends(get_db)
):
    """
    Connect a user to a community by creating/updating CommunityAdminProfile.

    Example:
        POST /admin/connect-user-to-community?user_email=fred.caldwell@oakmeadows.org&community_name=The Highlands
        POST /admin/connect-user-to-community?user_public_id=USR-1763002155-GRZVLL&community_name=The Highlands
    """

    if not (user_email or user_public_id):
        raise HTTPException(status_code=400, detail="Must provide user_email or user_public_id")

    if not (community_name or community_id):
        raise HTTPException(status_code=400, detail="Must provide community_name or community_id")

    # Find user
    if user_public_id:
        result = db.execute(text("""
            SELECT id, user_id, email, first_name, last_name, phone_e164, role
            FROM users
            WHERE user_id = :user_id
            LIMIT 1
        """), {"user_id": user_public_id})
    else:
        result = db.execute(text("""
            SELECT id, user_id, email, first_name, last_name, phone_e164, role
            FROM users
            WHERE email = :email
            LIMIT 1
        """), {"email": user_email})

    user = result.fetchone()

    if not user:
        identifier = user_public_id or user_email
        raise HTTPException(status_code=404, detail=f"User not found: {identifier}")

    # Find community
    if community_id:
        result = db.execute(text("""
            SELECT id, community_id, name
            FROM communities
            WHERE id = :id
            LIMIT 1
        """), {"id": community_id})
    else:
        result = db.execute(text("""
            SELECT id, community_id, name
            FROM communities
            WHERE name LIKE :name
            LIMIT 1
        """), {"name": f"%{community_name}%"})

    community = result.fetchone()

    if not community:
        raise HTTPException(status_code=404, detail=f"Community not found: {community_name}")

    # Check if admin profile exists
    result = db.execute(text("""
        SELECT id, community_admin_id, community_id
        FROM community_admin_profiles
        WHERE user_id = :user_id
    """), {"user_id": user.user_id})

    existing = result.fetchone()

    if existing:
        # Update existing
        db.execute(text("""
            UPDATE community_admin_profiles
            SET community_id = :community_id,
                first_name = :first_name,
                last_name = :last_name,
                contact_email = :email,
                contact_phone = :phone,
                updated_at = CURRENT_TIMESTAMP
            WHERE user_id = :user_id
        """), {
            "user_id": user.user_id,
            "community_id": community.id,
            "first_name": user.first_name,
            "last_name": user.last_name,
            "email": user.email,
            "phone": user.phone_e164
        })
        action = "updated"
        admin_typed_id = existing.community_admin_id
    else:
        # Create new
        admin_typed_id = generate_community_admin_id()
        db.execute(text("""
            INSERT INTO community_admin_profiles (
                community_admin_id, user_id, community_id,
                first_name, last_name, contact_email, contact_phone,
                title, can_post_announcements, can_manage_events, can_moderate_threads
            ) VALUES (
                :community_admin_id, :user_id, :community_id,
                :first_name, :last_name, :email, :phone,
                'Community Administrator', 1, 1, 1
            )
        """), {
            "community_admin_id": admin_typed_id,
            "user_id": user.user_id,
            "community_id": community.id,
            "first_name": user.first_name,
            "last_name": user.last_name,
            "email": user.email,
            "phone": user.phone_e164
        })
        action = "created"

    db.commit()

    return {
        "success": True,
        "action": action,
        "user": {
            "id": user.id,
            "user_id": user.user_id,
            "email": user.email,
            "name": f"{user.first_name} {user.last_name}",
            "role": user.role
        },
        "community": {
            "id": community.id,
            "community_id": community.community_id,
            "name": community.name
        },
        "admin_profile_community_admin_id": admin_typed_id,
        "endpoint": f"/api/v1/communities/for-user/{user.user_id}"
    }


@router.get("/database/stats", response_model=DatabaseStatsOut)
def get_database_stats(db: Session = Depends(get_db)):
    """
    Get comprehensive database and storage statistics for admin dashboard.

    Collects:
    - MariaDB database size, table counts, and record counts
    - Individual table statistics (name, size, record count)
    - Connection pool status and query performance metrics
    - MinIO storage usage
    - Database health indicators

    Example:
        GET /admin/database/stats
    """
    try:
        # Check database connection
        is_connected = True
        try:
            db.execute(text("SELECT 1"))
        except Exception:
            is_connected = False

        # Get database name from connection URL
        db_name = os.getenv("DB_URL", "").split("/")[-1].split("?")[0] or "artitec"

        # Get database size
        result = db.execute(text("""
            SELECT
                ROUND(SUM(data_length + index_length) / 1024 / 1024, 2) as size_mb,
                COUNT(*) as table_count
            FROM information_schema.TABLES
            WHERE table_schema = :db_name
        """), {"db_name": db_name})
        db_stats = result.fetchone()
        database_size_mb = float(db_stats.size_mb or 0)
        total_tables = int(db_stats.table_count or 0)

        # Get individual table statistics
        result = db.execute(text("""
            SELECT
                table_name,
                table_rows as record_count,
                ROUND((data_length + index_length) / 1024 / 1024, 2) as size_mb,
                update_time as last_updated
            FROM information_schema.TABLES
            WHERE table_schema = :db_name
            ORDER BY (data_length + index_length) DESC
            LIMIT 10
        """), {"db_name": db_name})

        tables = []
        total_records = 0
        for row in result.fetchall():
            tables.append(TableStatOut(
                table_name=row.table_name,
                record_count=int(row.record_count or 0),
                size_mb=float(row.size_mb or 0),
                last_updated=row.last_updated
            ))
            total_records += int(row.record_count or 0)

        # Get connection pool status
        result = db.execute(text("""
            SHOW STATUS WHERE Variable_name IN (
                'Threads_connected',
                'Max_used_connections',
                'Slow_queries'
            )
        """))
        pool_stats = {row.Variable_name: int(row.Value) for row in result.fetchall()}

        threads_connected = pool_stats.get('Threads_connected', 0)
        max_connections = 150  # Default MariaDB max_connections
        connection_pool_value = f"{threads_connected}/{max_connections} active"
        connection_pool_status = "good" if threads_connected < max_connections * 0.5 else "warning" if threads_connected < max_connections * 0.8 else "error"

        # Get query performance (average query time from slow query log)
        slow_queries = pool_stats.get('Slow_queries', 0)
        query_performance_value = f"{slow_queries} slow queries"
        query_performance_status = "good" if slow_queries < 10 else "warning" if slow_queries < 50 else "error"

        # Calculate storage usage percentage
        storage_usage_pct = (database_size_mb / 1024) * 100 / 100  # Assume 100GB limit
        storage_usage_value = f"{storage_usage_pct:.1f}% used"
        storage_usage_status = "good" if storage_usage_pct < 50 else "warning" if storage_usage_pct < 80 else "error"

        # Check index health (fragmentation)
        result = db.execute(text("""
            SELECT COUNT(*) as indexes_count
            FROM information_schema.STATISTICS
            WHERE table_schema = :db_name
        """), {"db_name": db_name})
        indexes_count = result.fetchone().indexes_count
        index_health_value = f"{indexes_count} indexes"
        index_health_status = "good"  # Could add more sophisticated checks

        # Get MinIO storage usage
        storage_used_gb = 0.0
        try:
            storage_backend = get_storage_backend()
            # For S3Storage (MinIO), calculate bucket size
            if hasattr(storage_backend, 's3_client'):
                # List all objects and sum their sizes
                try:
                    paginator = storage_backend.s3_client.get_paginator('list_objects_v2')
                    total_bytes = 0
                    for page in paginator.paginate(Bucket=storage_backend.bucket_name):
                        if 'Contents' in page:
                            for obj in page['Contents']:
                                total_bytes += obj['Size']
                    storage_used_gb = total_bytes / 1024 / 1024 / 1024
                except Exception:
                    # If MinIO not available, use placeholder
                    storage_used_gb = 0.0
            else:
                # For LocalFileStorage, calculate directory size
                if hasattr(storage_backend, 'base_dir'):
                    import pathlib
                    total_bytes = sum(f.stat().st_size for f in pathlib.Path(storage_backend.base_dir).rglob('*') if f.is_file())
                    storage_used_gb = total_bytes / 1024 / 1024 / 1024
        except Exception:
            storage_used_gb = 0.0

        # Get last backup time (placeholder - would need actual backup system)
        last_backup = None  # Could query backup logs or file timestamps

        # Build health response
        health = DatabaseHealthOut(
            connection_pool=connection_pool_status,
            connection_pool_value=connection_pool_value,
            query_performance=query_performance_status,
            query_performance_value=query_performance_value,
            storage_usage=storage_usage_status,
            storage_usage_value=storage_usage_value,
            index_health=index_health_status,
            index_health_value=index_health_value
        )

        return DatabaseStatsOut(
            is_connected=is_connected,
            database_size_mb=database_size_mb,
            total_tables=total_tables,
            total_records=total_records,
            last_backup=last_backup,
            storage_used_gb=storage_used_gb,
            tables=tables,
            health=health
        )

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error fetching database statistics: {str(e)}"
        )
