# routes/admin/users.py
"""
Enterprise builder provisioning and user management endpoints.
Admin-initiated enterprise builder account creation and user listings.
"""
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import text
import logging

from config.db import get_db
from config.dependencies import require_user
from model.user import Users, SessionToken
from model.profiles.builder import BuilderProfile
from model.enterprise import EnterpriseInvitation, _gen_invitation_code
from src.schemas import (
    EnterpriseBuilderProvisionIn,
    EnterpriseBuilderProvisionOut,
    BuilderProfileOut,
    UserOut,
    RoleOut,
    InvitationOut,
    AdminUserOut,
    AdminRoleOut,
)
from src.id_generator import generate_user_id, generate_builder_id

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
