# routes/auth/__init__.py
"""
Authentication module - Combines all auth-related routers
"""
from fastapi import APIRouter
from routes.auth import authentication, registration, verification

# Create main router
router = APIRouter()

# Include all sub-routers
router.include_router(authentication.router, tags=["Authentication"])
router.include_router(registration.router, tags=["Authentication"])
router.include_router(verification.router, tags=["Authentication"])
