"""
Status Enums

Defines all possible status values for entities.
"""
from enum import Enum


class BuilderStatus(str, Enum):
    """Builder business status values."""
    ACTIVE = "active"
    INACTIVE = "inactive"
    OUT_OF_BUSINESS = "out_of_business"
    MERGED = "merged"
    SUSPENDED = "suspended"  # Temporarily suspended by admin


class CommunityDevelopmentStatus(str, Enum):
    """Community development phase status."""
    PLANNED = "planned"
    UNDER_DEVELOPMENT = "under_development"
    ACTIVE = "active"
    SOLD_OUT = "sold_out"
    INACTIVE = "inactive"


class CommunityAvailabilityStatus(str, Enum):
    """Community lot/home availability status."""
    AVAILABLE = "available"
    LIMITED_AVAILABILITY = "limited_availability"
    SOLD_OUT = "sold_out"
    CLOSED = "closed"


class PropertyListingStatus(str, Enum):
    """Property listing/sales status."""
    AVAILABLE = "available"
    PENDING = "pending"
    RESERVED = "reserved"
    UNDER_CONTRACT = "under_contract"
    SOLD = "sold"
    OFF_MARKET = "off_market"


class PropertyVisibilityStatus(str, Enum):
    """Property visibility status."""
    PUBLIC = "public"
    PRIVATE = "private"
    HIDDEN = "hidden"
    ARCHIVED = "archived"
