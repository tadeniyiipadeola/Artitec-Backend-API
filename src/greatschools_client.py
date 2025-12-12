# src/greatschools_client.py
"""
GreatSchools API Client

Provides integration with the GreatSchools API for retrieving school ratings,
reviews, test scores, and demographic data.

API Documentation: https://www.greatschools.org/api/docs/

Free Tier:
- 10,000 requests per month
- Much more generous than other school data APIs
"""

import httpx
from typing import Optional, List, Dict, Any
from config.settings import GREATSCHOOLS_API_KEY
import logging

logger = logging.getLogger(__name__)


class GreatSchoolsError(Exception):
    """Base exception for GreatSchools API errors"""
    pass


class GreatSchoolsRateLimitError(GreatSchoolsError):
    """Raised when API rate limit is exceeded"""
    pass


class GreatSchoolsClient:
    """
    Client for interacting with the GreatSchools API.

    Example Usage:
        client = GreatSchoolsClient()
        schools = await client.search_schools_nearby(city="Austin", state="TX")
        school_details = await client.get_school_details(school_id="12345", state="TX")
    """

    BASE_URL = "https://api.greatschools.org"
    API_VERSION = "schools"  # Using schools endpoint

    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize the GreatSchools API client.

        Args:
            api_key: GreatSchools API key. If not provided, uses GREATSCHOOLS_API_KEY from settings.
        """
        self.api_key = api_key or GREATSCHOOLS_API_KEY
        if not self.api_key:
            logger.warning("GreatSchools API key not configured. School ratings will not be available.")

        self.client = httpx.AsyncClient(
            base_url=self.BASE_URL,
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
        Make an authenticated request to the GreatSchools API.

        Args:
            endpoint: API endpoint path
            params: Query parameters

        Returns:
            Response data as dictionary

        Raises:
            GreatSchoolsError: If API request fails
            GreatSchoolsRateLimitError: If rate limit is exceeded
        """
        if not self.api_key:
            raise GreatSchoolsError("GreatSchools API key not configured")

        # Add API key to query parameters
        request_params = params.copy() if params else {}
        request_params["key"] = self.api_key

        try:
            response = await self.client.get(endpoint, params=request_params)

            # Handle rate limiting
            if response.status_code == 429:
                logger.warning("GreatSchools API rate limit exceeded")
                raise GreatSchoolsRateLimitError("API rate limit exceeded. Please try again later.")

            # Handle other errors
            if response.status_code >= 400:
                error_msg = f"GreatSchools API error: {response.status_code}"
                logger.error(f"{error_msg} - {response.text}")
                raise GreatSchoolsError(error_msg)

            return response.json()

        except httpx.HTTPError as e:
            logger.error(f"HTTP error calling GreatSchools API: {str(e)}")
            raise GreatSchoolsError(f"Failed to call GreatSchools API: {str(e)}")

    async def search_schools_nearby(
        self,
        city: str,
        state: str,
        limit: int = 10,
        level_code: Optional[str] = None,
        sort: str = "distance"
    ) -> Dict[str, Any]:
        """
        Search for schools by city and state.

        Args:
            city: City name
            state: Two-letter state code (e.g., "TX", "CA")
            limit: Maximum number of results (default: 10, max: 25)
            level_code: School level filter:
                - "p" for preschool
                - "e" for elementary
                - "m" for middle
                - "h" for high
            sort: Sort order (default: "distance", options: "distance", "rating")

        Returns:
            Dictionary with school results

        Example:
            {
                "schools": [
                    {
                        "id": "12345",
                        "name": "Austin Elementary",
                        "address": "123 Main St",
                        "city": "Austin",
                        "state": "TX",
                        "zip": "78701",
                        "gsRating": 8,
                        "level": "Elementary",
                        "lat": 30.2672,
                        "lon": -97.7431
                    }
                ],
                "numberOfSchools": 10
            }
        """
        params = {
            "city": city,
            "state": state.upper(),
            "limit": min(limit, 25),  # API max is 25
            "sort": sort
        }

        if level_code:
            params["levelCode"] = level_code

        logger.info(f"Searching schools in {city}, {state}")
        endpoint = f"/{self.API_VERSION}/nearby"
        return await self._make_request(endpoint, params)

    async def search_schools_by_zip(
        self,
        zip_code: str,
        radius: float = 5.0,
        limit: int = 10,
        level_code: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Search for schools by ZIP code.

        Args:
            zip_code: ZIP/postal code
            radius: Search radius in miles (default: 5.0)
            limit: Maximum number of results
            level_code: School level filter (p/e/m/h)

        Returns:
            Dictionary with school results
        """
        params = {
            "zip": zip_code,
            "radius": radius,
            "limit": min(limit, 25)
        }

        if level_code:
            params["levelCode"] = level_code

        logger.info(f"Searching schools near ZIP {zip_code}")
        endpoint = f"/{self.API_VERSION}/nearby"
        return await self._make_request(endpoint, params)

    async def search_schools_by_location(
        self,
        latitude: float,
        longitude: float,
        radius: float = 5.0,
        limit: int = 10,
        level_code: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Find schools near a geographic location.

        Args:
            latitude: Latitude coordinate
            longitude: Longitude coordinate
            radius: Search radius in miles (default: 5.0)
            limit: Maximum number of results
            level_code: School level filter

        Returns:
            Dictionary with school results
        """
        params = {
            "lat": latitude,
            "lon": longitude,
            "radius": radius,
            "limit": min(limit, 25)
        }

        if level_code:
            params["levelCode"] = level_code

        logger.info(f"Searching schools near ({latitude}, {longitude})")
        endpoint = f"/{self.API_VERSION}/nearby"
        return await self._make_request(endpoint, params)

    async def get_school_details(
        self,
        school_id: str,
        state: str
    ) -> Dict[str, Any]:
        """
        Get detailed information about a specific school.

        Args:
            school_id: GreatSchools school ID
            state: Two-letter state code

        Returns:
            School details including ratings, test scores, demographics

        Example:
            {
                "id": "12345",
                "name": "Austin Elementary",
                "address": "123 Main St",
                "city": "Austin",
                "state": "TX",
                "zip": "78701",
                "gsRating": 8,
                "parentRating": 4,
                "level": "Elementary",
                "type": "public",
                "enrollment": 450,
                "students": {
                    "white": 45,
                    "hispanic": 30,
                    "black": 15,
                    "asian": 8,
                    "other": 2
                },
                "testScores": [...],
                "lat": 30.2672,
                "lon": -97.7431
            }
        """
        params = {"state": state.upper()}

        logger.info(f"Fetching school details for ID: {school_id} in {state}")
        endpoint = f"/{self.API_VERSION}/{state.upper()}/{school_id}"
        return await self._make_request(endpoint, params)

    async def get_school_reviews(
        self,
        school_id: str,
        state: str,
        limit: int = 10
    ) -> Dict[str, Any]:
        """
        Get parent reviews for a specific school.

        Args:
            school_id: GreatSchools school ID
            state: Two-letter state code
            limit: Maximum number of reviews to return

        Returns:
            Dictionary with review data
        """
        params = {
            "state": state.upper(),
            "limit": min(limit, 25)
        }

        logger.info(f"Fetching reviews for school ID: {school_id}")
        endpoint = f"/{self.API_VERSION}/{state.upper()}/{school_id}/reviews"
        return await self._make_request(endpoint, params)

    async def search_schools_by_name(
        self,
        school_name: str,
        state: str,
        city: Optional[str] = None,
        limit: int = 10
    ) -> Dict[str, Any]:
        """
        Search for schools by name.

        Args:
            school_name: School name to search for
            state: Two-letter state code
            city: Optional city to narrow search
            limit: Maximum number of results

        Returns:
            Dictionary with matching schools
        """
        params = {
            "q": school_name,
            "state": state.upper(),
            "limit": min(limit, 25)
        }

        if city:
            params["city"] = city

        logger.info(f"Searching for schools named '{school_name}' in {state}")
        endpoint = f"/{self.API_VERSION}/search"
        return await self._make_request(endpoint, params)


# Singleton instance for easy access
_client: Optional[GreatSchoolsClient] = None


def get_greatschools_client() -> GreatSchoolsClient:
    """
    Get or create the GreatSchools API client singleton instance.

    Returns:
        GreatSchoolsClient instance
    """
    global _client
    if _client is None:
        _client = GreatSchoolsClient()
    return _client


async def close_greatschools_client():
    """Close the GreatSchools API client connection."""
    global _client
    if _client is not None:
        await _client.close()
        _client = None
