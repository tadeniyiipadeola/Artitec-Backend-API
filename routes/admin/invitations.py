# routes/admin/invitations.py
"""
Enterprise invitation management endpoints.
All invitation-related functionality for enterprise builder provisioning.
"""
from datetime import datetime, timedelta
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
import logging

from config.db import get_db
from config.dependencies import require_user
from model.user import Users
from model.profiles.builder import BuilderProfile
from model.enterprise import EnterpriseInvitation, BuilderTeamMember, _gen_invitation_code
from src.schemas import (
    InvitationValidateOut,
    InvitationAcceptIn,
    InvitationOut,
    InvitationDetailedOut,
    InvitationListOut,
)

logger = logging.getLogger(__name__)

router = APIRouter()


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
