"""
Status State Machine

Defines valid status transitions and validates them.
"""
from typing import Dict, Set, Optional
from .enums import (
    BuilderStatus,
    CommunityDevelopmentStatus,
    CommunityAvailabilityStatus,
    PropertyListingStatus,
    PropertyVisibilityStatus
)


class InvalidStatusTransitionError(Exception):
    """Raised when an invalid status transition is attempted."""
    pass


class StatusStateMachine:
    """
    Defines and validates status transitions.

    Prevents invalid state changes (e.g., out_of_business -> active).
    """

    # Builder status transitions
    BUILDER_TRANSITIONS: Dict[BuilderStatus, Set[BuilderStatus]] = {
        BuilderStatus.ACTIVE: {
            BuilderStatus.INACTIVE,
            BuilderStatus.OUT_OF_BUSINESS,
            BuilderStatus.SUSPENDED,
            BuilderStatus.MERGED
        },
        BuilderStatus.INACTIVE: {
            BuilderStatus.ACTIVE,
            BuilderStatus.OUT_OF_BUSINESS,
            BuilderStatus.MERGED
        },
        BuilderStatus.SUSPENDED: {
            BuilderStatus.ACTIVE,
            BuilderStatus.OUT_OF_BUSINESS
        },
        BuilderStatus.OUT_OF_BUSINESS: set(),  # Terminal state
        BuilderStatus.MERGED: set()  # Terminal state
    }

    # Community development status transitions
    COMMUNITY_DEV_TRANSITIONS: Dict[CommunityDevelopmentStatus, Set[CommunityDevelopmentStatus]] = {
        CommunityDevelopmentStatus.PLANNED: {
            CommunityDevelopmentStatus.UNDER_DEVELOPMENT,
            CommunityDevelopmentStatus.INACTIVE
        },
        CommunityDevelopmentStatus.UNDER_DEVELOPMENT: {
            CommunityDevelopmentStatus.ACTIVE,
            CommunityDevelopmentStatus.INACTIVE
        },
        CommunityDevelopmentStatus.ACTIVE: {
            CommunityDevelopmentStatus.SOLD_OUT,
            CommunityDevelopmentStatus.INACTIVE
        },
        CommunityDevelopmentStatus.SOLD_OUT: {
            CommunityDevelopmentStatus.ACTIVE,  # Can reopen
            CommunityDevelopmentStatus.INACTIVE
        },
        CommunityDevelopmentStatus.INACTIVE: {
            CommunityDevelopmentStatus.ACTIVE  # Can reactivate
        }
    }

    # Community availability status transitions
    COMMUNITY_AVAIL_TRANSITIONS: Dict[CommunityAvailabilityStatus, Set[CommunityAvailabilityStatus]] = {
        CommunityAvailabilityStatus.AVAILABLE: {
            CommunityAvailabilityStatus.LIMITED_AVAILABILITY,
            CommunityAvailabilityStatus.SOLD_OUT,
            CommunityAvailabilityStatus.CLOSED
        },
        CommunityAvailabilityStatus.LIMITED_AVAILABILITY: {
            CommunityAvailabilityStatus.AVAILABLE,
            CommunityAvailabilityStatus.SOLD_OUT,
            CommunityAvailabilityStatus.CLOSED
        },
        CommunityAvailabilityStatus.SOLD_OUT: {
            CommunityAvailabilityStatus.AVAILABLE,  # Can add more inventory
            CommunityAvailabilityStatus.LIMITED_AVAILABILITY,
            CommunityAvailabilityStatus.CLOSED
        },
        CommunityAvailabilityStatus.CLOSED: {
            CommunityAvailabilityStatus.AVAILABLE  # Can reopen
        }
    }

    # Property listing status transitions
    PROPERTY_LISTING_TRANSITIONS: Dict[PropertyListingStatus, Set[PropertyListingStatus]] = {
        PropertyListingStatus.AVAILABLE: {
            PropertyListingStatus.PENDING,
            PropertyListingStatus.RESERVED,
            PropertyListingStatus.UNDER_CONTRACT,
            PropertyListingStatus.OFF_MARKET
        },
        PropertyListingStatus.PENDING: {
            PropertyListingStatus.AVAILABLE,
            PropertyListingStatus.RESERVED,
            PropertyListingStatus.UNDER_CONTRACT,
            PropertyListingStatus.OFF_MARKET
        },
        PropertyListingStatus.RESERVED: {
            PropertyListingStatus.AVAILABLE,
            PropertyListingStatus.UNDER_CONTRACT,
            PropertyListingStatus.OFF_MARKET
        },
        PropertyListingStatus.UNDER_CONTRACT: {
            PropertyListingStatus.AVAILABLE,  # Can fall through
            PropertyListingStatus.SOLD,
            PropertyListingStatus.OFF_MARKET
        },
        PropertyListingStatus.SOLD: {
            PropertyListingStatus.OFF_MARKET  # Can only go off-market after sold
        },
        PropertyListingStatus.OFF_MARKET: {
            PropertyListingStatus.AVAILABLE  # Can relist
        }
    }

    # Property visibility status transitions
    PROPERTY_VISIBILITY_TRANSITIONS: Dict[PropertyVisibilityStatus, Set[PropertyVisibilityStatus]] = {
        PropertyVisibilityStatus.PUBLIC: {
            PropertyVisibilityStatus.PRIVATE,
            PropertyVisibilityStatus.HIDDEN,
            PropertyVisibilityStatus.ARCHIVED
        },
        PropertyVisibilityStatus.PRIVATE: {
            PropertyVisibilityStatus.PUBLIC,
            PropertyVisibilityStatus.HIDDEN,
            PropertyVisibilityStatus.ARCHIVED
        },
        PropertyVisibilityStatus.HIDDEN: {
            PropertyVisibilityStatus.PUBLIC,
            PropertyVisibilityStatus.PRIVATE,
            PropertyVisibilityStatus.ARCHIVED
        },
        PropertyVisibilityStatus.ARCHIVED: {
            PropertyVisibilityStatus.PUBLIC,  # Can unarchive
            PropertyVisibilityStatus.PRIVATE
        }
    }

    @classmethod
    def can_transition_builder(
        cls,
        from_status: BuilderStatus,
        to_status: BuilderStatus
    ) -> bool:
        """Check if builder status transition is valid."""
        return to_status in cls.BUILDER_TRANSITIONS.get(from_status, set())

    @classmethod
    def validate_builder_transition(
        cls,
        from_status: BuilderStatus,
        to_status: BuilderStatus
    ) -> None:
        """Validate builder transition or raise exception."""
        if not cls.can_transition_builder(from_status, to_status):
            raise InvalidStatusTransitionError(
                f"Invalid builder status transition: {from_status.value} -> {to_status.value}"
            )

    @classmethod
    def can_transition_community_dev(
        cls,
        from_status: CommunityDevelopmentStatus,
        to_status: CommunityDevelopmentStatus
    ) -> bool:
        """Check if community development status transition is valid."""
        return to_status in cls.COMMUNITY_DEV_TRANSITIONS.get(from_status, set())

    @classmethod
    def validate_community_dev_transition(
        cls,
        from_status: CommunityDevelopmentStatus,
        to_status: CommunityDevelopmentStatus
    ) -> None:
        """Validate community development transition or raise exception."""
        if not cls.can_transition_community_dev(from_status, to_status):
            raise InvalidStatusTransitionError(
                f"Invalid community development status transition: {from_status.value} -> {to_status.value}"
            )

    @classmethod
    def can_transition_property_listing(
        cls,
        from_status: PropertyListingStatus,
        to_status: PropertyListingStatus
    ) -> bool:
        """Check if property listing status transition is valid."""
        return to_status in cls.PROPERTY_LISTING_TRANSITIONS.get(from_status, set())

    @classmethod
    def validate_property_listing_transition(
        cls,
        from_status: PropertyListingStatus,
        to_status: PropertyListingStatus
    ) -> None:
        """Validate property listing transition or raise exception."""
        if not cls.can_transition_property_listing(from_status, to_status):
            raise InvalidStatusTransitionError(
                f"Invalid property listing status transition: {from_status.value} -> {to_status.value}"
            )

    @classmethod
    def get_allowed_transitions(cls, entity_type: str, current_status: str) -> Set[str]:
        """
        Get list of allowed transitions for a given entity and status.

        Args:
            entity_type: 'builder', 'community_dev', 'community_avail', 'property_listing', 'property_visibility'
            current_status: Current status value

        Returns:
            Set of allowed next status values
        """
        transition_maps = {
            'builder': cls.BUILDER_TRANSITIONS,
            'community_dev': cls.COMMUNITY_DEV_TRANSITIONS,
            'community_avail': cls.COMMUNITY_AVAIL_TRANSITIONS,
            'property_listing': cls.PROPERTY_LISTING_TRANSITIONS,
            'property_visibility': cls.PROPERTY_VISIBILITY_TRANSITIONS
        }

        transition_map = transition_maps.get(entity_type)
        if not transition_map:
            return set()

        # Find the enum key that matches the status string
        for status_enum, allowed_statuses in transition_map.items():
            if status_enum.value == current_status:
                return {s.value for s in allowed_statuses}

        return set()
