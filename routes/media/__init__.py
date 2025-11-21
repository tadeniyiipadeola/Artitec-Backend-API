# routes/media/__init__.py
"""
Media module - Combines all media-related routers with /v1/media prefix
"""
from fastapi import APIRouter
from routes.media import upload, management, scraper, entities

# Create main router with /v1/media prefix
router = APIRouter(prefix="/v1/media", tags=["Media"])

# Include all sub-routers
router.include_router(upload.router)
router.include_router(management.router)
router.include_router(scraper.router)  # scraper already has /scraper prefix
router.include_router(entities.router)  # entity-specific upload routes
