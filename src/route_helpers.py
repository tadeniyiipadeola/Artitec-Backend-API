# src/route_helpers.py
"""
Helper utilities for FastAPI routes to work with public IDs.
Provides consistent lookup, validation, and error handling across all routes.
"""

from typing import Optional, Type, TypeVar
from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from model.user import Users
from model.profiles.buyer import BuyerProfile
from model.profiles.builder import BuilderProfile
from model.profiles.community import Community
from model.profiles.community_admin_profile import CommunityAdminProfile
from model.profiles.sales_rep import SalesRep

from src.id_generator import validate_public_id, PREFIX_MAP


T = TypeVar('T')


# =============================================================================
# User Lookups
# =============================================================================

def get_user_by_public_id(db: Session, user_id: str) -> Users:
    """
    Get user by user_id (e.g., USR-1699564234-A7K9M2).

    Args:
        db: Database session
        user_id: User user_id (USR-xxx)

    Returns:
        Users model instance

    Raises:
        HTTPException 400: Invalid user ID format
        HTTPException 404: User not found
    """
    if not validate_public_id(user_id, PREFIX_MAP["user"]):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid user ID format. Expected format: USR-TIMESTAMP-RANDOM"
        )

    user = db.query(Users).filter(Users.user_id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User {user_id} not found"
        )

    return user


# =============================================================================
# Buyer Profile Lookups
# =============================================================================

def get_buyer_by_public_id(db: Session, buyer_id: str) -> BuyerProfile:
    """
    Get buyer profile by buyer_id (e.g., BYR-1699564234-A7K9M2).

    Args:
        db: Database session
        buyer_id: Buyer profile buyer_id (BYR-xxx)

    Returns:
        BuyerProfile model instance

    Raises:
        HTTPException 400: Invalid buyer ID format
        HTTPException 404: Buyer profile not found
    """
    if not validate_public_id(buyer_id, PREFIX_MAP["buyer"]):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid buyer ID format. Expected format: BYR-TIMESTAMP-RANDOM"
        )

    buyer = db.query(BuyerProfile).filter(BuyerProfile.buyer_id == buyer_id).first()
    if not buyer:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Buyer profile {buyer_id} not found"
        )

    return buyer


def get_buyer_by_user_id(db: Session, user_id: str) -> BuyerProfile:
    """
    Get buyer profile by user's user_id.

    Args:
        db: Database session
        user_id: User user_id (USR-xxx)

    Returns:
        BuyerProfile model instance

    Raises:
        HTTPException 404: User or buyer profile not found
    """
    user = get_user_by_public_id(db, user_id)

    buyer = db.query(BuyerProfile).filter(BuyerProfile.user_id == user.user_id).first()
    if not buyer:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Buyer profile not found for user {user_id}"
        )

    return buyer


# =============================================================================
# Builder Profile Lookups
# =============================================================================

def get_builder_by_public_id(db: Session, builder_id: str) -> BuilderProfile:
    """
    Get builder profile by builder_id (e.g., BLD-1699564234-X3P8Q1).
    """
    if not validate_public_id(builder_id, PREFIX_MAP["builder"]):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid builder ID format. Expected format: BLD-TIMESTAMP-RANDOM"
        )

    builder = db.query(BuilderProfile).filter(BuilderProfile.builder_id == builder_id).first()
    if not builder:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Builder profile {builder_id} not found"
        )

    return builder


def get_builder_by_user_id(db: Session, user_id: str) -> BuilderProfile:
    """Get builder profile by user's user_id."""
    user = get_user_by_public_id(db, user_id)

    builder = db.query(BuilderProfile).filter(BuilderProfile.user_id == user.user_id).first()
    if not builder:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Builder profile not found for user {user_id}"
        )

    return builder


# =============================================================================
# Community Lookups
# =============================================================================

def get_community_by_public_id(db: Session, community_id: str) -> Community:
    """
    Get community by community_id (e.g., CMY-1699564234-Z5R7N4).
    """
    if not validate_public_id(community_id, PREFIX_MAP["community"]):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid community ID format. Expected format: CMY-TIMESTAMP-RANDOM"
        )

    community = db.query(Community).filter(Community.community_id == community_id).first()
    if not community:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Community {community_id} not found"
        )

    return community


# =============================================================================
# Community Admin Profile Lookups
# =============================================================================

def get_community_admin_by_public_id(db: Session, admin_id: str) -> CommunityAdminProfile:
    """
    Get community admin profile by community_admin_id (e.g., CAP-1699564234-M2K9L3).
    """
    if not validate_public_id(admin_id, PREFIX_MAP["community_admin"]):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid community admin ID format. Expected format: CAP-TIMESTAMP-RANDOM"
        )

    admin = db.query(CommunityAdminProfile).filter(CommunityAdminProfile.community_admin_id == admin_id).first()
    if not admin:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Community admin profile {admin_id} not found"
        )

    return admin


# =============================================================================
# Sales Rep Lookups
# =============================================================================

def get_sales_rep_by_public_id(db: Session, rep_id: str) -> SalesRep:
    """
    Get sales rep by sales_rep_id (e.g., SLS-1699564234-P7Q8R9).
    """
    if not validate_public_id(rep_id, PREFIX_MAP["sales_rep"]):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid sales rep ID format. Expected format: SLS-TIMESTAMP-RANDOM"
        )

    rep = db.query(SalesRep).filter(SalesRep.sales_rep_id == rep_id).first()
    if not rep:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Sales rep {rep_id} not found"
        )

    return rep


# =============================================================================
# Generic Lookup (for flexibility)
# =============================================================================

def get_by_public_id(
    db: Session,
    model: Type[T],
    typed_id: str,
    expected_prefix: Optional[str] = None,
    field_name: Optional[str] = None
) -> T:
    """
    Generic lookup by typed ID for any model.

    Args:
        db: Database session
        model: SQLAlchemy model class
        typed_id: The typed ID to search for (e.g., USR-xxx, BYR-xxx)
        expected_prefix: Optional prefix to validate (e.g., "USR", "BYR", "BLD")
        field_name: Optional field name to query (defaults to model's typed ID field)

    Returns:
        Model instance

    Raises:
        HTTPException 400: Invalid ID format
        HTTPException 404: Resource not found
    """
    if expected_prefix and not validate_public_id(typed_id, expected_prefix):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid {model.__tablename__} ID format. Expected prefix: {expected_prefix}"
        )

    # Map model to its typed ID field if not provided
    if field_name is None:
        field_map = {
            'users': 'user_id',
            'buyer_profiles': 'buyer_id',
            'builder_profiles': 'builder_id',
            'communities': 'community_id',
            'community_admin_profiles': 'community_admin_id',
            'sales_reps': 'sales_rep_id',
        }
        field_name = field_map.get(model.__tablename__, 'id')

    instance = db.query(model).filter(getattr(model, field_name) == typed_id).first()
    if not instance:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"{model.__name__} {typed_id} not found"
        )

    return instance


# =============================================================================
# Response Builders
# =============================================================================

def build_buyer_profile_response(buyer: BuyerProfile, user: Users) -> dict:
    """
    Build buyer profile response combining buyer and user data.
    Returns buyer_id as 'id' field for API consistency.
    """
    return {
        # Primary fields - use buyer_id as id
        "id": buyer.buyer_id,  # BYR-xxx (NOT internal DB id)
        "buyer_id": buyer.buyer_id,  # BYR-xxx
        "user_id": user.user_id,  # USR-xxx

        # Social engagement
        "followers_count": buyer.followers_count,

        # Identity / display
        "display_name": buyer.display_name,
        "first_name": buyer.first_name or user.first_name,
        "last_name": buyer.last_name or user.last_name,
        "profile_image": buyer.profile_image,
        "bio": buyer.bio,
        "location": buyer.location,
        "website_url": buyer.website_url,

        # Contact - Canonical fields
        "email": buyer.email or user.email,
        "phone": buyer.phone,
        "phone_e164": user.phone_e164,

        # Contact - Legacy fields
        "contact_email": buyer.contact_email,
        "contact_phone": buyer.contact_phone,
        "contact_preferred": buyer.contact_preferred,

        # Address
        "address": buyer.address,
        "city": buyer.city,
        "state": buyer.state,
        "zip_code": buyer.zip_code,

        # Core attributes
        "sex": buyer.sex,
        "timeline": buyer.timeline,

        # Financing snapshot
        "financing_status": buyer.financing_status,
        "loan_program": buyer.loan_program,
        "household_income_usd": buyer.household_income_usd,
        "budget_min_usd": buyer.budget_min_usd,
        "budget_max_usd": buyer.budget_max_usd,
        "down_payment_percent": buyer.down_payment_percent,
        "lender_name": buyer.lender_name,
        "agent_name": buyer.agent_name,

        # Flexible metadata
        "extra": buyer.extra,

        # Timestamps
        "created_at": buyer.created_at,
        "updated_at": buyer.updated_at,
    }


# =============================================================================
# Exports
# =============================================================================

__all__ = [
    # User
    "get_user_by_public_id",

    # Buyer
    "get_buyer_by_public_id",
    "get_buyer_by_user_id",

    # Builder
    "get_builder_by_public_id",
    "get_builder_by_user_id",

    # Community
    "get_community_by_public_id",

    # Community Admin
    "get_community_admin_by_public_id",

    # Sales Rep
    "get_sales_rep_by_public_id",

    # Generic
    "get_by_public_id",

    # Response Builders
    "build_buyer_profile_response",
]
