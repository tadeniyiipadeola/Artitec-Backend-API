# routes/admin/analytics.py
"""
Platform analytics and statistics endpoints for admin dashboard.
Includes stats, audit logs, and growth data visualization.
"""
from datetime import datetime, timedelta, date
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import text
import logging

from config.db import get_db
from src.schemas import (
    AdminStatsOut,
    AdminStatsTotals,
    AdminStatsPeriod,
    AdminAuditLogOut,
    GrowthDataPoint,
    GrowthTimeSeriesOut,
)

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/stats", response_model=AdminStatsOut)
def get_admin_stats(
    from_date: Optional[datetime] = Query(None, alias="from", description="Start date for period statistics"),
    to_date: Optional[datetime] = Query(None, alias="to", description="End date for period statistics"),
    db: Session = Depends(get_db)
):
    """
    Get platform statistics for admin analytics dashboard.

    Provides comprehensive counts of users, builders, communities, properties,
    and optionally period-based growth metrics.

    Example:
        GET /v1/admin/stats
        GET /v1/admin/stats?from=2025-10-18T00:00:00Z&to=2025-11-18T00:00:00Z
    """
    try:
        # Get total user count
        result = db.execute(text("SELECT COUNT(*) as count FROM users"))
        total_users = result.fetchone().count

        # Get active users (logged in within last 30 days)
        # Check if last_login_at column exists
        try:
            result = db.execute(text("""
                SELECT COUNT(*) as count FROM users
                WHERE last_login_at >= DATE_SUB(NOW(), INTERVAL 30 DAY)
            """))
            active_users = result.fetchone().count
        except:
            # If last_login_at doesn't exist, use created_at as fallback
            try:
                result = db.execute(text("""
                    SELECT COUNT(*) as count FROM users
                    WHERE created_at >= DATE_SUB(NOW(), INTERVAL 30 DAY)
                """))
                active_users = result.fetchone().count
            except:
                # If that also fails, just use total users
                active_users = total_users

        # Get user role distribution from users table (SINGLE SOURCE OF TRUTH)
        # Use GROUP BY to get all role counts in a single query
        role_counts = {
            'buyer': 0,
            'builder': 0,
            'sales_rep': 0,
            'community': 0,  # Community Point of Contact
            'community_admin': 0,
            'admin': 0
        }

        try:
            result = db.execute(text("""
                SELECT role, COUNT(*) as count
                FROM users
                WHERE role IS NOT NULL AND role != ''
                GROUP BY role
            """))

            for row in result.fetchall():
                role_name = row.role
                role_count = row.count

                # Map role names to our role_counts dictionary
                if role_name in role_counts:
                    role_counts[role_name] = role_count
                else:
                    # Log unknown roles for debugging
                    logger.warning(f"Unknown user role found in database: {role_name}")
        except Exception as e:
            logger.error(f"Failed to get role distribution: {str(e)}")

        # Extract individual role counts
        total_buyers = role_counts['buyer']
        # Count builders from builder_profiles table instead of users table
        # This gives the actual number of builder profiles, not just builder user accounts
        try:
            result = db.execute(text("SELECT COUNT(*) as count FROM builder_profiles"))
            total_builders = result.fetchone().count
        except:
            # Fallback to user role count if builder_profiles table doesn't exist
            total_builders = role_counts['builder']
        total_sales_reps = role_counts['sales_rep']
        total_community_pocs = role_counts['community']
        total_community_admins = role_counts['community_admin']
        total_admins = role_counts['admin']

        # Verify that role counts add up to total users (accounting for NULL/empty roles)
        total_role_count = sum(role_counts.values())
        if total_role_count != total_users:
            logger.warning(f"Role count mismatch: {total_role_count} roles counted vs {total_users} total users. "
                          f"This indicates {total_users - total_role_count} users with NULL or empty roles.")

        # Get community count (handle if table doesn't exist)
        try:
            result = db.execute(text("SELECT COUNT(*) as count FROM communities"))
            total_communities = result.fetchone().count
        except:
            total_communities = 0

        # Get property count (handle if table doesn't exist)
        try:
            result = db.execute(text("SELECT COUNT(*) as count FROM property_listings"))
            total_properties = result.fetchone().count
        except:
            # Try alternative table name
            try:
                result = db.execute(text("SELECT COUNT(*) as count FROM properties"))
                total_properties = result.fetchone().count
            except:
                total_properties = 0

        # Get posts count (handle if table doesn't exist)
        try:
            result = db.execute(text("SELECT COUNT(*) as count FROM posts"))
            total_posts = result.fetchone().count or 0
        except:
            total_posts = 0

        # Get tours count (if table exists)
        try:
            result = db.execute(text("SELECT COUNT(*) as count FROM property_tours"))
            total_tours = result.fetchone().count or 0
        except:
            total_tours = 0

        # Get documents count (if table exists)
        try:
            result = db.execute(text("SELECT COUNT(*) as count FROM documents"))
            total_documents = result.fetchone().count or 0
        except:
            total_documents = 0

        totals = AdminStatsTotals(
            users=total_users,
            active_users=active_users,
            builders=total_builders,
            communities=total_communities,
            properties=total_properties,
            posts=total_posts,
            tours=total_tours,
            documents=total_documents,
            buyers=total_buyers,
            sales_reps=total_sales_reps,
            community_pocs=total_community_pocs,
            community_admins=total_community_admins,
            admins=total_admins
        )

        period = None
        if from_date and to_date:
            # Get period-based growth metrics (handle missing tables)
            try:
                result = db.execute(text("""
                    SELECT COUNT(*) as count FROM users
                    WHERE created_at >= :from_date AND created_at <= :to_date
                """), {"from_date": from_date, "to_date": to_date})
                new_users = result.fetchone().count
            except:
                new_users = 0

            # Count new builders from builder_profiles table
            try:
                result = db.execute(text("""
                    SELECT COUNT(*) as count FROM builder_profiles
                    WHERE created_at >= :from_date AND created_at <= :to_date
                """), {"from_date": from_date, "to_date": to_date})
                new_builders = result.fetchone().count
            except:
                # Fallback to counting from users table if builder_profiles doesn't exist
                try:
                    result = db.execute(text("""
                        SELECT COUNT(*) as count FROM users
                        WHERE role = 'builder'
                        AND created_at >= :from_date AND created_at <= :to_date
                    """), {"from_date": from_date, "to_date": to_date})
                    new_builders = result.fetchone().count
                except:
                    new_builders = 0

            try:
                result = db.execute(text("""
                    SELECT COUNT(*) as count FROM communities
                    WHERE created_at >= :from_date AND created_at <= :to_date
                """), {"from_date": from_date, "to_date": to_date})
                new_communities = result.fetchone().count
            except:
                new_communities = 0

            try:
                result = db.execute(text("""
                    SELECT COUNT(*) as count FROM property_listings
                    WHERE created_at >= :from_date AND created_at <= :to_date
                """), {"from_date": from_date, "to_date": to_date})
                new_properties = result.fetchone().count
            except:
                # Try alternative table name
                try:
                    result = db.execute(text("""
                        SELECT COUNT(*) as count FROM properties
                        WHERE created_at >= :from_date AND created_at <= :to_date
                    """), {"from_date": from_date, "to_date": to_date})
                    new_properties = result.fetchone().count
                except:
                    new_properties = 0

            period = AdminStatsPeriod(
                from_date=from_date,
                to_date=to_date,
                new_users=new_users,
                new_builders=new_builders,
                new_communities=new_communities,
                new_properties=new_properties
            )

        logger.info(
            "Retrieved admin stats: users=%d, builders=%d, communities=%d, properties=%d",
            total_users, total_builders, total_communities, total_properties
        )

        return AdminStatsOut(totals=totals, period=period)

    except Exception as e:
        logger.error("Failed to retrieve admin stats: %s", str(e), exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Error fetching admin statistics: {str(e)}"
        )


@router.get("/audit-logs", response_model=List[AdminAuditLogOut])
def get_audit_logs(
    from_date: Optional[datetime] = Query(None, alias="from", description="Start date filter"),
    to_date: Optional[datetime] = Query(None, alias="to", description="End date filter"),
    actor_user_id: Optional[int] = Query(None, description="Filter by actor user ID"),
    limit: int = Query(100, le=500, description="Maximum number of logs to return"),
    db: Session = Depends(get_db)
):
    """
    Get audit log entries for admin activity tracking.

    NOTE: This endpoint requires an audit_logs table to be created.
    The table should have the following structure:

    CREATE TABLE audit_logs (
        id INT AUTO_INCREMENT PRIMARY KEY,
        actor_user_id INT NOT NULL,
        action VARCHAR(255) NOT NULL,
        entity_type VARCHAR(100) NOT NULL,
        entity_id VARCHAR(255) NOT NULL,
        ip_address VARCHAR(45),
        user_agent TEXT,
        metadata JSON,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        INDEX idx_actor_user (actor_user_id),
        INDEX idx_created_at (created_at),
        INDEX idx_entity (entity_type, entity_id)
    );

    Example:
        GET /v1/admin/audit-logs
        GET /v1/admin/audit-logs?from=2025-10-18T00:00:00Z&to=2025-11-18T00:00:00Z
        GET /v1/admin/audit-logs?actor_user_id=1
    """
    try:
        # Build query dynamically based on filters
        query = """
            SELECT id, actor_user_id, action, entity_type, entity_id,
                   ip_address, user_agent, metadata, created_at
            FROM audit_logs
            WHERE 1=1
        """
        params = {}

        if from_date:
            query += " AND created_at >= :from_date"
            params["from_date"] = from_date

        if to_date:
            query += " AND created_at <= :to_date"
            params["to_date"] = to_date

        if actor_user_id:
            query += " AND actor_user_id = :actor_user_id"
            params["actor_user_id"] = actor_user_id

        query += " ORDER BY created_at DESC LIMIT :limit"
        params["limit"] = limit

        result = db.execute(text(query), params)
        logs = []

        for row in result.fetchall():
            logs.append(AdminAuditLogOut(
                id=row.id,
                actor_user_id=row.actor_user_id,
                action=row.action,
                entity_type=row.entity_type,
                entity_id=row.entity_id,
                ip_address=row.ip_address,
                user_agent=row.user_agent,
                metadata=row.metadata,
                created_at=row.created_at
            ))

        logger.info("Retrieved %d audit log entries", len(logs))
        return logs

    except Exception as e:
        # If table doesn't exist, return empty list
        if "doesn't exist" in str(e).lower() or "no such table" in str(e).lower():
            logger.warning("Audit logs table doesn't exist, returning empty list")
            return []

        logger.error("Failed to retrieve audit logs: %s", str(e), exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Error fetching audit logs: {str(e)}"
        )


@router.get("/growth", response_model=GrowthTimeSeriesOut)
def get_growth_data(
    from_date: Optional[datetime] = Query(None, alias="from", description="Start date for growth data"),
    to_date: Optional[datetime] = Query(None, description="End date for growth data"),
    interval: str = Query("day", description="Time interval: 'day', 'week', or 'month'"),
    db: Session = Depends(get_db)
):
    """
    Get time-series growth data for various metrics.

    Returns daily/weekly/monthly counts of new users, builders, communities, and properties
    over the specified time period. Used for rendering growth charts in the admin dashboard.

    Args:
        from_date: Start date (defaults to 30 days ago)
        to_date: End date (defaults to now)
        interval: Grouping interval - 'day', 'week', or 'month'

    Returns:
        GrowthTimeSeriesOut: Time series data with counts for each metric

    Example:
        GET /v1/admin/growth?from=2025-10-01T00:00:00Z&to=2025-11-18T00:00:00Z&interval=day
    """
    try:
        # Default date range: last 30 days
        if not to_date:
            to_date = datetime.utcnow()
        if not from_date:
            from_date = to_date - timedelta(days=30)

        # Determine MySQL date format based on interval
        if interval == "week":
            date_format = "%Y-%U"  # Year-Week
            date_trunc = "DATE_FORMAT(created_at, '%Y-%U')"
        elif interval == "month":
            date_format = "%Y-%m"  # Year-Month
            date_trunc = "DATE_FORMAT(created_at, '%Y-%m')"
        else:  # day
            date_format = "%Y-%m-%d"  # Year-Month-Day
            date_trunc = "DATE(created_at)"

        # Helper function to query growth data for a table
        def get_growth_series(table_name: str) -> List[GrowthDataPoint]:
            try:
                query = f"""
                    SELECT {date_trunc} as period, COUNT(*) as count
                    FROM {table_name}
                    WHERE created_at >= :from_date AND created_at <= :to_date
                    GROUP BY period
                    ORDER BY period ASC
                """
                result = db.execute(text(query), {"from_date": from_date, "to_date": to_date})

                data_points = []
                for row in result.fetchall():
                    # Convert period to datetime
                    # row.period might be a date object or a string depending on database
                    if isinstance(row.period, str):
                        if interval == "week":
                            # For week format, use the first day of that week
                            period_date = datetime.strptime(row.period + "-1", "%Y-%U-%w")
                        elif interval == "month":
                            # For month format, use the first day of that month
                            period_date = datetime.strptime(row.period + "-01", "%Y-%m-%d")
                        else:  # day
                            period_date = datetime.strptime(row.period, "%Y-%m-%d")
                    else:
                        # If it's already a date/datetime object, convert to datetime
                        if isinstance(row.period, date):
                            period_date = datetime.combine(row.period, datetime.min.time())
                        else:
                            period_date = row.period

                    data_points.append(GrowthDataPoint(
                        date=period_date,
                        count=int(row.count)
                    ))

                return data_points
            except Exception as e:
                logger.warning(f"Failed to get growth data for {table_name}: {str(e)}")
                return []

        # Get growth data for each entity type
        users_growth = get_growth_series("users")
        builders_growth = get_growth_series("builder_profiles")
        communities_growth = get_growth_series("communities")

        # Try both property_listings and properties tables
        properties_growth = get_growth_series("property_listings")
        if not properties_growth:
            properties_growth = get_growth_series("properties")

        return GrowthTimeSeriesOut(
            users=users_growth,
            builders=builders_growth,
            communities=communities_growth,
            properties=properties_growth
        )

    except Exception as e:
        logger.error("Failed to retrieve growth data: %s", str(e), exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Error fetching growth data: {str(e)}"
        )
