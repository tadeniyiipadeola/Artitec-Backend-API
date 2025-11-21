# routes/admin/teams.py
"""
Enterprise builder team member management endpoints.
Handles team member listing, updates, and invitations.
"""
from datetime import datetime, timedelta
from typing import List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
import logging

from config.db import get_db
from config.dependencies import require_user
from model.user import Users
from model.enterprise import EnterpriseInvitation, BuilderTeamMember, _gen_invitation_code
from src.schemas import (
    InvitationOut,
    TeamMemberOut,
    TeamMemberCreateIn,
    TeamMemberUpdateIn,
    UserOut,
    RoleOut,
)

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get(
    "/builders/{builder_id}/team",
    response_model=List[TeamMemberOut],
    responses={
        200: {"description": "List of team members"},
        403: {"description": "Forbidden - Not authorized"},
        404: {"description": "Builder not found"}
    }
)
def list_team_members(
    builder_id: str,
    db: Session = Depends(get_db),
    current_user: Users = Depends(require_user)
):
    """
    List all team members for a builder.

    Returns team members with their roles, permissions, and community assignments.
    **Requires builder admin or platform admin role**
    """
    logger.info(
        "User %s listing team members for builder %s",
        current_user.user_id,
        builder_id
    )

    # Check authorization: Must be builder admin/team member OR platform admin
    is_platform_admin = current_user.role == "admin"
    is_builder_member = db.query(BuilderTeamMember).filter(
        BuilderTeamMember.builder_id == builder_id,
        BuilderTeamMember.user_id == current_user.user_id,
        BuilderTeamMember.role.in_(["admin", "manager"])
    ).first()

    if not (is_platform_admin or is_builder_member):
        raise HTTPException(
            status_code=403,
            detail="Not authorized to view team members"
        )

    # Get all team members
    team_members = db.query(BuilderTeamMember).filter(
        BuilderTeamMember.builder_id == builder_id
    ).all()

    # Convert to response models with user info
    result = []
    for member in team_members:
        user = db.query(Users).filter(Users.user_id == member.user_id).first()
        user_out = None
        if user:
            user_out = UserOut(
                public_id=user.user_id,
                first_name=user.first_name,
                last_name=user.last_name,
                email=user.email,
                phone_e164=user.phone_e164,
                role=RoleOut(key=user.role, name=user.role.replace("_", " ").title()) if user.role else None,
                is_email_verified=user.is_email_verified,
                onboarding_completed=user.onboarding_completed,
                plan_tier=user.plan_tier,
                created_at=user.created_at,
                updated_at=user.updated_at
            )

        member_out = TeamMemberOut(
            id=member.id,
            builder_id=member.builder_id,
            user_id=member.user_id,
            role=member.role,
            permissions=member.permissions,
            communities_assigned=member.communities_assigned,
            is_active=member.is_active,
            created_at=member.created_at,
            user=user_out
        )
        result.append(member_out)

    logger.info(
        "Found %d team members for builder %s",
        len(result),
        builder_id
    )

    return result


@router.patch(
    "/builders/{builder_id}/team/{user_id}",
    response_model=TeamMemberOut,
    responses={
        200: {"description": "Team member updated"},
        403: {"description": "Forbidden - Not authorized"},
        404: {"description": "Team member not found"}
    }
)
def update_team_member(
    builder_id: str,
    user_id: str,
    body: TeamMemberUpdateIn,
    db: Session = Depends(get_db),
    current_user: Users = Depends(require_user)
):
    """
    Update team member role, permissions, or community assignments.

    **Requires builder admin or platform admin role**
    """
    logger.info(
        "User %s updating team member %s for builder %s",
        current_user.user_id,
        user_id,
        builder_id
    )

    # Check authorization
    is_platform_admin = current_user.role == "admin"
    is_builder_admin = db.query(BuilderTeamMember).filter(
        BuilderTeamMember.builder_id == builder_id,
        BuilderTeamMember.user_id == current_user.user_id,
        BuilderTeamMember.role == "admin"
    ).first()

    if not (is_platform_admin or is_builder_admin):
        raise HTTPException(
            status_code=403,
            detail="Not authorized to update team members"
        )

    # Find team member
    team_member = db.query(BuilderTeamMember).filter(
        BuilderTeamMember.builder_id == builder_id,
        BuilderTeamMember.user_id == user_id
    ).first()

    if not team_member:
        raise HTTPException(
            status_code=404,
            detail="Team member not found"
        )

    try:
        # Update fields
        if body.role is not None:
            team_member.role = body.role
        if body.permissions is not None:
            team_member.permissions = body.permissions
        if body.communities_assigned is not None:
            team_member.communities_assigned = body.communities_assigned
        if body.is_active is not None:
            team_member.is_active = body.is_active

        db.commit()
        db.refresh(team_member)

        logger.info(
            "Updated team member %s: role=%s, communities=%s",
            user_id,
            team_member.role,
            len(team_member.communities_assigned) if team_member.communities_assigned else "all"
        )

        # Get user info
        user = db.query(Users).filter(Users.user_id == team_member.user_id).first()
        user_out = None
        if user:
            user_out = UserOut(
                public_id=user.user_id,
                first_name=user.first_name,
                last_name=user.last_name,
                email=user.email,
                phone_e164=user.phone_e164,
                role=RoleOut(key=user.role, name=user.role.replace("_", " ").title()) if user.role else None,
                is_email_verified=user.is_email_verified,
                onboarding_completed=user.onboarding_completed,
                plan_tier=user.plan_tier,
                created_at=user.created_at,
                updated_at=user.updated_at
            )

        return TeamMemberOut(
            id=team_member.id,
            builder_id=team_member.builder_id,
            user_id=team_member.user_id,
            role=team_member.role,
            permissions=team_member.permissions,
            communities_assigned=team_member.communities_assigned,
            is_active=team_member.is_active,
            created_at=team_member.created_at,
            user=user_out
        )

    except Exception as e:
        db.rollback()
        logger.error(
            "Failed to update team member: %s",
            str(e),
            exc_info=True
        )
        raise HTTPException(
            status_code=500,
            detail=f"Failed to update team member: {str(e)}"
        )


@router.post(
    "/builders/{builder_id}/team/invite",
    response_model=InvitationOut,
    responses={
        201: {"description": "Team member invitation created"},
        403: {"description": "Forbidden - Not authorized"},
        409: {"description": "Conflict - Email already invited or is team member"}
    }
)
def invite_team_member(
    builder_id: str,
    body: TeamMemberCreateIn,
    db: Session = Depends(get_db),
    current_user: Users = Depends(require_user)
):
    """
    Invite a new team member to the builder's team.

    Creates an invitation for additional team members (sales reps, managers, viewers).
    Can assign to specific communities or grant access to all.

    **Requires builder admin/manager or platform admin role**
    """
    logger.info(
        "User %s inviting team member %s to builder %s",
        current_user.user_id,
        body.invited_email,
        builder_id
    )

    # Check authorization
    is_platform_admin = current_user.role == "admin"
    team_member = db.query(BuilderTeamMember).filter(
        BuilderTeamMember.builder_id == builder_id,
        BuilderTeamMember.user_id == current_user.user_id
    ).first()

    can_invite = is_platform_admin or (
        team_member and team_member.can_invite_members
    )

    if not can_invite:
        raise HTTPException(
            status_code=403,
            detail="Not authorized to invite team members"
        )

    # Check if email already has pending invitation
    existing_invitation = db.query(EnterpriseInvitation).filter(
        EnterpriseInvitation.builder_id == builder_id,
        EnterpriseInvitation.invited_email == body.invited_email,
        EnterpriseInvitation.status == "pending"
    ).first()

    if existing_invitation:
        raise HTTPException(
            status_code=409,
            detail="This email already has a pending invitation"
        )

    # Check if user is already a team member
    user = db.query(Users).filter(Users.email == body.invited_email).first()
    if user:
        existing_member = db.query(BuilderTeamMember).filter(
            BuilderTeamMember.builder_id == builder_id,
            BuilderTeamMember.user_id == user.user_id
        ).first()
        if existing_member:
            raise HTTPException(
                status_code=409,
                detail="This user is already a team member"
            )

    try:
        # Create invitation
        invitation_code = _gen_invitation_code()
        expires_at = datetime.utcnow() + timedelta(days=body.invitation_expires_days)

        invitation = EnterpriseInvitation(
            invitation_code=invitation_code,
            builder_id=builder_id,
            invited_email=body.invited_email,
            invited_role=body.invited_role,
            invited_first_name=body.invited_first_name,
            invited_last_name=body.invited_last_name,
            created_by_user_id=current_user.user_id,
            expires_at=expires_at,
            status="pending",
            custom_message=body.custom_message
        )
        db.add(invitation)
        db.commit()
        db.refresh(invitation)

        logger.info(
            "Created team member invitation: code=%s, email=%s, communities=%s",
            invitation_code,
            body.invited_email,
            len(body.communities_assigned) if body.communities_assigned else "all"
        )

        return InvitationOut(
            invitation_code=invitation.invitation_code,
            builder_id=invitation.builder_id,
            invited_email=invitation.invited_email,
            invited_role=invitation.invited_role,
            invited_first_name=invitation.invited_first_name,
            invited_last_name=invitation.invited_last_name,
            expires_at=invitation.expires_at,
            status=invitation.status,
            custom_message=invitation.custom_message,
            created_at=invitation.created_at
        )

    except Exception as e:
        db.rollback()
        logger.error(
            "Failed to create team member invitation: %s",
            str(e),
            exc_info=True
        )
        raise HTTPException(
            status_code=500,
            detail=f"Failed to create invitation: {str(e)}"
        )
