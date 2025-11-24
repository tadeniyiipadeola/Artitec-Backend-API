# routes/admin/__init__.py
"""
Admin module combining all enterprise and admin-related routers.

This module splits the original large enterprise.py file into logical components:
- invitations: Invitation validation, acceptance, listing, and management
- teams: Team member management and invitations
- communities: Community listing and assignment
- analytics: Platform statistics, audit logs, and growth data
- users: User management and enterprise builder provisioning

All routers are combined into a single main router for easy inclusion in the app.
"""
from fastapi import APIRouter

# Import all sub-routers
from .invitations import router as invitations_router
from .teams import router as teams_router
from .communities import router as communities_router
from .analytics import router as analytics_router
from .users import router as users_router
from .collection import router as collection_router

# Create main router that combines all admin routes
router = APIRouter()

# Include all sub-routers
# Note: The main app.py will add the /v1/admin prefix
router.include_router(invitations_router, tags=["Enterprise - Invitations"])
router.include_router(teams_router, tags=["Enterprise - Teams"])
router.include_router(communities_router, tags=["Enterprise - Communities"])
router.include_router(analytics_router, tags=["Enterprise - Analytics"])
router.include_router(users_router, tags=["Enterprise - Users"])
router.include_router(collection_router, tags=["Admin - Data Collection"])

__all__ = ["router"]
