# routes/enterprise.py
"""
Enterprise builder provisioning and team management endpoints.
Admin-initiated enterprise builder account creation for companies like Perry Homes.
"""
from datetime import datetime, timedelta
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import text
import logging

from config.db import get_db
from config.dependencies import require_user
from model.user import Users, SessionToken
from model.profiles.builder import BuilderProfile
from model.enterprise import EnterpriseInvitation, BuilderTeamMember, _gen_invitation_code
from src.schemas import (
    EnterpriseBuilderProvisionIn,
    EnterpriseBuilderProvisionOut,
    InvitationValidateOut,
    InvitationAcceptIn,
    InvitationOut,
    InvitationDetailedOut,
    InvitationListOut,
    BuilderProfileOut,
    UserOut,
    RoleOut,
    AdminUserOut,
    AdminRoleOut,
    TeamMemberOut,
    TeamMemberCreateIn,
    TeamMemberUpdateIn,
    CommunityOut,
    BuilderCommunityListOut,
    AdminStatsOut,
    AdminStatsTotals,
    AdminStatsPeriod,
    AdminAuditLogOut,
    GrowthDataPoint,
    GrowthTimeSeriesOut,
)
from src.id_generator import generate_user_id, generate_builder_id
from src.utils import hash_password

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post(
    "/builders/enterprise/provision",
    response_model=EnterpriseBuilderProvisionOut,
    responses={
        201: {"description": "Enterprise builder account created successfully"},
        400: {"description": "Bad Request - Invalid input"},
        403: {"description": "Forbidden - Admin access required"},
        409: {"description": "Conflict - Email already in use"},
        500: {"description": "Internal Server Error"}
    }
)
def provision_enterprise_builder(
    body: EnterpriseBuilderProvisionIn,
    db: Session = Depends(get_db),
    current_user: Users = Depends(require_user)
):
    """
    Admin-initiated enterprise builder account provisioning.

    Creates:
    1. User account (with role='builder', plan_tier='enterprise')
    2. Builder profile
    3. Invitation code for primary contact

    Workflow:
    - Admin provides company details and primary contact info
    - System creates builder profile and user account
    - Invitation code sent to primary contact email
    - Contact registers/logs in and accepts invitation to activate account
    - After activation, can invite additional team members

    **Requires admin role**
    """
    logger.info(
        "Enterprise builder provisioning initiated by user_id=%s for company=%s",
        current_user.user_id,
        body.company_name
    )

    # Authorization check: Only admins can provision enterprise builders
    if current_user.role != "admin":
        logger.warning(
            "Non-admin user %s attempted to provision enterprise builder",
            current_user.user_id
        )
        raise HTTPException(
            status_code=403,
            detail="Only administrators can provision enterprise builder accounts"
        )

    # Check if email already exists
    existing_user = db.query(Users).filter(Users.email == body.primary_contact_email).first()
    if existing_user:
        logger.warning(
            "Email already in use: %s",
            body.primary_contact_email
        )
        raise HTTPException(
            status_code=409,
            detail=f"Email {body.primary_contact_email} is already registered"
        )

    try:
        # 1. Create user account (without password - will be set when invitation is accepted)
        user_id = generate_user_id()
        new_user = Users(
            user_id=user_id,
            email=body.primary_contact_email,
            first_name=body.primary_contact_first_name,
            last_name=body.primary_contact_last_name,
            phone_e164=body.primary_contact_phone,
            role="builder",
            plan_tier=body.plan_tier,
            is_email_verified=False,  # Will verify when they accept invitation
            onboarding_completed=False
        )
        db.add(new_user)
        db.flush()  # Get the new_user.id

        logger.info("Created user account: user_id=%s, email=%s", user_id, body.primary_contact_email)

        # 2. Create builder profile
        builder_id = generate_builder_id()
        builder_profile = BuilderProfile(
            builder_id=builder_id,
            user_id=user_id,
            name=body.company_name,
            website=body.website_url,
            address=body.company_address,
            verified=1,  # Enterprise builders are pre-verified
        )
        db.add(builder_profile)
        db.flush()

        logger.info("Created builder profile: builder_id=%s, name=%s", builder_id, body.company_name)

        # 2b. Associate builder with communities (if provided)
        if body.community_ids:
            from model.profiles.community import Community
            from model.profiles.builder import builder_communities as bc_table

            # Find communities by community_id
            communities = db.query(Community).filter(
                Community.community_id.in_(body.community_ids)
            ).all()

            if communities:
                # Insert into builder_communities junction table
                for community in communities:
                    stmt = bc_table.insert().values(
                        builder_id=builder_profile.id,  # Internal ID
                        community_id=community.id  # Internal ID
                    )
                    db.execute(stmt)

                logger.info(
                    "Associated builder %s with %d communities: %s",
                    builder_id,
                    len(communities),
                    [c.community_id for c in communities]
                )
            else:
                logger.warning(
                    "No communities found for provided community_ids: %s",
                    body.community_ids
                )

        # 3. Create invitation
        invitation_code = _gen_invitation_code()
        expires_at = datetime.utcnow() + timedelta(days=body.invitation_expires_days)

        invitation = EnterpriseInvitation(
            invitation_code=invitation_code,
            builder_id=builder_id,
            invited_email=body.primary_contact_email,
            invited_role="builder",
            invited_first_name=body.primary_contact_first_name,
            invited_last_name=body.primary_contact_last_name,
            created_by_user_id=current_user.user_id,
            expires_at=expires_at,
            status="pending",
            custom_message=body.custom_message
        )
        db.add(invitation)
        db.commit()

        logger.info(
            "Created invitation: code=%s, builder_id=%s, expires_at=%s",
            invitation_code,
            builder_id,
            expires_at
        )

        # 4. Build response
        # Refresh objects to get all fields
        db.refresh(new_user)
        db.refresh(builder_profile)
        db.refresh(invitation)

        # Convert to response models
        user_out = UserOut(
            public_id=new_user.user_id,
            first_name=new_user.first_name,
            last_name=new_user.last_name,
            email=new_user.email,
            phone_e164=new_user.phone_e164,
            role=RoleOut(key=new_user.role, name="Builder"),
            is_email_verified=new_user.is_email_verified,
            onboarding_completed=new_user.onboarding_completed,
            plan_tier=new_user.plan_tier,
            created_at=new_user.created_at,
            updated_at=new_user.updated_at
        )

        builder_out = BuilderProfileOut(
            builder_id=builder_profile.builder_id,
            name=builder_profile.name,
            website=builder_profile.website,
            verified=builder_profile.verified,
            created_at=builder_profile.created_at
        )

        invitation_out = InvitationOut(
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

        response = EnterpriseBuilderProvisionOut(
            builder=builder_out,
            user=user_out,
            invitation=invitation_out,
            message="Enterprise builder account created successfully",
            next_steps=[
                f"Send invitation code {invitation_code} to {body.primary_contact_email}",
                "User must register/login and accept invitation to activate account",
                "After activation, user can invite additional team members",
                f"Invitation expires on {expires_at.strftime('%Y-%m-%d %H:%M UTC')}"
            ]
        )

        logger.info(
            "Enterprise builder provisioning completed successfully: builder_id=%s, user_id=%s",
            builder_id,
            user_id
        )

        return response

    except Exception as e:
        db.rollback()
        logger.error(
            "Failed to provision enterprise builder: %s",
            str(e),
            exc_info=True
        )
        raise HTTPException(
            status_code=500,
            detail=f"Failed to create enterprise builder account: {str(e)}"
        )


@router.get(
    "/invitations/{invitation_code}/validate",
    response_model=InvitationValidateOut,
    responses={
        200: {"description": "Invitation validation result"},
        404: {"description": "Invitation not found"}
    }
)
def validate_invitation(
    invitation_code: str,
    db: Session = Depends(get_db)
):
    """
    Validate an invitation code and return invitation details.

    Public endpoint - no authentication required.
    Used when user clicks invitation link or enters code during registration.
    """
    logger.info("Validating invitation code: %s", invitation_code[:4] + "...")

    # Find invitation
    invitation = db.query(EnterpriseInvitation).filter(
        EnterpriseInvitation.invitation_code == invitation_code
    ).first()

    if not invitation:
        logger.warning("Invitation not found: %s", invitation_code[:4] + "...")
        return InvitationValidateOut(
            valid=False,
            invitation_code=invitation_code,
            error_message="Invitation code not found"
        )

    # Check if invitation is valid
    if not invitation.is_valid():
        error_msg = None
        if invitation.status == "used":
            error_msg = "This invitation has already been used"
        elif invitation.status == "expired":
            error_msg = "This invitation has expired"
        elif invitation.status == "revoked":
            error_msg = "This invitation has been revoked"
        elif invitation.expires_at < datetime.utcnow():
            error_msg = f"This invitation expired on {invitation.expires_at.strftime('%Y-%m-%d')}"
        else:
            error_msg = "This invitation is not valid"

        logger.info(
            "Invalid invitation: code=%s, status=%s, error=%s",
            invitation_code[:4] + "...",
            invitation.status,
            error_msg
        )

        return InvitationValidateOut(
            valid=False,
            invitation_code=invitation_code,
            error_message=error_msg
        )

    # Get builder name
    builder = db.query(BuilderProfile).filter(
        BuilderProfile.builder_id == invitation.builder_id
    ).first()

    builder_name = builder.name if builder else None

    logger.info(
        "Valid invitation: code=%s, builder=%s, email=%s",
        invitation_code[:4] + "...",
        builder_name,
        invitation.invited_email
    )

    return InvitationValidateOut(
        valid=True,
        invitation_code=invitation_code,
        builder_name=builder_name,
        invited_email=invitation.invited_email,
        invited_role=invitation.invited_role,
        expires_at=invitation.expires_at,
        custom_message=invitation.custom_message
    )


@router.post(
    "/invitations/accept",
    response_model=dict,
    responses={
        200: {"description": "Invitation accepted successfully"},
        400: {"description": "Bad Request - Invalid invitation or user"},
        403: {"description": "Forbidden - Email mismatch"},
        404: {"description": "Invitation not found"},
        409: {"description": "Conflict - Already a team member"}
    }
)
def accept_invitation(
    body: InvitationAcceptIn,
    db: Session = Depends(get_db),
    current_user: Users = Depends(require_user)
):
    """
    Accept an enterprise builder invitation.

    Links the authenticated user to the builder's team.
    Creates a BuilderTeamMember record and marks invitation as used.

    **Requires authentication**
    """
    logger.info(
        "User %s attempting to accept invitation %s",
        current_user.user_id,
        body.invitation_code[:4] + "..."
    )

    # Verify user_public_id matches current user
    if body.user_public_id != current_user.user_id:
        raise HTTPException(
            status_code=400,
            detail="User ID mismatch"
        )

    # Find invitation
    invitation = db.query(EnterpriseInvitation).filter(
        EnterpriseInvitation.invitation_code == body.invitation_code
    ).first()

    if not invitation:
        raise HTTPException(
            status_code=404,
            detail="Invitation not found"
        )

    # Validate invitation
    if not invitation.is_valid():
        raise HTTPException(
            status_code=400,
            detail=f"Invitation is not valid (status: {invitation.status})"
        )

    # Verify email matches
    if invitation.invited_email.lower() != current_user.email.lower():
        logger.warning(
            "Email mismatch: invitation=%s, user=%s",
            invitation.invited_email,
            current_user.email
        )
        raise HTTPException(
            status_code=403,
            detail="This invitation is for a different email address"
        )

    # Check if already a team member
    existing_member = db.query(BuilderTeamMember).filter(
        BuilderTeamMember.builder_id == invitation.builder_id,
        BuilderTeamMember.user_id == current_user.user_id
    ).first()

    if existing_member:
        raise HTTPException(
            status_code=409,
            detail="You are already a member of this builder's team"
        )

    try:
        # Create team member record
        team_member = BuilderTeamMember(
            builder_id=invitation.builder_id,
            user_id=current_user.user_id,
            role="admin" if invitation.invited_role == "builder" else invitation.invited_role,
            is_active="active",
            added_by_user_id=invitation.created_by_user_id
        )
        db.add(team_member)

        # Mark invitation as used
        invitation.mark_used(current_user.user_id)

        # Update user's role if needed
        if current_user.role != "builder" and invitation.invited_role == "builder":
            current_user.role = "builder"

        # Mark onboarding as completed
        current_user.onboarding_completed = True

        db.commit()

        logger.info(
            "Invitation accepted successfully: user_id=%s, builder_id=%s, role=%s",
            current_user.user_id,
            invitation.builder_id,
            team_member.role
        )

        return {
            "success": True,
            "message": "Invitation accepted successfully",
            "builder_id": invitation.builder_id,
            "team_member_role": team_member.role
        }

    except Exception as e:
        db.rollback()
        logger.error(
            "Failed to accept invitation: %s",
            str(e),
            exc_info=True
        )
        raise HTTPException(
            status_code=500,
            detail=f"Failed to accept invitation: {str(e)}"
        )


# MARK: - Team Member Management

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


# MARK: - Community Management

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
    from model.profiles.community import Community

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
    from model.profiles.community import Community
    from model.property.property import Property

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
    from sqlalchemy import select, func as sql_func

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


# =============================
# Platform Analytics Endpoints
# =============================

@router.get("/stats", response_model=AdminStatsOut)
def get_admin_stats(
    from_date: Optional[datetime] = Query(None, alias="from", description="Start date for period statistics"),
    to_date: Optional[datetime] = Query(None, alias="to", description="End date for period statistics"),
    db: Session = Depends(get_db)
):
    """
    Get platform statistics for admin analytics dashboard.

    Provides comprehensive counts of users, builders, communities, properties,
    and optionally period-based growth metrics.

    Example:
        GET /v1/admin/stats
        GET /v1/admin/stats?from=2025-10-18T00:00:00Z&to=2025-11-18T00:00:00Z
    """
    try:
        # Get total user count
        result = db.execute(text("SELECT COUNT(*) as count FROM users"))
        total_users = result.fetchone().count

        # Get active users (logged in within last 30 days)
        # Check if last_login_at column exists
        try:
            result = db.execute(text("""
                SELECT COUNT(*) as count FROM users
                WHERE last_login_at >= DATE_SUB(NOW(), INTERVAL 30 DAY)
            """))
            active_users = result.fetchone().count
        except:
            # If last_login_at doesn't exist, use created_at as fallback
            try:
                result = db.execute(text("""
                    SELECT COUNT(*) as count FROM users
                    WHERE created_at >= DATE_SUB(NOW(), INTERVAL 30 DAY)
                """))
                active_users = result.fetchone().count
            except:
                # If that also fails, just use total users
                active_users = total_users

        # Get user role distribution from users table (SINGLE SOURCE OF TRUTH)
        # Use GROUP BY to get all role counts in a single query
        role_counts = {
            'buyer': 0,
            'builder': 0,
            'sales_rep': 0,
            'community': 0,  # Community Point of Contact
            'community_admin': 0,
            'admin': 0
        }

        try:
            result = db.execute(text("""
                SELECT role, COUNT(*) as count
                FROM users
                WHERE role IS NOT NULL AND role != ''
                GROUP BY role
            """))

            for row in result.fetchall():
                role_name = row.role
                role_count = row.count

                # Map role names to our role_counts dictionary
                if role_name in role_counts:
                    role_counts[role_name] = role_count
                else:
                    # Log unknown roles for debugging
                    logger.warning(f"Unknown user role found in database: {role_name}")
        except Exception as e:
            logger.error(f"Failed to get role distribution: {str(e)}")

        # Extract individual role counts
        total_buyers = role_counts['buyer']
        # Count builders from builder_profiles table instead of users table
        # This gives the actual number of builder profiles, not just builder user accounts
        try:
            result = db.execute(text("SELECT COUNT(*) as count FROM builder_profiles"))
            total_builders = result.fetchone().count
        except:
            # Fallback to user role count if builder_profiles table doesn't exist
            total_builders = role_counts['builder']
        total_sales_reps = role_counts['sales_rep']
        total_community_pocs = role_counts['community']
        total_community_admins = role_counts['community_admin']
        total_admins = role_counts['admin']

        # Verify that role counts add up to total users (accounting for NULL/empty roles)
        total_role_count = sum(role_counts.values())
        if total_role_count != total_users:
            logger.warning(f"Role count mismatch: {total_role_count} roles counted vs {total_users} total users. "
                          f"This indicates {total_users - total_role_count} users with NULL or empty roles.")

        # Get community count (handle if table doesn't exist)
        try:
            result = db.execute(text("SELECT COUNT(*) as count FROM communities"))
            total_communities = result.fetchone().count
        except:
            total_communities = 0

        # Get property count (handle if table doesn't exist)
        try:
            result = db.execute(text("SELECT COUNT(*) as count FROM property_listings"))
            total_properties = result.fetchone().count
        except:
            # Try alternative table name
            try:
                result = db.execute(text("SELECT COUNT(*) as count FROM properties"))
                total_properties = result.fetchone().count
            except:
                total_properties = 0

        # Get posts count (handle if table doesn't exist)
        try:
            result = db.execute(text("SELECT COUNT(*) as count FROM posts"))
            total_posts = result.fetchone().count or 0
        except:
            total_posts = 0

        # Get tours count (if table exists)
        try:
            result = db.execute(text("SELECT COUNT(*) as count FROM property_tours"))
            total_tours = result.fetchone().count or 0
        except:
            total_tours = 0

        # Get documents count (if table exists)
        try:
            result = db.execute(text("SELECT COUNT(*) as count FROM documents"))
            total_documents = result.fetchone().count or 0
        except:
            total_documents = 0

        totals = AdminStatsTotals(
            users=total_users,
            active_users=active_users,
            builders=total_builders,
            communities=total_communities,
            properties=total_properties,
            posts=total_posts,
            tours=total_tours,
            documents=total_documents,
            buyers=total_buyers,
            sales_reps=total_sales_reps,
            community_pocs=total_community_pocs,
            community_admins=total_community_admins,
            admins=total_admins
        )

        period = None
        if from_date and to_date:
            # Get period-based growth metrics (handle missing tables)
            try:
                result = db.execute(text("""
                    SELECT COUNT(*) as count FROM users
                    WHERE created_at >= :from_date AND created_at <= :to_date
                """), {"from_date": from_date, "to_date": to_date})
                new_users = result.fetchone().count
            except:
                new_users = 0

            # Count new builders from builder_profiles table
            try:
                result = db.execute(text("""
                    SELECT COUNT(*) as count FROM builder_profiles
                    WHERE created_at >= :from_date AND created_at <= :to_date
                """), {"from_date": from_date, "to_date": to_date})
                new_builders = result.fetchone().count
            except:
                # Fallback to counting from users table if builder_profiles doesn't exist
                try:
                    result = db.execute(text("""
                        SELECT COUNT(*) as count FROM users
                        WHERE role = 'builder'
                        AND created_at >= :from_date AND created_at <= :to_date
                    """), {"from_date": from_date, "to_date": to_date})
                    new_builders = result.fetchone().count
                except:
                    new_builders = 0

            try:
                result = db.execute(text("""
                    SELECT COUNT(*) as count FROM communities
                    WHERE created_at >= :from_date AND created_at <= :to_date
                """), {"from_date": from_date, "to_date": to_date})
                new_communities = result.fetchone().count
            except:
                new_communities = 0

            try:
                result = db.execute(text("""
                    SELECT COUNT(*) as count FROM property_listings
                    WHERE created_at >= :from_date AND created_at <= :to_date
                """), {"from_date": from_date, "to_date": to_date})
                new_properties = result.fetchone().count
            except:
                # Try alternative table name
                try:
                    result = db.execute(text("""
                        SELECT COUNT(*) as count FROM properties
                        WHERE created_at >= :from_date AND created_at <= :to_date
                    """), {"from_date": from_date, "to_date": to_date})
                    new_properties = result.fetchone().count
                except:
                    new_properties = 0

            period = AdminStatsPeriod(
                from_date=from_date,
                to_date=to_date,
                new_users=new_users,
                new_builders=new_builders,
                new_communities=new_communities,
                new_properties=new_properties
            )

        logger.info(
            "Retrieved admin stats: users=%d, builders=%d, communities=%d, properties=%d",
            total_users, total_builders, total_communities, total_properties
        )

        return AdminStatsOut(totals=totals, period=period)

    except Exception as e:
        logger.error("Failed to retrieve admin stats: %s", str(e), exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Error fetching admin statistics: {str(e)}"
        )


@router.get("/audit-logs", response_model=List[AdminAuditLogOut])
def get_audit_logs(
    from_date: Optional[datetime] = Query(None, alias="from", description="Start date filter"),
    to_date: Optional[datetime] = Query(None, alias="to", description="End date filter"),
    actor_user_id: Optional[int] = Query(None, description="Filter by actor user ID"),
    limit: int = Query(100, le=500, description="Maximum number of logs to return"),
    db: Session = Depends(get_db)
):
    """
    Get audit log entries for admin activity tracking.

    NOTE: This endpoint requires an audit_logs table to be created.
    The table should have the following structure:

    CREATE TABLE audit_logs (
        id INT AUTO_INCREMENT PRIMARY KEY,
        actor_user_id INT NOT NULL,
        action VARCHAR(255) NOT NULL,
        entity_type VARCHAR(100) NOT NULL,
        entity_id VARCHAR(255) NOT NULL,
        ip_address VARCHAR(45),
        user_agent TEXT,
        metadata JSON,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        INDEX idx_actor_user (actor_user_id),
        INDEX idx_created_at (created_at),
        INDEX idx_entity (entity_type, entity_id)
    );

    Example:
        GET /v1/admin/audit-logs
        GET /v1/admin/audit-logs?from=2025-10-18T00:00:00Z&to=2025-11-18T00:00:00Z
        GET /v1/admin/audit-logs?actor_user_id=1
    """
    try:
        # Build query dynamically based on filters
        query = """
            SELECT id, actor_user_id, action, entity_type, entity_id,
                   ip_address, user_agent, metadata, created_at
            FROM audit_logs
            WHERE 1=1
        """
        params = {}

        if from_date:
            query += " AND created_at >= :from_date"
            params["from_date"] = from_date

        if to_date:
            query += " AND created_at <= :to_date"
            params["to_date"] = to_date

        if actor_user_id:
            query += " AND actor_user_id = :actor_user_id"
            params["actor_user_id"] = actor_user_id

        query += " ORDER BY created_at DESC LIMIT :limit"
        params["limit"] = limit

        result = db.execute(text(query), params)
        logs = []

        for row in result.fetchall():
            logs.append(AdminAuditLogOut(
                id=row.id,
                actor_user_id=row.actor_user_id,
                action=row.action,
                entity_type=row.entity_type,
                entity_id=row.entity_id,
                ip_address=row.ip_address,
                user_agent=row.user_agent,
                metadata=row.metadata,
                created_at=row.created_at
            ))

        logger.info("Retrieved %d audit log entries", len(logs))
        return logs

    except Exception as e:
        # If table doesn't exist, return empty list
        if "doesn't exist" in str(e).lower() or "no such table" in str(e).lower():
            logger.warning("Audit logs table doesn't exist, returning empty list")
            return []

        logger.error("Failed to retrieve audit logs: %s", str(e), exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Error fetching audit logs: {str(e)}"
        )


@router.get("/growth", response_model=GrowthTimeSeriesOut)
def get_growth_data(
    from_date: Optional[datetime] = Query(None, alias="from", description="Start date for growth data"),
    to_date: Optional[datetime] = Query(None, description="End date for growth data"),
    interval: str = Query("day", description="Time interval: 'day', 'week', or 'month'"),
    db: Session = Depends(get_db)
):
    """
    Get time-series growth data for various metrics.

    Returns daily/weekly/monthly counts of new users, builders, communities, and properties
    over the specified time period. Used for rendering growth charts in the admin dashboard.

    Args:
        from_date: Start date (defaults to 30 days ago)
        to_date: End date (defaults to now)
        interval: Grouping interval - 'day', 'week', or 'month'

    Returns:
        GrowthTimeSeriesOut: Time series data with counts for each metric

    Example:
        GET /v1/admin/growth?from=2025-10-01T00:00:00Z&to=2025-11-18T00:00:00Z&interval=day
    """
    try:
        # Default date range: last 30 days
        if not to_date:
            to_date = datetime.utcnow()
        if not from_date:
            from_date = to_date - timedelta(days=30)

        # Determine MySQL date format based on interval
        if interval == "week":
            date_format = "%Y-%U"  # Year-Week
            date_trunc = "DATE_FORMAT(created_at, '%Y-%U')"
        elif interval == "month":
            date_format = "%Y-%m"  # Year-Month
            date_trunc = "DATE_FORMAT(created_at, '%Y-%m')"
        else:  # day
            date_format = "%Y-%m-%d"  # Year-Month-Day
            date_trunc = "DATE(created_at)"

        # Helper function to query growth data for a table
        def get_growth_series(table_name: str) -> List[GrowthDataPoint]:
            try:
                query = f"""
                    SELECT {date_trunc} as period, COUNT(*) as count
                    FROM {table_name}
                    WHERE created_at >= :from_date AND created_at <= :to_date
                    GROUP BY period
                    ORDER BY period ASC
                """
                result = db.execute(text(query), {"from_date": from_date, "to_date": to_date})

                data_points = []
                for row in result.fetchall():
                    # Convert period to datetime
                    # row.period might be a date object or a string depending on database
                    if isinstance(row.period, str):
                        if interval == "week":
                            # For week format, use the first day of that week
                            period_date = datetime.strptime(row.period + "-1", "%Y-%U-%w")
                        elif interval == "month":
                            # For month format, use the first day of that month
                            period_date = datetime.strptime(row.period + "-01", "%Y-%m-%d")
                        else:  # day
                            period_date = datetime.strptime(row.period, "%Y-%m-%d")
                    else:
                        # If it's already a date/datetime object, convert to datetime
                        from datetime import date
                        if isinstance(row.period, date):
                            period_date = datetime.combine(row.period, datetime.min.time())
                        else:
                            period_date = row.period

                    data_points.append(GrowthDataPoint(
                        date=period_date,
                        count=int(row.count)
                    ))

                return data_points
            except Exception as e:
                logger.warning(f"Failed to get growth data for {table_name}: {str(e)}")
                return []

        # Get growth data for each entity type
        users_growth = get_growth_series("users")
        builders_growth = get_growth_series("builder_profiles")
        communities_growth = get_growth_series("communities")

        # Try both property_listings and properties tables
        properties_growth = get_growth_series("property_listings")
        if not properties_growth:
            properties_growth = get_growth_series("properties")

        return GrowthTimeSeriesOut(
            users=users_growth,
            builders=builders_growth,
            communities=communities_growth,
            properties=properties_growth
        )

    except Exception as e:
        logger.error("Failed to retrieve growth data: %s", str(e), exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Error fetching growth data: {str(e)}"
        )


@router.get("/debug/users")
def debug_list_users(db: Session = Depends(get_db)):
    """Debug endpoint to list all users and their roles"""
    try:
        result = db.execute(text("""
            SELECT *
            FROM users
            ORDER BY id
        """))

        users = []
        for row in result.fetchall():
            # Convert row to dict with all columns
            user_dict = dict(row._mapping)
            # Convert datetime to string for JSON serialization
            for key, value in user_dict.items():
                if hasattr(value, 'isoformat'):
                    user_dict[key] = value.isoformat()
            users.append(user_dict)

        return {"users": users, "total_count": len(users)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# =============================================================================
# INVITATION MANAGEMENT ENDPOINTS (Admin)
# =============================================================================

@router.get("/invitations", response_model=InvitationListOut)
def list_invitations(
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(50, ge=1, le=200, description="Items per page"),
    status: Optional[str] = Query(None, description="Filter by status (pending, used, expired, revoked)"),
    builder_id: Optional[str] = Query(None, description="Filter by builder ID"),
    email: Optional[str] = Query(None, description="Filter by invited email"),
    db: Session = Depends(get_db),
    current_user: Users = Depends(require_user)
):
    """
    List all enterprise invitations with filtering and pagination.

    **Requires admin role**

    Features:
    - Pagination support
    - Filter by status, builder_id, or email
    - Includes builder name and usage information
    - Shows total count and page metadata

    Example:
        GET /v1/admin/invitations?page=1&page_size=50&status=pending
        GET /v1/admin/invitations?builder_id=BLD-PERRYHOMES-1234
        GET /v1/admin/invitations?email=john@example.com
    """
    # Authorization check: Only admins can list all invitations
    if current_user.role != "admin":
        logger.warning(
            "Non-admin user %s attempted to list invitations",
            current_user.user_id
        )
        raise HTTPException(
            status_code=403,
            detail="Only administrators can list all invitations"
        )

    try:
        # Build base query with builder name join
        query = db.query(
            EnterpriseInvitation,
            BuilderProfile.name.label("builder_name")
        ).outerjoin(
            BuilderProfile,
            BuilderProfile.builder_id == EnterpriseInvitation.builder_id
        )

        # Apply filters
        if status:
            query = query.filter(EnterpriseInvitation.status == status)
        if builder_id:
            query = query.filter(EnterpriseInvitation.builder_id == builder_id)
        if email:
            query = query.filter(EnterpriseInvitation.invited_email.like(f"%{email}%"))

        # Get total count
        total = query.count()

        # Apply pagination
        offset = (page - 1) * page_size
        query = query.order_by(EnterpriseInvitation.created_at.desc())
        query = query.offset(offset).limit(page_size)

        # Execute query
        results = query.all()

        # Build response
        invitations = []
        for invitation, builder_name in results:
            invitations.append(InvitationDetailedOut(
                invitation_code=invitation.invitation_code,
                builder_id=invitation.builder_id,
                builder_name=builder_name,
                invited_email=invitation.invited_email,
                invited_role=invitation.invited_role,
                invited_first_name=invitation.invited_first_name,
                invited_last_name=invitation.invited_last_name,
                expires_at=invitation.expires_at,
                status=invitation.status,
                custom_message=invitation.custom_message,
                created_at=invitation.created_at,
                created_by_user_id=invitation.created_by_user_id,
                used_at=invitation.used_at,
                used_by_user_id=invitation.used_by_user_id
            ))

        total_pages = (total + page_size - 1) // page_size

        logger.info(
            "Listed %d invitations (page %d/%d) for admin user %s",
            len(invitations), page, total_pages, current_user.user_id
        )

        return InvitationListOut(
            invitations=invitations,
            total=total,
            page=page,
            page_size=page_size,
            total_pages=total_pages
        )

    except Exception as e:
        logger.error("Failed to list invitations: %s", str(e), exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to list invitations: {str(e)}"
        )


@router.get("/invitations/{invitation_code}", response_model=InvitationDetailedOut)
def get_invitation(
    invitation_code: str,
    db: Session = Depends(get_db),
    current_user: Users = Depends(require_user)
):
    """
    Get detailed information about a specific invitation.

    **Requires admin role**

    Returns:
    - Full invitation details
    - Builder information
    - Usage and expiration status
    """
    # Authorization check
    if current_user.role != "admin":
        raise HTTPException(
            status_code=403,
            detail="Only administrators can view invitation details"
        )

    try:
        # Query invitation with builder name
        result = db.query(
            EnterpriseInvitation,
            BuilderProfile.name.label("builder_name")
        ).outerjoin(
            BuilderProfile,
            BuilderProfile.builder_id == EnterpriseInvitation.builder_id
        ).filter(
            EnterpriseInvitation.invitation_code == invitation_code
        ).first()

        if not result:
            raise HTTPException(
                status_code=404,
                detail="Invitation not found"
            )

        invitation, builder_name = result

        return InvitationDetailedOut(
            invitation_code=invitation.invitation_code,
            builder_id=invitation.builder_id,
            builder_name=builder_name,
            invited_email=invitation.invited_email,
            invited_role=invitation.invited_role,
            invited_first_name=invitation.invited_first_name,
            invited_last_name=invitation.invited_last_name,
            expires_at=invitation.expires_at,
            status=invitation.status,
            custom_message=invitation.custom_message,
            created_at=invitation.created_at,
            created_by_user_id=invitation.created_by_user_id,
            used_at=invitation.used_at,
            used_by_user_id=invitation.used_by_user_id
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to get invitation: %s", str(e), exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get invitation: {str(e)}"
        )


@router.post("/invitations/{invitation_code}/revoke")
def revoke_invitation(
    invitation_code: str,
    db: Session = Depends(get_db),
    current_user: Users = Depends(require_user)
):
    """
    Revoke an invitation, preventing it from being used.

    **Requires admin role**

    Use cases:
    - Cancel invitation sent to wrong email
    - Revoke access before invitation is accepted
    - Administrative cleanup of pending invitations
    """
    # Authorization check
    if current_user.role != "admin":
        raise HTTPException(
            status_code=403,
            detail="Only administrators can revoke invitations"
        )

    try:
        # Find invitation
        invitation = db.query(EnterpriseInvitation).filter(
            EnterpriseInvitation.invitation_code == invitation_code
        ).first()

        if not invitation:
            raise HTTPException(
                status_code=404,
                detail="Invitation not found"
            )

        # Check if already used or revoked
        if invitation.status == "used":
            raise HTTPException(
                status_code=400,
                detail="Cannot revoke an invitation that has already been used"
            )

        if invitation.status == "revoked":
            return {
                "message": "Invitation is already revoked",
                "invitation_code": invitation_code,
                "status": "revoked"
            }

        # Revoke invitation
        invitation.status = "revoked"
        db.commit()

        logger.info(
            "Invitation revoked: code=%s, builder_id=%s, admin=%s",
            invitation_code,
            invitation.builder_id,
            current_user.user_id
        )

        return {
            "message": "Invitation revoked successfully",
            "invitation_code": invitation_code,
            "status": "revoked"
        }

    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error("Failed to revoke invitation: %s", str(e), exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to revoke invitation: {str(e)}"
        )


@router.post("/invitations/{invitation_code}/resend")
def resend_invitation(
    invitation_code: str,
    extend_days: int = Query(7, ge=1, le=90, description="Days to extend expiration"),
    db: Session = Depends(get_db),
    current_user: Users = Depends(require_user)
):
    """
    Resend/extend an invitation by extending its expiration date.

    **Requires admin role**

    Use cases:
    - Invitation expired before user could accept
    - User needs more time to accept
    - Administrative grace period extension

    Parameters:
    - extend_days: Number of days to extend from now (default: 7, max: 90)
    """
    # Authorization check
    if current_user.role != "admin":
        raise HTTPException(
            status_code=403,
            detail="Only administrators can resend invitations"
        )

    try:
        # Find invitation
        invitation = db.query(EnterpriseInvitation).filter(
            EnterpriseInvitation.invitation_code == invitation_code
        ).first()

        if not invitation:
            raise HTTPException(
                status_code=404,
                detail="Invitation not found"
            )

        # Check if already used or revoked
        if invitation.status == "used":
            raise HTTPException(
                status_code=400,
                detail="Cannot resend an invitation that has already been used"
            )

        if invitation.status == "revoked":
            raise HTTPException(
                status_code=400,
                detail="Cannot resend a revoked invitation. Create a new invitation instead."
            )

        # Extend expiration and reset status to pending
        old_expires_at = invitation.expires_at
        invitation.expires_at = datetime.utcnow() + timedelta(days=extend_days)
        invitation.status = "pending"
        db.commit()

        logger.info(
            "Invitation resent: code=%s, old_expiry=%s, new_expiry=%s, admin=%s",
            invitation_code,
            old_expires_at.strftime("%Y-%m-%d"),
            invitation.expires_at.strftime("%Y-%m-%d"),
            current_user.user_id
        )

        return {
            "message": "Invitation expiration extended successfully",
            "invitation_code": invitation_code,
            "status": "pending",
            "expires_at": invitation.expires_at,
            "extended_days": extend_days
        }

    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error("Failed to resend invitation: %s", str(e), exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to resend invitation: {str(e)}"
        )


# =============================================================================
# Admin User Management
# =============================================================================

@router.get("/users", response_model=list[AdminUserOut])
def list_users(
    db: Session = Depends(get_db),
    current_user: Users = Depends(require_user)
):
    """
    List all users with their roles (admin only).

    Returns user details including:
    - Basic info (id, email, display_name)
    - Role information
    - Account status (is_active)
    - Last login timestamp
    - Creation and update timestamps
    """
    # Verify admin role
    if current_user.role != "admin":
        raise HTTPException(
            status_code=403,
            detail="Only administrators can list users"
        )

    try:
        # Query all users
        users = db.query(Users).all()

        # Convert to AdminUserOut format
        result = []
        for user in users:
            # Get the most recent session for last_login_at
            last_session = db.query(SessionToken)\
                .filter(SessionToken.user_id == user.id)\
                .order_by(SessionToken.created_at.desc())\
                .first()

            # Convert single role string to list with one AdminRoleOut
            role_obj = AdminRoleOut(
                id=0,  # Not using role ID since role is a string
                name=user.role_display_name
            )

            # Create AdminUserOut object
            admin_user = AdminUserOut(
                id=user.id,
                email=user.email,
                display_name=f"{user.first_name} {user.last_name}" if user.first_name and user.last_name else None,
                is_active=(user.status == "active"),
                roles=[role_obj],
                last_login_at=last_session.created_at if last_session else None,
                created_at=user.created_at,
                updated_at=user.updated_at
            )
            result.append(admin_user)

        logger.info(f"Admin {current_user.user_id} listed {len(result)} users")
        return result

    except Exception as e:
        logger.error("Failed to list users: %s", str(e), exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to list users: {str(e)}"
        )
