# routes/enterprise.py
"""
Enterprise builder provisioning and team management endpoints.
Admin-initiated enterprise builder account creation for companies like Perry Homes.
"""
from datetime import datetime, timedelta
from typing import List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
import logging

from config.db import get_db
from config.dependencies import require_user
from model.user import Users
from model.profiles.builder import BuilderProfile
from model.enterprise import EnterpriseInvitation, BuilderTeamMember, _gen_invitation_code
from src.schemas import (
    EnterpriseBuilderProvisionIn,
    EnterpriseBuilderProvisionOut,
    InvitationValidateOut,
    InvitationAcceptIn,
    InvitationOut,
    BuilderProfileOut,
    UserOut,
    RoleOut,
    TeamMemberOut,
    TeamMemberCreateIn,
    TeamMemberUpdateIn,
    CommunityOut,
    BuilderCommunityListOut,
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
