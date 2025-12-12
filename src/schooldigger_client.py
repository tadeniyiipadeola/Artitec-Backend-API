# src/schooldigger_client.py
"""
SchoolDigger API Client

Provides integration with the SchoolDigger API for retrieving school ratings,
rankings, test scores, and demographic data.

API Documentation: https://developer.schooldigger.com/docs

Rate Limits (Free Tier):
- 1 request per minute
- 20 requests per day
"""

import httpx
from typing import Optional, List, Dict, Any
from config.settings import SCHOOLDIGGER_API_KEY
import logging

logger = logging.getLogger(__name__)


class SchoolDiggerError(Exception):
    """Base exception for SchoolDigger API errors"""
    pass


class SchoolDiggerRateLimitError(SchoolDiggerError):
    """Raised when API rate limit is exceeded"""
    pass


class SchoolDiggerClient:
    """
    Client for interacting with the SchoolDigger API.

    Example Usage:
        client = SchoolDiggerClient()
        schools = await client.search_schools(query="Oakland Elementary", state="CA")
        school_details = await client.get_school_details(school_id="001234")
    """

    BASE_URL = "https://api.schooldigger.com"
    API_VERSION = "v2.0"  # Using v2.0 for latest features

    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize the SchoolDigger API client.

        Args:
            api_key: SchoolDigger API key. If not provided, uses SCHOOLDIGGER_API_KEY from settings.
        """
        self.api_key = api_key or SCHOOLDIGGER_API_KEY
        if not self.api_key:
            logger.warning("SchoolDigger API key not configured. School ratings will not be available.")

        self.client = httpx.AsyncClient(
            base_url=f"{self.BASE_URL}/{self.API_VERSION}",
            timeout=30.0,
            headers={
                "Accept": "application/json",
            }
        )

    async def close(self):
        """Close the HTTP client connection."""
        await self.client.aclose()

    async def _make_request(
        self,
        endpoint: str,
        params: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Make an authenticated request to the SchoolDigger API.

        Args:
            endpoint: API endpoint path (e.g., "schools/v2")
            params: Query parameters

        Returns:
            Response data as dictionary

        Raises:
            SchoolDiggerError: If API request fails
            SchoolDiggerRateLimitError: If rate limit is exceeded
        """
        if not self.api_key:
            raise SchoolDiggerError("SchoolDigger API key not configured")

        # Add API key to query parameters
        request_params = params.copy() if params else {}
        request_params["appid"] = self.api_key
        request_params["appkey"] = self.api_key

        try:
            response = await self.client.get(endpoint, params=request_params)

            # Handle rate limiting
            if response.status_code == 429:
                logger.warning("SchoolDigger API rate limit exceeded")
                raise SchoolDiggerRateLimitError("API rate limit exceeded. Please try again later.")

            # Handle other errors
            if response.status_code >= 400:
                error_msg = f"SchoolDigger API error: {response.status_code}"
                logger.error(f"{error_msg} - {response.text}")
                raise SchoolDiggerError(error_msg)

            return response.json()

        except httpx.HTTPError as e:
            logger.error(f"HTTP error calling SchoolDigger API: {str(e)}")
            raise SchoolDiggerError(f"Failed to call SchoolDigger API: {str(e)}")

    async def search_schools(
        self,
        query: Optional[str] = None,
        state: Optional[str] = None,
        city: Optional[str] = None,
        zip_code: Optional[str] = None,
        district: Optional[str] = None,
        level: Optional[str] = None,
        page: int = 1,
        per_page: int = 10
    ) -> Dict[str, Any]:
        """
        Search for schools by various criteria.

        Args:
            query: School name search query
            state: Two-letter state code (e.g., "CA", "TX")
            city: City name
            zip_code: ZIP/postal code
            district: School district name
            level: School level filter (e.g., "Elementary", "Middle", "High")
            page: Page number for pagination (default: 1)
            per_page: Results per page (default: 10, max: 50)

        Returns:
            Dictionary with 'schools' list and pagination info

        Example:
            {
                "schools": [
                    {
                        "schoolid": "001234",
                        "schoolName": "Oakland Elementary",
                        "address": "123 Main St",
                        "city": "Oakland",
                        "state": "CA",
                        "zip": "94601",
                        "phone": "(510) 555-1234",
                        "rankHistory": [...],
                        "schoolDiggerRating": 8
                    }
                ],
                "totalResults": 100,
                "page": 1,
                "perPage": 10
            }
        """
        params = {
            "page": page,
            "perPage": min(per_page, 50)  # API max is 50
        }

        if query:
            params["q"] = query
        if state:
            params["st"] = state.upper()
        if city:
            params["city"] = city
        if zip_code:
            params["zip"] = zip_code
        if district:
            params["district"] = district
        if level:
            params["level"] = level

        logger.info(f"Searching schools with params: {params}")
        return await self._make_request("schools", params)

    async def get_school_details(self, school_id: str) -> Dict[str, Any]:
        """
        Get detailed information about a specific school.

        Args:
            school_id: SchoolDigger school ID

        Returns:
            School details including ratings, test scores, demographics

        Example:
            {
                "schoolid": "001234",
                "schoolName": "Oakland Elementary",
                "address": "123 Main St",
                "city": "Oakland",
                "state": "CA",
                "zip": "94601",
                "phone": "(510) 555-1234",
                "schoolDiggerRating": 8,
                "rankHistory": [
                    {"year": 2023, "rank": 42, "rankOf": 500, "rankStars": 8}
                ],
                "testScores": [...],
                "studentDemographics": {...}
            }
        """
        logger.info(f"Fetching school details for ID: {school_id}")
        return await self._make_request(f"schools/{school_id}")

    async def get_school_rankings(
        self,
        state: str,
        level: Optional[str] = None,
        year: Optional[int] = None,
        page: int = 1,
        per_page: int = 20
    ) -> Dict[str, Any]:
        """
        Get school rankings by state.

        Args:
            state: Two-letter state code (e.g., "CA", "TX")
            level: School level ("Elementary", "Middle", "High")
            year: Year for rankings (default: most recent)
            page: Page number
            per_page: Results per page

        Returns:
            Ranked list of schools in the state
        """
        params = {
            "st": state.upper(),
            "page": page,
            "perPage": min(per_page, 50)
        }

        if level:
            params["level"] = level
        if year:
            params["year"] = year

        logger.info(f"Fetching school rankings for {state} with params: {params}")
        return await self._make_request("rankings", params)

    async def search_districts(
        self,
        state: str,
        query: Optional[str] = None,
        page: int = 1,
        per_page: int = 10
    ) -> Dict[str, Any]:
        """
        Search for school districts.

        Args:
            state: Two-letter state code
            query: District name search query
            page: Page number
            per_page: Results per page

        Returns:
            List of matching school districts
        """
        params = {
            "st": state.upper(),
            "page": page,
            "perPage": min(per_page, 50)
        }

        if query:
            params["q"] = query

        logger.info(f"Searching districts in {state}")
        return await self._make_request("districts", params)

    async def get_district_details(self, district_id: str) -> Dict[str, Any]:
        """
        Get detailed information about a specific school district.

        Args:
            district_id: SchoolDigger district ID

        Returns:
            District details and statistics
        """
        logger.info(f"Fetching district details for ID: {district_id}")
        return await self._make_request(f"districts/{district_id}")

    async def get_schools_near_location(
        self,
        latitude: float,
        longitude: float,
        radius_miles: float = 5.0,
        level: Optional[str] = None,
        per_page: int = 10
    ) -> Dict[str, Any]:
        """
        Find schools near a geographic location.

        Args:
            latitude: Latitude coordinate
            longitude: Longitude coordinate
            radius_miles: Search radius in miles (default: 5.0)
            level: School level filter
            per_page: Results per page

        Returns:
            List of schools within the specified radius
        """
        params = {
            "lat": latitude,
            "lon": longitude,
            "distance": radius_miles,
            "perPage": min(per_page, 50)
        }

        if level:
            params["level"] = level

        logger.info(f"Searching schools near ({latitude}, {longitude})")
        return await self._make_request("schools/nearby", params)


# Singleton instance for easy access
_client: Optional[SchoolDiggerClient] = None


def get_schooldigger_client() -> SchoolDiggerClient:
    """
    Get or create the SchoolDigger API client singleton instance.

    Returns:
        SchoolDiggerClient instance
    """
    global _client
    if _client is None:
        _client = SchoolDiggerClient()
    return _client


async def close_schooldigger_client():
    """Close the SchoolDigger API client connection."""
    global _client
    if _client is not None:
        await _client.close()
        _client = None
