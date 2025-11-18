# model/enterprise.py
"""
Enterprise-specific models for:
- Enterprise builder account provisioning
- Invitation system for team members
- Builder team member management

Used for Phase 1 of enterprise builder onboarding (Perry Homes, etc.)
"""

from sqlalchemy import (
    Column, String, BigInteger, TIMESTAMP, ForeignKey, Text, JSON,
    Enum as SAEnum, Index
)
from sqlalchemy.dialects.mysql import BIGINT as MyBIGINT
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import secrets
from datetime import datetime, timedelta
from model.base import Base


# Helper to generate secure invitation codes
def _gen_invitation_code() -> str:
    """Generate secure 12-character invitation code (alphanumeric, uppercase)"""
    return secrets.token_urlsafe(9).replace('-', '').replace('_', '').upper()[:12]


# --- Enterprise Invitations ---------------------------------------------------
class EnterpriseInvitation(Base):
    """
    Tracks enterprise builder invitations for team members (sales reps, admins, etc.)

    Flow:
    1. Admin creates enterprise builder account → invitation created
    2. Invitation link/code sent to primary contact
    3. Contact registers/accepts → invitation marked as 'used'
    4. Can invite additional team members later
    """
    __tablename__ = "enterprise_invitations"

    id = Column(MyBIGINT(unsigned=True), primary_key=True, autoincrement=True)

    # Unique invitation code (e.g., "X3P8Q1R9T2M4")
    invitation_code = Column(String(64), unique=True, nullable=False, index=True)

    # Builder this invitation is for
    builder_id = Column(
        String(50),
        ForeignKey("builder_profiles.builder_id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )

    # Invited user details (before they register)
    invited_email = Column(String(255), nullable=False, index=True)
    invited_role = Column(
        SAEnum("builder", "salesrep", "manager", "viewer", name="invited_role_enum"),
        nullable=False,
        server_default="builder"
    )
    invited_first_name = Column(String(120))
    invited_last_name = Column(String(120))

    # Who created this invitation (admin or builder admin)
    created_by_user_id = Column(
        String(50),
        ForeignKey("users.user_id", ondelete="SET NULL"),
        nullable=True
    )

    # Expiration and usage tracking
    expires_at = Column(TIMESTAMP, nullable=False)  # Default: 7 days from creation
    used_at = Column(TIMESTAMP, nullable=True)
    used_by_user_id = Column(
        String(50),
        ForeignKey("users.user_id", ondelete="SET NULL"),
        nullable=True
    )

    # Status tracking
    status = Column(
        SAEnum("pending", "used", "expired", "revoked", name="invitation_status_enum"),
        nullable=False,
        server_default="pending",
        index=True
    )

    # Optional custom message
    custom_message = Column(Text)

    # Metadata
    created_at = Column(TIMESTAMP, server_default=func.current_timestamp(), nullable=False)
    updated_at = Column(
        TIMESTAMP,
        server_default=func.current_timestamp(),
        onupdate=func.current_timestamp(),
        nullable=False
    )

    __table_args__ = (
        Index("ix_enterprise_invitations_builder_status", "builder_id", "status"),
        Index("ix_enterprise_invitations_email", "invited_email"),
    )

    # Relationships
    builder = relationship("BuilderProfile", foreign_keys=[builder_id])
    created_by = relationship("Users", foreign_keys=[created_by_user_id])
    used_by = relationship("Users", foreign_keys=[used_by_user_id])

    def is_valid(self) -> bool:
        """Check if invitation is still valid"""
        return (
            self.status == "pending" and
            self.expires_at > datetime.utcnow() and
            self.used_at is None
        )

    def mark_used(self, user_id: str) -> None:
        """Mark invitation as used"""
        self.status = "used"
        self.used_at = func.current_timestamp()
        self.used_by_user_id = user_id


# --- Builder Team Members -----------------------------------------------------
class BuilderTeamMember(Base):
    """
    Tracks team members (users) associated with a builder profile.

    Enables:
    - Multi-user access for enterprise builder accounts
    - Role-based permissions (admin, sales_rep, manager, viewer)
    - Community/property assignment for sales reps
    - Audit trail of who added whom

    Example:
    - Perry Homes (builder_id) has:
      - John Smith (admin) - full access
      - Jane Doe (sales_rep) - assigned to "Oak Forest" and "Cedar Park" communities
      - Bob Johnson (manager) - can manage properties and invite reps
    """
    __tablename__ = "builder_team_members"

    id = Column(MyBIGINT(unsigned=True), primary_key=True, autoincrement=True)

    # Builder this team member belongs to
    builder_id = Column(
        String(50),
        ForeignKey("builder_profiles.builder_id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )

    # User account for this team member
    user_id = Column(
        String(50),
        ForeignKey("users.user_id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )

    # Role within the builder organization
    role = Column(
        SAEnum("admin", "sales_rep", "manager", "viewer", name="builder_team_role_enum"),
        nullable=False,
        server_default="sales_rep"
    )

    # Permissions (JSON array of permission keys)
    # Examples:
    # - ["manage_properties", "invite_reps", "view_analytics"]
    # - ["create_listings", "edit_listings"]
    # - ["view_only"]
    permissions = Column(JSON)  # ["manage_properties", "invite_reps", "view_analytics"]

    # Community assignments (for sales reps)
    # Array of community IDs this team member can access
    # Examples: ["CMY-ABC123", "CMY-XYZ789"]
    # If null/empty: access to all communities
    communities_assigned = Column(JSON)  # ["community_id1", "community_id2"]

    # Who added this team member
    added_by_user_id = Column(
        String(50),
        ForeignKey("users.user_id", ondelete="SET NULL"),
        nullable=True
    )

    # Status
    is_active = Column(SAEnum("active", "inactive", name="team_member_status"), server_default="active")

    # Metadata
    created_at = Column(TIMESTAMP, server_default=func.current_timestamp(), nullable=False)
    updated_at = Column(
        TIMESTAMP,
        server_default=func.current_timestamp(),
        onupdate=func.current_timestamp(),
        nullable=False
    )

    __table_args__ = (
        # Unique constraint: one user can only be on a builder's team once
        Index("uq_builder_team_member", "builder_id", "user_id", unique=True),
        Index("ix_builder_team_members_role", "role"),
    )

    # Relationships
    builder = relationship("BuilderProfile", foreign_keys=[builder_id])
    user = relationship("Users", foreign_keys=[user_id])
    added_by = relationship("Users", foreign_keys=[added_by_user_id])

    @property
    def has_full_access(self) -> bool:
        """Check if team member has admin/full access"""
        return self.role == "admin"

    @property
    def can_invite_members(self) -> bool:
        """Check if can invite new team members"""
        return self.role in ("admin", "manager") or (
            self.permissions and "invite_members" in self.permissions
        )
