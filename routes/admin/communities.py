# routes/admin/communities.py
"""
Enterprise builder community management endpoints.
Handles community listings and assignments for enterprise builders.
"""
from typing import List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import select, func as sql_func
import logging

from config.db import get_db
from config.dependencies import require_user
from model.user import Users
from model.profiles.builder import BuilderProfile
from model.profiles.community import Community
from model.property.property import Property
from model.enterprise import BuilderTeamMember
from src.schemas import (
    CommunityOut,
    BuilderCommunityListOut,
)

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get(
    "/communities/available",
    response_model=List[CommunityOut],
    responses={
        200: {"description": "List of available communities"},
        403: {"description": "Forbidden - Admin access required"}
    }
)
def list_available_communities(
    db: Session = Depends(get_db),
    current_user: Users = Depends(require_user)
):
    """
    List all available communities for enterprise builder provisioning.

    Returns all communities in the system that can be assigned to builders.
    Used by the admin form to populate community selection dropdown.

    **Requires admin role**
    """
    logger.info(
        "User %s fetching available communities for builder provisioning",
        current_user.user_id
    )

    # Authorization check: Only admins can view all communities for provisioning
    if current_user.role != "admin":
        logger.warning(
            "Non-admin user %s attempted to fetch available communities",
            current_user.user_id
        )
        raise HTTPException(
            status_code=403,
            detail="Only administrators can view available communities"
        )

    try:
        # Get all communities ordered by name
        communities = db.query(Community).order_by(Community.name).all()

        # Convert to response models
        community_list = []
        for community in communities:
            community_list.append(CommunityOut(
                community_id=community.community_id,
                name=community.name,
                city=community.city,
                state=community.state,
                property_count=0,  # Not needed for selection list
                active_status="active"
            ))

        logger.info(
            "Returning %d available communities",
            len(community_list)
        )

        return community_list

    except Exception as e:
        logger.error(
            "Failed to fetch available communities: %s",
            str(e),
            exc_info=True
        )
        raise HTTPException(
            status_code=500,
            detail=f"Failed to fetch available communities: {str(e)}"
        )


@router.get(
    "/builders/{builder_id}/communities",
    response_model=BuilderCommunityListOut,
    responses={
        200: {"description": "List of builder communities"},
        403: {"description": "Forbidden - Not authorized"},
        404: {"description": "Builder not found"}
    }
)
def list_builder_communities(
    builder_id: str,
    db: Session = Depends(get_db),
    current_user: Users = Depends(require_user)
):
    """
    List all communities where the builder is active.

    Returns communities with property counts and active status.
    **Requires builder team member or platform admin role**
    """
    logger.info(
        "User %s listing communities for builder %s",
        current_user.user_id,
        builder_id
    )

    # Check authorization
    is_platform_admin = current_user.role == "admin"
    is_builder_member = db.query(BuilderTeamMember).filter(
        BuilderTeamMember.builder_id == builder_id,
        BuilderTeamMember.user_id == current_user.user_id
    ).first()

    if not (is_platform_admin or is_builder_member):
        raise HTTPException(
            status_code=403,
            detail="Not authorized to view builder communities"
        )

    # Get builder
    builder = db.query(BuilderProfile).filter(
        BuilderProfile.builder_id == builder_id
    ).first()

    if not builder:
        raise HTTPException(
            status_code=404,
            detail="Builder not found"
        )

    # Get communities through builder_communities association
    from model.profiles.builder import builder_communities as bc_table

    try:
        # Get communities with property counts
        stmt = select(
            Community,
            sql_func.count(Property.id).label("property_count")
        ).join(
            bc_table,
            bc_table.c.community_id == Community.id
        ).outerjoin(
            Property,
            (Property.community_id == Community.community_id) &
            (Property.builder_id == builder_id)
        ).where(
            bc_table.c.builder_id == builder.id
        ).group_by(Community.id)

        results = db.execute(stmt).all()

        communities = []
        for community, prop_count in results:
            communities.append(CommunityOut(
                community_id=community.community_id,
                name=community.name,
                city=community.city,
                state=community.state,
                property_count=int(prop_count) if prop_count else 0,
                active_status="active"
            ))

        logger.info(
            "Found %d communities for builder %s",
            len(communities),
            builder_id
        )

        return BuilderCommunityListOut(
            builder_id=builder_id,
            builder_name=builder.name,
            communities=communities,
            total_communities=len(communities)
        )
    except Exception as e:
        logger.error(
            "Failed to list builder communities: %s",
            str(e),
            exc_info=True
        )
        raise HTTPException(
            status_code=500,
            detail=f"Failed to list builder communities: {str(e)}"
        )
