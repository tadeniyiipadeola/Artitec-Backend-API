# routes/schools.py
"""
School Data API Routes

Provides endpoints for searching and retrieving school information using the GreatSchools API.
Useful for community property listings to show nearby schools and their ratings.
"""

from fastapi import APIRouter, HTTPException, Query
from typing import Optional
import logging

from src.greatschools_client import (
    get_greatschools_client,
    close_greatschools_client,
    GreatSchoolsError,
    GreatSchoolsRateLimitError
)

router = APIRouter()
logger = logging.getLogger(__name__)


@router.get("/search/nearby")
async def search_schools_nearby(
    city: str = Query(..., description="City name"),
    state: str = Query(..., description="Two-letter state code (e.g., TX, CA)"),
    limit: int = Query(10, ge=1, le=25, description="Maximum number of results (1-25)"),
    level_code: Optional[str] = Query(None, description="School level: p (preschool), e (elementary), m (middle), h (high)"),
    sort: str = Query("distance", description="Sort order: distance or rating")
):
    """
    Search for schools by city and state.

    Returns schools with ratings, location, and basic info sorted by distance or rating.

    Example:
        GET /v1/schools/search/nearby?city=Austin&state=TX&limit=10&level_code=e
    """
    try:
        client = get_greatschools_client()
        result = await client.search_schools_nearby(
            city=city,
            state=state,
            limit=limit,
            level_code=level_code,
            sort=sort
        )
        return result
    except GreatSchoolsRateLimitError:
        raise HTTPException(
            status_code=429,
            detail="School API rate limit exceeded. Please try again later."
        )
    except GreatSchoolsError as e:
        logger.error(f"GreatSchools API error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"School API error: {str(e)}")
    except Exception as e:
        logger.error(f"Unexpected error searching schools: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to search schools")


@router.get("/search/by-zip")
async def search_schools_by_zip(
    zip_code: str = Query(..., description="ZIP/postal code"),
    radius: float = Query(5.0, ge=0.1, le=25.0, description="Search radius in miles (0.1-25)"),
    limit: int = Query(10, ge=1, le=25, description="Maximum number of results (1-25)"),
    level_code: Optional[str] = Query(None, description="School level: p (preschool), e (elementary), m (middle), h (high)")
):
    """
    Search for schools by ZIP code and radius.

    Example:
        GET /v1/schools/search/by-zip?zip_code=78701&radius=5&limit=10
    """
    try:
        client = get_greatschools_client()
        result = await client.search_schools_by_zip(
            zip_code=zip_code,
            radius=radius,
            limit=limit,
            level_code=level_code
        )
        return result
    except GreatSchoolsRateLimitError:
        raise HTTPException(
            status_code=429,
            detail="School API rate limit exceeded. Please try again later."
        )
    except GreatSchoolsError as e:
        logger.error(f"GreatSchools API error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"School API error: {str(e)}")
    except Exception as e:
        logger.error(f"Unexpected error searching schools: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to search schools")


@router.get("/search/by-location")
async def search_schools_by_location(
    latitude: float = Query(..., description="Latitude coordinate"),
    longitude: float = Query(..., description="Longitude coordinate"),
    radius: float = Query(5.0, ge=0.1, le=25.0, description="Search radius in miles (0.1-25)"),
    limit: int = Query(10, ge=1, le=25, description="Maximum number of results (1-25)"),
    level_code: Optional[str] = Query(None, description="School level: p (preschool), e (elementary), m (middle), h (high)")
):
    """
    Find schools near a geographic location (latitude/longitude).

    Useful for property listings to show nearby schools.

    Example:
        GET /v1/schools/search/by-location?latitude=30.2672&longitude=-97.7431&radius=5
    """
    try:
        client = get_greatschools_client()
        result = await client.search_schools_by_location(
            latitude=latitude,
            longitude=longitude,
            radius=radius,
            limit=limit,
            level_code=level_code
        )
        return result
    except GreatSchoolsRateLimitError:
        raise HTTPException(
            status_code=429,
            detail="School API rate limit exceeded. Please try again later."
        )
    except GreatSchoolsError as e:
        logger.error(f"GreatSchools API error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"School API error: {str(e)}")
    except Exception as e:
        logger.error(f"Unexpected error searching schools: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to search schools")


@router.get("/search/by-name")
async def search_schools_by_name(
    school_name: str = Query(..., description="School name to search for"),
    state: str = Query(..., description="Two-letter state code"),
    city: Optional[str] = Query(None, description="City name to narrow search"),
    limit: int = Query(10, ge=1, le=25, description="Maximum number of results (1-25)")
):
    """
    Search for schools by name.

    Example:
        GET /v1/schools/search/by-name?school_name=Austin+Elementary&state=TX&city=Austin
    """
    try:
        client = get_greatschools_client()
        result = await client.search_schools_by_name(
            school_name=school_name,
            state=state,
            city=city,
            limit=limit
        )
        return result
    except GreatSchoolsRateLimitError:
        raise HTTPException(
            status_code=429,
            detail="School API rate limit exceeded. Please try again later."
        )
    except GreatSchoolsError as e:
        logger.error(f"GreatSchools API error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"School API error: {str(e)}")
    except Exception as e:
        logger.error(f"Unexpected error searching schools: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to search schools")


@router.get("/{state}/{school_id}")
async def get_school_details(
    state: str,
    school_id: str
):
    """
    Get detailed information about a specific school.

    Returns comprehensive data including ratings, test scores, demographics, and reviews.

    Example:
        GET /v1/schools/TX/12345
    """
    try:
        client = get_greatschools_client()
        result = await client.get_school_details(
            school_id=school_id,
            state=state
        )
        return result
    except GreatSchoolsRateLimitError:
        raise HTTPException(
            status_code=429,
            detail="School API rate limit exceeded. Please try again later."
        )
    except GreatSchoolsError as e:
        logger.error(f"GreatSchools API error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"School API error: {str(e)}")
    except Exception as e:
        logger.error(f"Unexpected error fetching school details: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to fetch school details")


@router.get("/{state}/{school_id}/reviews")
async def get_school_reviews(
    state: str,
    school_id: str,
    limit: int = Query(10, ge=1, le=25, description="Maximum number of reviews (1-25)")
):
    """
    Get parent reviews for a specific school.

    Example:
        GET /v1/schools/TX/12345/reviews?limit=10
    """
    try:
        client = get_greatschools_client()
        result = await client.get_school_reviews(
            school_id=school_id,
            state=state,
            limit=limit
        )
        return result
    except GreatSchoolsRateLimitError:
        raise HTTPException(
            status_code=429,
            detail="School API rate limit exceeded. Please try again later."
        )
    except GreatSchoolsError as e:
        logger.error(f"GreatSchools API error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"School API error: {str(e)}")
    except Exception as e:
        logger.error(f"Unexpected error fetching school reviews: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to fetch school reviews")


@router.on_event("shutdown")
async def shutdown_event():
    """Close GreatSchools API client connection on app shutdown."""
    await close_greatschools_client()
    logger.info("GreatSchools API client closed")
